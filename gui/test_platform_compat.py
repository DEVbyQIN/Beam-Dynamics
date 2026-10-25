"""Cross-platform GUI contracts: POSIX behaviour, simulated Windows branches,
UTF-8 I/O and Chinese/space paths.

The Windows branches are exercised on macOS by forcing the ``windows``
override and by patching the two OS-specific seams (``_taskkill`` and
``_signal_group``); no Windows host is required and nothing here claims a
native Windows run.  The native checks live in gui/test_windows_native.py.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main, skipIf
from unittest.mock import patch
import json, os, signal, subprocess, sys, threading, time

from gui import platform_compat as compat
from gui.server import Jobs
from shared.params import load_config

ROOT = Path(__file__).resolve().parents[1]
POSIX_ONLY = skipIf(compat.IS_WINDOWS, 'POSIX-only behaviour')


class FakeProc:
    """Minimal Popen stand-in for the branches we cannot run natively."""

    def __init__(self, pid=4321, ignore_terminate=False):
        self.pid = pid
        self.returncode = None
        self.terminated = 0
        self.killed = 0
        self.ignore_terminate = ignore_terminate
        self._stop = threading.Event()

    def terminate(self):
        self.terminated += 1
        if self.ignore_terminate:
            return
        self.returncode = 1
        self._stop.set()

    def kill(self):
        self.killed += 1
        self.returncode = -9
        self._stop.set()

    def wait(self, timeout=None):
        if self.returncode is not None:
            return self.returncode
        if self._stop.wait(timeout):
            return self.returncode
        raise subprocess.TimeoutExpired('fake-worker', timeout)

    def alive(self):
        return self.returncode is None


class LaunchScripts(TestCase):
    """Static contracts for the Windows entry points shipped in the repo root."""

    def bat(self, name):
        path = ROOT / name
        self.assertTrue(path.is_file(), f'{name} missing')
        return path, path.read_bytes()

    def test_batch_files_are_crlf_ascii(self):
        for name in ('启动界面.bat', '安装环境.bat', '运行GUI测试.bat'):
            with self.subTest(name=name):
                _, raw = self.bat(name)
                self.assertIn(b'\r\n', raw)
                self.assertEqual(raw.replace(b'\r\n', b''), raw.replace(b'\r\n', b'').replace(b'\n', b''),
                                 'batch file contains a bare LF')
                # ASCII-only keeps cmd.exe parsing independent of the OEM code page.
                self.assertTrue(all(byte < 128 for byte in raw), 'batch file must stay ASCII')

    def test_launcher_guards(self):
        _, raw = self.bat('启动界面.bat')
        text = raw.decode('ascii')
        for needle in ('chcp 65001', 'PYTHONUTF8=1', 'PYTHONIOENCODING=utf-8',
                       'cd /d "%~dp0"', '.venv\\Scripts\\python.exe', 'run_gui.py --open',
                       'sys.version_info >= (3, 10)', 'import ocelot'):
            self.assertIn(needle, text)

    def test_installer_pins_and_venv(self):
        _, raw = self.bat('安装环境.bat')
        text = raw.decode('ascii')
        for needle in ('requirements-gui.txt', '-m venv', 'pip install',
                       'sys.version_info[:2]==(3,12)', 'py -3.12'):
            self.assertIn(needle, text)

    def test_posix_only_calls_are_isolated(self):
        for name in ('server.py', 'worker.py'):
            text = (ROOT / 'gui' / name).read_text(encoding='utf-8')
            for forbidden in ('os.killpg(', 'os.getppid(', 'start_new_session='):
                self.assertNotIn(forbidden, text, f'gui/{name} must not call {forbidden} directly')

    def test_macos_launcher_unchanged(self):
        text = (ROOT / '启动界面.command').read_text(encoding='utf-8')
        self.assertIn('#!/bin/zsh', text)
        self.assertIn('run_gui.py --open', text)


class SpawnKwargs(TestCase):
    def test_posix_uses_session_leader(self):
        self.assertEqual(compat.spawn_kwargs(windows=False), {'start_new_session': True})

    def test_windows_uses_process_group_only(self):
        kwargs = compat.spawn_kwargs(windows=True)
        self.assertEqual(kwargs, {'creationflags': 0x00000200})
        self.assertNotIn('start_new_session', kwargs)


class StopPaths(TestCase):
    def test_windows_request_stop_uses_handle_never_killpg_or_os_kill(self):
        proc = FakeProc()

        def forbidden(*_a, **_k):
            raise AssertionError('POSIX signalling must not run on Windows')

        with patch('gui.platform_compat.os.killpg', side_effect=forbidden), \
                patch('gui.platform_compat.os.kill', side_effect=forbidden), \
                patch('gui.platform_compat.os.getpgid', side_effect=forbidden):
            self.assertTrue(compat.request_stop(proc, windows=True))
        self.assertEqual(proc.terminated, 1)

    def test_windows_force_stop_prefers_taskkill_tree(self):
        proc = FakeProc()
        calls = []

        def taskkill(pid, force=True):
            calls.append((pid, force))
            proc.returncode = -9
            return True

        with patch('gui.platform_compat._taskkill', side_effect=taskkill):
            self.assertTrue(compat.force_stop(proc, windows=True))
        self.assertEqual(calls, [(4321, True)])
        self.assertEqual(proc.killed, 0)

    def test_windows_force_stop_falls_back_to_process_handle(self):
        proc = FakeProc()
        with patch('gui.platform_compat._taskkill', return_value=False):
            self.assertTrue(compat.force_stop(proc, windows=True))
        self.assertEqual(proc.killed, 1)

    def test_taskkill_argv_is_a_list_not_a_shell_string(self):
        seen = {}

        class Result:
            returncode = 0

        with patch('gui.platform_compat.subprocess.run', side_effect=lambda args, **kw: seen.update(args=args, kw=kw) or Result()):
            self.assertTrue(compat._taskkill(1234, force=True))
        self.assertEqual(seen['args'], ['taskkill', '/PID', '1234', '/T', '/F'])
        self.assertIn('timeout', seen['kw'])

    def test_windows_terminate_tree_escalates_after_grace(self):
        proc = FakeProc(ignore_terminate=True)   # terminate() alone does not stop it
        with patch('gui.platform_compat._taskkill', return_value=False):
            code = compat.terminate_tree(proc, grace=0.01, windows=True)
        self.assertEqual(proc.terminated, 1)
        self.assertEqual(proc.killed, 1)
        self.assertEqual(code, -9)

    @POSIX_ONLY
    def test_posix_request_stop_signals_the_group_with_sigterm(self):
        proc = FakeProc()
        with patch('gui.platform_compat.os.getpgid', return_value=777), \
                patch('gui.platform_compat.os.killpg') as killpg:
            self.assertTrue(compat.request_stop(proc, windows=False))
        killpg.assert_called_once_with(777, signal.SIGTERM)

    @POSIX_ONLY
    def test_posix_force_stop_signals_the_group_with_sigkill(self):
        proc = FakeProc()
        with patch('gui.platform_compat.os.getpgid', return_value=777), \
                patch('gui.platform_compat.os.killpg') as killpg:
            self.assertTrue(compat.force_stop(proc, windows=False))
        killpg.assert_called_once_with(777, signal.SIGKILL)

    @POSIX_ONLY
    def test_posix_real_child_is_stopped(self):
        proc = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'],
                                **compat.spawn_kwargs(windows=False))
        try:
            time.sleep(0.2)
            self.assertEqual(os.getpgid(proc.pid), proc.pid, 'child must lead its own session')
            self.assertTrue(compat.process_alive(proc.pid))
            self.assertTrue(compat.request_stop(proc, windows=False))
            self.assertIsNotNone(compat._wait_quietly(proc, 5))
            self.assertFalse(compat.process_alive(proc.pid))
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()


class Liveness(TestCase):
    @POSIX_ONLY
    def test_posix_parent_alive_uses_real_parent(self):
        self.assertTrue(compat.parent_alive(os.getppid(), windows=False))
        self.assertFalse(compat.parent_alive(os.getpid(), windows=False))

    @POSIX_ONLY
    def test_posix_process_alive_tracks_a_real_child(self):
        proc = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
        try:
            time.sleep(0.1)
            self.assertTrue(compat.process_alive(proc.pid))
            proc.kill()
            proc.wait()
            time.sleep(0.05)
            self.assertFalse(compat.process_alive(proc.pid))
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()

    def test_windows_parent_probe_uses_handle_and_not_getppid(self):
        def forbidden():
            raise AssertionError('os.getppid() is stale on Windows')

        with patch('gui.platform_compat._windows_process_alive', return_value=True) as probe, \
                patch('gui.platform_compat.os.getppid', side_effect=forbidden):
            self.assertTrue(compat.parent_alive(1234, windows=True))
        probe.assert_called_once_with(1234)

    def test_invalid_pids_are_not_alive(self):
        for bad in (0, -1, 'x', None):
            with self.subTest(pid=bad):
                self.assertFalse(compat.parent_alive(0 if bad is None else bad, windows=True))
                self.assertFalse(compat.process_alive(0 if bad is None else bad, windows=True))


class Utf8Io(TestCase):
    def test_json_roundtrip_keeps_chinese_as_utf8_bytes(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / '进度.json'
            compat.write_json(path, {'阶段': 'AG 正在积分', 's_m': 1.5})
            raw = path.read_bytes()
            self.assertIn('AG 正在积分'.encode('utf-8'), raw)
            self.assertNotIn(b'\\u', raw)          # ensure_ascii=False
            self.assertEqual(compat.read_json(path)['阶段'], 'AG 正在积分')

    def test_read_text_ignores_a_non_utf8_locale(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / '中文 配置.yaml'
            path.write_bytes('名称: 束流\n'.encode('utf-8'))
            self.assertEqual(compat.read_text(path), '名称: 束流\n')

    def test_atomic_write_retries_while_target_is_busy(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'job.json'
            real_replace = Path.replace
            calls = {'n': 0}

            def flaky_replace(self, target):
                calls['n'] += 1
                if calls['n'] == 1:
                    raise PermissionError('transient sharing violation')
                return real_replace(self, target)

            with patch.object(Path, 'replace', flaky_replace):
                compat.write_json(path, {'状态': 'running'})
            self.assertEqual(calls['n'], 2)
            self.assertEqual(compat.read_json(path), {'状态': 'running'})

    def test_log_sink_is_binary_utf8(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / '运行 日志.log'
            with compat.open_log(path) as handle:
                handle.write('AG 正在积分\n'.encode('utf-8'))
            self.assertEqual(path.read_bytes(), 'AG 正在积分\n'.encode('utf-8'))

    def test_worker_env_forces_utf8_and_headless_backends(self):
        env = compat.worker_env('/tmp/ignored-cache')
        self.assertEqual(env['PYTHONUTF8'], '1')
        self.assertEqual(env['PYTHONIOENCODING'], 'utf-8')
        self.assertEqual(env['PYTHONDONTWRITEBYTECODE'], '1')
        self.assertEqual(env['MPLBACKEND'], 'Agg')
        self.assertTrue(env['MPLCONFIGDIR'].endswith('mpl'))
        self.assertTrue(env['NUMBA_CACHE_DIR'].endswith('numba'))

    def test_worker_env_does_not_mutate_the_parent_environment(self):
        before = dict(os.environ)
        compat.worker_env('/tmp/ignored-cache')
        self.assertEqual({k: v for k, v in os.environ.items() if k in before}, before)


class ChineseSpacePaths(TestCase):
    def wait_terminal(self, jobs, timeout=10):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            snapshot = jobs.snapshot()
            if snapshot and snapshot[0]['status'] in ('failed', 'timeout', 'cancelled', 'complete', 'interrupted'):
                return snapshot[0]
            time.sleep(0.02)
        self.fail('job did not reach a terminal status')

    def test_runs_data_dir_with_chinese_and_spaces(self):
        with TemporaryDirectory() as tmp:
            data = Path(tmp) / '中文 目录' / '运行 记录'
            data.mkdir(parents=True)
            real_popen = subprocess.Popen

            def spawn(args, **kwargs):
                return real_popen([sys.executable, '-c', 'import sys; sys.exit(7)'], **kwargs)

            with patch('gui.server.subprocess.Popen', side_effect=spawn):
                jobs = Jobs(data, timeout=5)
                try:
                    job = jobs.submit(load_config(), ['AG'])[0]
                    job_dir = data / job['id']
                    end = self.wait_terminal(jobs)
                    self.assertEqual(end['status'], 'failed')
                    self.assertEqual(end['exit_code'], 7)
                    self.assertTrue((job_dir / 'config.json').is_file())
                    self.assertTrue((job_dir / 'config.yaml').is_file())
                    self.assertTrue((job_dir / 'run.log').is_file())
                    self.assertEqual(compat.read_json(job_dir / 'config.json')['beam']['energy_keV'], 100.0)
                finally:
                    jobs.shutdown()

    def test_yaml_snapshot_roundtrips_chinese_names(self):
        with TemporaryDirectory() as tmp:
            data = Path(tmp) / '路径 带空格'
            data.mkdir()
            real_popen = subprocess.Popen

            def spawn(args, **kwargs):
                return real_popen([sys.executable, '-c', 'import sys; sys.exit(7)'], **kwargs)

            with patch('gui.server.subprocess.Popen', side_effect=spawn):
                jobs = Jobs(data, timeout=5)
                try:
                    cfg = load_config()
                    cfg['lattice']['elements'][0]['name'] = '阴极 面'
                    job = jobs.submit(cfg, ['AG'])[0]
                    text = (data / job['id'] / 'config.yaml').read_text(encoding='utf-8')
                    self.assertIn('阴极 面', text)
                finally:
                    jobs.shutdown()


class WindowsServerPath(TestCase):
    """The server queue must use the Windows branches when forced on."""

    def wait_status(self, jobs, statuses, timeout=10):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            snapshot = jobs.snapshot()
            if snapshot and snapshot[0]['status'] in statuses:
                return snapshot[0]
            time.sleep(0.02)
        self.fail(f'job never reached {statuses}')

    def test_cancel_uses_windows_handle_and_skips_killpg(self):
        def forbidden(*_a, **_k):
            raise AssertionError('killpg must never run on the Windows branch')

        proc = FakeProc()
        with TemporaryDirectory() as tmp, \
                patch('gui.platform_compat.IS_WINDOWS', True), \
                patch('gui.platform_compat.os.killpg', side_effect=forbidden), \
                patch('gui.server.subprocess.Popen', return_value=proc) as popen:
            jobs = Jobs(tmp, timeout=30)
            try:
                job = jobs.submit(load_config(), ['AG'])[0]
                started = self.wait_status(jobs, ('running',), timeout=5)
                self.assertEqual(started['worker_pid'], proc.pid)
                self.assertEqual(popen.call_args.kwargs.get('creationflags'), 0x00000200)
                self.assertNotIn('start_new_session', popen.call_args.kwargs)
                jobs.cancel([job['id']])
                end = self.wait_status(jobs, ('cancelled', 'failed', 'timeout'))
                self.assertEqual(end['status'], 'cancelled')
                self.assertEqual(proc.terminated, 1)
            finally:
                jobs.shutdown()

    def test_timeout_uses_forced_windows_stop(self):
        proc = FakeProc()

        def fake_taskkill(pid, force=True):
            proc.returncode = -9
            return True

        with TemporaryDirectory() as tmp, \
                patch('gui.platform_compat.IS_WINDOWS', True), \
                patch('gui.platform_compat._taskkill', side_effect=fake_taskkill) as taskkill, \
                patch('gui.server.subprocess.Popen', return_value=proc):
            jobs = Jobs(tmp, timeout=0.2)
            try:
                jobs.submit(load_config(), ['AG'])
                end = self.wait_status(jobs, ('timeout', 'failed'))
                self.assertEqual(end['status'], 'timeout')
                self.assertTrue(taskkill.called)
                self.assertFalse((Path(tmp) / end['id'] / 'result.json').exists())
            finally:
                jobs.shutdown()


if __name__ == '__main__':
    main()

"""Windows-native checks: only run on a real Windows host.

Every test here is skipped on macOS/Linux.  This file is the part of the
deliverable that must be run on an actual Windows machine (or Windows CI);
the macOS-side suite only simulates the Windows branches, see
gui/test_platform_compat.py.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main, skipUnless
import json, os, subprocess, sys, time

from gui import platform_compat as compat
from gui.server import Jobs
from shared.params import load_config

WINDOWS = skipUnless(compat.IS_WINDOWS, 'requires a real Windows host')


@WINDOWS
class WindowsNative(TestCase):
    def test_killpg_does_not_exist(self):
        self.assertFalse(hasattr(os, 'killpg'), 'os.killpg is POSIX-only')

    def test_spawn_kwargs_use_process_group(self):
        self.assertEqual(compat.spawn_kwargs(), {'creationflags': 0x00000200})

    def test_real_child_stop_uses_handles(self):
        proc = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'],
                                **compat.spawn_kwargs())
        try:
            time.sleep(0.4)
            self.assertTrue(compat.process_alive(proc.pid))
            self.assertTrue(compat.request_stop(proc))
            self.assertIsNotNone(compat._wait_quietly(proc, 10))
            time.sleep(0.2)
            self.assertFalse(compat.process_alive(proc.pid))
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()

    def test_parent_liveness_detects_an_exited_process(self):
        proc = subprocess.Popen([sys.executable, '-c', 'pass'])
        proc.wait()
        self.assertFalse(compat.parent_alive(proc.pid))
        self.assertTrue(compat.parent_alive(os.getpid()))

    def test_cancel_and_shutdown_in_chinese_space_path(self):
        with TemporaryDirectory() as tmp:
            data = Path(tmp) / '中文 目录' / '运行 记录'
            jobs = Jobs(data, timeout=60)
            try:
                cfg = load_config()
                cfg['space_charge']['enabled'] = True
                cfg['output']['step_size_m'] = 0.0005
                job = jobs.submit(cfg, ['AG'])[0]
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    if jobs.snapshot()[0]['status'] == 'running':
                        break
                    time.sleep(0.05)
                self.assertEqual(jobs.snapshot()[0]['status'], 'running')
                jobs.cancel([job['id']])
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    current = jobs.snapshot()[0]
                    if current['status'] == 'cancelled':
                        break
                    time.sleep(0.05)
                self.assertEqual(jobs.snapshot()[0]['status'], 'cancelled')
                worker_pid = jobs.snapshot()[0].get('worker_pid')
                if worker_pid:
                    deadline = time.monotonic() + 10
                    while time.monotonic() < deadline and compat.process_alive(worker_pid):
                        time.sleep(0.05)
                    self.assertFalse(compat.process_alive(worker_pid), 'worker survived cancel')
                self.assertFalse((data / job['id'] / 'result.json').exists(),
                                 'a cancelled job must not publish a result')
            finally:
                jobs.shutdown()

    def test_utf8_json_roundtrip_in_console_codepage(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / '进度.json'
            compat.write_json(path, {'阶段': '已完成'})
            self.assertEqual(compat.read_json(path)['阶段'], '已完成')


if __name__ == '__main__':
    main()

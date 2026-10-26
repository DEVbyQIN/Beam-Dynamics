"""Regressions for independently reproduced platform failures; no beam tracking."""
import ctypes
from ctypes import wintypes
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, skipIf
from unittest.mock import Mock, patch
import os, signal, subprocess, sys, time

from gui import platform_compat as compat
from gui.server import Jobs
from gui.worker import abort_parent
from shared.params import load_config
from gui.test_platform_compat import FakeProc


class WindowsFailures(TestCase):
    def test_nonzero_taskkill_status_uses_original_process_handle(self):
        proc=FakeProc()
        with patch.object(compat.subprocess,'run',return_value=subprocess.CompletedProcess([],5)):
            self.assertFalse(compat._taskkill(proc.pid))
            self.assertTrue(compat.force_stop(proc,windows=True))
        self.assertEqual(proc.killed,1)

    def test_exited_process_is_not_killed_by_reused_pid(self):
        proc=FakeProc();proc.returncode=0
        with patch.object(compat,'_taskkill') as kill:
            self.assertTrue(compat.force_stop(proc,windows=True))
        kill.assert_not_called()

    def kernel(self):
        k=Mock();k.OpenProcess.return_value=2**40+17
        k.WaitForSingleObject.return_value=0x102;k.CloseHandle.return_value=1
        return k

    def test_pointer_width_abi_and_one_retained_parent_handle(self):
        k=self.kernel()
        with patch.object(compat.ctypes,'WinDLL',return_value=k,create=True):
            with compat.ParentMonitor(1234,windows=True) as monitor:
                self.assertIs(k.OpenProcess.restype,wintypes.HANDLE)
                self.assertEqual(k.WaitForSingleObject.argtypes,[wintypes.HANDLE,wintypes.DWORD])
                self.assertEqual(k.CloseHandle.argtypes,[wintypes.HANDLE])
                self.assertTrue(monitor.alive());self.assertTrue(monitor.alive())
                k.WaitForSingleObject.return_value=0
                self.assertFalse(monitor.alive())
        k.OpenProcess.assert_called_once_with(compat._SYNCHRONIZE,False,1234)
        self.assertEqual(k.WaitForSingleObject.call_args.args,(2**40+17,0))
        k.CloseHandle.assert_called_once_with(2**40+17)

    def test_access_denied_is_an_error_not_a_dead_parent(self):
        k=self.kernel();k.OpenProcess.return_value=0
        with patch.object(compat.ctypes,'WinDLL',return_value=k,create=True), \
             patch.object(compat.ctypes,'get_last_error',return_value=5,create=True):
            with self.assertRaisesRegex(OSError,'OpenProcess failed'):
                compat._windows_process_alive(1234)

    def test_missing_pid_is_dead(self):
        k=self.kernel();k.OpenProcess.return_value=0
        with patch.object(compat.ctypes,'WinDLL',return_value=k,create=True), \
             patch.object(compat.ctypes,'get_last_error',return_value=87,create=True):
            self.assertFalse(compat._windows_process_alive(1234))
        k.CloseHandle.assert_not_called()

    def test_wait_failed_is_an_error_not_a_dead_parent(self):
        k=self.kernel();k.WaitForSingleObject.return_value=0xffffffff
        with patch.object(compat.ctypes,'WinDLL',return_value=k,create=True), \
             patch.object(compat.ctypes,'get_last_error',return_value=6,create=True):
            with self.assertRaisesRegex(OSError,'WaitForSingleObject'):
                compat._windows_process_alive(1234)
        k.CloseHandle.assert_called_once()

    def test_error_file_failure_cannot_disable_worker_exit(self):
        with patch('gui.worker.save',side_effect=PermissionError('sharing violation')), \
             patch('gui.worker.os._exit',side_effect=SystemExit(2)) as exit_process:
            with self.assertRaises(SystemExit):abort_parent('unused','parent gone')
        exit_process.assert_called_once_with(2)

    def test_windows_break_signal_enters_keyboardinterrupt_cleanup(self):
        with patch.object(compat,'IS_WINDOWS',True), \
             patch.object(compat.signal,'SIGBREAK',21,create=True), \
             patch.object(compat.signal,'signal') as install:
            compat.configure_shutdown_signals()
        event,handler=install.call_args.args
        self.assertEqual(event,21)
        with self.assertRaises(KeyboardInterrupt):handler(event,None)


class QueueFailures(TestCase):
    def test_invalid_timeout_cannot_start_a_queue(self):
        for value in [0,-1,float('nan'),float('inf'),True]:
            with self.subTest(value=value), TemporaryDirectory() as tmp:
                with self.assertRaisesRegex(ValueError,'有限的正秒数'):Jobs(tmp,timeout=value)

    def test_unconfirmed_stop_is_bounded_and_blocks_new_workers(self):
        proc=FakeProc(ignore_terminate=True)
        with TemporaryDirectory() as tmp, patch('gui.server.subprocess.Popen',return_value=proc), \
             patch('gui.server.STOP_WAIT_S',.02),patch.object(compat,'force_stop',return_value=False):
            jobs=Jobs(tmp,timeout=.02)
            try:
                jobs.submit(load_config(),['AG','OCELOT'])
                end=time.monotonic()+2
                while time.monotonic()<end and jobs.thread.is_alive():time.sleep(.01)
                self.assertFalse(jobs.thread.is_alive(),'queue must not wait forever')
                failed=[j for j in jobs.snapshot() if j['route']=='AG'][0]
                self.assertEqual(failed['status'],'failed');self.assertTrue(failed['stop_failed'])
                with self.assertRaisesRegex(RuntimeError,'尚未退出'):jobs.submit(load_config(),['AG'])
                self.assertEqual([j for j in jobs.snapshot() if j['route']=='OCELOT'][0]['status'],'cancelled')
                proc.returncode=1
                with self.assertRaisesRegex(RuntimeError,'暂停'):jobs.submit(load_config(),['AG'])
            finally:
                proc.returncode=1;proc._stop.set();jobs.shutdown()

    @skipIf(os.name=='nt','real SIGTERM resistance is POSIX-only')
    def test_cancel_escalates_for_a_real_sigterm_resistant_child(self):
        real=subprocess.Popen
        with TemporaryDirectory() as tmp:
            ready=Path(tmp)/'ready'
            script='import signal,time,pathlib;signal.signal(signal.SIGTERM,signal.SIG_IGN);pathlib.Path('+repr(str(ready))+').write_text("ready");time.sleep(30)'
            def spawn(args,**kw):return real([sys.executable,'-c',script],**kw)
            with patch('gui.server.subprocess.Popen',side_effect=spawn),patch('gui.server.CANCEL_GRACE_S',.05):
                jobs=Jobs(Path(tmp)/'runs',timeout=20)
                try:
                    job=jobs.submit(load_config(),['AG'])[0]
                    deadline=time.monotonic()+3
                    while not ready.exists() and time.monotonic()<deadline:time.sleep(.01)
                    self.assertTrue(ready.exists());proc=jobs.process
                    jobs.cancel([job['id']]);deadline=time.monotonic()+3
                    while time.monotonic()<deadline and jobs.snapshot()[0]['status']=='running':time.sleep(.01)
                    self.assertEqual(jobs.snapshot()[0]['status'],'cancelled')
                    self.assertIsNotNone(proc.poll())
                    self.assertFalse((jobs.data/job['id']/'result.json').exists())
                finally:jobs.shutdown()

if __name__=='__main__':
    import unittest
    unittest.main()

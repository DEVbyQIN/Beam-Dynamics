"""Cross-platform process control and UTF-8 file I/O for the local GUI.

The GUI runs exactly one worker child per job.  POSIX has process groups
(``start_new_session`` + ``killpg``); Windows has neither, so this module is
the *only* place that knows the difference.  It is stdlib-only and safe to
import before NumPy/OCELOT so the worker can use it early.

Windows rules encoded here
--------------------------
* The worker is started with ``CREATE_NEW_PROCESS_GROUP`` so a Ctrl+C in the
  launcher console is not delivered to it twice: the server receives the
  interrupt and stops the worker itself.  ``start_new_session`` is not passed
  on Windows (setsid does not exist there).
* Stopping uses the process handle (``Popen.terminate`` / ``Popen.kill``).
  Forced cleanup of the whole tree uses ``taskkill /PID <pid> /T /F``.
* ``os.killpg`` does not exist on Windows, and ``os.kill(pid, 0)`` is *not* a
  liveness probe there: on Windows ``os.kill`` with any signal other than
  CTRL_C_EVENT/CTRL_BREAK_EVENT terminates the target process.  Parent
  liveness therefore uses a waitable process handle
  (``OpenProcess`` + ``WaitForSingleObject(..., 0)``), because ``os.getppid()``
  is stale once the parent exits.
* Files are written atomically with ``Path.replace``; on Windows that call can
  transiently fail while another handle is reading the same file, so atomic
  writes retry briefly instead of dropping a progress update.
"""
from __future__ import annotations

import ctypes
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

IS_WINDOWS = os.name == "nt"
ENCODING = "utf-8"

# Constants from winbase.h.  Harmless to define on POSIX; never used there.
_CREATE_NEW_PROCESS_GROUP = 0x00000200
_CREATE_NO_WINDOW = 0x08000000
_SYNCHRONIZE = 0x00100000
_WAIT_TIMEOUT = 0x00000102

_TASKKILL_TIMEOUT_S = 15.0
_REPLACE_RETRIES = 5
_REPLACE_RETRY_DELAY_S = 0.02


def _windows(flag=None):
    """Resolve the ``windows`` override used by tests against the real OS."""
    return IS_WINDOWS if flag is None else bool(flag)


# ── Process creation ──────────────────────────────────────────────────────


def spawn_kwargs(windows=None):
    """Extra ``subprocess.Popen`` keywords for the worker child."""
    if _windows(windows):
        return {"creationflags": _CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


# ── Stopping ──────────────────────────────────────────────────────────────


def _signal_group(pid, sig):
    """POSIX: signal the child's whole process group.  Never used on Windows."""
    try:
        os.killpg(os.getpgid(int(pid)), sig)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def _taskkill(pid, force=True):
    """Windows: kill the worker tree.  Returns False if taskkill is unusable."""
    args = ["taskkill", "/PID", str(int(pid)), "/T"]
    if force:
        args.append("/F")
    try:
        subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=_TASKKILL_TIMEOUT_S, check=False,
                       creationflags=_CREATE_NO_WINDOW)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def request_stop(proc, windows=None):
    """Ask a worker to stop without waiting.

    POSIX: SIGTERM to the process group (children included).
    Windows: TerminateProcess on the worker handle; the worker spawns no
    grandchildren in this GUI, so a tree kill is only needed on escalation.
    """
    if proc is None:
        return False
    if _windows(windows):
        try:
            proc.terminate()
            return True
        except OSError:
            return False
    return _signal_group(proc.pid, signal.SIGTERM)


def force_stop(proc, windows=None):
    """Unconditional stop: SIGKILL to the group, or taskkill /T /F on Windows."""
    if proc is None:
        return False
    if _windows(windows):
        if _taskkill(proc.pid, force=True):
            return True
        try:
            proc.kill()
            return True
        except OSError:
            return False
    return _signal_group(proc.pid, signal.SIGKILL)


def _wait_quietly(proc, timeout):
    """Return the exit code, or None if the child was still running."""
    try:
        return proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        return None


def terminate_tree(proc, grace=3.0, windows=None):
    """Stop a worker (and its tree), escalating after ``grace`` seconds.

    Returns the exit code when observed, else None.  Used on service shutdown.
    """
    if proc is None:
        return None
    request_stop(proc, windows=windows)
    code = _wait_quietly(proc, grace)
    if code is None:
        force_stop(proc, windows=windows)
        code = _wait_quietly(proc, 5.0)
    return code


# ── Liveness ──────────────────────────────────────────────────────────────


def _windows_process_alive(pid):
    """Windows: a process that opened a SYNCHRONIZE handle is not yet signaled.

    Any failure to probe is reported as alive: an orphaned worker keeps
    computing (and stays stoppable by the server) rather than aborting a job
    because of an introspection error.
    """
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    except (AttributeError, OSError):
        return True
    handle = kernel32.OpenProcess(_SYNCHRONIZE, False, int(pid))
    if not handle:
        return False
    try:
        return kernel32.WaitForSingleObject(handle, 0) == _WAIT_TIMEOUT
    finally:
        kernel32.CloseHandle(handle)


def process_alive(pid, windows=None):
    """True if ``pid`` is still running (never uses os.kill on Windows)."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if _windows(windows):
        return _windows_process_alive(pid)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def parent_alive(pid, windows=None):
    """True while the server process that spawned this worker still exists.

    POSIX keeps the original ``os.getppid()`` comparison.  Windows probes the
    parent PID with a waitable handle, because ``os.getppid()`` keeps returning
    the original number after the parent exits.
    """
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if _windows(windows):
        return _windows_process_alive(pid)
    return os.getppid() == pid


# ── UTF-8 file I/O ────────────────────────────────────────────────────────


def read_text(path):
    """Read text as UTF-8 regardless of the Windows ANSI code page."""
    return Path(path).read_text(encoding=ENCODING)


def write_text(path, text):
    Path(path).write_text(text, encoding=ENCODING)


def read_json(path):
    return json.loads(read_text(path))


def write_json(path, value, indent=2):
    """Atomically write UTF-8 JSON (never ASCII-escaped, never NaN)."""
    target = Path(path)
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=indent,
                               allow_nan=False), encoding=ENCODING)
    for attempt in range(_REPLACE_RETRIES):
        try:
            tmp.replace(target)
            return
        except PermissionError:
            if attempt == _REPLACE_RETRIES - 1:
                raise
            time.sleep(_REPLACE_RETRY_DELAY_S)


def open_log(path):
    """Open the child's stdout/stderr sink in binary mode.

    Bytes from the child (which we start with PYTHONIOENCODING=utf-8) pass
    through unchanged; no locale code page or newline translation is applied.
    """
    return Path(path).open("wb")


def worker_env(cache_dir=None, base=None):
    """Environment for a worker child: UTF-8 everywhere and headless backends."""
    env = dict(os.environ if base is None else base)
    env.update(
        PYTHONUTF8="1",
        PYTHONIOENCODING="utf-8",
        PYTHONDONTWRITEBYTECODE="1",
        MPLBACKEND="Agg",
        OCELOT_NUM_THREADS="2",
        NUMBA_NUM_THREADS="2",
    )
    if cache_dir is not None:
        cache = Path(cache_dir)
        env["MPLCONFIGDIR"] = str(cache / "mpl")
        env["NUMBA_CACHE_DIR"] = str(cache / "numba")
    return env


def configure_stdio():
    """Stop a legacy console code page from turning console output into a crash."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass

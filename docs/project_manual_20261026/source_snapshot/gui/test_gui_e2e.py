"""Real end-to-end GUI regression: real server process, real worker children.

Covers: successful short AG/OCELOT runs, cancellation of a running worker (status,
no published result, worker actually gone), and service shutdown while a job
is running (no leftover worker, job marked cancelled).  The run directory uses
Chinese characters and spaces on purpose.

The same test exercises the Windows branches when run on Windows, but this
repository's evidence was produced on macOS only - see gui/WINDOWS.md.
Set UED_GUI_E2E=0 to skip this module.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main, skipUnless
import io, json, os, shutil, signal, socket, subprocess, sys, time, urllib.error, urllib.request, zipfile

ROOT = Path(__file__).resolve().parents[1]
from shared.params import load_config                      # noqa: E402
from gui import platform_compat as compat                  # noqa: E402

ENABLED = os.environ.get('UED_GUI_E2E', '1') != '0'
TERMINAL = ('complete', 'failed', 'timeout', 'cancelled', 'interrupted')


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


class Client:
    def __init__(self, base):
        self.base = base
        self.token = None

    def request(self, method, path, payload=None, raw=False):
        body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8')
        request = urllib.request.Request(self.base + path, data=body, method=method)
        request.add_header('Content-Type', 'application/json')
        if self.token:
            request.add_header('X-UED-Token', self.token)
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read()
            return data if raw else json.loads(data)


@skipUnless(ENABLED, 'set UED_GUI_E2E=1 to run the end-to-end GUI test')
class GuiEndToEnd(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = TemporaryDirectory()
        cls.data = Path(cls.tmp.name) / '中文 运行目录' / '记录'
        cls.port = free_port()
        cls.base = f'http://127.0.0.1:{cls.port}'
        cls.log_path = Path(cls.tmp.name) / 'server.log'
        env = dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8',
                   PYTHONDONTWRITEBYTECODE='1')
        cls.log = open(cls.log_path, 'wb')
        cls.server = subprocess.Popen(
            [sys.executable, 'run_gui.py', '--port', str(cls.port), '--data-dir', str(cls.data),
             '--timeout', '180'],
            cwd=ROOT, stdout=cls.log, stderr=subprocess.STDOUT, env=env,
            **compat.spawn_kwargs())
        cls.client = Client(cls.base)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if cls.server.poll() is not None:
                cls.fail(f'server exited during startup:\n{cls.log_path.read_text(errors="replace")}')
            try:
                bootstrap = cls.client.request('GET', '/api/bootstrap')
                cls.client.token = bootstrap['token']
                break
            except (urllib.error.URLError, ConnectionError, OSError):
                time.sleep(0.05)
        else:
            cls.fail('server did not answer within 60 s')
        cls.addClassCleanup(cls._stop_server)

    @classmethod
    def _stop_server(cls):
        server = cls.server
        if server.poll() is None:
            server.send_signal(signal.CTRL_BREAK_EVENT if os.name=='nt' else signal.SIGINT)
            try:
                server.wait(timeout=30)
            except subprocess.TimeoutExpired:
                compat.force_stop(server)
                server.wait(timeout=10)
        cls.log.close()
        if os.environ.get('UED_GUI_E2E_ARTIFACTS'):
            dest=Path(os.environ['UED_GUI_E2E_ARTIFACTS']).resolve();dest.mkdir(parents=True,exist_ok=True)
            if cls.data.resolve() in dest.parents:raise ValueError('E2E artifacts must be outside the temporary data directory')
            for record in cls.data.glob('*/job.json'):
                shutil.copytree(record.parent,dest/record.parent.name,dirs_exist_ok=True)
            shutil.copy2(cls.log_path,dest/'server.log')
        cls.tmp.cleanup()

    # ── helpers ───────────────────────────────────────────────────────────
    def snapshot(self, job_id):
        for job in self.client.request('GET', '/api/jobs'):
            if job['id'] == job_id:
                return job
        self.fail(f'job {job_id} disappeared from the API')

    def wait_status(self, job_id, statuses, timeout=240):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            job = self.snapshot(job_id)
            if job['status'] in statuses:
                return job
            time.sleep(0.05)
        self.fail(f'job {job_id} never reached {statuses} (last {self.snapshot(job_id)["status"]})')

    def wait_worker_gone(self, job, timeout=10):
        pid = job.get('worker_pid')
        if not pid:
            return
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and compat.process_alive(pid):
            time.sleep(0.05)
        self.assertFalse(compat.process_alive(pid), f'worker {pid} survived')

    def submit(self, config, routes):
        created = self.client.request('POST', '/api/jobs', {'config': config, 'routes': routes})
        return created[0]

    def slow_config(self):
        """SC AG setup used only to be stopped; output dz does not set AG steps."""
        config = load_config()
        config['space_charge']['enabled'] = True
        config['output']['step_size_m'] = 0.0005
        return config

    def short_config(self):
        config=load_config()
        config['beam']['n_particles']=2000
        elements=config['lattice']['elements']
        for e,start,length in zip(elements,[0,.0,.002,.004,.006,.007,.01],[0,.002,.002,.002,.001,.003,0]):
            e.update(z_start=start,length=length)
        config['space_charge']['enabled']=False
        config['output'].update(step_size_m=.001,z_diagnostics_mm=[0,2,4,6,7,10])
        return config

    def wait_computing(self,job_id):
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            job=self.snapshot(job_id)
            if 'AG 正在积分' in job.get('progress',{}).get('phase',''):return job
            if job['status'] in TERMINAL:self.fail(f'worker ended before entering integration: {job}')
            time.sleep(.02)
        self.fail('worker did not enter the formal AG integration')

    # ── tests (ordered by name) ───────────────────────────────────────────
    def test_a_short_ag_run_completes(self):
        config = self.short_config()
        job = self.submit(config, ['AG'])
        done = self.wait_status(job['id'], TERMINAL)
        self.assertEqual(done['status'], 'complete', done.get('error'))
        self.assertEqual(done['exit_code'], 0)
        self.assertEqual(done['progress'].get('phase'), '已完成')

        result = self.client.request('GET', f'/api/jobs/{job["id"]}/result')
        self.assertEqual(result['route'], 'AG')
        self.assertIn('probes', result)
        self.assertIn('history', result)
        self.assertAlmostEqual(result['history']['z_mm'][-1],10.,places=8)

        bundle = self.client.request('GET', f'/api/jobs/{job["id"]}/bundle', raw=True)
        with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
            names = archive.namelist()
        for expected in ('config.json', 'config.yaml', 'job.json', 'run.log', 'progress.json'):
            self.assertIn(expected, names)
        self.assertIn('AG_results.json', names)

        log = self.client.request('GET', f'/api/jobs/{job["id"]}/log')['text']
        self.assertIn('AG complete', log)

    def test_a_short_ocelot_run_completes(self):
        job=self.submit(self.short_config(),['OCELOT'])
        done=self.wait_status(job['id'],TERMINAL)
        self.assertEqual(done['status'],'complete',done.get('error'))
        result=self.client.request('GET',f'/api/jobs/{job["id"]}/result')
        self.assertEqual(result['route'],'GPT')
        self.assertAlmostEqual(result['history']['z_mm'][-1],10.,places=8)
        self.assertEqual(result['meta']['rf_kicks_applied'],1)

    def test_b_cancel_stops_the_real_worker(self):
        job = self.submit(self.slow_config(), ['AG'])
        self.wait_computing(job['id'])
        self.client.request('POST', '/api/cancel', {'ids': [job['id']]})
        stopped = self.wait_status(job['id'], ('cancelled', 'failed', 'timeout', 'complete'), timeout=60)
        self.assertEqual(stopped['status'], 'cancelled')
        self.assertFalse((self.data / job['id'] / 'result.json').exists(),
                         'a cancelled job must not publish a result')
        self.wait_worker_gone(stopped)
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.client.request('GET', f'/api/jobs/{job["id"]}/result')
        self.assertEqual(caught.exception.code, 409)

    def test_c_service_shutdown_leaves_no_worker(self):
        job = self.submit(self.slow_config(), ['AG'])
        running = self.wait_computing(job['id'])
        server = type(self).server
        server.send_signal(signal.CTRL_BREAK_EVENT if os.name=='nt' else signal.SIGINT)
        self.assertEqual(server.wait(timeout=30), 0, 'server should exit cleanly on SIGINT')
        time.sleep(0.5)
        self.wait_worker_gone(running)
        saved = json.loads((self.data / job['id'] / 'job.json').read_text(encoding='utf-8'))
        self.assertIn(saved['status'], ('cancelled', 'interrupted'), saved)
        self.assertNotEqual(saved['status'], 'complete')
        self.assertIn('UED GUI', self.log_path.read_text(encoding='utf-8', errors='replace'))


if __name__ == '__main__':
    main()

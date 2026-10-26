"""Loopback-only GUI, immutable run snapshots, and a serial worker queue."""
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import argparse, hashlib, io, json, math, mimetypes, os, re, secrets
import subprocess, sys, threading, time, uuid, webbrowser, zipfile
from copy import deepcopy
from urllib.parse import urlsplit
import yaml
from shared.params import load_config, config_sha
from shared.geometry import validate_geometry
try:                          # normal entry: run_gui.py / python -m gui.server
    from . import platform_compat as compat
except ImportError:           # direct execution: python gui/server.py
    import platform_compat as compat

ROOT=Path(__file__).resolve().parents[1]
WEB=Path(__file__).parent/'web'
TERMINAL={'complete','failed','cancelled','timeout','interrupted'}
def fingerprint(cfg):
    return hashlib.sha256(json.dumps(cfg,sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest()
def write_json(path,value):
    """Atomic UTF-8 JSON (see gui.platform_compat for the Windows retry)."""
    compat.write_json(path,value)
def validate_config(cfg):
    """UI input checks plus the unchanged shared geometry validator."""
    def number(value,name,minimum=None,positive=False,integer=False):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ValueError(name+' 必须是有限数值')
        if integer and int(value)!=value:raise ValueError(name+' 必须是整数')
        if positive and value<=0:raise ValueError(name+' 必须大于零')
        if minimum is not None and value<minimum:raise ValueError(name+f' 不得小于 {minimum}')
    try:
        number(cfg['beam']['energy_keV'],'动能 / keV',positive=True)
        number(cfg['beam']['charge_fC'],'电荷幅值 / fC',minimum=0)
        number(cfg['beam']['n_particles'],'宏粒子数',minimum=2,integer=True)
        ib=cfg['initial_distribution']
        for key in ('spot_rms_um','bunch_length_um'):number(ib[key],key,positive=True)
        for key in ('epsilon_n_mm_mrad','sigma_delta'):number(ib[key],key,minimum=0)
        number(cfg['output']['step_size_m'],'追踪步长 / m',positive=True)
        number(cfg['random']['seed'],'随机种子',minimum=0,integer=True)
        if cfg['random']['seed']>4294967294:raise ValueError('随机种子须小于 4294967295（另一个随机源使用 seed+1）')
        sc=cfg['space_charge'];mesh=sc['mesh']
        if not isinstance(mesh,list) or len(mesh)!=3:raise ValueError('SC 网格须为三个整数')
        for n in mesh:number(n,'SC 网格',minimum=3,integer=True)
        number(sc['step'],'SC 调用间隔',minimum=1,integer=True)
        if not isinstance(sc['enabled'],bool):raise ValueError('SC 开关须为布尔值')
        for key in ('rf_longitudinal_kick','rf_transverse_kick'):
            if not isinstance(cfg['physics_switches'][key],bool):raise ValueError(key+' 须为布尔值')
        for e in cfg['lattice']['elements']:
            p=e.get('parameters',{})
            if e['type']=='solenoid':number(p['B_field_T'],e['name']+' 磁场 / T')
            if e['type']=='rf_cavity':
                number(p['frequency_GHz'],e['name']+' 频率 / GHz',positive=True)
                number(p['voltage_kV'],e['name']+' 有效电压 / kV')
                number(p['phase_rad'],e['name']+' 相位 / rad')
        geometry=validate_geometry(cfg)
        # Match the integer types expected by formal numerical APIs, without rounding.
        cfg=deepcopy(cfg);cfg['beam']['n_particles']=int(cfg['beam']['n_particles'])
        cfg['random']['seed']=int(cfg['random']['seed']);cfg['space_charge']['step']=int(sc['step'])
        cfg['space_charge']['mesh']=[int(n) for n in mesh]
        return cfg,geometry
    except (KeyError,TypeError,AttributeError) as e:
        raise ValueError('配置结构缺失或格式不正确：'+str(e)) from e

class Jobs:
    def __init__(self,data,timeout=1800):
        self.data=Path(data).resolve();self.data.mkdir(parents=True,exist_ok=True)
        self.timeout=timeout;self.lock=threading.RLock();self.wake=threading.Event();self.closed=False
        self.jobs={};self.process=None;self.active=None
        for p in sorted(self.data.glob('*/job.json')):
            try:
                job=compat.read_json(p)
                if job['status'] not in TERMINAL:
                    job.update(status='interrupted',error='上次界面关闭，运行未完成；未自动重跑。',finished=time.time());write_json(p,job)
                self.jobs[job['id']]=job
            except (ValueError,KeyError,OSError):continue
        self.thread=threading.Thread(target=self.loop,daemon=True);self.thread.start()
    def save(self,job):write_json(self.data/job['id']/'job.json',job)
    def submit(self,cfg,routes):
        cfg,geometry=validate_config(cfg)
        if not isinstance(routes,list) or not routes or len(routes)!=len(set(routes)) or any(r not in ('AG','OCELOT') for r in routes):
            raise ValueError('选择 AG、OCELOT 或两者')
        with self.lock:
            if any(j['status'] not in TERMINAL for j in self.jobs.values()):raise RuntimeError('已有任务在运行或排队，请先完成或停止。')
            batch=uuid.uuid4().hex;created=[]
            for route in routes:
                job=dict(id=uuid.uuid4().hex,batch=batch,route=route,status='queued',created=time.time(),
                    config_fingerprint=fingerprint(cfg),config_sha=config_sha(cfg),sample_m=geometry['sample_m'],timeout_s=self.timeout)
                d=self.data/job['id'];d.mkdir();write_json(d/'config.json',cfg)
                compat.write_text(d/'config.yaml',yaml.safe_dump(cfg,allow_unicode=True,sort_keys=False))
                self.jobs[job['id']]=job;self.save(job);created.append(deepcopy(job))
            self.wake.set();return created
    def snapshot(self):
        with self.lock:
            values=deepcopy(list(self.jobs.values()))
        for j in values:
            try:j['progress']=compat.read_json(self.data/j['id']/'progress.json')
            except (OSError,ValueError):j['progress']={}
            j['elapsed_s']=max(0,j.get('finished',time.time())-j.get('started',time.time()))
        return sorted(values,key=lambda j:j['created'],reverse=True)
    def cancel(self,ids):
        with self.lock:
            for jid in ids:
                if jid not in self.jobs:raise ValueError('任务不存在')
                j=self.jobs[jid]
                if j['status'] in TERMINAL:continue
                j['cancel_requested']=True
                if j['status']=='queued':j.update(status='cancelled',finished=time.time())
                elif self.active==jid and self.process is not None:
                    compat.request_stop(self.process)
                self.save(j)
        self.wake.set()
    def loop(self):
        while not self.closed:
            self.wake.wait(.3);self.wake.clear()
            with self.lock:
                queued=sorted((j for j in self.jobs.values() if j['status']=='queued'),key=lambda j:j['created'])
                if not queued:continue
                j=queued[0];d=self.data/j['id'];j.update(status='running',started=time.time());self.save(j);self.active=j['id']
                env=compat.worker_env(self.data/'cache')
                log=compat.open_log(d/'run.log')
                try:
                    self.process=subprocess.Popen([sys.executable,'-m','gui.worker',str(d),j['route'],str(os.getpid())],
                        cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=env,**compat.spawn_kwargs())
                except OSError as e:
                    log.close();j.update(status='failed',error=str(e),finished=time.time());self.save(j);self.active=None;continue
                proc=self.process
                # Diagnostics only: a leftover worker clears itself through its
                # parent-liveness check; a PID from an older session is never
                # killed because Windows reuses PIDs.
                j['worker_pid']=proc.pid;self.save(j)
            timedout=False
            try:code=proc.wait(timeout=self.timeout)
            except subprocess.TimeoutExpired:
                timedout=True
                compat.force_stop(proc)
                code=proc.wait()
            finally:log.close()
            with self.lock:
                j.update(exit_code=code,finished=time.time())
                if j.get('cancel_requested'):j['status']='cancelled'
                elif timedout:j.update(status='timeout',error=f'达到本次运行 {self.timeout:g} 秒上限，未标为成功。')
                elif code==0 and (d/'result.json').exists():j['status']='complete'
                else:
                    error='计算未成功完成，请查看日志。'
                    try:error=compat.read_json(d/'error.json')['error']
                    except (OSError,ValueError,KeyError):pass
                    j.update(status='failed',error=error)
                self.save(j);self.process=None;self.active=None;self.wake.set()
    def shutdown(self):
        self.closed=True;self.cancel([j['id'] for j in self.snapshot() if j['status'] not in TERMINAL]);self.wake.set()
        proc=self.process
        if proc is not None:
            compat.terminate_tree(proc,grace=3.0)
        self.thread.join(timeout=4)

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def send(self,value,status=200,ctype='application/json; charset=utf-8',filename=None):
        data=json.dumps(value,ensure_ascii=False,allow_nan=False).encode() if isinstance(value,(dict,list)) else value
        self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        if filename:self.send_header('Content-Disposition','attachment; filename="'+filename+'"')
        self.end_headers()
        try:self.wfile.write(data)
        except (BrokenPipeError,ConnectionResetError):pass
    def do_GET(self):
        if not self.allowed_host():return self.send({'error':'Host rejected'},403)
        path=urlsplit(self.path).path
        try:
            if path=='/api/bootstrap':return self.send(dict(config=load_config(),token=self.server.token,timeout_s=self.server.jobs.timeout))
            if path=='/api/jobs':return self.send(self.server.jobs.snapshot())
            m=re.fullmatch(r'/api/jobs/([a-f0-9]{32})/(config|result|log|bundle)',path)
            if m:
                jid,kind=m.groups();jobs=self.server.jobs
                with jobs.lock:
                    if jid not in jobs.jobs:raise ValueError('任务不存在')
                    job=deepcopy(jobs.jobs[jid])
                d=jobs.data/jid
                if kind=='config':return self.send(compat.read_json(d/'config.json'))
                if kind=='result':
                    if job['status']!='complete':return self.send({'error':'任务尚未成功，暂无完整结果'},409)
                    return self.send((d/'result.json').read_bytes(),ctype='application/json',filename=job['route']+'_results.json')
                if kind=='log':
                    if not (d/'run.log').exists():return self.send({'text':''})
                    with (d/'run.log').open('rb') as f:f.seek(max(0,(d/'run.log').stat().st_size-24000));text=f.read().decode('utf-8',errors='replace')
                    return self.send({'text':text})
                buffer=io.BytesIO()
                with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as z:
                    for name in ['config.json','config.yaml','job.json','progress.json','run.log','error.json']:
                        if (d/name).exists():z.write(d/name,name)
                    if job['status']=='complete':z.write(d/'result.json',job['route']+'_results.json')
                return self.send(buffer.getvalue(),ctype='application/zip',filename='ued_'+jid[:8]+'.zip')
            static={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}.get(path)
            if static:return self.send((WEB/static).read_bytes(),ctype=mimetypes.guess_type(static)[0]+'; charset=utf-8')
            return self.send({'error':'Not found'},404)
        except (ValueError,OSError) as e:self.send({'error':str(e)},400)
    def allowed_host(self):
        return self.headers.get('Host','') in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
    def do_POST(self):
        if not self.allowed_host():return self.send({'error':'Host rejected'},403)
        origin=self.headers.get('Origin')
        if origin and origin not in {f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'}:return self.send({'error':'Origin rejected'},403)
        if self.headers.get('X-UED-Token')!=self.server.token:return self.send({'error':'请刷新本地界面后重试'},403)
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=2_000_000:raise ValueError('配置为空或超过 2 MB')
            body=json.loads(self.rfile.read(length));path=urlsplit(self.path).path
            if path=='/api/validate':
                cfg,geometry=validate_config(body['config']);return self.send(dict(config=cfg,geometry=geometry,config_fingerprint=fingerprint(cfg)))
            if path=='/api/import-config':
                cfg,geometry=validate_config(yaml.safe_load(body['text']));return self.send(dict(config=cfg,geometry=geometry))
            if path=='/api/jobs':return self.send(self.server.jobs.submit(body['config'],body['routes']),201)
            if path=='/api/cancel':self.server.jobs.cancel(body['ids']);return self.send({'ok':True})
            return self.send({'error':'Not found'},404)
        except RuntimeError as e:self.send({'error':str(e)},409)
        except (ValueError,TypeError,KeyError,yaml.YAMLError) as e:self.send({'error':str(e)},400)

def serve(port=8765,data=None,timeout=1800,open_browser=False):
    try:server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    except OSError as e:
        raise SystemExit(f'无法监听 127.0.0.1:{port}（{e}）。端口可能被占用，可改用 --port 8766。') from e
    server.token=secrets.token_urlsafe(24);server.jobs=Jobs(data or ROOT/'gui_runs',timeout)
    url=f'http://127.0.0.1:{server.server_port}'
    print('UED GUI '+url,flush=True);print('Runs: '+str(server.jobs.data),flush=True)
    if open_browser:threading.Timer(.6,lambda:webbrowser.open(url)).start()
    try:server.serve_forever(poll_interval=.25)
    except KeyboardInterrupt:pass
    finally:server.jobs.shutdown();server.server_close()
def main():
    compat.configure_stdio()
    p=argparse.ArgumentParser(description='UED local GUI (existing AG/OCELOT drivers)')
    p.add_argument('--port',type=int,default=8765);p.add_argument('--data-dir',type=Path);p.add_argument('--timeout',type=float,default=1800);p.add_argument('--open',action='store_true')
    a=p.parse_args()
    if a.timeout<=0:p.error('--timeout must be positive')
    serve(a.port,a.data_dir,a.timeout,a.open)
if __name__=='__main__':main()

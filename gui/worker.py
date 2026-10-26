"""One child process, one immutable configuration, one existing formal driver call."""
from pathlib import Path
from contextlib import contextmanager
import hashlib, importlib, json, os, sys, threading, time, traceback
from unittest.mock import patch
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
try:                          # normal entry: python -m gui.worker
    from . import platform_compat as compat
except ImportError:           # direct execution: python gui/worker.py
    import platform_compat as compat
def save(path,value):
    compat.write_json(path,value)

def abort_parent(directory,message):
    """Failure to write an error file must not disable orphan cleanup."""
    try:save(Path(directory)/'error.json',{'error':message})
    except OSError:pass
    finally:os._exit(2)

def run(directory,route,parent):
    # Open before numerical imports and retain the Windows process object.
    with compat.ParentMonitor(parent) as monitor:
        stopped=threading.Event()
        def watch_parent():
            while not stopped.wait(2):
                try:
                    if not monitor.alive():abort_parent(directory,'界面服务已关闭，计算中止。')
                except OSError as e:abort_parent(directory,'父进程监控失败，计算中止：'+str(e))
        if not monitor.alive():raise RuntimeError('界面服务已关闭，计算未启动。')
        watcher=threading.Thread(target=watch_parent,daemon=True);watcher.start()
        try:return run_job(directory,route)
        finally:
            stopped.set();watcher.join()

def run_job(directory,route):
    d=Path(directory);cfg=compat.read_json(d/'config.json');started=time.monotonic()
    from shared.geometry import validate_geometry
    from shared.params import config_sha
    from shared.output_schema import write_results
    sample=validate_geometry(cfg)['sample_m'];last=[-10.]
    def progress(s,phase,force=False):
        now=time.monotonic()
        if force or now-last[0]>.5:
            save(d/'progress.json',dict(s_m=float(s),sample_m=sample,fraction=max(0,min(1,float(s)/sample)),phase=phase,elapsed_s=now-started));last[0]=now
    progress(0,'准备计算依赖',True)
    if route=='AG':
        from AG.runner import run_from_config
        import beam_dynamics_6d as core
        real=core.propagate
        def observe(beam,z_span,*args,**kwargs):
            progress(z_span[0],'AG 正在积分（按束线分段更新）',True)
            result=real(beam,z_span,*args,**kwargs);progress(z_span[1],'AG 分段积分完成',True);return result
        with patch.object(core,'propagate',observe):result=run_from_config(cfg,section='full')
        probes=result.probes_at(cfg['output']['z_diagnostics_mm']);history=result.history();meta=result.meta;label='AG'
    elif route=='OCELOT':
        model=importlib.import_module('GPT模拟.ued_beamline_v2')
        import shared.diagnostics as diag
        real=diag.particle_diagnostics
        def observe(p,ref):
            progress(p.s,'OCELOT 正在推进');return real(p,ref)
        with patch.object(diag,'particle_diagnostics',observe):result=model.run_from_config(cfg,section='full')
        probes=result['probes'];history=result['history'];meta=result['meta'];label='GPT'
    else:raise ValueError('Unknown route')
    if not history['z_mm'] or abs(history['z_mm'][-1]-sample*1e3)>1e-8:raise RuntimeError('正式结果未到样品面，未标为成功')
    path=Path(write_results(label,probes,history,config_sha(cfg),meta['sc_effective'],out_dir=str(d),meta=meta))
    # The download name stays common for the GUI; original route field is preserved.
    payload=compat.read_json(path);compat.write_json(d/'result.json',payload)
    progress(sample,'已完成',True)
    print(route+' complete: '+str(d/'result.json'),flush=True)
if __name__=='__main__':
    d=Path(sys.argv[1])
    try:run(d,sys.argv[2],int(sys.argv[3]))
    except BaseException as e:
        save(d/'error.json',{'error':str(e),'type':type(e).__name__});traceback.print_exc();sys.exit(1)

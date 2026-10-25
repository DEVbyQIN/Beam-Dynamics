"""Finite short-SC study through production APIs; never writes default results.

See sc_scope_study_physics_note.md. A required --out contains resumable case
records; --reuse accepts the explicitly verified older PIC controls only.
"""
from pathlib import Path
import argparse,contextlib,copy,hashlib,importlib.metadata,io,json,sys,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'AG')]
from shared.params import load_config,config_sha
from shared.constants import E_SI
from shared.diagnostics import pair_moments,covariance_area,longitudinal_diagnostics
import shared.diagnostics as diagnostics
from validation.backend import run_ag,run_ocelot
import beam_dynamics_6d as bd
from AG.longitudinal_state import inspect_longitudinal_state

FIELDS=('sigma_x_um','sigma_y_um','sigma_z_um','sigma_delta_e3','chirp_per_m',
        'eps_nx_mm_mrad','eps_ny_mm_mrad','eps_nz_mm_mrad')
SEEDS=(42,104729,130363,155921,196613)

def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,indent=2));tmp.replace(path)

def case_config(q,n,mesh,dz,seed):
    c=load_config();c['beam'].update(charge_fC=q,n_particles=n,energy_keV=100.)
    c['initial_distribution'].update(spot_rms_um=85.,bunch_length_um=300.,sigma_delta=1e-4,epsilon_n_mm_mrad=.08)
    c['random']['seed']=seed;c['space_charge'].update(enabled=q>0,mesh=[mesh]*3,step=1)
    c['lattice']['elements']=[dict(name='cathode',type='cathode',z_start=0.,length=0.,parameters={}),dict(name='drift',type='drift',z_start=0.,length=.05,parameters={}),dict(name='sample',type='sample',z_start=.05,length=0.,parameters={})]
    c['output'].update(z_diagnostics_mm=[0,10,25,50],step_size_m=dz)
    return c

def residual_stats(raw,beta):
    z=-beta*raw[4];d=raw[5]/beta;z=z-z.mean();d=d-d.mean()
    h=float(np.mean(z*d)/np.mean(z*z));v=d-h*z;variance=float(np.mean(v*v))
    return dict(sigma_uncorrelated_delta_e3=float(np.sqrt(variance)*1e3),
                residual_kurtosis=float(np.mean(v**4)/variance**2),chirp_per_m=h)

def cloud_record(raw,ref):
    moments=[pair_moments(raw[0],raw[1]),pair_moments(raw[2],raw[3]),pair_moments(-ref['beta']*raw[4],raw[5]/ref['beta'])]
    return dict(raw_sha256=hashlib.sha256(raw.tobytes()).hexdigest(),moments=[list(map(float,m)) for m in moments],
                beta=float(ref['beta']),gamma=float(ref['gamma']),beta_gamma=float(ref['beta_gamma']),
                initial_residual=residual_stats(raw,ref['beta']))

def matched_initial_beam(q,cloud):
    # Diagnostic only: the same AG kernel with its retained initial pair moments.
    # No alternative lattice/event loop and no replacement of formal AG input.
    (ax,bx,cx),(ay,by,cy),(az,bz,cz)=cloud['moments'];bg=cloud['beta_gamma']
    b=bd.make_beam_100keV(Ne=q*1e-15/E_SI,beamK_eV=100000.,sigma_x0_um=np.sqrt(ax)*1e6,
        sigma_y0_um=np.sqrt(ay)*1e6,sigma_z0_um=np.sqrt(az)*1e6,sigma_delta=np.sqrt(bz),
        eps_nx_um=bg*covariance_area(ax,bx,cx)*1e6,eps_ny_um=bg*covariance_area(ay,by,cy)*1e6)
    # Match geometric pair moments using the core reference momentum.
    # Existing shared/core rest-energy constants differ at the ppm level.
    b.eps_nx=b.p0*covariance_area(ax,bx,cx);b.eps_ny=b.p0*covariance_area(ay,by,cy)
    b.nu_x=cx/b.sigma_x;b.nu_y=cy/b.sigma_y;b.C_zd=cz;b.nu_z=cz/(b.gamma**2*b.sigma_z)
    b.eps_nz=inspect_longitudinal_state(b)['epsilon_from_covariance_mm_mrad']*1e-6
    return b

def matched_ag(q,cloud):
    b=matched_initial_beam(q,cloud)
    _,st=bd.propagate(b,(0.,.05),n_points=51,rtol=1e-10,atol=1e-12)
    diag=longitudinal_diagnostics(st[-1,2],st[-1,4],st[-1,5],st[-1,11])
    result=dict(sigma_x_um=st[-1,0]*1e6,sigma_y_um=st[-1,1]*1e6,sigma_z_um=st[-1,2]*1e6,
        sigma_delta_e3=st[-1,4]*1e3,eps_nx_mm_mrad=st[-1,12]*1e6,eps_ny_mm_mrad=st[-1,13]*1e6,
        **{k:float(v) for k,v in diag.items()})
    return {k:float(result[k]) for k in FIELDS}

def run_pic(c):
    capture={};original=diagnostics.particle_diagnostics
    def spy(p,ref):
        if not capture:capture.update(raw=p.rparticles.copy(),ref=ref.copy(),particle=p)
        return original(p,ref)
    diagnostics.particle_diagnostics=spy
    try:
        with contextlib.redirect_stdout(io.StringIO()):r=run_ocelot(c,'full')
    finally:diagnostics.particle_diagnostics=original
    assert abs(r.z_mm[-1]-50.)<1e-9 and r.meta['rf_kicks_applied']==0
    if c['space_charge']['enabled']:assert r.meta['sc_effective'] and r.meta['sc_apply_count']>0
    cloud=cloud_record(capture['raw'],capture['ref']);final=capture['particle'].rparticles
    data=dict(endpoint={k:float(getattr(r,k)[-1]) for k in FIELDS},history=r.history(),meta=r.meta,
              initial_raw_sha256=cloud['raw_sha256'],initial=cloud,
              residual=residual_stats(final,cloud['beta']),origin='new_production_API')
    if c['random']['seed']==42 and c['beam']['n_particles']==50000:
        sel=np.linspace(0,final.shape[1]-1,1600,dtype=int)
        data['phase_plot_sample']={'zeta_um':(-cloud['beta']*final[4,sel]*1e6).tolist(),'delta_e3':(final[5,sel]/cloud['beta']*1e3).tolist()}
    return data,cloud

def reuse_gate(path):
    if path is None:return [],dict(source_and_versions_match=False,reason='reuse not requested')
    old=json.loads(Path(path).read_text());ctx=json.loads((Path(path).parent/'full_sc_diagnostic.json').read_text())['OCELOT']['meta']['provenance']
    relevant=('GPT模拟/ued_beamline_v2.py','shared/params.py','shared/constants.py','shared/beam_physics.py','shared/diagnostics.py','shared/beam_result.py','shared/rf_model.py')
    matches={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==ctx['source_sha256'][p] for p in relevant}
    runtime={}
    for name in ctx['dependency_versions']:
        try:runtime[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:runtime[name]='unavailable'
    unknown=[name for name,v in ctx['dependency_versions'].items() if v=='unavailable' or runtime[name]=='unavailable']
    versions={name:runtime[name]==v and name not in unknown for name,v in ctx['dependency_versions'].items()}
    return old,dict(source_and_versions_match=all(matches.values()) and all(versions.values()),sources=matches,versions=versions,unknown_dependency_versions=unknown,missing_version_policy='do not reuse; rerun controls',
                    original_file=str(path),original_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),sentinel_repeats={})

def mean_interval(values):
    from scipy.stats import t as student_t
    a=np.asarray(values,float)
    if a.size<2:return dict(n=int(a.size),mean=float(a.mean()) if a.size else None,halfwidth95=None)
    return dict(n=int(a.size),mean=float(a.mean()),halfwidth95=float(student_t.ppf(.975,a.size-1)*a.std(ddof=1)/np.sqrt(a.size)))


def summarize(records):
    targets={'sigma_x_um':5.,'sigma_y_um':5.,'sigma_z_um':5.,'sigma_delta_e3':2.,
             'eps_nx_mm_mrad':5.,'eps_ny_mm_mrad':5.,'eps_nz_mm_mrad':None}
    def base(q,seed,n=50000):
        return next((r for r in records if r['spec']==dict(Q_fC=q,N=n,mesh=63,dz_m=.001,seed=seed)),None)
    result=[]
    for q in (0,1,10,100):
        cohort=[base(q,seed) for seed in SEEDS];cohort=[r for r in cohort if r is not None]
        if not cohort:continue
        controls={}
        if q:
            for label,n,m,d in [('N',20000,63,.001),('mesh',50000,95,.001),('dz',50000,63,.0005)]:
                controls[label]=next((r for r in records if r['spec']==dict(Q_fC=q,N=n,mesh=m,dz_m=d,seed=42)),None)
        for field,target in targets.items():
            formal=[100*(r['AG']['endpoint'][field]/r['PIC']['endpoint'][field]-1) for r in cohort]
            matched=[100*(r['AG_matched_retained_moments'][field]/r['PIC']['endpoint'][field]-1) for r in cohort]
            fi=mean_interval(formal);mi=mean_interval(matched);pi=mean_interval([r['PIC']['endpoint'][field] for r in cohort])
            shifts={};growth_shifts={};ref=base(q,42)
            if ref:
                for label,r in controls.items():
                    if r is not None:
                        shifts[label]=100*(r['AG']['endpoint'][field]/r['PIC']['endpoint'][field]-ref['AG']['endpoint'][field]/ref['PIC']['endpoint'][field])
                        off=base(0,42,r['spec']['N']);ref_off=base(0,42)
                        if off is not None and ref_off is not None:
                            growth_shifts[label]=100*(r['PIC']['endpoint'][field]/off['PIC']['endpoint'][field]-ref['PIC']['endpoint'][field]/ref_off['PIC']['endpoint'][field])
            complete=(len(cohort)==5 and (q==0 or len(shifts)==3))
            budget=sum(abs(v) for v in shifts.values())
            envelope=None;status='pending'
            if complete and fi['halfwidth95'] is not None:
                envelope=[fi['mean']-fi['halfwidth95']-budget,fi['mean']+fi['halfwidth95']+budget]
                if target is None:status='no_fixed_target'
                elif max(abs(v) for v in envelope)<target:status='supported_in_this_case'
                elif envelope[0]>target or envelope[1]<-target:status='not_supported'
                else:status='borderline'
            gp=[];ga=[];gm=[]
            for r in cohort:
                off=base(0,r['spec']['seed'])
                if off is not None:
                    gp.append(100*(r['PIC']['endpoint'][field]/off['PIC']['endpoint'][field]-1))
                    ga.append(100*(r['AG']['endpoint'][field]/off['AG']['endpoint'][field]-1))
                    gm.append(100*(r['AG_matched_retained_moments'][field]/off['AG_matched_retained_moments'][field]-1))
            result.append(dict(Q_fC=q,field=field,target_percent=target,PIC=pi,AG_relative_error_percent=fi,
                matched_relative_error_percent=mi,observed_control_error_shifts_percent=shifts,
                empirical_error_envelope_percent=envelope,screening_status=status,
                PIC_paired_growth_percent=mean_interval(gp),AG_paired_growth_percent=mean_interval(ga),
                matched_paired_growth_percent=mean_interval(gm),observed_control_growth_shifts_percent=growth_shifts,
                growth_control_shift_sum_percent=sum(abs(v) for v in growth_shifts.values())))
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--reuse',type=Path);args=ap.parse_args()
    out=args.out;out.mkdir(parents=True,exist_ok=True);old,gate=reuse_gate(args.reuse);write(out/'reuse_gate.json',gate)
    specs=[(0,50000,63,.001,s) for s in SEEDS]+[(0,20000,63,.001,42)]
    specs += [(q,50000,63,.001,s) for q in (1,10,100) for s in SEEDS]
    specs += [(q,n,m,d,42) for q in (1,10) for n,m,d in ((20000,63,.001),(50000,95,.001),(50000,63,.0005))]
    specs += [(100,n,m,d,42) for n,m,d in ((20000,33,.001),(20000,63,.001),(50000,95,.001),(50000,63,.0005))]
    records=[];clouds={};nominal={}
    for number,(q,n,mesh,dz,seed) in enumerate(specs,1):
        t=time.monotonic();c=case_config(q,n,mesh,dz,seed);spec=dict(Q_fC=q,N=n,mesh=mesh,dz_m=dz,seed=seed)
        name=f'q{q}_n{n}_m{mesh}_dz{dz:g}_s{seed}';file=out/'cases'/(name+'.json')
        if file.exists():
            record=json.loads(file.read_text());assert record['config_sha']==config_sha(c)
            if q==0:clouds[(n,seed)]=record['PIC']['initial']
        else:
            eligible=(q==100 and (n,mesh,dz)!=(50000,63,.001) and seed==42
                      and gate['source_and_versions_match'] and all(gate['sentinel_repeats'].get(str(qq),{}).get('passed',False) for qq in (10,100)))
            previous=next((r for r in old if all(r[k]==v for k,v in spec.items())),None)
            if eligible and previous:
                cloud=clouds[(n,seed)];assert cloud['raw_sha256']==previous['initial_raw_sha256']
                pic=dict(endpoint=previous['PIC'],initial_raw_sha256=cloud['raw_sha256'],initial=cloud,
                         origin='reused_PIC_control_only',history=None,meta=None,residual=None,
                         evidence=dict(file=gate['original_file'],sha256=gate['original_sha256'],spec=spec))
            else:
                pic,cloud=run_pic(c)
            if q==0:clouds[(n,seed)]=cloud
            else:assert cloud['raw_sha256']==clouds[(n,seed)]['raw_sha256']
            if q not in nominal:
                with contextlib.redirect_stdout(io.StringIO()):a=run_ag(c,'full',n_points=101)
                nominal[q]=dict(reuse_semantics='formal AG evaluated once per physical charge; N, mesh, dz and seed variants affect PIC only; meta preserves actual AG run config',endpoint={k:float(getattr(a,k)[-1]) for k in FIELDS},history=a.history(),meta=a.meta)
            record=dict(spec=spec,config_sha=config_sha(c),PIC=pic,AG=nominal[q],AG_matched_retained_moments=matched_ag(q,cloud),seconds=time.monotonic()-t)
            write(file,record)
        if q in (10,100) and (n,mesh,dz,seed)==(50000,63,.001,42):
            previous=next(r for r in old if all(r[k]==v for k,v in spec.items())) if old else None
            if previous:
                diffs={k:float(abs(record['PIC']['endpoint'][k]/previous['PIC'][k]-1)) for k in FIELDS}
                passed=(record['PIC']['initial_raw_sha256']==previous['initial_raw_sha256'] and max(diffs.values())<1e-12)
                gate['sentinel_repeats'][str(q)]=dict(passed=passed,max_relative_difference=max(diffs.values()))
                write(out/'reuse_gate.json',gate)
        records.append(record);write(out/'records.json',records)
        print(f'{number}/{len(specs)} {name} {record["PIC"]["origin"]} {time.monotonic()-t:.1f}s delta={record["PIC"]["endpoint"]["sigma_delta_e3"]:.8g} epsnz={record["PIC"]["endpoint"]["eps_nz_mm_mrad"]:.8g}',flush=True)
    print('All short cases completed; thresholds/config/models were not modified.',flush=True)
    return 0
if __name__=='__main__':sys.exit(main())

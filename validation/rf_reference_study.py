"""C1: six formal short trajectories, then independent RF-only analysis.

Capture and analysis are separate: reanalyzing frozen event snapshots never
reruns a trajectory. No production physics or particle coordinates are changed.
See rf_gaussian_reference_physics_note.md and the pre-run calculation card.
"""
import argparse
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import platform
import sys
import time
from unittest.mock import patch
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from validation.rf_gaussian_reference import (gaussian_reference,
    compare_references, time_kick_on_cloud, cloud_moments,
    iid_clt_halfwidth95, tabulated_sampler_reference, sampler_interval_reference)

CASES = (30., 300., 3000.)
METRICS = ('sigma_delta', 'chirp_per_m', 'sigma_uncorrelated_delta', 'eps_nz_mm_mrad')
MOMENTS = ('A_m2', 'B', 'C_m', 'chirp_per_m', 'sigma_delta',
           'sigma_uncorrelated_delta', 'eps_nz_mm_mrad', 'D_m2')


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n')


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def state(beam):
    return {k:float(getattr(beam,k)) for k in
        ('sigma_z','sigma_delta','C_zd','nu_z','gamma','beta','eps_nz')}


def state_moments(s):
    A, B, C = s['sigma_z']**2, s['sigma_delta']**2, s['C_zd']
    W = B-C*C/A
    if W <= 0:
        raise ValueError('nonpositive captured AG residual variance')
    return dict(A_m2=A,B=B,C_m=C,chirp_per_m=C/A,sigma_delta=np.sqrt(B),
        sigma_uncorrelated_delta=np.sqrt(W),D_m2=A*W,
        eps_nz_mm_mrad=s['beta']*s['gamma']*np.sqrt(A*W)*1e6,
        state_eps_nz_mm_mrad=s['eps_nz']*1e6,
        nu_relation_relative=abs(s['nu_z']-C/(s['gamma']**2*np.sqrt(A)))/
            max(abs(s['nu_z']),1e-80))


def config_for(sigma_um):
    from shared.params import load_config
    cfg = deepcopy(load_config())
    rf = deepcopy(next(e for e in cfg['lattice']['elements'] if e['type']=='rf_cavity'))
    rf.update(z_start=0.,length=.022)
    cfg['lattice']['elements'] = [
        dict(name='cathode',type='cathode',z_start=0.,length=0.,parameters={}),
        rf, dict(name='sample',type='sample',z_start=.022,length=0.,parameters={})]
    cfg['beam'].update(energy_keV=100.,charge_fC=100.,n_particles=50000)
    cfg['initial_distribution'].update(bunch_length_um=sigma_um,spot_rms_um=85.,
        sigma_delta=1e-4,epsilon_n_mm_mrad=.08)
    cfg['space_charge']['enabled'] = False
    cfg['physics_switches'].update(rf_longitudinal_kick=True,rf_transverse_kick=False)
    cfg['output'].update(z_diagnostics_mm=[0.,22.],step_size_m=.001)
    cfg['random']['seed'] = 42
    return cfg


def assert_saved_contract(saved, cfg):
    from shared.params import config_sha
    assert saved['config_sha'] == config_sha(cfg)
    assert saved['sc_enabled'] is False
    assert saved['meta']['sc_effective'] is False
    events = saved['meta']['rf_events']
    assert len(events)==1 and events[0]['instance']=='rf1'
    assert abs(events[0]['z_actual_m']) < 1e-15
    assert abs(saved['history']['z_mm'][-1]-22.) < 1e-10
    assert len(saved['probes']) == 2
    for probe in saved['probes']:
        assert abs(probe.get('z_actual_mm',probe['z_mm'])-probe['z_mm']) < 1e-10
    assert saved['meta']['switches']['rf_longitudinal_kick'] is True
    assert saved['meta']['switches']['rf_transverse_kick'] is False


def capture(out):
    """Exactly three cases x two CLI functions. Refuse accidental reruns."""
    receipt = out/'execution.json'
    if receipt.exists() or (out/'runs').exists():
        raise FileExistsError('capture already started; analyze existing snapshots, do not rerun')
    from AG import run_shared, runner
    oc = importlib.import_module('GPT模拟.ued_beamline_v2')
    core = sys.modules['beam_dynamics_6d']
    from shared.beam_physics import BeamReference
    from shared.constants import M_E_SI, E_SI, C_SI
    from shared.ocelot_coords import get_tau, get_p_oc
    import scipy
    import mpmath
    import ocelot
    from ocelot.cpbd.beam import generate_parray
    import ocelot.common.math_op as math_op
    version = dict(python=platform.python_version(),numpy=np.__version__,
        scipy=scipy.__version__,mpmath=mpmath.__version__,
        ocelot=getattr(ocelot,'__version__','unavailable'))
    sources = {str(p.relative_to(ROOT)):file_hash(p) for p in ROOT.rglob('*.py')
               if p.parts[len(ROOT.parts)] in ('AG','shared','GPT模拟','validation')
               and '__pycache__' not in p.parts}
    sampler_sources = {}
    for name, fn in [('generate_parray',generate_parray),('invert_cdf',math_op.invert_cdf)]:
        p = Path(inspect.getsourcefile(fn))
        sampler_sources[name] = dict(path=str(p),sha256=file_hash(p))
        (out/f'{name}_source.txt').write_text(inspect.getsource(fn))
    record = dict(status='running',formal_trajectory_budget=6,versions=version,
        source_root=str(ROOT),source_sha256=sources,sampler_sources=sampler_sources,runs=[])
    dump(receipt,record)
    real_ag, real_oc = core.apply_rf_thin_lens, oc.apply_rf_kick
    for sigma_um in CASES:
        cfg = config_for(sigma_um)
        case = out/'runs'/f'sigma_{sigma_um:g}um'
        dump(case/'config.json',cfg)
        for route in ('AG','OCELOT'):
            run_dir=case/route
            run_dir.mkdir(parents=True)
            observed=[]
            started=time.time()
            with (run_dir/'cli.log').open('w') as log, redirect_stdout(log), redirect_stderr(log):
                if route=='AG':
                    def observer(beam,H):
                        before=state(beam)
                        result=real_ag(beam,H)
                        assert state(beam)==before, 'AG input mutated by RF'
                        observed.append(dict(before=before,after=state(result),H_received=float(H)))
                        return result
                    with patch.object(core,'apply_rf_thin_lens',observer):
                        path=run_shared.main(out_dir=str(run_dir),cfg_override=deepcopy(cfg))
                    br=BeamReference.from_energy_keV(cfg['beam']['energy_keV'])
                    reference=dict(beta=br.beta,gamma=br.gamma,
                        energy_total_eV=br.gamma*M_E_SI*C_SI**2/E_SI,
                        normalization_beta_gamma=observed[0]['before']['beta']*observed[0]['before']['gamma'])
                else:
                    def observer(parray,rf_elem,rf_transverse=False,rf_longitudinal=True,ref=None):
                        before=parray.rparticles.copy()
                        weights=parray.q_array.copy()
                        result=real_oc(parray,rf_elem,rf_transverse,rf_longitudinal,ref=ref)
                        after=parray.rparticles.copy()
                        assert np.array_equal(before[:5],after[:5]), 'RF changed nonlongitudinal coordinates'
                        assert np.array_equal(weights,parray.q_array), 'RF changed weights'
                        assert np.all(weights==weights[0]), 'IID uncertainty requires equal weights'
                        np.savez_compressed(run_dir/'rf_event_cloud.npz',tau_before=before[4],
                            p_oc_before=before[5],tau_after=get_tau(parray).copy(),
                            p_oc_after=get_p_oc(parray).copy(),weights=weights)
                        observed.append(dict(reference={k:float(ref[k]) for k in
                            ('beta','gamma','E_total_eV')},nonlongitudinal_unchanged=True,
                            weights_unchanged=True,rf_transverse=rf_transverse,
                            rf_longitudinal=rf_longitudinal))
                        return result
                    with patch.object(oc,'apply_rf_kick',observer):
                        path=oc.main(out_dir=str(run_dir),cfg_override=deepcopy(cfg),step=3)
                    r=observed[0]['reference']
                    reference=dict(beta=r['beta'],gamma=r['gamma'],energy_total_eV=r['E_total_eV'])
            assert len(observed)==1, 'expected exactly one actual RF call'
            dump(run_dir/'rf_event.json',dict(route=route,observations=observed,reference=reference))
            saved=json.loads(Path(path).read_text())
            assert_saved_contract(saved,cfg)
            record['runs'].append(dict(sigma_z_um=sigma_um,route=route,
                result=str(Path(path).relative_to(out)),result_sha256=file_hash(path),
                event_snapshot=str((run_dir/'rf_event.json').relative_to(out)),
                actual_rf_calls=len(observed),cli_function_returned=True,
                contract_checks_passed=True,seconds=time.time()-started))
            dump(receipt,record)
            print(f'captured {route} sigma={sigma_um:g}um ({len(record["runs"])}/6)',flush=True)
    assert len(record['runs'])==6
    record['status']='complete'
    dump(receipt,record)


def parameter_bundle(cfg, reference):
    pv=next(e['parameters'] for e in cfg['lattice']['elements'] if e['type']=='rf_cavity')
    return dict(sigma_z_m=cfg['initial_distribution']['bunch_length_um']*1e-6,
        sigma_delta=cfg['initial_distribution']['sigma_delta'],covariance_m=0.,
        voltage_V=pv['voltage_kV']*1000,frequency_Hz=pv['frequency_GHz']*1e9,
        phase_rad=pv['phase_rad'],**reference)


def moment_differences(candidate,reference):
    """Nonzero reference moments for this card; nearzero mean uses sigma scale."""
    out={k:float(abs(candidate[k]-reference[k])/abs(reference[k])) for k in MOMENTS}
    if 'mean_delta' in candidate:
        out['mean_delta_scaled_by_sigma']=float(abs(candidate['mean_delta']-reference['mean_delta'])/
                                               reference['sigma_delta'])
    return out


def analyze(out):
    receipt=json.loads((out/'execution.json').read_text())
    assert receipt['status']=='complete' and len(receipt['runs'])==6
    analysis=dict(scope='instantaneous fixed-reference RF; SC off; no exit-drift comparison',
        cases=[],checks=[],formal_trajectories=6,
        uncertainty='single-cloud pointwise asymptotic iid/CLT 95%; not multiseed or joint coverage')
    def check(name,value,limit):
        analysis['checks'].append(dict(name=name,value=float(value),limit=limit,passed=bool(value<=limit)))
    for sigma_um in CASES:
        case=out/'runs'/f'sigma_{sigma_um:g}um'
        cfg=json.loads((case/'config.json').read_text())
        row=dict(sigma_z_um=sigma_um,routes={})
        for route in ('AG','OCELOT'):
            d=case/route
            event=json.loads((d/'rf_event.json').read_text())
            run=next(r for r in receipt['runs'] if r['sigma_z_um']==sigma_um and r['route']==route)
            assert file_hash(out/run['result'])==run['result_sha256']
            saved=json.loads((out/run['result']).read_text())
            assert_saved_contract(saved,cfg)
            p=parameter_bundle(cfg,event['reference'])
            q45=gaussian_reference(**p,method='quadrature',dps=45)
            q65=gaussian_reference(**p,method='quadrature',dps=65)
            exact=gaussian_reference(**p,method='analytic',dps=65)
            linear=gaussian_reference(**p,method='linear',dps=65)
            error45=compare_references(q45,q65)
            error65=compare_references(q65,exact)
            check(f'{sigma_um:g}/{route}/quadrature45vs65',max(error45.values()),1e-25)
            check(f'{sigma_um:g}/{route}/quadrature65vsanalytic',max(error65.values()),1e-25)
            references=dict(parameters=p,quadrature45=q45,quadrature65=q65,analytic65=exact,
                linear65=linear,relative_error45vs65=error45,relative_error65vsanalytic=error65)
            actual=dict(reference=event['reference'])
            if route=='AG':
                s=event['observations'][0]
                before,after=state_moments(s['before']),state_moments(s['after'])
                diff=moment_differences(after,linear['values'])
                check(f'{sigma_um:g}/AG/moments_vs_linear',max(diff.values()),1e-10)
                check(f'{sigma_um:g}/AG/H',abs(s['H_received']/linear['values']['H_linear_per_m']-1),1e-10)
                check(f'{sigma_um:g}/AG/nu_constraint',after['nu_relation_relative'],1e-10)
                check(f'{sigma_um:g}/AG/state_emittance',abs(after['state_eps_nz_mm_mrad']/linear['values']['eps_nz_mm_mrad']-1),1e-10)
                actual.update(before=before,after=after,implementation_relative=diff,H_received=s['H_received'])
                history_side='after_RF'
            else:
                cloud=np.load(d/'rf_event_cloud.npz')
                beta=p['beta'];bg=beta*p['gamma']
                z=-beta*cloud['tau_before'];delta=cloud['p_oc_before']/beta
                za=-beta*cloud['tau_after'];da=cloud['p_oc_after']/beta
                independent=time_kick_on_cloud(z,delta,**{k:p[k] for k in
                    ('beta','energy_total_eV','voltage_V','frequency_Hz','phase_rad')})
                max_residual=float(np.max(abs(da-independent)))
                before=cloud_moments(z,delta,bg,cloud['weights'])
                after=cloud_moments(za,da,bg,cloud['weights'])
                same=cloud_moments(z,independent,bg,cloud['weights'])
                diff=moment_differences(after,same)
                check(f'{sigma_um:g}/OCELOT/pointwise_delta',max_residual,1e-14)
                check(f'{sigma_um:g}/OCELOT/moments_same_cloud',max(diff.values()),1e-10)
                sp={k:v for k,v in p.items() if k not in ('covariance_m','normalization_beta_gamma')}
                sampler8=tabulated_sampler_reference(**sp,order=8)
                sampler16=tabulated_sampler_reference(**sp,order=16)
                sampler_hp=sampler_interval_reference(**sp,dps=65)
                sampler_errors={k:abs(sampler8['values'][k]/sampler16['values'][k]-1) for k in METRICS}
                check(f'{sigma_um:g}/sampler/GL8vs16',max(sampler_errors.values()),1e-12)
                sampler_hp_errors={k:abs(sampler16['values'][k]/sampler_hp['values'][k]-1) for k in METRICS}
                check(f'{sigma_um:g}/sampler/GLvs_highprecision',max(sampler_hp_errors.values()),1e-12)
                check(f'{sigma_um:g}/sampler/mean_scaled_by_sigma',
                    abs(sampler16['values']['mean_delta']-sampler_hp['values']['mean_delta'])/
                    sampler_hp['values']['sigma_delta'],1e-12)
                references.update(sampler8=sampler8,sampler16=sampler16,sampler_highprecision=sampler_hp,
                    sampler_order_relative=sampler_errors,sampler_highprecision_relative=sampler_hp_errors)
                ci=iid_clt_halfwidth95(za,da,bg)
                actual.update(before=before,after=after,same_cloud_reference=same,
                    implementation_relative=diff,max_pointwise_delta_residual=max_residual,
                    iid_clt95_halfwidth=ci,
                    sample_minus_sampler_population={k:after[k]-sampler16['values'][k] for k in METRICS},
                    sample_deviation_over_halfwidth={k:(after[k]-sampler16['values'][k])/ci[k] for k in METRICS},
                    sampler_vs_infinite_gaussian_relative={k:sampler16['values'][k]/exact['values'][k]-1 for k in METRICS},
                    measured_initial_sigma_z_um=np.sqrt(before['A_m2'])*1e6)
                history_side='before_RF'
            # Saved histories must be interpreted on their actual event side.
            h0={k:saved['history'][k][0] for k in
                ('z_mm','sigma_z_um','sigma_delta_e3','C_zdelta_m','chirp_per_m','eps_nz_mm_mrad')}
            expected=after if history_side=='after_RF' else before
            check(f'{sigma_um:g}/{route}/history0_event_side',
                abs(h0['sigma_delta_e3']*1e-3/expected['sigma_delta']-1),1e-10)
            actual.update(saved_history0=h0,saved_history0_side=history_side,
                          saved_result=run['result'])
            dump(d/'independent_references.json',references)
            row['routes'][route]=actual
            if route=='OCELOT':
                # Same constants and ideal Gaussian on both sides: pure approximation.
                row['common_reference']=dict(linear=linear['values'],sine=exact['values'])
                row['linear_minus_sine_relative']={k:linear['values'][k]/exact['values'][k]-1 for k in METRICS}
                row['sigma_delta_screen_2pct_supported']=abs(row['linear_minus_sine_relative']['sigma_delta'])<=.02
                row['phase_rms_rad']=exact['values']['phase_rms_rad']
        ar,pr=row['routes']['AG']['reference'],row['routes']['OCELOT']['reference']
        row['normalization_differences_ppm']=dict(
            H_AG_vs_OC=(row['routes']['AG']['H_received']/row['common_reference']['linear']['H_linear_per_m']-1)*1e6,
            beta_gamma_AG_vs_OC=(ar['normalization_beta_gamma']/(pr['beta']*pr['gamma'])-1)*1e6,
            RF_energy_AG_vs_OC=(ar['energy_total_eV']/pr['energy_total_eV']-1)*1e6)
        analysis['cases'].append(row)
        print(f'analyzed sigma={sigma_um:g}um',flush=True)
    analysis['all_mathematical_checks_passed']=all(c['passed'] for c in analysis['checks'])
    analysis['analysis_source_sha256']={str(p.relative_to(ROOT)):file_hash(p) for p in
        (Path(__file__),Path(__file__).with_name('rf_gaussian_reference.py'))}
    dump(out/'analysis.json',analysis)
    if not analysis['all_mathematical_checks_passed']:
        raise AssertionError('mathematical checks failed; inspect analysis.json')
    return analysis


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('capture','analyze'))
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if not args.out.is_absolute():
        parser.error('--out must be absolute')
    args.out.mkdir(parents=True,exist_ok=True)
    if args.mode=='capture':capture(args.out)
    else:analyze(args.out)


if __name__=='__main__':main()

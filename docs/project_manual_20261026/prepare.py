"""Freeze documentary evidence and exact source excerpts; never run a driver."""
from pathlib import Path
import ast, hashlib, importlib.metadata as md, json, platform, shutil, subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
HISTORY = Path('/Users/qin/Documents/Codex/2026-10-04/ued-beam-dynamics-ocelot-ag-astra/outputs')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args): return subprocess.check_output(['git', *args], cwd=ROOT).decode().strip()
def dump(name, x): (HERE/name).write_text(json.dumps(x, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def esc(x):
    return str(x).replace('\\', r'\textbackslash{}').replace('&', r'\&').replace('%', r'\%').replace('_', r'\_').replace('#', r'\#')

all_names = git('ls-files','--cached','--others','--exclude-standard','-z').split('\0')
protected = {n:sha(ROOT/n) for n in all_names if n and not n.startswith(('docs/', '.scratch/')) and (ROOT/n).is_file()}
dump('protected_before.json', protected)
core = [*sorted(ROOT.glob('shared/*.py')),
        *[ROOT/'AG'/n for n in ['runner.py','run_shared.py','beam_dynamics_6d.py','external_forces.py','beamline_sim.py','longitudinal_state.py','alpha_coefficients.py']],
        ROOT/'GPT模拟/ued_beamline_v2.py', ROOT/'validation/backend.py', ROOT/'validation/run_all.py',
        *sorted(ROOT.glob('validation/test_*.py')), ROOT/'validation/rf_gaussian_reference.py',
        ROOT/'validation/alpha_reference.py', ROOT/'validation/reference.py',
        ROOT/'validation/common.py', ROOT/'validation/config_check.py', ROOT/'LICENSE', ROOT/'CALCULATION_CARD_TEMPLATE.md',
        *sorted(ROOT.glob('gui/*.py')), *sorted(ROOT.glob('gui/web/*')),
        ROOT/'run_gui.py', ROOT/'shared/beamline_config.yaml', ROOT/'requirements-gui.txt',
        ROOT/'启动界面.command', ROOT/'启动界面.bat', ROOT/'安装环境.bat', ROOT/'运行GUI测试.bat']
notes = [ROOT/'README.md', ROOT/'PROJECT_STATUS.md', ROOT/'AI_HANDOFF.md', ROOT/'AGENTS.md',
         ROOT/'gui/README.md', ROOT/'gui/WINDOWS.md', ROOT/'shared/geometry_contract.md',
         *sorted(ROOT.glob('*CHANGELOG*.md')), *sorted(ROOT.glob('AG/*physics_note.md')),
         *sorted(ROOT.glob('shared/*physics_note.md')), *sorted(ROOT.glob('GPT模拟/*physics_note.md')),
         *sorted(ROOT.glob('validation/*physics_note.md'))]
manifest=[]
for p in sorted(set(core+notes)):
    if not p.is_file(): raise FileNotFoundError(p)
    rel=p.relative_to(ROOT); dest=HERE/'source_snapshot'/rel
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    manifest.append({'path':str(rel),'sha256':sha(p),'bytes':p.stat().st_size})
dump('source_manifest.json',manifest)
(HERE/'snapshot_info.tex').write_text(r'\newcommand{\SourceCount}{'+str(len(manifest))+'}\n',encoding='utf-8')
dump('version.json',{'date':'2026-10-26','root':str(ROOT),'head':git('rev-parse','HEAD'),
    'branch':git('branch','--show-current'),'status_at_capture':git('status','--short'),
    'python':platform.python_version(),'platform':platform.platform(),
    'packages':{k:md.version(k) for k in ['numpy','scipy','matplotlib','PyYAML','ocelot-collab']},
    'document_version':'1.1','github_reviewed_head':'b4aa241fc8e3ca8e3aad98ecdf6c1e058a56c51f',
    'engineering_complete_10mm_runs':4,'engineering_interrupted_sc_calls':4,
    'new_complete_sc_studies':0,'physical_source_edits_this_document':0})

evidence = {
 'E01':['implementation_20261021/report.html'],
 'E02':['alpha_accuracy_20261022/report.html'],
 'E03':['rf_reference_20261024/report.html'],
 'E04':['beamline_acceptance_20261024/report.html'],
 'E05':['ag_emittance_closure_20261025/analysis.json','ag_emittance_closure_20261025/report.html'],
 'E06':['ocelot_method_acceptance_20261025/report.html'],
 'E07':['ocelot_sc_local_20261025/analysis.json','ocelot_sc_local_20261025/report.html'],
 'E08':['ocelot_stability_20261025/analysis.json','ocelot_stability_20261025/specs.json',
        'ocelot_stability_20261025/saved_verification.json','ocelot_stability_20261025/ledger.json',
        'ocelot_stability_20261025/runs/combined/termination.json'],
 'E09':['gui_mvp_20261025/acceptance.json','gui_mvp_20261025/tracking_cancel_qa.json',
        'gui_mvp_20261025/installed_browser_qa.json']}
receipts=[]
for eid, names in evidence.items():
 for name in names:
    p=HISTORY/name
    if not p.exists():
        receipts.append({'id':eid,'path':str(p),'available':False});continue
    dest=HERE/'evidence'/eid/p.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    receipts.append({'id':eid,'path':str(p),'local':str(dest.relative_to(HERE)),'sha256':sha(p),'available':True})
p=ROOT/'.scratch/test_evidence_20261025.log'
if p.exists():
 dest=HERE/'evidence/E10/windows_test_log.txt';dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
 receipts.append({'id':'E10','path':str(p),'local':str(dest.relative_to(HERE)),'sha256':sha(p),'available':True})
for name in ['REVIEW.md','test_summary.json','math_review.json','unit_tests.log','e2e_tests.log','before_repro.json','context.json']:
 p=ROOT/'docs/review_20261026'/name;dest=HERE/'evidence/E11'/name
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
 receipts.append({'id':'E11','path':str(p),'local':str(dest.relative_to(HERE)),'sha256':sha(p),'available':True})
dump('evidence_manifest.json',receipts)

# Exact lines from the captured files; numbers are ORIGINAL source line numbers.
specs=[
 ('entry','正式入口适配','validation/backend.py','run_ag'),
 ('geometry','共同几何校验','shared/geometry.py', (39,62)),
 ('state','AG 活动状态重建与配对面积演化','AG/beam_dynamics_6d.py',(1024,1051)),
 ('g','AG 三方向面积变化率','AG/beam_dynamics_6d.py','space_charge_area_log_rates'),
 ('force','AG 高斯 SC 纵向力及其上下文','AG/beam_dynamics_6d.py',(318,340)),
 ('alpha','直接积分及域外保护','AG/alpha_coefficients.py',(51,100)),
 ('rfshared','共同 RF 系数与正弦调制','shared/rf_model.py',(11,27)),
 ('rfag','AG 协方差薄透镜','AG/beam_dynamics_6d.py','apply_rf_thin_lens'),
 ('method','OCELOT 实际传输方法守门','GPT模拟/ued_beamline_v2.py',(195,209)),
 ('schedule','OCELOT 原生 SC 调度','GPT模拟/ued_beamline_v2.py',(518,536)),
 ('diagnostic','共同中心矩与纵向输出','shared/diagnostics.py',(22,42)),
 ('worker','GUI 调用正式模型','gui/worker.py','run_job'),
 ('platform','Windows 父进程存活检查（尚待实机验收）','gui/platform_compat.py','ParentMonitor')]
snippets=[]; lines=[]
for sid,title,name,selection in specs:
 p=HERE/'source_snapshot'/name; src=p.read_text(encoding='utf-8').splitlines()
 if isinstance(selection,str):
    node=next(n for n in ast.walk(ast.parse('\n'.join(src))) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) and n.name==selection)
    start,end=node.lineno,node.end_lineno
 else: start,end=selection
 dest=HERE/'snippets'/f'{sid}.txt';dest.parent.mkdir(exist_ok=True)
 dest.write_text('\n'.join(src[start-1:end])+'\n',encoding='utf-8')
 snippets.append({'id':sid,'title':title,'path':name,'start':start,'end':end,'sha256':sha(p)})
 lines.extend([rf'\Needspace{{7\baselineskip}}\subsection{{{title}}}\label{{code:{sid}}}',
               rf'\noindent 原文件：\path{{{name}}}，第 {start}--{end} 行。以下逐字摘录，行号保留原编号。',
               rf'\VerbatimInput[firstnumber={start}]{{snippets/{sid}.txt}}',''])
(HERE/'appendix_code.tex').write_text('\n'.join(lines),encoding='utf-8')
dump('code_excerpts.json',snippets)
print(json.dumps({'snapshot_files':len(manifest),'protected_files':len(protected),'evidence_files':len(receipts),'missing_evidence':[r['path'] for r in receipts if not r['available']]},ensure_ascii=False))

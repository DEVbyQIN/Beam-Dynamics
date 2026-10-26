"""Documentation only: conceptual contours and a table from frozen JSON."""
from pathlib import Path
import json, os, subprocess
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/ued-manual-mpl')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

HERE=Path(__file__).resolve().parent
font_path=subprocess.check_output(['kpsewhich','FandolHei-Regular.otf'],text=True).strip()
font=FontProperties(fname=font_path)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':3})
fig,axes=plt.subplots(1,3,figsize=(10,3.2))
t=np.linspace(0,2*np.pi,600)
for i,(ax,title) in enumerate(zip(axes,['初始：无相关','线性 RF：倾斜','非线性 RF：弯曲'])):
 for r in [.45,.75,1.]:
  x=r*np.cos(t); y=.17*r*np.sin(t)
  if i==1:y=y+.75*x
  if i==2:y=y+.75*x-.55*x**3
  ax.plot(x,y,color=['#547e96','#22766b','#9b612f'][i],lw=1.2,alpha=.55+.4*r)
 ax.axhline(0,color='#b7c8c7',lw=.6);ax.axvline(0,color='#b7c8c7',lw=.6)
 ax.set(xlim=(-1.2,1.2),ylim=(-1.05,1.05),xticks=[],yticks=[],xlabel=r'$\zeta$ (arbitrary units)',ylabel=r'$\delta_p$')
 ax.set_title(title,fontproperties=font,pad=12)
fig.tight_layout(w_pad=2)
(HERE/'figures').mkdir(exist_ok=True)
fig.savefig(HERE/'figures/phase_space.pdf',bbox_inches='tight')
fig.savefig(HERE/'figures/phase_space.png',dpi=180,bbox_inches='tight');plt.close(fig)

data=json.loads((HERE/'evidence/E08/analysis.json').read_text())
sample=data['planes']['sample']
fields=[('sigma_x_um',r'$\sigma_x$ [$\mu$m]'),('sigma_y_um',r'$\sigma_y$ [$\mu$m]'),
 ('sigma_z_um',r'$\sigma_\zeta$ [$\mu$m]'),('chirp_per_m',r'$h$ [m$^{-1}$]'),
 ('sigma_delta_e3',r'$\sigma_\delta$ [$10^{-3}$]'),('eps_nx_mm_mrad',r'$\varepsilon_{nx}$ [$\mmemit$]'),
 ('eps_ny_mm_mrad',r'$\varepsilon_{ny}$ [$\mmemit$]'),('eps_nz_mm_mrad',r'$\varepsilon_{n,p}$ [$\mmemit$]')]
lines=[r'\begin{table}[H]\centering\small',r'\begin{tabular}{lrr}\toprule',
 r'样品面观测量 & 基准值 & 已完成控制相对基准最大绝对变化 \\ \midrule']
for key,label in fields:
 v=sample[key];lines.append(f"{label} & {v['values']['baseline']:.7g} & {v['max_abs_percent']:.5g}\\% "+r'\\')
lines += [r'\bottomrule\end{tabular}',r'\caption{直接提取 E08 保存结果。最后一列是有限设置变化幅度，不是误差上界或置信区间。}',r'\end{table}']
(HERE/'sample_table.tex').write_text('\n'.join(lines)+'\n',encoding='utf-8')

manifest=json.loads((HERE/'source_manifest.json').read_text())
paths=['AG/runner.py','AG/run_shared.py','AG/beam_dynamics_6d.py','AG/external_forces.py','AG/alpha_coefficients.py',
 'AG/longitudinal_state.py','GPT模拟/ued_beamline_v2.py','shared/beamline_config.yaml','shared/params.py',
 'shared/geometry.py','shared/rf_model.py','shared/diagnostics.py','shared/beam_result.py','shared/output_schema.py',
 'shared/run_contract.py','shared/sc_state.py','shared/beam_physics.py','shared/ocelot_coords.py',
 'validation/backend.py','validation/run_all.py','gui/server.py','gui/worker.py','gui/platform_compat.py',
 'gui/web/app.js','requirements-gui.txt']
lookup={r['path']:r for r in manifest}
lines=[r'\begin{longtable}{P{91mm}rr}',r'\toprule 文件（相对 source\_snapshot） & 字节 & SHA256 前12位 \\ \midrule\endhead']
for path in paths:
 r=lookup[path];lines.append(r'\path{'+path+'} & '+str(r['bytes'])+r' & \texttt{'+r['sha256'][:12]+r'} \\')
lines += [r'\bottomrule\end{longtable}']
(HERE/'source_index.tex').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('Created conceptual diagram, sample table, source index; no driver calls.')

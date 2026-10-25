'use strict';
const $=s=>document.querySelector(s),clone=v=>JSON.parse(JSON.stringify(v)),esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let config,defaults,token,jobs=[],results={},viewFingerprint=null,metric='sigma_z_um',dirty=false,seen=new Set(),selectedElement=0,chartData=[],logJob=null;
const names={cathode:'初态面',drift:'漂移',solenoid:'磁透镜',rf_cavity:'RF 腔',sample:'样品面'},statusNames={queued:'排队中',running:'运行中',complete:'已完成',failed:'失败',cancelled:'已停止',timeout:'超时',interrupted:'上次中断'};
const metrics=[['sigma_z_um','束长','μm'],['sigma_x_um','横向束宽 x','μm'],['sigma_y_um','横向束宽 y','μm'],['chirp_per_m','chirp','1/m'],['sigma_delta_e3','动量展宽','×10⁻³'],['eps_nz_mm_mrad','纵向发射度','mm·mrad'],['eps_nx_mm_mrad','发射度 x','mm·mrad'],['eps_ny_mm_mrad','发射度 y','mm·mrad'],['C_zdelta_m','纵向相关矩','m'],['sigma_t_fs','RMS 时宽','fs']];
const fields=[['beam','energy_keV','动能','keV'],['beam','charge_fC','电荷幅值','fC'],['initial_distribution','spot_rms_um','横向束宽','μm'],['initial_distribution','bunch_length_um','束长','μm'],['initial_distribution','epsilon_n_mm_mrad','横向发射度','mm·mrad'],['initial_distribution','sigma_delta','相对动量展宽','Δp/p₀']];
const numeric=[['beam','n_particles','宏粒子数',''],['random','seed','随机种子',''],['output','step_size_m','追踪步长','mm'],['space_charge','step','SC 调用间隔','步']];
function message(text,error=false){const e=$('#message');e.textContent=text;e.className='message'+(error?' error':'');e.hidden=!text;}
async function api(path,body){const r=await fetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-UED-Token':token},body:JSON.stringify(body)});const d=await r.json();if(!r.ok)throw Error(d.error||'请求失败');return d;}
function markDirty(){dirty=true;$('#configState').textContent='工作配置已修改';$('#geometryState').textContent='待检查';$('#geometryState').className='pill';if(Object.keys(results).length)$('#resultContext').textContent='工作配置已修改；图中仍是上一次运行的结果。';drawBeamline();}
function fieldHTML(f){const [section,key,title,unit]=f;let v=config[section][key];if(key==='step_size_m')v*=1000;return `<label class="field">${title} <small>${unit}</small><input type="number" step="any" data-section="${section}" data-field="${key}" aria-label="${title}" value="${v}"></label>`;}
function renderConfig(){
 $('#beamFields').innerHTML=fields.map(fieldHTML).join('');$('#numericFields').innerHTML=numeric.map(fieldHTML).join('');
 $('#mesh').value=config.space_charge.mesh.join(', ');$('#probes').value=config.output.z_diagnostics_mm.join(', ');
 $('#switches').innerHTML=[['space_charge','enabled','空间电荷 SC'],['physics_switches','rf_longitudinal_kick','RF 纵向作用'],['physics_switches','rf_transverse_kick','RF 横向作用']].map(([s,k,t])=>`<label class="switch">${t}<input type="checkbox" data-section="${s}" data-switch="${k}" ${config[s][k]?'checked':''} aria-label="${t}"></label>`).join('');renderElements();drawBeamline();
 $('#configState').textContent=dirty?'工作配置已修改':'共享配置副本';
 if(Object.keys(results).length)$('#resultContext').textContent='工作配置已载入；图中仍保留之前运行的结果，尚未用此配置重新计算。';
}
function renderElements(){
 $('#elements').innerHTML=config.lattice.elements.map((e,i)=>{
  const ps=e.type==='solenoid'?[['B_field_T','磁场 / T']]:e.type==='rf_cavity'?[['frequency_GHz','频率 / GHz'],['voltage_kV','有效电压 / kV'],['phase_rad','相位 / rad']]:[];
  return `<tr data-row="${i}" class="${i===selectedElement?'selected-row':''}"><td><input data-key="name" value="${esc(e.name)}" aria-label="元件${i+1}名称"></td><td>${names[e.type]}</td><td><input type="number" step="any" data-key="z_start" value="${+(e.z_start*1000).toPrecision(12)}" aria-label="${esc(e.name)}入口"></td><td><input type="number" step="any" data-key="length" value="${+(e.length*1000).toPrecision(12)}" aria-label="${esc(e.name)}长度"></td><td><div class="params">${ps.map(([k,t])=>`<label>${t}<input type="number" step="any" data-param="${k}" value="${e.parameters[k]}" aria-label="${esc(e.name)}${t}"></label>`).join('')||'<span class="muted">—</span>'}</div></td><td>${['cathode','sample'].includes(e.type)?'':`<button data-remove="${i}" aria-label="删除${esc(e.name)}">×</button>`}</td></tr>`;
 }).join('');
}
function drawBeamline(){
 const es=config.lattice.elements,total=Math.max(.001,...es.map(e=>Number(e.z_start)+Number(e.length)).filter(Number.isFinite)),W=900,L=34,R=866,x=s=>L+(s/total)*(R-L);
 let out=`<svg viewBox="0 0 900 145" role="img" aria-label="束线示意"><defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto"><path d="M0,0 L0,6 L6,3z" fill="#a9bcb3"/></marker></defs><line x1="${L}" y1="64" x2="${R+12}" y2="64" stroke="#a9bcb3" stroke-width="2" marker-end="url(#arrow)"/>`;
 es.forEach((e,i)=>{if(!Number.isFinite(e.z_start)||!Number.isFinite(e.length))return;const start=x(e.z_start),end=x(e.z_start+e.length),mid=(start+end)/2;
  if(e.type==='drift')out+=`<text x="${mid}" y="88" text-anchor="middle" fill="#a1afa9" font-size="9">${esc(e.name)}</text>`;
  else{const color=e.type==='rf_cavity'?'#c38450':e.type==='solenoid'?'#408d7b':'#7a9890';out+=`<g data-element="${i}" tabindex="0" role="button" aria-label="选择${esc(e.name)}" style="cursor:pointer"><rect x="${start-5}" y="43" width="${Math.max(10,end-start+10)}" height="42" rx="5" fill="${color}" opacity=".15" stroke="${color}"/><line x1="${start}" y1="${e.type==='sample'?36:46}" x2="${start}" y2="${e.type==='sample'?91:82}" stroke="${color}" stroke-width="3"/><text x="${mid}" y="29" text-anchor="middle" fill="${color}" font-size="11">${esc(e.name)}</text><text x="${mid}" y="107" text-anchor="middle" fill="#738980" font-size="9">${+(e.z_start*1000).toPrecision(7)} mm</text></g>`;}
 });out+='<text x="34" y="134" fill="#91a49c" font-size="9">束线位置 s / mm · 示意按实际位置绘制</text></svg>';
 $('#beamline').innerHTML=out;const sample=es.find(e=>e.type==='sample');$('#sampleLabel').textContent='样品面 '+(sample?+(sample.z_start*1000).toPrecision(7)+' mm':'未设置');
}
async function validate(show=true){try{const d=await api('/api/validate',{config});config=d.config;$('#geometryState').textContent='输入与几何已检查';$('#geometryState').className='pill ok';if(show)message('检查通过。元件顺序连续，样品面与诊断位置合法。');return d;}catch(e){$('#geometryState').textContent='需要调整';$('#geometryState').className='pill error';message('输入或束线几何需要调整：\n'+e.message,true);throw e;}}
async function run(routes){try{await validate(false);const created=await api('/api/jobs',{config,routes});message('已提交 '+routes.join(' → ')+'。运行使用已保存的配置快照。');dirty=false;$('#configState').textContent='已提交运行快照';if(Object.keys(results).length)$('#resultContext').textContent='新任务正在运行；图中保留上一批已完成结果。';await poll();}catch(e){message(e.message,true);}}
function download(data,name,type='application/json'){const url=URL.createObjectURL(new Blob([data],{type})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function validResult(r){const h=r.history;if(!h||!Array.isArray(h.z_mm)||h.z_mm.length<2)throw Error('结果缺少完整轨迹');for(const [k] of metrics){if(h[k]&&(!Array.isArray(h[k])||h[k].length!==h.z_mm.length||h[k].some(v=>!Number.isFinite(v))))throw Error('结果数组或数值无效：'+k);}return r;}
async function loadJob(job,withConfig=false){
 try{
  if(withConfig){config=await api(`/api/jobs/${job.id}/config`);dirty=false;renderConfig();$('#configState').textContent='历史运行配置';}
  if(viewFingerprint!==job.config_fingerprint){results={};viewFingerprint=job.config_fingerprint;}
  const matching=jobs.filter(j=>j.batch===job.batch&&j.status==='complete');
  for(const j of matching.length?matching:[job])results[j.route]=validResult(await api(`/api/jobs/${j.id}/result`));
  $('#resultContext').textContent=`运行 ${job.batch.slice(0,8)} · 配置 ${job.config_fingerprint.slice(0,10)}${dirty?' · 工作配置已有修改':''}`;renderResults();
 }catch(e){message('结果读取失败：'+e.message,true);}
}
function renderResults(){
 $('.metric-tabs').innerHTML=metrics.map(([k,t])=>`<button role="tab" aria-selected="${k===metric}" data-metric="${k}" class="${k===metric?'active':''}">${t}</button>`).join('');
 const cards=[['sigma_z_um','样品面束长','μm'],['chirp_per_m','样品面 chirp','1/m'],['sigma_delta_e3','动量展宽','×10⁻³'],['eps_nz_mm_mrad','纵向发射度','mm·mrad']];
 $('#metrics').innerHTML=cards.map(([k,t,u])=>`<div class="metric"><div class="label">${t}</div>${['AG','OCELOT'].map(r=>{const h=results[r]?.history,v=h?.[k]?.at(-1);return `<div><span class="route ${r==='OCELOT'?'oc':''}">${r}</span><span class="value">${Number.isFinite(v)?format(v):'—'}</span></div>`;}).join('')}<div class="unit">${u}</div></div>`).join('');drawChart();
}
function format(v){return v===0?'0':Math.abs(v)<.001||Math.abs(v)>1e5?v.toExponential(3):Number(v.toPrecision(6)).toLocaleString('en-US',{maximumFractionDigits:8});}
function drawChart(){
 const svg=$('#chart'),W=920,H=300,p={l:66,r:20,t:22,b:42},definition=metrics.find(x=>x[0]===metric);chartData=[];
 for(const route of ['AG','OCELOT']){const h=results[route]?.history;if(h?.[metric])chartData.push({route,x:h.z_mm,y:h[metric],color:route==='AG'?'#247f70':'#cb7848'});}
 $('#emptyChart').style.display=chartData.length?'none':'flex';$('#exportSVG').disabled=$('#exportPNG').disabled=!chartData.length;
 let xmin=Infinity,xmax=-Infinity,ymin=Infinity,ymax=-Infinity;for(const d of chartData){for(const v of d.x){xmin=Math.min(xmin,v);xmax=Math.max(xmax,v);}for(const v of d.y){ymin=Math.min(ymin,v);ymax=Math.max(ymax,v);}}if(!chartData.length){xmin=0;xmax=800;ymin=0;ymax=1;}
 if(xmin===xmax)xmax=xmin+1;const scale=Math.max(Math.abs(ymin),Math.abs(ymax),1e-9);if(ymax-ymin<scale*1e-5){const pad=scale*.03;ymin-=pad;ymax+=pad;}else{const pad=(ymax-ymin)*.08;ymin-=pad;ymax+=pad;}
 const x=v=>p.l+(v-xmin)/(xmax-xmin)*(W-p.l-p.r),y=v=>H-p.b-(v-ymin)/(ymax-ymin)*(H-p.t-p.b);
 let out=`<rect width="920" height="300" fill="white"/><text x="${p.l}" y="13" font-size="10" fill="#70857e">${esc(definition[1]+' / '+definition[2])}</text>`;
 chartData.forEach((d,i)=>{out+=`<line x1="${680+i*105}" x2="${698+i*105}" y1="10" y2="10" stroke="${d.color}" stroke-width="2"/><text x="${703+i*105}" y="14" fill="#60786e" font-size="10">${d.route}</text>`;});
 for(let i=0;i<5;i++){const v=ymin+(ymax-ymin)*i/4,yy=y(v),step=(ymax-ymin)/4,dp=Math.min(10,Math.max(0,Math.ceil(-Math.log10(step))+1)),tick=Math.abs(v)>1e6||(v!==0&&Math.abs(v)<1e-6)?v.toExponential(3):String(Number(v.toFixed(dp)));out+=`<line x1="${p.l}" x2="${W-p.r}" y1="${yy}" y2="${yy}" stroke="#e5ece8"/><text x="${p.l-9}" y="${yy+4}" text-anchor="end" font-size="10" fill="#899c94">${tick}</text>`;}
 for(let i=0;i<6;i++){const v=xmin+(xmax-xmin)*i/5,xx=x(v);out+=`<text x="${xx}" y="${H-23}" text-anchor="middle" font-size="10" fill="#899c94">${Number(v.toPrecision(4))}</text>`;}
 out+=`<text x="${W-p.r}" y="${H-5}" text-anchor="end" font-size="10" fill="#899c94">束线位置 s / mm</text>`;
 if(viewFingerprint)out+=`<text x="${p.l}" y="${H-5}" font-size="9" fill="#899c94">配置 ${viewFingerprint.slice(0,10)} · 实际记录点</text>`;
 const rfPositions=new Set(Object.values(results).flatMap(r=>(r.meta?.rf_events||[]).map(e=>e.z_actual_m*1000)));
 for(const s of rfPositions){if(s>=xmin&&s<=xmax)out+=`<line x1="${x(s)}" x2="${x(s)}" y1="${p.t}" y2="${H-p.b}" stroke="#b7c4bc" stroke-dasharray="3 4"/><text x="${x(s)+4}" y="${p.t+12}" fill="#8b9d93" font-size="9">RF</text>`;}
 for(const d of chartData){const path=d.x.map((v,i)=>(i?'L':'M')+x(v).toFixed(2)+','+y(d.y[i]).toFixed(2)).join(' ');out+=`<path d="${path}" fill="none" stroke="${d.color}" stroke-width="2" stroke-linejoin="round"/>`;}
 out+='<line id="cursorLine" x1="0" y1="22" x2="0" y2="258" stroke="#9db3a9" stroke-dasharray="3 3" visibility="hidden"/>';svg.innerHTML=out;
 svg.onpointermove=e=>{if(!chartData.length)return;const box=svg.getBoundingClientRect(),px=(e.clientX-box.left)*W/box.width,v=xmin+(px-p.l)/(W-p.l-p.r)*(xmax-xmin);if(v<xmin||v>xmax)return;
  const lines=[];for(const d of chartData){let lo=0,hi=d.x.length-1;while(lo<hi){const m=(lo+hi)>>1;if(d.x[m]<v)lo=m+1;else hi=m;}const i=lo>0&&Math.abs(d.x[lo-1]-v)<Math.abs(d.x[lo]-v)?lo-1:lo;lines.push(`${d.route}  ${format(d.y[i])} ${definition[2]}  @ ${format(d.x[i])} mm`);}
  const t=$('#hover');t.hidden=false;t.textContent=lines.join('\n');t.style.left=Math.max(3,Math.min(e.clientX-box.left+12,box.width-245))+'px';t.style.top='22px';const c=$('#cursorLine');c.setAttribute('x1',px);c.setAttribute('x2',px);c.setAttribute('visibility','visible');};
 svg.onpointerleave=()=>{$('#hover').hidden=true;$('#cursorLine')?.setAttribute('visibility','hidden');};
}
function renderJobs(){
 const active=jobs.filter(j=>['running','queued'].includes(j.status));$('#stop').disabled=!active.length;for(const id of ['runBoth','runAG','runOC'])$('#'+id).disabled=!!active.length;
 $('#jobs').innerHTML=jobs.length?jobs.map(j=>{const q=j.progress||{},fraction=j.status==='complete'?1:Math.min(.99,q.fraction||0),detail=j.status==='queued'?'等待上一条路线':j.error||q.phase||statusNames[j.status];return `<div class="job"><div class="job-route" style="color:${j.route==='AG'?'#247f70':'#bf733d'}">${j.route}<br><small>${j.id.slice(0,8)}</small></div><div><div class="job-title">${statusNames[j.status]} · ${esc(detail)}</div><div class="progress"><i style="width:${fraction*100}%"></i></div><small>${Math.round(j.elapsed_s||0)} 秒${q.s_m!==undefined?' · 最新记录 '+format(q.s_m*1000)+' / '+format(j.sample_m*1000)+' mm':''} · 配置 ${j.config_fingerprint.slice(0,8)}</small></div><div class="actions">${j.status==='complete'?`<button data-view="${j.id}">查看</button>`:''}<a href="/api/jobs/${j.id}/bundle">下载</a><button data-log="${j.id}">日志</button></div></div>`;}).join(''):'<p class="muted">还没有运行记录。</p>';
}
async function poll(){try{jobs=await api('/api/jobs');$('#connection').textContent='已连接';renderJobs();const newly=jobs.filter(j=>j.status==='complete'&&!seen.has(j.id)).sort((a,b)=>a.created-b.created);for(const j of newly){seen.add(j.id);await loadJob(j);}if(logJob){const d=await api(`/api/jobs/${logJob}/log`);$('#log').textContent=d.text||'正在准备计算依赖…';}}catch(e){$('#connection').textContent='连接中断';}}
document.addEventListener('input',e=>{const a=e.target;if(a.dataset.field){let v=Number(a.value);if(a.value==='')v=NaN;if(a.dataset.field==='step_size_m')v/=1000;config[a.dataset.section][a.dataset.field]=v;markDirty();}else if(a.dataset.switch){config[a.dataset.section][a.dataset.switch]=a.checked;markDirty();}else if(a.closest('[data-row]')){const i=Number(a.closest('[data-row]').dataset.row),el=config.lattice.elements[i];if(a.dataset.key){el[a.dataset.key]=a.dataset.key==='name'?a.value:(a.value===''?NaN:Number(a.value)/1000);}if(a.dataset.param)el.parameters[a.dataset.param]=a.value===''?NaN:Number(a.value);markDirty();}});
$('#mesh').oninput=e=>{config.space_charge.mesh=e.target.value.split(/[,，\s]+/).filter(Boolean).map(Number);markDirty();};$('#probes').oninput=e=>{config.output.z_diagnostics_mm=e.target.value.split(/[,，\s]+/).filter(Boolean).map(Number);markDirty();};
$('#elements').onclick=e=>{const b=e.target.closest('[data-remove]');if(b){config.lattice.elements.splice(Number(b.dataset.remove),1);renderElements();markDirty();}};
$('#beamline').onclick=e=>{const g=e.target.closest('[data-element]');if(g){selectedElement=Number(g.dataset.element);$('.geometry-editor').open=true;renderElements();$(`#elements [data-row="${selectedElement}"]`)?.scrollIntoView({block:'nearest',behavior:'smooth'});}};
$('#beamline').onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();e.target.closest('[data-element]')?.dispatchEvent(new MouseEvent('click',{bubbles:true}));}};
$('#addElement').onclick=()=>{const type=$('#addType').value,els=config.lattice.elements,sample=els.at(-1),start=sample.z_start;let n=1;while(els.some(e=>e.name===type+n))n++;const params=type==='rf_cavity'?{frequency_GHz:2.856,voltage_kV:30,phase_rad:Math.PI}:type==='solenoid'?{B_field_T:.05}:{};els.splice(els.length-1,0,{name:type+n,type,z_start:start,length:.01,parameters:params});renderElements();markDirty();message('已添加元件行。请调整入口、长度、相邻漂移和样品位置，再检查几何。');};
$('.metric-tabs').onclick=e=>{const b=e.target.closest('[data-metric]');if(b){metric=b.dataset.metric;renderResults();}};
$('#jobs').onclick=async e=>{const b=e.target.closest('[data-view]'),l=e.target.closest('[data-log]');if(b)await loadJob(jobs.find(j=>j.id===b.dataset.view),true);if(l){logJob=l.dataset.log;$('#log').closest('details').open=true;await poll();}};
$('#runBoth').onclick=()=>run(['AG','OCELOT']);$('#runAG').onclick=()=>run(['AG']);$('#runOC').onclick=()=>run(['OCELOT']);$('#validate').onclick=()=>validate().catch(()=>{});
$('#stop').onclick=async()=>{try{await api('/api/cancel',{ids:jobs.filter(j=>['running','queued'].includes(j.status)).map(j=>j.id)});message('已发送停止请求；未完成任务不会标为成功。');await poll();}catch(e){message(e.message,true);}};
$('#resetConfig').onclick=()=>{config=clone(defaults);dirty=false;renderConfig();message('已恢复共享配置副本。既有运行结果保持原记录。');};
 $('#exportConfig').onclick=async()=>{try{await validate(false);download(JSON.stringify(config,null,2),'ued_config.json');}catch(e){message('导出前请先修正配置：'+e.message,true);}};$('#importConfig').onclick=()=>$('#configFile').click();
$('#configFile').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;const r=await api('/api/import-config',{text:await file.text()});config=r.config;dirty=true;renderConfig();await validate(false);message('配置已导入并检查。运行前可以继续编辑。');}catch(e){message('导入失败：'+e.message,true);}finally{e.target.value='';}};
function exportSVG(){const s=$('#chart').cloneNode(true);s.setAttribute('xmlns','http://www.w3.org/2000/svg');s.querySelector('#cursorLine')?.remove();return new XMLSerializer().serializeToString(s);}
$('#exportSVG').onclick=()=>download(exportSVG(),'ued_'+metric+'.svg','image/svg+xml');
$('#exportPNG').onclick=()=>{const data=exportSVG(),url=URL.createObjectURL(new Blob([data],{type:'image/svg+xml'})),img=new Image();img.onload=()=>{const canvas=document.createElement('canvas');canvas.width=1840;canvas.height=600;canvas.getContext('2d').drawImage(img,0,0,1840,600);canvas.toBlob(b=>{const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='ued_'+metric+'.png';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);});URL.revokeObjectURL(url);};img.src=url;};
async function init(){try{const d=await api('/api/bootstrap');token=d.token;config=clone(d.config);defaults=clone(d.config);renderConfig();renderResults();await poll();setInterval(poll,1500);}catch(e){message('本地服务连接失败：'+e.message,true);}}
init();

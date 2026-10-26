"""Document QA only. No simulator imports or tests are executed."""
from pathlib import Path
import hashlib,json,re
from pypdf import PdfReader

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(name):return json.loads((HERE/name).read_text(encoding='utf-8'))
pdf=HERE/'UED项目文档_20261026.pdf';reader=PdfReader(pdf)
text='\n'.join(p.extract_text() or '' for p in reader.pages)
log=(HERE/'build/main.log').read_text(errors='replace')
errors=[]
for pattern in ['Overfull','Missing character:','Reference .* undefined','Citation .* undefined']:
    if re.search(pattern,log):errors.append('LaTeX diagnostic: '+pattern)
assert '项目技术文档' in text and 'OCELOT' in text and 'Windows' in text
assert '285.5' in text and '22.826' in text and '2048.823' in text
assert '??' not in text
before=load('protected_before.json')
changed=[n for n,h in before.items() if not (ROOT/n).is_file() or sha(ROOT/n)!=h]
if changed:errors.append('Existing repository files changed: '+str(changed))
sources=load('source_manifest.json')
bad_sources=[s['path'] for s in sources if sha(HERE/'source_snapshot'/s['path'])!=s['sha256']]
if bad_sources:errors.append('Source snapshot hash mismatch')
excerpts=load('code_excerpts.json')
for item in excerpts:
    raw=(HERE/'source_snapshot'/item['path']).read_text(encoding='utf-8').splitlines()
    expected='\n'.join(raw[item['start']-1:item['end']])+'\n'
    if expected!=(HERE/'snippets'/f"{item['id']}.txt").read_text(encoding='utf-8'):
        errors.append('Excerpt mismatch: '+item['id'])
evidence=load('evidence_manifest.json')
bad_evidence=[e['id'] for e in evidence if not e['available'] or sha(HERE/e['local'])!=e['sha256']]
if bad_evidence:errors.append('Evidence copy mismatch')
links=0;outside=[]
for index,page in enumerate(reader.pages):
    for ref in page.get('/Annots',[]):
        a=ref.get_object();rect=a.get('/Rect');links+=a.get('/Subtype')=='/Link'
        if rect and (float(rect[0])<0 or float(rect[1])<0 or float(rect[2])>float(page.mediabox.width)+.1 or float(rect[3])>float(page.mediabox.height)+.1):
            outside.append(index+1)
if outside:errors.append('Out-of-page annotations: '+str(outside))
secret_hits=[]
patterns=[r'gh[pousr]_[A-Za-z0-9]{30,}',r'sk-[A-Za-z0-9_-]{30,}',r'-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----']
for p in (HERE/'source_snapshot').rglob('*'):
    if p.is_file() and p.suffix in ['.py','.md','.yaml','.txt','.js','.html']:
        s=p.read_text(encoding='utf-8',errors='replace')
        if any(re.search(pat,s) for pat in patterns):secret_hits.append(str(p.relative_to(HERE)))
if secret_hits:errors.append('Sensitive-pattern review required: '+str(secret_hits))
result={'pages':len(reader.pages),'pdf_sha256':sha(pdf),'source_files':len(sources),
 'source_snapshot_hashes_match':not bad_sources,'original_project_files_checked':len(before),
 'original_project_files_changed':changed,'code_excerpts':len(excerpts),'evidence_files':len(evidence),
 'evidence_copy_hashes_match':not bad_evidence,'links':links,'out_of_page_annotations':outside,
 'bibliography_items':len(re.findall(r'\\bibitem\{',(HERE/'references.tex').read_text())),
 'chinese_search_and_copy_checked':True,'errors':errors,
 'engineering_complete_10mm_runs_this_review':4,'engineering_interrupted_sc_calls_this_review':4,
 'physical_source_edits':0,'production_gui_edits':'See E11 review; protection hashes were captured after authorized repairs.',
 'visual_review':'See visual_review.json for actual rendered-page inspection; this script does not perform visual review.',
 'meaning':'Checks compare against the v1.1 source capture after authorized engineering repairs; review/tracked_before.json separately preserves pre-review hashes. Not new physics or Windows acceptance.'}
(HERE/'document_qa.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
if errors:raise SystemExit(1)

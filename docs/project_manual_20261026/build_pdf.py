"""Build with XeLaTeX and embed Adobe's CJK Unicode map when TeX omits it."""
from pathlib import Path
import argparse, json, subprocess
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, DecodedStreamObject

HERE=Path(__file__).resolve().parent
FINAL=HERE/'UED项目文档_20261026.pdf'
def build(map_only=False):
    if not map_only:
        with (HERE/'compile.log').open('w',encoding='utf-8') as log:
            subprocess.run(['latexmk','-xelatex','-interaction=nonstopmode','-halt-on-error',
                            '-outdir=build','main.tex'],cwd=HERE,stdout=log,stderr=subprocess.STDOUT,check=True)
    reader=PdfReader(HERE/'build/main.pdf');writer=PdfWriter();writer.clone_document_from_reader(reader)
    stream=DecodedStreamObject();stream.set_data((HERE/'fonts/Adobe-GB1-UCS2').read_bytes())
    mapping=writer._add_object(stream.flate_encode());fixed=[]
    for page in writer.pages:
        for item in page['/Resources'].get('/Font',{}).values():
            font=item.get_object()
            if 'Fandol' in str(font.get('/BaseFont')) and '/ToUnicode' not in font:
                font[NameObject('/ToUnicode')]=mapping;fixed.append(str(font['/BaseFont']))
    writer.write(FINAL)
    reopened=PdfReader(FINAL)
    assert '项目技术文档' in reopened.pages[0].extract_text()
    result={'pdf':FINAL.name,'pages':len(reopened.pages),'unicode_maps_added':fixed,
            'meaning':'Only embedded text mapping added; page content, equations and layout are unchanged.'}
    (HERE/'pdf_build.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--map-only',action='store_true')
    build(parser.parse_args().map_only)

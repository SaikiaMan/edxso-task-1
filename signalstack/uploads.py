import csv,io,hashlib
from pathlib import Path
from signalstack.db import put,rows,data_directory

def ingest(company,name,content,synthetic=False):
    if len(content)>10_000_000: raise ValueError('Upload limit is 10 MB')
    suffix=Path(name).suffix.lower()
    if suffix=='.pdf':
        from pypdf import PdfReader
        text='\n'.join(p.extract_text() or '' for p in PdfReader(io.BytesIO(content)).pages)
    elif suffix=='.xlsx':
        from openpyxl import load_workbook
        book=load_workbook(io.BytesIO(content),read_only=True,data_only=True)
        try:
            text='\n'.join(' | '.join('' if v is None else str(v) for v in row) for sheet in book for row in sheet.iter_rows(values_only=True))
        finally:
            book.close()
    elif suffix in ('.csv','.txt'):
        text=content.decode('utf-8-sig')
    else: raise ValueError('Supported formats: CSV, XLSX, PDF, TXT')
    if not text.strip(): raise ValueError('No extractable text; scanned PDFs need OCR before upload')
    digest=hashlib.sha256(content).hexdigest()
    duplicate=next((r for r in rows('record',company) if r.get('hash')==digest),None)
    if duplicate: return duplicate['id']
    attachment=data_directory()/'uploads'/str(company)/(digest+suffix)
    attachment.parent.mkdir(parents=True,exist_ok=True)
    attachment.write_bytes(content)
    return put('record',company,{'url':'internal:'+Path(name).name,'title':Path(name).name,'text':text[:60000], 'category':'Internal','hash':digest,'publication_date':None,'change':'uploaded','synthetic':bool(synthetic),'attachment':str(attachment.relative_to(data_directory()))})

import json
import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT.parent / '.env')
load_dotenv(ROOT / '.env')

def data_directory():
    return Path(os.getenv('SIGNALSTACK_DB',str(ROOT/'data'/'signalstack.db'))).resolve().parent

@contextmanager
def connection():
    path = Path(os.getenv('SIGNALSTACK_DB', str(ROOT / 'data' / 'signalstack.db')))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=30)
    db.row_factory = sqlite3.Row
    db.executescript((ROOT / 'signalstack' / 'schema.sql').read_text())
    try:
        with db:
            yield db
    finally:
        db.close()

def put(kind, company, data, id=None):
    with connection() as db:
        if id is None:
            return db.execute('INSERT INTO objects(kind,company,data) VALUES(?,?,?)', (kind,company,json.dumps(data))).lastrowid
        db.execute('UPDATE objects SET data=? WHERE id=? AND kind=? AND company=?', (json.dumps(data),id,kind,company))
        return id

def rows(kind, company=None):
    with connection() as db:
        result = db.execute('SELECT * FROM objects WHERE kind=?' + (' AND company=?' if company is not None else '') + ' ORDER BY id DESC', (kind,company) if company is not None else (kind,)).fetchall()
    return [dict(json.loads(r['data']), id=r['id'], created=r['created']) for r in result]

def remove(kind, company, id):
    with connection() as db:
        db.execute('DELETE FROM objects WHERE kind=? AND company=? AND id=?', (kind,company,id))

def patch(kind,company,id,changes):
    """Merge selected fields atomically without clobbering other workers' updates."""
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT data FROM objects WHERE kind=? AND company=? AND id=?',(kind,company,id)).fetchone()
        if row is None: raise ValueError('Record no longer exists')
        data=json.loads(row['data'])
        data.update(changes)
        db.execute('UPDATE objects SET data=? WHERE kind=? AND company=? AND id=?',(json.dumps(data),kind,company,id))

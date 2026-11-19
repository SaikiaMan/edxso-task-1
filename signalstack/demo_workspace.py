"""Open the three saved demonstrations in a separate, editable workspace."""
import gzip
import json
import os

from signalstack.db import ROOT, connection


def open_demo():
    path = ROOT / 'data' / 'assignment-demo.db'
    os.environ['SIGNALSTACK_DB'] = str(path)
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT 1 FROM objects LIMIT 1').fetchone():
            return path
        snapshot = ROOT / 'examples' / 'public-demo.json.gz'
        with gzip.open(snapshot, 'rt', encoding='utf-8') as stream:
            records = json.load(stream)
        db.executemany(
            'INSERT INTO objects(id,kind,company,created,data) VALUES(?,?,?,?,?)',
            ((r['id'], r['kind'], r['company'], r['created'], json.dumps(r['data'])) for r in records),
        )
    return path


if __name__ == '__main__':
    from signalstack.__main__ import main
    open_demo()
    main()

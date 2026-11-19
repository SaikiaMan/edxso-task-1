CREATE TABLE IF NOT EXISTS objects (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 kind TEXT NOT NULL,
 company INTEGER NOT NULL DEFAULT 0,
 data TEXT NOT NULL,
 created TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX IF NOT EXISTS objects_kind_company ON objects(kind, company);

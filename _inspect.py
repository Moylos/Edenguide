import sqlite3, json
c=sqlite3.connect('data/app.db')
c.row_factory=sqlite3.Row
tables = c.execute("SELECT name, sql FROM sqlite_master WHERE type='table'").fetchall()
for t in tables:
    print('TABLE', t['name'])
    print(t['sql'])
    print('---')
rows=c.execute('SELECT * FROM users').fetchall()
for r in rows:
    print(json.dumps(dict(r), default=str, ensure_ascii=False))
c.close()

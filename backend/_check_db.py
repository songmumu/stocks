import sqlite3
conn = sqlite3.connect('trading.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('Tables:', cur.fetchall())
for table_row in cur.fetchall():
    name = table_row[0]
    cur.execute(f"SELECT count(*) FROM {name}")
    print(f'  {name}: {cur.fetchone()[0]} rows')
cur.execute("SELECT id, code, name, trade_type, trade_date, price, quantity FROM trade_records")
rows = cur.fetchall()
print(f'\n=== trade_records ({len(rows)}) ===')
for r in rows:
    print(r)
conn.close()

import sqlite3
from datetime import datetime, timezone

c = sqlite3.connect('trading.db')
cur = c.cursor()
cur.execute('SELECT id, username, role, is_active, last_login_at, created_at FROM users')
for row in cur.fetchall():
    print(f'ID={row[0]} username={row[1]} role={row[2]} active={row[3]} last_login={row[4]} created={row[5]}')

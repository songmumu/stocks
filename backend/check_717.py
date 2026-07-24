import sqlite3
db = sqlite3.connect(r'C:\Users\admin\.qclaw\workspace-v733kxt9elzfv7u1\trading-system\backend\trading.db')
cur = db.execute("SELECT code, date, close_price FROM price_history WHERE date = '2026-07-17'")
for r in cur:
    print(r)
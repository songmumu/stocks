import sqlite3
db = sqlite3.connect(r'C:\Users\admin\.qclaw\workspace-v733kxt9elzfv7u1\trading-system\backend\trading.db')
cur = db.execute("SELECT date, close_price FROM price_history WHERE code='600415' ORDER BY date DESC LIMIT 5")
for r in cur:
    print(r)
print('---')
cur = db.execute("SELECT code, MAX(date) FROM price_history GROUP BY code")
for r in cur:
    print(r)
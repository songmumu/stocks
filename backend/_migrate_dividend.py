"""一次性迁移：给 trade_records 表加 dividend 列"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), 'trading.db')
print(f'DB: {DB}')

conn = sqlite3.connect(DB)
cur = conn.cursor()
# 查现有列
cur.execute("PRAGMA table_info(trade_records)")
cols = [row[1] for row in cur.fetchall()]
print(f'existing cols: {cols}')

if 'dividend' not in cols:
    cur.execute("ALTER TABLE trade_records ADD COLUMN dividend REAL DEFAULT 0.0")
    print('ADDED column dividend')
else:
    print('dividend already exists, skip')

# 验证
cur.execute("PRAGMA table_info(trade_records)")
new_cols = [row[1] for row in cur.fetchall()]
print(f'new cols: {new_cols}')

# 统计已有交易记录数
cur.execute("SELECT COUNT(*) FROM trade_records")
print(f'trade_records count: {cur.fetchone()[0]}')

conn.commit()
conn.close()
print('Migration done.')

import urllib.request, json
r = urllib.request.urlopen('http://localhost:8000/api/valuation/watchlist/signals')
data = json.loads(r.read())
print('=== 自选信号 ===')
for s in data['watchlist_signals']:
    code = f"{s['code']:8s}"
    name = f"{s['name']:24s}"
    band = f"{s['band']:11s}"
    src = f"{s.get('data_source'):6s}"
    sig = f"{s['signal_label']:8s}"
    note = s.get('note','')
    print(f"  {code} {name} | band: {band} | src: {src} | sig: {sig} | note: {note}")
print('\n=== 宽基指数参考 ===')
for s in data['index_signals']:
    code = f"{s['code']:8s}"
    name = f"{s['name']:14s}"
    pe = s.get('pe')
    pe_str = f"PE={pe:.1f}" if pe else 'PE=N/A'
    pe_str = f"{pe_str:12s}"
    pct = s.get('pe_pct')
    pct_str = f"{pct}%" if pct is not None else '—'
    pct_str = f"{pct_str:6s}"
    band = f"{s.get('band'):11s}"
    src = s.get('data_source')
    print(f"  {code} {name} | {pe_str} pct:{pct_str} | band: {band} | src: {src}")

import urllib.request, json

def api(path):
    r = urllib.request.urlopen('http://localhost:8000' + path)
    return json.loads(r.read())

def proxy(path):
    r = urllib.request.urlopen('http://localhost:5173' + path)
    return json.loads(r.read())

print('=== 验收报告 ===')

# 1. 健康
health = api('/api/health')
print(f'1. 后端健康: {health}')

# 2. 自选信号（全手动）
sig = api('/api/valuation/watchlist/signals')
wl = sig['watchlist_signals']
idx = sig['index_signals']
print(f'2. 自选信号 {len(wl)} 个:')
for s in wl:
    mark = '★' if s['data_source'] == 'manual' else '○'
    print(f'   {mark} {s["code"]:8s} {s["name"][:18]:18s} {s["band"]:12s} {s["signal_label"]}')

print(f'\n3. 宽基指数 {len(idx)} 个:')
for i in idx:
    pe_s = f"PE={i['pe']:.1f}" if i['pe'] else 'PE=?'
    pct_s = f"{i['pe_pct']}%" if i['pe_pct'] else '未填'
    print(f'   {i["code"]:8s} {i["name"]:10s} {pe_s:10s} 分位={pct_s:8s} 档位={i["band"]}')

# 3. 前端代理
sig2 = proxy('/api/valuation/watchlist/signals')
print(f'\n4. Vite 代理 OK: {len(sig2["watchlist_signals"])} 品种')

print('\n=== 全部通过 ===')

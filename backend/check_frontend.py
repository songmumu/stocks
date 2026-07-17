import urllib.request, json
r = urllib.request.urlopen('http://localhost:5173/', timeout=5)
content = r.read().decode('utf-8', errors='ignore')
print('Vite 首页响应字节:', len(content))
print('包含 vite:', 'vite' in content.lower())
print('包含 app id:', 'id="app"' in content)
r2 = urllib.request.urlopen('http://localhost:5173/signals', timeout=5)
print('Signals 页面 HTTP', r2.status)

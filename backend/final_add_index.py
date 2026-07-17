import urllib.request, json

BASE = "http://localhost:8000"

def post(path, data):
    payload = json.dumps(data).encode()
    req = urllib.request.Request(BASE + path, data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    return json.loads(urllib.request.urlopen(req).read())

def get(path):
    return json.loads(urllib.request.urlopen(BASE + path).read())

def delete(path):
    req = urllib.request.Request(BASE + path, method="DELETE")
    return json.loads(urllib.request.urlopen(req).read())

# 1. 添加中证红利
print("添加 中证红利(000922)...")
r = post("/api/indices/custom", {"code": "000922", "name": "中证红利"})
print(f"  → id={r['id']} {r['code']} {r['name']}")

# 2. 验证 valuation 接口
vals = get("/api/valuation/indices")
custom = [v for v in vals if v.get("is_custom")]
print(f"\n自定义指数 ({len(custom)} 个):")
for v in custom:
    print(f"  {v['code']} {v['name']:8s} PE={str(v['pe']):6s} PB={str(v['pb']):5s} is_custom={v['is_custom']}")

# 3. 前端页面可访问
import urllib.request as ur
r2 = ur.urlopen("http://localhost:5173/index-valuation")
print(f"\n前端页面: HTTP {r2.status}")

# 4. 清理
delete("/api/indices/custom/000922")
print("\n清理完成，测试通过!")

"""A：0–5DTE = Gamma world，7–180DTE = Vanna world（页面最长 78DTE）。10-12→10-23（GEX 分到期全表），VEX 从 10-08。
帧 09:45–15:25 每 5 分钟，结果窗 30 分钟。净值 = spot±30。"""
import datetime as dt, json, glob, gzip, statistics as st
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    import vexrows as R
ET = R.ET; NW = R.NW
def grids(day, metric):
    out = []
    for p in sorted(glob.glob(f"{NW}/history/SPX/{day}/SPX_{metric}_*.json.gz")):
        d = json.load(gzip.open(p)); t = dt.datetime.fromisoformat(d["captured_at"]).astimezone(ET)
        if t.time() < dt.time(9, 30): continue
        a = [i for i, x in enumerate(d["dte"]) if x <= 5]; b = [i for i, x in enumerate(d["dte"]) if 7 <= x <= 180]
        out.append((t, {k: (sum(r[i] or 0 for i in a), sum(r[i] or 0 for i in b)) for k, r in zip(d["strikes"], d["values"])}))
    return out
cache = {}
for f in R.F:
    for m in ("GEX", "VEX"):
        key = (f["day"], m)
        if key not in cache: cache[key] = grids(f["day"], m)
        g = R.at(cache[key], f["T"], 600)
        if g:
            near = [v for k, v in g[1].items() if abs(k - f["S"]) <= 30]
            f[m + "_f"] = sum(v[0] for v in near); f[m + "_b"] = sum(v[1] for v in near)
sg = lambda x: 1 if x > 0 else -1
def beta(s): b = [f for f in s if f["dvix"] is not None]; return sum(f["dvix"] * f["ret"] for f in b) / sum(f["dvix"] ** 2 for f in b) if b else float("nan")
def desc(s):
    m = [f for f in s if f["pret"] is not None and abs(f["pret"]) >= 3]; rev = sum(sg(f["ret"]) != sg(f["pret"]) for f in m)
    p = [f for f in s if f["pdvix"] is not None and f["pdvix"] <= -0.15]
    return (f"{len(s):>3} 帧/{len({f['day'] for f in s}):>2} 天  振幅中位 {st.median([f['rng'] for f in s]):5.1f}  反转 {rev}/{len(m)}={rev/len(m)*100 if m else 0:3.0f}%  "
            f"β(SPX/VIX) {beta(s):+6.1f}  VIX 先跌→SPX 涨 {sum(f['ret']>0 for f in p)}/{len(p)}")
G = [f for f in R.F if "GEX_f" in f]; V = [f for f in R.F if "VEX_f" in f]
print(f"GEX 分到期帧 {len(G)}（{len({f['day'] for f in G})} 天）；VEX 分到期帧 {len(V)}（{len({f['day'] for f in V})} 天）\n")
print("A1 Gamma world：哪个到期段的 GEX 符号更能分出振幅/反转")
for lab, key in (("0–5DTE GEX", "GEX_f"), ("7–180DTE GEX", "GEX_b")):
    for s_ in (1, -1):
        print(f"  {lab} {'+' if s_>0 else '−'}: " + desc([f for f in G if sg(f[key]) == s_]))
print("\nA2 Vanna world：哪个到期段的 VEX 符号更能分出 SPX 对 VIX 的反应")
for lab, key in (("0–5DTE VEX", "VEX_f"), ("7–180DTE VEX", "VEX_b")):
    for s_ in (1, -1):
        print(f"  {lab} {'+' if s_>0 else '−'}: " + desc([f for f in V if sg(f[key]) == s_]))
print("\nA3 截图四态，改用 GEX=0–5DTE、VEX=7–180DTE")
GV = [f for f in G if "VEX_b" in f]
for name, g, v in (("+GEX +VEX", 1, 1), ("−GEX −VEX", -1, -1), ("+GEX −VEX", 1, -1), ("−GEX +VEX", -1, 1)):
    s = [f for f in GV if sg(f["GEX_f"]) == g and sg(f["VEX_b"]) == v]
    print(f"  {name}: " + (desc(s) if s else "无帧"))

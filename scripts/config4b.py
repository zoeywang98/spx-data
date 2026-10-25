import io, contextlib, statistics as st, datetime as dt
with contextlib.redirect_stdout(io.StringIO()):
    import config4 as C
F = C.F
def dr(s):
    d = [f for f in s if f["pret"] is not None and f["pret"] <= -3]; r = [f for f in s if f["pret"] is not None and f["pret"] >= 3]
    return (f"跌后 30 分钟反弹 {sum(f['ret']>0 for f in d)}/{len(d)}={sum(f['ret']>0 for f in d)/len(d)*100:3.0f}% 均 {st.mean(f['ret'] for f in d):+4.1f}   "
            f"涨后续涨 {sum(f['ret']>0 for f in r)}/{len(r)}={sum(f['ret']>0 for f in r)/len(r)*100:3.0f}% 均 {st.mean(f['ret'] for f in r):+4.1f}")
print("dealer 行为（前 15 分钟 ≥3 点）")
for lab, b, a, cl in (("① 下+ 上−", 1, -1, "跌后反弹、涨后续涨"), ("② 下− 上+", -1, 1, "跌后续跌、涨后回落"), ("  对照 下+ 上+", 1, 1, ""), ("  对照 下− 上−", -1, -1, "")):
    print(f"  {lab:<14} {dr([f for f in F if f['sb']==b and f['sa']==a])}   {('截图：' + cl) if cl else ''}")
# ③ VEX：10 月，7–78DTE，spot±30 内上下最强 VEX 节点符号相反
with contextlib.redirect_stdout(io.StringIO()):
    import vexrows as R, worlds as W
import glob, gzip, json
print("\n③ 夹在 +VEX 与 −VEX 簇之间（7–78DTE，spot±30 上下最强 |VEX| 节点符号相反）→ 小 vol 变动就换手")
cache = {}
rows = []
for f in R.F:
    if f["day"] not in cache: cache[f["day"]] = W.grids(f["day"], "VEX")
    g = R.at(cache[f["day"]], f["T"], 600)
    if not g or f["dvix"] is None: continue
    vb = {k: v[1] for k, v in g[1].items() if abs(k - f["S"]) <= 30 and v[1]}
    if not vb: continue
    a = {k: v for k, v in vb.items() if k > f["S"]}; b = {k: v for k, v in vb.items() if k < f["S"]}
    if not a or not b: continue
    ka = max(a, key=lambda k: abs(a[k])); kb = max(b, key=lambda k: abs(b[k]))
    rows.append(dict(f, opp=a[ka] * b[kb] < 0))
def beta(s): return sum(f["dvix"] * f["ret"] for f in s) / sum(f["dvix"] ** 2 for f in s)
for lab, opp in (("夹在反向簇之间", True), ("对照 上下同号", False)):
    s = [f for f in rows if f["opp"] == opp]; sm = [f for f in s if 0.03 <= abs(f["dvix"]) <= 0.15]
    print(f"  {lab}: {len(s)} 帧/{len({f['day'] for f in s})} 天  全部 β {beta(s):+.1f}   小 vol 变动（0.03–0.15）{len(sm)} 帧 β {beta(sm):+.1f}  SPX 与 VIX 反向 {sum((f['ret']>0)!=(f['dvix']>0) for f in sm)}/{len(sm)}  |涨跌|中位 {st.median([abs(f['ret']) for f in sm]):.1f}")

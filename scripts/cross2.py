"""T2 vanna 分到期段；T4 vol spike + 前端 +GEX + 长端 vanna。10-08→10-23（VEX 分到期），帧 5 分钟、结果 30 分钟。"""
import datetime as dt, json, glob, gzip, statistics as st, io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    import vexrows as R
ET = R.ET; NW = R.NW
BK = {"0DTE": (0, 0), "1–7DTE": (1, 7), "8–30DTE": (8, 30), ">30DTE": (31, 999)}
def grids(day, metric):
    out = []
    for p in sorted(glob.glob(f"{NW}/history/SPX/{day}/SPX_{metric}_*.json.gz")):
        d = json.load(gzip.open(p)); t = dt.datetime.fromisoformat(d["captured_at"]).astimezone(ET)
        if t.time() < dt.time(9, 30): continue
        ix = {b: [i for i, x in enumerate(d["dte"]) if lo <= x <= hi] for b, (lo, hi) in BK.items()}
        out.append((t, {k: {b: sum(r[i] or 0 for i in v) for b, v in ix.items()} for k, r in zip(d["strikes"], d["values"])}))
    return out
cache = {}
for f in R.F:
    if f["day"] not in cache: cache[f["day"]] = grids(f["day"], "VEX")
    g = R.at(cache[f["day"]], f["T"], 600)
    if g:
        for b in BK:
            f["V" + b] = sum(v[b] for k, v in g[1].items() if abs(k - f["S"]) <= 50)
            f["A" + b] = sum(abs(v[b]) for k, v in g[1].items() if abs(k - f["S"]) <= 50)
F = [f for f in R.F if "V0DTE" in f]
sg = lambda x: 1 if x > 0 else -1
print(f"{len({f['day'] for f in F})} 天，{len(F)} 帧\n")
print("T2 vanna：+VEX → IV↓ 买 / IV↑ 卖；−VEX 反过来。预测 = −sign(前 15 分钟 ΔVIX) × sign(VEX)，看之后 30 分钟 SPX（|ΔVIX| ≥0.10 的帧）")
tot = sum(st.mean([f["A" + b] for f in F]) for b in BK)
for b in BK:
    s = [f for f in F if f["pdvix"] is not None and abs(f["pdvix"]) >= 0.10]
    hit = [sg(f["ret"]) == -sg(f["pdvix"]) * sg(f["V" + b]) for f in s]
    pos = [f for f in s if f["V" + b] > 0]; neg = [f for f in s if f["V" + b] <= 0]
    pr = lambda q: f"{sum(sg(f['ret']) == -sg(f['pdvix']) for f in q)}/{len(q)}" if q else "—"
    print(f"  {b:<8} |VEX| 占比 {st.mean([f['A'+b] for f in F])/tot*100:4.1f}%  命中 {sum(hit)}/{len(hit)} = {sum(hit)/len(hit)*100:.0f}%   "
          f"（VEX+ 时 SPX 与 VIX 反向 {pr(pos)}；VEX− 时 {pr(neg)}，− 时说法要求同向）")
s = [f for f in F if f["pdvix"] is not None and abs(f["pdvix"]) >= 0.10]
print(f"  基准：不分 VEX，SPX 与前 15 分钟 VIX 反向 {sum(sg(f['ret']) == -sg(f['pdvix']) for f in s)}/{len(s)}")
print("\nT4 vol spike（前 15 分钟 VIX ≥ +0.15）+ 前端 0DTE 净 +GEX 且下方 +GEX（支撑区）→ 长端 vanna 压过、照样卖")
sp = [f for f in F if f["pdvix"] is not None and f["pdvix"] >= 0.15 and f["g_net"] > 0]
for b in (">30DTE", "8–30DTE"):
    for sgn, lab in ((1, "+"), (-1, "−")):
        q = [f for f in sp if sg(f["V" + b]) == sgn]
        if q:
            print(f"  长端 {b} VEX {lab}: {len(q)} 帧/{len({f['day'] for f in q})} 天  30 分钟下跌 {sum(f['ret']<0 for f in q)}/{len(q)}  均 {st.mean(f['ret'] for f in q):+.1f}  "
                  f"按天 " + " ".join(f"{d[5:]}:{sum(f['day']==d for f in q)}" for d in sorted({f['day'] for f in q})))
q = [f for f in F if f["pdvix"] is not None and f["pdvix"] >= 0.15 and f["g_net"] <= 0]
print(f"  对照 前端 −GEX + vol spike: {len(q)} 帧  下跌 {sum(f['ret']<0 for f in q)}/{len(q)}  均 {st.mean(f['ret'] for f in q):+.1f}")
q = [f for f in F if f["g_net"] > 0]
print(f"  对照 前端 +GEX 全部: {len(q)} 帧  下跌 {sum(f['ret']<0 for f in q)}/{len(q)}  均 {st.mean(f['ret'] for f in q):+.1f}")

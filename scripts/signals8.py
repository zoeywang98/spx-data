"""截图 8 条 signal。帧 09:45–15:25 每 5 分钟；GEX = 0–5DTE、VEX = 7–78DTE；10-12→10-23；结果 = 之后 30 分钟。
ΔVIX = 前 15 分钟（vol crush ≤ −0.15，spike ≥ +0.15）。"""
import datetime as dt, json, statistics as st, io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    import states_trade as X
ET = X.ET
F = []
for day in X.DAYS:
    D = dt.date.fromisoformat(day)
    j = json.load(open(f"{X.B.KL}/{day}.json"))
    bars = {dt.datetime.fromisoformat(x["time"]).astimezone(ET) + dt.timedelta(minutes=1): (x["high"], x["low"], x["close"]) for x in j["bars"]}
    if max(bars).time() < dt.time(16):
        bars = {t.replace(second=0) + dt.timedelta(minutes=1): (s, s, s) for t, s, g in X.B.heat_series(day)}
    ts = sorted(bars); G, V, VI = X.grids(day, "GEX", 0, 5), X.grids(day, "VEX", 7, 78), X.vix(day)
    C = lambda t: next((bars[x][2] for x in reversed(ts) if x <= t), None)
    def vat(t):
        for k in range(4):
            x = VI.get(t - dt.timedelta(minutes=k))
            if x: return x
    T = dt.datetime.combine(D, dt.time(9, 45), ET)
    while T.time() <= dt.time(15, 25):
        g = max((x for x in G if x[0] <= T), key=lambda x: x[0], default=None); v = max((x for x in V if x[0] <= T), key=lambda x: x[0], default=None)
        c0, cp, c15 = C(T), C(T - dt.timedelta(minutes=5)), C(T - dt.timedelta(minutes=15))
        E = min(T + dt.timedelta(minutes=30), dt.datetime.combine(D, dt.time(16), ET))
        if g and v and (T - g[0]).seconds <= 300 and (T - v[0]).seconds <= 300 and c0 and cp and c15:
            S = c0; path = [bars[x] for x in ts if T < x <= E]
            if path:
                f = dict(day=day, S=S, ret=C(E) - S, hi=max(p[0] for p in path) - S, lo=min(p[1] for p in path) - S, pret=S - c15, p5=S - cp)
                f["rng"] = f["hi"] - f["lo"]
                v0, v15 = vat(T), vat(T - dt.timedelta(minutes=15)); f["dv"] = (v0 - v15) if v0 and v15 else None
                gg, vv = g[1], v[1]
                rng = lambda m, a, b: sum(x for k, x in m.items() if S + a <= k <= S + b)
                f["gb"], f["ga"] = rng(gg, -30, -0.01), rng(gg, 0.01, 30); f["vb"], f["va"] = rng(vv, -30, -0.01), rng(vv, 0.01, 30)
                f["vnet"] = f["vb"] + f["va"]
                near = {k: x for k, x in gg.items() if abs(k - S) <= 50 and k % 5 == 0}
                mx = max(abs(x) for x in near.values()) or 1
                # flip（+ 在上、− 在下）：相邻 5 点 strike 下负上正，|值| 都 ≥ 最大 10%
                f["flips"] = [b for a, b in zip(sorted(near), sorted(near)[1:]) if b - a == 5 and near[a] < -0.1 * mx and near[b] > 0.1 * mx]
                srt = sorted(near, key=lambda k: -abs(near[k]))
                f["king"] = srt[0]; f["king_dom"] = abs(near[srt[0]]) / (abs(near[srt[1]]) or 1); f["second"] = srt[1]
                f["c_end"] = C(E)
                tot = sum(abs(x) for k, x in near.items() if abs(k - S) <= 30) or 1
                f["pk_up"] = sum(abs(x) for k, x in near.items() if S < k <= S + 15) / tot
                f["pk_dn"] = sum(abs(x) for k, x in near.items() if S - 15 <= k < S) / tot
                f["cp"] = cp
                F.append(f)
        T += dt.timedelta(minutes=5)
sg = lambda x: 1 if x > 0 else -1
def wr(s, d, key="ret"):
    if not s: return "—"
    return f"{len(s):>3} 帧/{len({f['day'] for f in s}):>2} 天  {'涨' if d>0 else '跌'} {sum(sg(f[key])==d for f in s)}/{len(s)} = {sum(sg(f[key])==d for f in s)/len(s)*100:3.0f}%  均 {st.mean(f[key] for f in s):+5.1f}"
print(f"{len(X.DAYS)} 天，{len(F)} 帧\n")
dips = [f for f in F if f["pret"] <= -3]
print("① +GEX 与 +VEX 都堆在现价下方（下方净 GEX>0、净 VEX>0，且都大于上方）→ fade dips（跌后买）")
c1 = lambda f: f["gb"] > 0 and f["vb"] > 0 and f["gb"] > f["ga"] and f["vb"] > f["va"]
print("   是：" + wr([f for f in dips if c1(f)], 1)); print("   否：" + wr([f for f in dips if not c1(f)], 1))
print("\n② −GEX 与 −VEX 都堆在现价下方（下方净 GEX<0、净 VEX<0）→ panic zone，顺势（跌后继续跌）")
c2 = lambda f: f["gb"] < 0 and f["vb"] < 0
print("   是：" + wr([f for f in dips if c2(f)], -1)); print("   否：" + wr([f for f in dips if not c2(f)], -1))
q = [f for f in F if c2(f)]; r = [f for f in F if not c2(f)]
print(f"   下行幅度（30 分钟最低）中位：是 {st.median([f['lo'] for f in q]):.1f}（{len(q)} 帧）  否 {st.median([f['lo'] for f in r]):.1f}")
print("\n③ 向下穿过 flip（上 + 下 −）→ rug-pull")
cr = [f for f in F if any(f["cp"] > k - 2.5 >= f["S"] for k in f["flips"])]
other = [f for f in F if f["p5"] <= -3 and f not in cr]
print("   穿 flip：" + wr(cr, -1)); print("   对照（5 分钟跌 ≥3 点、没穿 flip）：" + wr(other, -1))
if cr: print(f"   穿 flip 后 30 分钟最低中位 {st.median([f['lo'] for f in cr]):.1f}  对照 {st.median([f['lo'] for f in other]):.1f}")
print("\n④ 大 King Node（|GEX| 最大且 ≥ 第二名 2 倍，距现价 5–40 点）→ 回归磁铁")
def mag(s, key):
    return f"{len(s):>3} 帧/{len({f['day'] for f in s}):>2} 天  30 分钟后离它更近 {sum(abs(f['c_end']-f[key])<abs(f['S']-f[key]) for f in s)}/{len(s)} = {sum(abs(f['c_end']-f[key])<abs(f['S']-f[key]) for f in s)/len(s)*100:3.0f}%" if s else "—"
kk = [f for f in F if f["king_dom"] >= 2 and 5 <= abs(f["king"] - f["S"]) <= 40]
print("   King：" + mag(kk, "king")); print("   对照（同帧第二大节点，同距离段）：" + mag([f for f in F if 5 <= abs(f["second"] - f["S"]) <= 40], "second"))
kw = [f for f in F if f["king_dom"] < 2 and 5 <= abs(f["king"] - f["S"]) <= 40]; print("   不够大的 King（<2 倍）：" + mag(kw, "king"))
print("\n⑤ 宽 air pocket（现价一侧 15 点内 |GEX| < spot±30 合计的 10%）→ 往那边加速")
up = [f for f in F if f["pk_up"] < 0.10 and f["pk_dn"] >= 0.10]; dn = [f for f in F if f["pk_dn"] < 0.10 and f["pk_up"] >= 0.10]
no = [f for f in F if f["pk_up"] >= 0.10 and f["pk_dn"] >= 0.10]
print("   上方真空：" + wr(up, 1) + f"  振幅 {st.median([f['rng'] for f in up]) if up else 0:.1f}")
print("   下方真空：" + wr(dn, -1) + f"  振幅 {st.median([f['rng'] for f in dn]) if dn else 0:.1f}")
print("   两边都不空：" + f"{len(no)} 帧  振幅 {st.median([f['rng'] for f in no]):.1f}")
print("\n⑥⑦⑧ vol × VEX（净 VEX spot±30）")
for lab, cond, d in (("⑥ vol crush + +VEX → 涨势延续", lambda f: f["dv"] is not None and f["dv"] <= -0.15 and f["vnet"] > 0, 1),
                     ("   vol crush + −VEX（对照）", lambda f: f["dv"] is not None and f["dv"] <= -0.15 and f["vnet"] <= 0, 1),
                     ("⑦ vol spike + +VEX → dealer 卖、阻力", lambda f: f["dv"] is not None and f["dv"] >= 0.15 and f["vnet"] > 0, -1),
                     ("⑧ vol spike + −VEX → dealer 买、轧空", lambda f: f["dv"] is not None and f["dv"] >= 0.15 and f["vnet"] <= 0, 1)):
    print(f"   {lab:<30} " + wr([f for f in F if cond(f)], d))

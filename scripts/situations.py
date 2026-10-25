"""截图 6 种 situation。帧 09:45–15:25 每 5 分钟；GEX = 0–5DTE、VEX = 7–78DTE，取 ≤T 最新帧；10-12→10-23。
指标（之后 30 分钟）：振幅 = 高−低；效率 = |净变动| / 逐分钟 |变动| 之和（越低越 choppy）；反转 = 前 15 分钟动 ≥3 点后方向相反；
突破 = 60 分钟内越出节点区间。节点 = spot±30 内 |值| ≥ 该侧最大 |值| 的 40% 的 strike。"""
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
        c0 = C(T); E = min(T + dt.timedelta(minutes=30), dt.datetime.combine(D, dt.time(16), ET)); E60 = min(T + dt.timedelta(minutes=60), dt.datetime.combine(D, dt.time(16), ET))
        if g and v and (T - g[0]).seconds <= 300 and (T - v[0]).seconds <= 300 and c0:
            S = c0; gn = {k: x for k, x in g[1].items() if abs(k - S) <= 30 and x}; vn = {k: x for k, x in v[1].items() if abs(k - S) <= 30 and x}
            path = [bars[x] for x in ts if T < x <= E]; path60 = [bars[x] for x in ts if T < x <= E60]
            if path and gn and vn:
                cl = [c0] + [p[2] for p in path]
                f = dict(day=day, ret=cl[-1] - c0, rng=max(p[0] for p in path) - min(p[1] for p in path),
                         eff=abs(cl[-1] - c0) / (sum(abs(b - a) for a, b in zip(cl, cl[1:])) or 1), pret=(c0 - C(T - dt.timedelta(minutes=15))) if C(T - dt.timedelta(minutes=15)) else None)
                v0, v30 = vat(T), vat(T - dt.timedelta(minutes=30)); f["dv"] = (v0 - v30) if v0 and v30 else None
                v1 = vat(E); f["fdv"] = (v1 - v0) if v1 and v0 else None
                f["gs"] = 1 if sum(gn.values()) > 0 else -1; f["vs"] = 1 if sum(vn.values()) > 0 else -1
                def nodes(m):
                    mx = max(abs(x) for x in m.values()); return {k: x for k, x in m.items() if abs(x) >= 0.4 * mx}
                Gn, Vn = nodes(gn), nodes(vn)
                ga = [k for k in Gn if k > S]; gb = [k for k in Gn if k < S]
                # R1：上下最近的 GEX 节点符号相反
                f["r1"] = None
                if ga and gb:
                    ka, kb = min(ga), max(gb)
                    if Gn[ka] * Gn[kb] < 0:
                        f["r1"] = (kb, ka); f["brk"] = any(p[0] > ka or p[1] < kb for p in path60)
                va = [k for k in Vn if k > S]; vb = [k for k in Vn if k < S]
                f["r2"] = bool(va and vb)
                # R3：spot±15 内，相距 ≤10 点的两个 GEX 节点符号相反
                kk = sorted(k for k in Gn if abs(k - S) <= 15)
                f["r3"] = any(Gn[a] * Gn[b] < 0 and b - a <= 10 for a in kk for b in kk if b > a)
                F.append(f)
        T += dt.timedelta(minutes=5)
sg = lambda x: 1 if x > 0 else -1
def m(s):
    if not s: return "—"
    r = [f for f in s if f["pret"] is not None and abs(f["pret"]) >= 3]; rev = sum(sg(f["ret"]) != sg(f["pret"]) for f in r)
    return (f"{len(s):>3} 帧/{len({f['day'] for f in s}):>2} 天  振幅 {st.median([f['rng'] for f in s]):4.1f}  效率 {st.median([f['eff'] for f in s]):.2f}  "
            f"反转 {rev}/{len(r)}={rev/len(r)*100 if r else 0:3.0f}%  |VIX 30 分钟变动| {st.median([abs(f['fdv']) for f in s if f['fdv'] is not None]):.2f}")
def cmp(lab, cond, claim):
    print(f"■ {lab}  —— 截图：{claim}")
    print(f"   是：{m([f for f in F if cond(f)])}")
    print(f"   否：{m([f for f in F if not cond(f)])}")
print(f"{len(X.DAYS)} 天，{len(F)} 帧；振幅/效率取中位；效率低 = 来回扫\n")
cmp("R1 现价夹在符号相反的 GEX 节点之间", lambda f: f["r1"], "区间压缩 → 突破；突破前 fade")
s = [f for f in F if f["r1"]]; print(f"   60 分钟内突破节点区间 {sum(f['brk'] for f in s)}/{len(s)}；区间宽度中位 {st.median([f['r1'][1]-f['r1'][0] for f in s]):.0f} 点")
cmp("R2 现价夹在 VEX 节点之间", lambda f: f["r2"], "来回扫 → VIX 一动就快")
for lab, sub in (("R2 是", [f for f in F if f["r2"]]), ("R2 否", [f for f in F if not f["r2"]])):
    q = [f for f in sub if f["fdv"] is not None and abs(f["fdv"]) >= 0.20]
    print(f"   {lab} 且之后 30 分钟 |ΔVIX| ≥0.20：{len(q)} 帧  |涨跌| 中位 {st.median([abs(f['ret']) for f in q]) if q else 0:.1f}  效率 {st.median([f['eff'] for f in q]) if q else 0:.2f}")
cmp("R3 叠在一起的反向 GEX 节点（spot±15，相距 ≤10）", lambda f: f["r3"], "突然单边 snap")
cmp("R4 对齐 +GEX +VEX", lambda f: f["gs"] > 0 and f["vs"] > 0, "平静低波；均值回归")
cmp("R5 对齐 −GEX −VEX", lambda f: f["gs"] < 0 and f["vs"] < 0, "vol 扩张；趋势加速")
cmp("R6 错位（+−/−+）", lambda f: f["gs"] != f["vs"], "来回扫、犹豫")
print("\n四态并列：")
for g_, v_ in ((1, 1), (-1, -1), (1, -1), (-1, 1)):
    print(f"   {'+' if g_>0 else '−'}GEX {'+' if v_>0 else '−'}VEX: {m([f for f in F if f['gs']==g_ and f['vs']==v_])}")

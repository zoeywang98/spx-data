"""截图 5 行 GEX×VEX 读法回测（有 VEX 的天：10-08、10-09、10-12→10-23）。
帧：09:45–15:25 每 5 分钟；结果窗 = 之后 30 分钟（不越过 16:00）。
GEX = Nightwatch series 0DTE；VEX = Nightwatch history 全到期逐 strike 加总（L3 口径）；VIX = TV layout 每分钟 price；SPX = VolSignals 1m K（缺则 NW 页面 spot）。"""
import datetime as dt, json, glob, gzip, os, csv, statistics as st, sys
from zoneinfo import ZoneInfo
ET = ZoneInfo("America/New_York")
NW = "/Users/yuwang/.openclaw/workspace-claw-general/nightwatch/data"
KL = "/Users/yuwang/.openclaw/workspace-claw-0tde/spx_kline/history/SPX"
VX = "/Users/yuwang/.openclaw/workspace-claw-general/tv_prices/layouts/aE4H0b7t/history/VIX"
W, H = 30, 30
VEX0 = "--vex0" in sys.argv   # 只用 0DTE VEX
DAYS = sorted(d for d in os.listdir(f"{NW}/history/SPX") if len(glob.glob(f"{NW}/history/SPX/{d}/SPX_VEX_*.json.gz")) > 50)

def series(day):
    out = []
    for l in open(f"{NW}/series/SPX/{day}.jsonl"):
        try: r = json.loads(l)
        except ValueError: continue
        if r.get("dte") == 0 and r.get("spot"):
            out.append((dt.datetime.fromisoformat(r["t"]).astimezone(ET), r["spot"], {k: v for k, v in r["k"]}))
    return sorted(out, key=lambda x: x[0])

def vexes(day):
    out = []
    for p in sorted(glob.glob(f"{NW}/history/SPX/{day}/SPX_VEX_*.json.gz")):
        d = json.load(gzip.open(p)); t = dt.datetime.fromisoformat(d["captured_at"]).astimezone(ET)
        if t.time() < dt.time(9, 30): continue
        cols = [i for i, x in enumerate(d["dte"]) if x == 0] if VEX0 else range(len(d["dte"]))
        out.append((t, {k: sum((row[i] or 0) for i in cols) for k, row in zip(d["strikes"], d["values"])}))
    return out

def bars(day, ser):
    j = json.load(open(f"{KL}/{day}.json"))
    b = [(dt.datetime.fromisoformat(x["time"]).astimezone(ET) + dt.timedelta(minutes=1), x["high"], x["low"], x["close"]) for x in j["bars"]]
    if b[-1][0].time() < dt.time(16): b = [(t, s, s, s) for t, s, g in ser]
    return b

def vix(day):
    out = []
    for r in csv.DictReader(open(f"{VX}/{day}.csv")):
        t = dt.datetime.fromisoformat(r["time"]).astimezone(ET)
        if dt.time(9, 30) <= t.time() <= dt.time(16, 1) and r["price"]: out.append((t, float(r["price"])))
    return out

def at(xs, T, stale=300):
    best = None
    for x in xs:
        if x[0] <= T: best = x
        else: break
    return best if best and (T - best[0]).total_seconds() <= stale else None

F = []  # 每帧特征 + 结果
for day in DAYS:
    ser, vx, bs, vi = series(day), vexes(day), None, vix(day)
    bs = bars(day, ser); D = dt.date.fromisoformat(day)
    T = dt.datetime.combine(D, dt.time(9, 45), ET)
    while T.time() <= dt.time(15, 25):
        g, v, b0 = at(ser, T), at(vx, T, 600), at(bs, T, 120)
        E = min(T + dt.timedelta(minutes=H), dt.datetime.combine(D, dt.time(16), ET))
        b1 = at(bs, E, 300); v0, v1 = at(vi, T, 180), at(vi, E, 180)
        if g and v and b0 and b1:
            S = b0[3]; G = g[2]; V = v[1]
            fut = [x for x in bs if T < x[0] <= E]
            f = dict(day=day, T=T, S=S, ret=b1[3] - S, hi=max(x[1] for x in fut) - S, lo=min(x[2] for x in fut) - S,
                     dvix=(v1[1] - v0[1]) if v0 and v1 else None)
            f["rng"] = f["hi"] - f["lo"]
            bp = at(bs, T - dt.timedelta(minutes=15), 300); vp_ = at(vi, T - dt.timedelta(minutes=15), 180)
            f["pret"] = S - bp[3] if bp and bp[0].date() == D else None
            f["pdvix"] = (v0[1] - vp_[1]) if v0 and vp_ else None
            f["v_net"] = sum(x for k, x in V.items() if abs(k - S) <= W)
            gn = {k: x for k, x in G.items() if abs(k - S) <= W}; vn = {k: x for k, x in V.items() if abs(k - S) <= W}
            f["g_net"] = sum(gn.values()); f["g_abs"] = sum(abs(x) for x in gn.values())
            f["v_abs"] = sum(abs(x) for x in vn.values())
            f["v_above"] = sum(x for k, x in vn.items() if k > S); f["v_below"] = sum(x for k, x in vn.items() if k < S)
            f["g_above"] = sum(x for k, x in gn.items() if k > S)
            gp = {k: x for k, x in gn.items() if x > 0}; vp = {k: x for k, x in vn.items() if x > 0}
            f["kg"] = max(gp, key=gp.get) if gp else None; f["kv"] = max(vp, key=vp.get) if vp else None
            ceil = [k for k, x in gn.items() if k > S and x > 0]
            f["ceil"] = max(ceil, key=lambda k: gn[k]) if ceil else None
            # 同一 strike 边界 GEX、VEX 都换号（spot±15，5 点格）
            ks = sorted(k for k in set(gn) & set(vn) if abs(k - S) <= 15 and k % 5 == 0)
            f["flip"] = [(a, b) for a, b in zip(ks, ks[1:]) if b - a == 5 and gn[a] * gn[b] < 0 and vn[a] * vn[b] < 0
                         and (gn[a] < 0) == (vn[a] < 0)]
            F.append(f)
        T += dt.timedelta(minutes=5)

def pct(xs, q): xs = sorted(xs); return xs[int(q * (len(xs) - 1))]
def show(name, sub, base, keyf, fmt):
    nd = len({f["day"] for f in sub})
    print(f"  {name}: 帧 {len(sub)}（{nd} 天）  {fmt(sub)}   |  其余帧 {len(base)}  {fmt(base)}")

print(f"样本 {len(DAYS)} 天 {DAYS[0]}→{DAYS[-1]}，有效帧 {len(F)}；VEX={'0DTE' if VEX0 else '全到期'}；结果窗 {H} 分钟\n")
med = lambda key: (lambda s: f"{key} 中位 {st.median([f[key] for f in s]):.1f}" if s else "—")
absret = lambda s: f"|30分钟涨跌| 中位 {st.median([abs(f['ret']) for f in s]):.1f}，振幅中位 {st.median([f['rng'] for f in s]):.1f}" if s else "—"

# R1
r1 = [f for f in F if f["kg"] and f["kv"] and abs(f["kg"] - f["kv"]) <= 10 and f["g_net"] > 0]
rest = [f for f in F if f not in r1]
print("① +GEX 与 +VEX 同区（spot±30 最大 +GEX strike 与最大 +VEX strike 相距 ≤10，且 0DTE 净 GEX >0）→ pin & drift")
show("触发", r1, rest, None, absret)
tw = lambda s: f"向簇靠近率 {sum(abs(f['S']+f['ret']-f['kg']) < abs(f['S']-f['kg']) for f in s)}/{len(s)} = {sum(abs(f['S']+f['ret']-f['kg']) < abs(f['S']-f['kg']) for f in s)/len(s)*100:.0f}%" if s else "—"
show("drift", r1, [f for f in rest if f["kg"]], None, tw)

# R2
r2 = [f for f in F if f["g_net"] < 0 and f["v_below"] > 0 and f["v_below"] >= 2 / 3 * f["v_abs"]]
rest = [f for f in F if f not in r2]
up = lambda s: (f"30 分钟上涨 {sum(f['ret']>0 for f in s)}/{len(s)} = {sum(f['ret']>0 for f in s)/len(s)*100:.0f}%，均 {st.mean(f['ret'] for f in s):+.1f}；"
                f"VIX 跌 {sum((f['dvix'] or 0)<0 for f in s)}/{sum(f['dvix'] is not None for f in s)}") if s else "—"
print("\n② −GEX 但 +VEX 堆在下方（0DTE 净 GEX <0；下方 +VEX 净 >0 且 ≥ 合计 |VEX| 2/3）→ vol 压缩反弹")
show("触发", r2, rest, None, up)

# R3
r3 = [f for f in F if f["g_net"] > 0 and f["v_above"] < 0 and f["ceil"]]
ctl = [f for f in F if f["g_net"] > 0 and f["v_above"] >= 0 and f["ceil"]]
held = lambda s: (f"30 分钟内没碰天花板 {sum(f['S']+f['hi']<f['ceil'] for f in s)}/{len(s)} = {sum(f['S']+f['hi']<f['ceil'] for f in s)/len(s)*100:.0f}%（天花板距现价中位 {st.median([f['ceil']-f['S'] for f in s]):.0f} 点）") if s else "—"
print("\n③ +GEX 但上方 −VEX（0DTE 净 GEX >0；上方 VEX 净 <0；天花板 = 上方最大 +GEX strike）→ 天花板守住，直到 vol 崩")
show("触发", r3, ctl, None, held)
vc = [f for f in r3 if f["dvix"] is not None and f["dvix"] <= -0.3]; vn_ = [f for f in r3 if f["dvix"] is not None and f["dvix"] > -0.3]
show("其中 VIX 30 分钟 ≤−0.3（vol 崩）", vc, vn_, None, held)

# R4
ga = sorted(f["g_abs"] for f in F); va = sorted(f["v_abs"] for f in F)
gq, vq = pct(ga, 1 / 3), pct(va, 2 / 3)
r4 = [f for f in F if f["g_abs"] <= gq and f["v_abs"] >= vq and f["dvix"] is not None]
rest = [f for f in F if f not in r4 and f["dvix"] is not None]
def corr(s):
    if len(s) < 3: return "—"
    x = [f["dvix"] for f in s]; y = [f["ret"] for f in s]
    c = st.correlation(x, y)
    mv = [f for f in s if abs(f["dvix"]) >= 0.1]
    opp = sum((f["dvix"] > 0) != (f["ret"] > 0) for f in mv)
    return f"corr(ΔVIX, ΔSPX) = {c:+.2f}；VIX 动 ≥0.1 时 SPX 反向 {opp}/{len(mv)} = {opp/len(mv)*100 if mv else 0:.0f}%"
print(f"\n④ GEX 平、VEX 主导（spot±30 |GEX| 在全部帧下 1/3 且 |VEX| 在上 1/3）→ 价格跟 VIX 走")
show("触发", r4, rest, None, corr)

# R5
r5 = [f for f in F if f["flip"]]
rest = [f for f in F if not f["flip"]]
print("\n⑤ 同一 strike GEX/VEX 同时换号（spot±15，相邻 5 点 strike 两者都变号、方向一致）→ 方向加速")
show("触发", r5, rest, None, absret)
def cross(s):
    n = c = 0
    for f in s:
        a, b = f["flip"][0]; k = (a + b) / 2
        if f["S"] + f["lo"] <= k <= f["S"] + f["hi"] and abs(f["S"] - k) >= 1:
            n += 1; d = 1 if k > f["S"] else -1; c += (f["ret"] * d > abs(k - f["S"]))
    return f"30 分钟内穿过换号位 {n} 次，穿过后收在穿越方向外侧 {c}/{n}" if n else "—"
print("  " + cross(r5))

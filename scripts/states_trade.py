"""截图「How We Trade」四态，逐分钟扫描（09:45–15:30），每个 setup 触发后 30 分钟冷却；出场 = 30 / 60 分钟后收盘（不越过 16:00）。
状态：0–5DTE 净 GEX、7–78DTE 净 VEX（spot±30），取 ≤t 最新一帧（≤5 分钟）。10-12→10-23。
setup（所有状态都跑，按状态分组看）：
 S1 fade +GEX 边：现价上方最强 +GEX strike（spot+3..+30）= 上边、下方 = 下边；1m 高点碰上边（距 ≤1）→ 空；低点碰下边 → 多。
    「add on VIX bleed」= 多单且入场前 30 分钟 VIX ≤−0.10 的子集。
 S2 趋势回撤：前 30 分钟跌 ≥8 点后从低点反弹 ≥4 点 → 空（sell rips）；涨 ≥8 后从高点回落 ≥4 → 多（buy dips）。
 S3 rip into +GEX：前 15 分钟涨 ≥4 点且碰到上边 → 空；「IV compressing」= 入场前 15 分钟 VIX ≤−0.10 子集。
 S4 panic → vanna buy：前 30 分钟跌 ≥10 点、创当日新低后 15 分钟内，VIX 从 15 分钟高点回落 ≥0.15 → 多。"""
import datetime as dt, json, glob, gzip, csv, os, statistics as st
import bt_vac_dn as B
from zoneinfo import ZoneInfo
ET = ZoneInfo("America/New_York")
NW = "/Users/yuwang/.openclaw/workspace-claw-general/nightwatch/data/history/SPX"
VX = "/Users/yuwang/.openclaw/workspace-claw-general/tv_prices/layouts/aE4H0b7t/history/VIX"
DAYS = [d for d in sorted(os.listdir(NW)) if "2026-10-12" <= d <= "2026-10-23"]
def grids(day, metric, lo, hi):
    out = []
    for p in sorted(glob.glob(f"{NW}/{day}/SPX_{metric}_*.json.gz")):
        d = json.load(gzip.open(p)); t = dt.datetime.fromisoformat(d["captured_at"]).astimezone(ET)
        if t.time() < dt.time(9, 30): continue
        ix = [i for i, x in enumerate(d["dte"]) if lo <= x <= hi]
        out.append((t, {k: sum(r[i] or 0 for i in ix) for k, r in zip(d["strikes"], d["values"])}))
    return out
def vix(day):
    out = {}
    for r in csv.DictReader(open(f"{VX}/{day}.csv")):
        t = dt.datetime.fromisoformat(r["time"]).astimezone(ET).replace(second=0)
        if r["price"]: out[t] = float(r["price"])
    return out
T_ = []
for day in DAYS:
    D = dt.date.fromisoformat(day)
    j = json.load(open(f"{B.KL}/{day}.json"))
    bars = {dt.datetime.fromisoformat(x["time"]).astimezone(ET) + dt.timedelta(minutes=1): (x["high"], x["low"], x["close"]) for x in j["bars"]}
    if max(bars).time() < dt.time(16):
        bars = {t.replace(second=0) + dt.timedelta(minutes=1): (s, s, s) for t, s, g in B.heat_series(day)}
    G, V, VI = grids(day, "GEX", 0, 5), grids(day, "VEX", 7, 78), vix(day)
    ts = sorted(bars); C = lambda t: next((bars[x][2] for x in reversed(ts) if x <= t), None)
    def vat(t):
        for k in range(4):
            x = VI.get(t - dt.timedelta(minutes=k))
            if x: return x
    gi = vi_ = 0; last = {}
    for t in ts:
        if not (dt.time(9, 45) <= t.time() <= dt.time(15, 30)): continue
        while gi + 1 < len(G) and G[gi + 1][0] <= t: gi += 1
        while vi_ + 1 < len(V) and V[vi_ + 1][0] <= t: vi_ += 1
        if G[gi][0] > t or V[vi_][0] > t or (t - G[gi][0]).seconds > 300 or (t - V[vi_][0]).seconds > 300: continue
        h, l, c = bars[t]; S = C(t - dt.timedelta(minutes=1)) or c
        g = {k: x for k, x in G[gi][1].items() if abs(k - S) <= 30}; v = {k: x for k, x in V[vi_][1].items() if abs(k - S) <= 30}
        state = ("+GEX" if sum(g.values()) > 0 else "−GEX") + " " + ("+VEX" if sum(v.values()) > 0 else "−VEX")
        up = {k: x for k, x in g.items() if k >= S + 3 and x > 0}; dn = {k: x for k, x in g.items() if k <= S - 3 and x > 0}
        ue = max(up, key=up.get) if up else None; le = max(dn, key=dn.get) if dn else None
        win = [bars[x] for x in ts if t - dt.timedelta(minutes=30) < x <= t]
        p30, p15 = C(t - dt.timedelta(minutes=30)), C(t - dt.timedelta(minutes=15))
        v0, v30, v15 = vat(t), vat(t - dt.timedelta(minutes=30)), vat(t - dt.timedelta(minutes=15))
        dv30 = v0 - v30 if v0 and v30 else None; dv15 = v0 - v15 if v0 and v15 else None
        cands = []
        if ue and h >= ue - 1: cands.append(("S1", -1, dict(vb=False)))
        if le and l <= le + 1: cands.append(("S1", 1, dict(vb=dv30 is not None and dv30 <= -0.10)))
        if p30 and win:
            lo30 = min(x[1] for x in win); hi30 = max(x[0] for x in win)
            if c - p30 <= -8 and False: pass
            if p30 - lo30 >= 8 and c - lo30 >= 4 and c < p30: cands.append(("S2", -1, {}))
            if hi30 - p30 >= 8 and hi30 - c >= 4 and c > p30: cands.append(("S2", 1, {}))
        if p15 and ue and c - p15 >= 4 and h >= ue - 1: cands.append(("S3", -1, dict(ivc=dv15 is not None and dv15 <= -0.10)))
        if p30 and win and p30 - min(x[1] for x in win) >= 10:
            dlow = min(bars[x][1] for x in ts if x <= t); lowt = max(x for x in ts if x <= t and bars[x][1] == dlow)
            vw = [vat(t - dt.timedelta(minutes=k)) for k in range(15)]; vw = [x for x in vw if x]
            if (t - lowt).seconds <= 900 and vw and v0 and max(vw) - v0 >= 0.15: cands.append(("S4", 1, {}))
        for name, d, ex in cands:
            if name + str(d) in last and (t - last[name + str(d)]).seconds < 1800: continue
            last[name + str(d)] = t
            e30 = min(t + dt.timedelta(minutes=30), dt.datetime.combine(D, dt.time(16), ET)); e60 = min(t + dt.timedelta(minutes=60), dt.datetime.combine(D, dt.time(16), ET))
            T_.append(dict(day=day, t=t, s=name, d=d, state=state, r30=(C(e30) - c) * d, r60=(C(e60) - c) * d, **ex))
fmt = lambda s, k="r30": f"{sum(x[k]>0 for x in s)}/{len(s)} {sum(x[k]>0 for x in s)/len(s)*100:3.0f}% {st.mean(x[k] for x in s):+5.1f}" if s else "—"
STATES = ["+GEX +VEX", "−GEX −VEX", "+GEX −VEX", "−GEX +VEX"]
print(f"{len(DAYS)} 天；格子 = 胜/笔 胜率 均点数（30 分钟出场 | 60 分钟出场）\n")
def table(title, pick, claim):
    print(f"### {title}   截图对应：{claim}")
    for stt in STATES + ["全部"]:
        s = [x for x in T_ if pick(x) and (stt == "全部" or x["state"] == stt)]
        print(f"  {stt:<10} {fmt(s):>18} | {fmt(s, 'r60'):>18}   ({len({x['day'] for x in s})} 天)")
    print()
table("S1 空 上 +GEX 边", lambda x: x["s"] == "S1" and x["d"] == -1, "+GEX +VEX")
table("S1 多 下 +GEX 边", lambda x: x["s"] == "S1" and x["d"] == 1, "+GEX +VEX")
table("S1 多 下边 + VIX bleed", lambda x: x["s"] == "S1" and x["d"] == 1 and x["vb"], "+GEX +VEX add on VIX bleed")
table("S2 空 sell rips（下跌趋势反弹）", lambda x: x["s"] == "S2" and x["d"] == -1, "−GEX −VEX")
table("S2 多 buy dips（上涨趋势回落）", lambda x: x["s"] == "S2" and x["d"] == 1, "−GEX −VEX")
table("S3 空 rip into +GEX", lambda x: x["s"] == "S3", "+GEX −VEX")
table("S3 空 rip into +GEX，IV 压缩时", lambda x: x["s"] == "S3" and x["ivc"], "+GEX −VEX：IV 压缩 → 减空（应更差）")
table("S3 空 rip into +GEX，IV 不压缩", lambda x: x["s"] == "S3" and not x["ivc"], "+GEX −VEX")
table("S4 多 panic → VIX 回落", lambda x: x["s"] == "S4", "−GEX +VEX")
json.dump([dict(x, t=x["t"].isoformat()) for x in T_], open("states_trade.json", "w"), ensure_ascii=False)

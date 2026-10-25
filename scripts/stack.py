"""Stacked Nodes「Volatility Springs」。上下相邻的反号暴露 = 弹簧；价格穿过两者分界 → 看之后 30 分钟。
GEX：07-15→10-23，0DTE（7–9 月 heatmap，10 月 series）。VEX：10-08→10-23，Nightwatch history，7–78DTE（--vall = 0–78DTE）。
弹簧：spot±30、5 点格，分界 B = k+2.5；上区 = k+5,k+10 合计、下区 = k,k−5 合计；两区反号，且各自 |区| ≥ 窗内最大单 strike |值| ×40%（--m=）。
对照：同号相邻区（+/+、−/−，同样大小门槛）。事件 = 1 分钟收盘越过 B（前一根在另一侧）；同一 B 同一天 30 分钟冷却。
帧取 ≤t 最新（≤5 分钟），B 由穿越前一分钟那帧定。结果：30 分钟后收盘（不越 16:00）、30 分钟振幅（收盘高低）、ΔVIX 30 分钟（08-24 起）。"""
import datetime as dt, json, csv, glob, gzip, sys, statistics as st, collections
import bt_vac_dn as B
from zoneinfo import ZoneInfo
ET = ZoneInfo("America/New_York")
M = float(next((a.split("=")[1] for a in sys.argv if a.startswith("--m=")), 0.40))
VALL = "--vall" in sys.argv
NW = "/Users/yuwang/.openclaw/workspace-claw-general/nightwatch/data/history/SPX"
V5 = [(dt.datetime.fromtimestamp(b[0], ET) + dt.timedelta(minutes=5), b[4]) for b in json.load(open("/Users/yuwang/skylit-learn/backtest/tv_vix1d/raw_VIX_5m.json"))]
def vix_series(day):
    if day <= "2026-10-09": return [x for x in V5 if x[0].date().isoformat() == day]
    out = []
    try:
        for r in csv.DictReader(open(f"/Users/yuwang/.openclaw/workspace-claw-general/tv_prices/layouts/aE4H0b7t/history/VIX/{day}.csv")):
            t = dt.datetime.fromisoformat(r["time"]).astimezone(ET)
            if r["price"] and dt.time(9, 30) <= t.time() <= dt.time(16, 1): out.append((t, float(r["price"])))
    except FileNotFoundError: pass
    return out
def vat(xs, T):
    b = [x for x in xs if x[0] <= T]; return b[-1][1] if b and (T - b[-1][0]).total_seconds() <= 600 else None
def vgrids(day):
    out = []
    for p in sorted(glob.glob(f"{NW}/{day}/SPX_VEX_*.json.gz")):
        d = json.load(gzip.open(p)); t = dt.datetime.fromisoformat(d["captured_at"]).astimezone(ET)
        if t.time() < dt.time(9, 30): continue
        ix = [i for i, x in enumerate(d["dte"]) if (0 if VALL else 7) <= x <= 78]
        out.append((t, d.get("spot"), {k: sum(r[i] or 0 for i in ix) for k, r in zip(d["strikes"], d["values"])}))
    return out
def springs(g, S):
    near = {k: v for k, v in g.items() if abs(k - S) <= 30 and k % 5 == 0}
    mx = max((abs(v) for v in near.values()), default=0)
    if not mx: return []
    out = []
    for k in range(int(S - 25) // 5 * 5, int(S + 25) + 1, 5):
        up = near.get(k + 5, 0) + near.get(k + 10, 0); dn = near.get(k, 0) + near.get(k - 5, 0)
        if abs(up) >= M * mx and abs(dn) >= M * mx:
            out.append((k + 2.5, ("+" if up > 0 else "−") + "/" + ("+" if dn > 0 else "−")))
    return out
EV = []
def scan(day, frames, bars, kind):
    D = dt.date.fromisoformat(day); end = dt.datetime.combine(D, dt.time(16), ET)
    vx = vix_series(day); ca = lambda T: ([c for t, c in bars if t <= T] or [None])[-1]
    fi = 0; last = {}
    for i in range(1, len(bars)):
        t, c = bars[i]; tp, cp = bars[i - 1]
        if not (dt.time(9, 45) <= t.time() <= dt.time(15, 30)): continue
        while fi + 1 < len(frames) and frames[fi + 1][0] <= tp: fi += 1
        ft, S, g = frames[fi]
        if ft > tp or (tp - ft).total_seconds() > 300: continue
        for b, typ in springs(g, S or cp):
            d = 1 if cp < b <= c else -1 if cp > b >= c else 0
            if not d or ((b, d) in last and (t - last[(b, d)]).total_seconds() < 1800): continue
            last[(b, d)] = t
            e = min(t + dt.timedelta(minutes=30), end); fut = [x for tt, x in bars if t < tt <= e]
            if not fut: continue
            v0, v1 = vat(vx, t), vat(vx, e)
            EV.append(dict(day=day, kind=kind, typ=typ, d=d, ret=ca(e) - c, rng=max(fut + [c]) - min(fut + [c]),
                           dvix=v1 - v0 if v0 and v1 else None))
for day, src in B.days():
    heat = B.heat_hm(day) if src == "hm" else B.heat_series(day)
    bars = B.bars_replay(day) if src == "hm" else B.bars_kl(day)
    if src == "ser" and bars[-1][0].time() < dt.time(16): bars = [(t, sp) for t, sp, g in heat]
    scan(day, heat, bars, "GEX")
    if src == "ser" and day >= "2026-10-08":
        vg = vgrids(day)
        if vg: scan(day, vg, bars, "VEX")
def row(s):
    if not s: return "—"
    cont = sum(f["ret"] * f["d"] > 0 for f in s); up = sum(f["ret"] > 0 for f in s); v = [f["dvix"] for f in s if f["dvix"] is not None]
    return (f"{len(s):>4} 次/{len({f['day'] for f in s}):>2} 天  续行 {cont/len(s)*100:3.0f}%  顺向均 {st.mean(f['ret']*f['d'] for f in s):+5.1f}  "
            f"30 分钟后涨 {up/len(s)*100:3.0f}% 均 {st.mean(f['ret'] for f in s):+5.1f}  振幅中位 {st.median(f['rng'] for f in s):4.1f}  "
            f"ΔVIX {('%+.2f' % st.mean(v)) if v else '—'} (n={len(v)})")
for kind in ("GEX", "VEX"):
    E = [f for f in EV if f["kind"] == kind]
    print(f"\n## {kind}  {len({f['day'] for f in E})} 天 {min(f['day'] for f in E)}→{max(f['day'] for f in E)}  门槛 {M:.0%}" + ("（VEX 0–78DTE）" if kind == "VEX" and VALL else "（VEX 7–78DTE）" if kind == "VEX" else "（0DTE）"))
    for typ in ("+/−", "−/+", "+/+", "−/−"):
        for d, lab in ((-1, "向下穿"), (1, "向上穿")):
            print(f"  上{typ[0]}下{typ[2]} {lab}  " + row([f for f in E if f["typ"] == typ and f["d"] == d]))

"""尾盘 GEX 真空（5 分钟一读、20%、连续两次、每时段每方向一天一次、持有到 16:00）× 两 King 夹住。07-15→10-23。
夹住（入场帧）：0DTE spot±30 内 |GEX| 最大、第二大分处现价两侧，第二 ≥ 第一 50%。
vol 平 = 入场前 30 分钟 |ΔVIX| <0.10（VIX 仅 08-24 起；之前记为未知）。
版本：原规则 / 否决夹住 / 否决「夹住且 vol 平」/ 只做夹住 / 夹住时以信号方向的 King 为目标（碰到即出，否则收盘）。"""
import datetime as dt, json, statistics as st, io, contextlib
import bt_vac_dn as B
with contextlib.redirect_stdout(io.StringIO()):
    import potential as P
from zoneinfo import ZoneInfo
ET = ZoneInfo("America/New_York")
WINS = [(dt.time(14, 30), dt.time(15)), (dt.time(15), dt.time(15, 30)), (dt.time(15, 30), dt.time(16)), (dt.time(14, 30), dt.time(16))]
def trap(g, S):
    near = {k: v for k, v in g.items() if abs(k - S) <= 30 and k % 5 == 0 and v}
    if len(near) < 2: return None
    k1, k2 = sorted(near, key=lambda k: -abs(near[k]))[:2]
    return (k1, k2) if (k1 - S) * (k2 - S) < 0 and abs(near[k2]) >= 0.5 * abs(near[k1]) else None
rows = []
for day, src in B.days():
    heat = B.heat_hm(day) if src == "hm" else B.heat_series(day)
    if src == "hm":
        j = json.load(open(f"{B.BT}/nw_replay/SPX_{day}.json"))
        bars = [(dt.datetime.fromtimestamp(b[0] / 1000, ET) + dt.timedelta(minutes=1), b[2], b[3], b[4]) for b in j["bars"]]
    else:
        j = json.load(open(f"{B.KL}/{day}.json"))
        bars = [(dt.datetime.fromisoformat(x["time"]).astimezone(ET) + dt.timedelta(minutes=1), x["high"], x["low"], x["close"]) for x in j["bars"]]
        if bars[-1][0].time() < dt.time(16): bars = [(t, s, s, s) for t, s, g in heat]
    vx = P.vix_series(day) if day >= "2026-08-24" else []
    D = dt.date.fromisoformat(day); end = dt.datetime.combine(D, dt.time(16), ET)
    ca = lambda T: ([c for t, h, l, c in bars if t <= T] or [None])[-1]
    c16 = ca(end)
    def frame(T):
        xs = [h for h in heat if h[0] <= T]
        return xs[-1] if xs and (T - xs[-1][0]).seconds <= 300 else None
    for wi, (a, b) in enumerate(WINS):
        for d in (-1, 1):
            T = dt.datetime.combine(D, a, ET); E = dt.datetime.combine(D, b, ET); prev = None
            while T < E:
                fr = frame(T); s = B.gex_dir(fr[2], fr[1]) if fr else None
                if s == d and prev == d:
                    px = ca(T); tp = trap(fr[2], fr[1])
                    v0, v1 = (P.vat(vx, T - dt.timedelta(minutes=30)), P.vat(vx, T)) if vx else (None, None)
                    vflat = None if not (v0 and v1) else abs(v1[1] - v0[1]) < 0.10
                    tgt_pnl = (c16 - px) * d
                    if tp:
                        K = max(tp) if d > 0 else min(tp)   # 信号方向那个 King
                        hit = next((t for t, h, l, c in bars if T < t <= end and (h >= K if d > 0 else l <= K)), None)
                        if hit: tgt_pnl = (K - px) * d
                    rows.append(dict(day=day, w=wi, d=d, pnl=(c16 - px) * d, trap=bool(tp), vflat=vflat, tgt=tgt_pnl,
                                     kdist=(abs((max(tp) if d > 0 else min(tp)) - px) if tp else None)))
                    break
                prev = s; T += dt.timedelta(minutes=5)
fmt = lambda s, k="pnl": f"{sum(r[k]>0 for r in s)}/{len(s)} {sum(r[k]>0 for r in s)/len(s)*100:3.0f}% {st.mean(r[k] for r in s):+5.1f}" if s else "—"
VER = [("原规则", lambda r: True, "pnl"), ("否决夹住", lambda r: not r["trap"], "pnl"),
       ("否决 夹住且 vol 平", lambda r: not (r["trap"] and r["vflat"]), "pnl"),
       ("只做夹住（被否决的那些）", lambda r: r["trap"], "pnl"), ("夹住时 King 为目标", lambda r: True, "tgt")]
hdr = ["14:30–15:00", "15:00–15:30", "15:30–16:00", "14:30–16:00 一天一次"]
print(f"{len({r['day'] for r in rows})} 个有信号的交易日（07-15→10-23）；格子 = 胜/笔 胜率 均点数\n")
for d, dn in ((-1, "做空"), (1, "做多"), (0, "多+空")):
    print(f"### {dn}"); print(f"{'':24}" + "".join(f"{h:>22}" for h in hdr))
    for name, cond, k in VER:
        print(f"{name:<24}" + "".join(f"{fmt([r for r in rows if r['w']==wi and (d==0 or r['d']==d) and cond(r)], k):>22}" for wi in range(4)))
    print()
s = [r for r in rows if r["w"] == 3]
print(f"一天一次口径：入场时夹住 {sum(r['trap'] for r in s)}/{len(s)} 笔；夹住时信号方向 King 距入场中位 {st.median([r['kdist'] for r in s if r['trap']]):.1f} 点")
print("夹住 × vol（08-24 起，一天一次）：")
for lab, c in (("夹住 vol 平", lambda r: r["trap"] and r["vflat"] is True), ("夹住 vol 动", lambda r: r["trap"] and r["vflat"] is False),
               ("不夹 vol 平", lambda r: not r["trap"] and r["vflat"] is True), ("不夹 vol 动", lambda r: not r["trap"] and r["vflat"] is False)):
    print(f"  {lab}: {fmt([r for r in s if c(r)])}")
print("按月（一天一次，多+空）：")
for m in ("07", "08", "09", "10"):
    q = [r for r in s if r["day"][5:7] == m]
    print(f"  {m} 月  原规则 {fmt(q)}   否决夹住 {fmt([r for r in q if not r['trap']])}   夹住 {fmt([r for r in q if r['trap']])}")

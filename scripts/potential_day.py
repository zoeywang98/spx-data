"""全天每 10 分钟帧（09:40–15:00），GEX 真空方向 × 入场前 30 分钟 VIX 变化；结果 = 60 分钟后收盘同号（不越过 16:00）。"""
import datetime as dt, statistics as st, sys
import bt_vac_dn as B, potential as P
from zoneinfo import ZoneInfo
ET = ZoneInfo("America/New_York"); TH = P.TH
rows = []
for day, src in B.days():
    if day < "2026-08-24": continue
    heat = B.heat_hm(day) if src == "hm" else B.heat_series(day)
    bars = B.bars_replay(day) if src == "hm" else B.bars_kl(day)
    if src == "ser" and bars[-1][0].time() < dt.time(16): bars = [(t, sp) for t, sp, g in heat]
    vx = P.vix_series(day); D = dt.date.fromisoformat(day)
    ca = lambda T: ([c for t, c in bars if t <= T] or [None])[-1]
    T = dt.datetime.combine(D, dt.time(9, 40), ET)
    while T.time() <= dt.time(15):
        xs = [h for h in heat if h[0] <= T]
        if xs and (T - xs[-1][0]).total_seconds() <= 300:
            d = B.gex_dir(xs[-1][2], xs[-1][1])
            v0, v1 = P.vat(vx, T - dt.timedelta(minutes=30)), P.vat(vx, T)
            if d and v0 and v1 and v1[0] > v0[0]:
                dv = v1[1] - v0[1]; E = min(T + dt.timedelta(minutes=60), dt.datetime.combine(D, dt.time(16), ET))
                reg = "同向" if -d * dv >= TH else "反向" if d * dv >= TH else "走平"
                ph = "早盘" if T.time() < dt.time(11) else "中盘" if T.time() < dt.time(14, 30) else "尾盘"
                rows.append(dict(day=day, ph=ph, pnl=(ca(E) - ca(T)) * d, reg=reg))
        T += dt.timedelta(minutes=10)
fmt = lambda s: f"{sum(r['pnl']>0 for r in s)}/{len(s)} = {sum(r['pnl']>0 for r in s)/len(s)*100:.0f}% 均 {st.mean(r['pnl'] for r in s):+.1f}（{len({r['day'] for r in s})}天）" if s else "—"
print(f"VIX 门槛 ±{TH}；60 分钟窗")
print(f"{'':8}{'全部':>28}{'VIX 同向':>28}{'VIX 走平':>28}{'VIX 反向':>28}")
for ph in ("早盘", "中盘", "尾盘"):
    s = [r for r in rows if r["ph"] == ph]
    print(f"{ph:<8}" + "".join(f"{fmt([r for r in s if reg is None or r['reg'] == reg]):>28}" for reg in (None, "同向", "走平", "反向")))

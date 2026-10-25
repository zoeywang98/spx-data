"""T1 gamma：+GEX 逆势稳定 / −GEX 顺势放大。07-15→10-23。帧 09:45–15:25 每 5 分钟，结果 30 分钟。
GEX：7–9 月 heatmap（0DTE 列、全到期列），10 月 series 0DTE（无全到期）。净 = spot±30；另测 spot±10（现价附近 gamma）。"""
import datetime as dt, json, statistics as st
import bt_vac_dn as B
from zoneinfo import ZoneInfo
ET = ZoneInfo("America/New_York")
def heat_full(day):
    d = json.load(open(f"{B.BT}/nw_heatmap/SPX_gex_{day}.json")); out = []
    for hm, sp, f in zip(d["minutes"], d["spot"], d["frames"]):
        if hm and sp and f:
            t = dt.datetime.fromisoformat(hm).astimezone(ET) if "T" in hm else dt.datetime.fromisoformat(f"{day}T{hm}").replace(tzinfo=ET)
            out.append((t + dt.timedelta(minutes=1), sp, {s: (a or 0, z or 0) for s, a, z in zip(f[0], f[1], f[4])}))
    return out
F = []
for day, src in B.days():
    if src == "hm": heat = heat_full(day); bars = B.bars_replay(day)
    else:
        heat = [(t, sp, {k: (v, None) for k, v in g.items()}) for t, sp, g in B.heat_series(day)]; bars = B.bars_kl(day)
        if bars[-1][0].time() < dt.time(16): bars = [(t, sp) for t, sp, g in heat]
    D = dt.date.fromisoformat(day); ca = lambda T: ([c for t, c in bars if t <= T] or [None])[-1]
    T = dt.datetime.combine(D, dt.time(9, 45), ET); hi = 0
    while T.time() <= dt.time(15, 25):
        while hi + 1 < len(heat) and heat[hi + 1][0] <= T: hi += 1
        h = heat[hi]
        if h[0] <= T and (T - h[0]).total_seconds() <= 300:
            S = h[1]; g = h[2]; E = T + dt.timedelta(minutes=30)
            fut = [c for t, c in bars if T < t <= E]
            p0, pm, p1 = ca(T - dt.timedelta(minutes=15)), ca(T), ca(E)
            if fut and p0 and pm and p1:
                f = dict(day=day, pret=pm - p0, ret=p1 - pm, rng=max(fut) - min(fut))
                f["g30"] = sum(v[0] for k, v in g.items() if abs(k - S) <= 30); f["g10"] = sum(v[0] for k, v in g.items() if abs(k - S) <= 10)
                f["a30"] = None if src != "hm" else sum(v[1] for k, v in g.items() if abs(k - S) <= 30)
                F.append(f)
        T += dt.timedelta(minutes=5)
sg = lambda x: 1 if x > 0 else -1
def row(lab, s):
    m = [f for f in s if abs(f["pret"]) >= 3]; rev = sum(sg(f["ret"]) != sg(f["pret"]) for f in m)
    cont = st.mean(f["ret"] * sg(f["pret"]) for f in m)
    print(f"  {lab:<22} {len(s):>5} 帧/{len({f['day'] for f in s}):>2} 天  振幅中位 {st.median([f['rng'] for f in s]):5.1f}  "
          f"前 15 分钟动 ≥3 点后反转 {rev}/{len(m)} = {rev/len(m)*100:3.0f}%  顺前势均 {cont:+5.2f} 点")
print(f"{len({f['day'] for f in F})} 天，{len(F)} 帧\n")
for key, lab in (("g30", "0DTE 净 GEX spot±30"), ("g10", "0DTE 净 GEX spot±10"), ("a30", "全到期净 GEX spot±30（7–9 月）")):
    print(lab)
    s = [f for f in F if f[key] is not None]
    for sgn in (1, -1): row(("+GEX" if sgn > 0 else "−GEX"), [f for f in s if sg(f[key]) == sgn])
    for mon in ("2026-07", "2026-08", "2026-09", "2026-10"):
        ss = [f for f in s if f["day"].startswith(mon)]
        if not ss: continue
        out = []
        for sgn in (1, -1):
            m = [f for f in ss if sg(f[key]) == sgn and abs(f["pret"]) >= 3]
            out.append(f"{'+' if sgn>0 else '−'} 反转 {sum(sg(f['ret'])!=sg(f['pret']) for f in m)}/{len(m)}")
        print(f"     {mon[5:]}月: " + "   ".join(out))
    print()

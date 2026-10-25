"""T3 charm：价格和 IV 不动，dealer 也会因时间流逝再平衡 → 漂移。VolSignals MM 0DTE charm（10 分钟 slot，09-25→10-23）。
现价处 charm = latest_by_price 在 underlying_price 线性插值；换算 ×5/1440（每 5 分钟口径）。正 = dealer 卖（压），负 = 买（托）。
预测 SPX 方向 = −sign(charm)。结果 = 之后 30 分钟（不越过 16:00）。"""
import datetime as dt, json, glob, os, statistics as st, io, contextlib
import bt_vac_dn as B
with contextlib.redirect_stdout(io.StringIO()):
    import potential as P
from zoneinfo import ZoneInfo
ET = ZoneInfo("America/New_York")
VS = "/Users/yuwang/.openclaw/workspace-claw-0tde/volsignals/history/SPX"
F = []
for day in sorted(os.listdir(VS)):
    if not os.path.exists(f"{B.KL}/{day}.json"): continue
    bars = B.bars_kl(day)
    if bars[-1][0].time() < dt.time(16):
        if not os.path.exists(f"{B.NWS}/{day}.jsonl"): continue
        bars = [(t, sp) for t, sp, g in B.heat_series(day)]
    vx = P.vix_series(day); D = dt.date.fromisoformat(day)
    ca = lambda T: ([c for t, c in bars if t <= T] or [None])[-1]
    for p in sorted(glob.glob(f"{VS}/{day}/charm_*.json")):
        hm = p[-9:-5]
        if not ("0940" <= hm <= "1530"): continue
        d = json.load(open(p)); S = d["underlying_price"]; lb = sorted(d["latest_by_price"])
        lo = [x for x in lb if x[0] <= S]; hi = [x for x in lb if x[0] > S]
        if not lo or not hi: continue
        (a, va), (b, vb) = lo[-1], hi[0]; ch = (va + (vb - va) * (S - a) / (b - a)) * 5 / 1440
        T = dt.datetime.fromisoformat(d["data_time"]).astimezone(ET) + dt.timedelta(minutes=2)  # 文件约 data_time+2 分钟可得
        E = min(T + dt.timedelta(minutes=30), dt.datetime.combine(D, dt.time(16), ET))
        p_, p0, p1 = ca(T - dt.timedelta(minutes=30)), ca(T), ca(E)
        v0, v1 = P.vat(vx, T - dt.timedelta(minutes=30)), P.vat(vx, T)
        if p_ and p0 and p1:
            F.append(dict(day=day, hm=hm, ch=ch, ret=p1 - p0, pret=p0 - p_, pdv=(v1[1] - v0[1]) if v0 and v1 else None))
sg = lambda x: 1 if x > 0 else -1
def row(lab, s):
    if not s: print(f"  {lab}: —"); return
    hit = sum(sg(f["ret"]) == -sg(f["ch"]) for f in s)
    pnl = st.mean(-sg(f["ch"]) * f["ret"] for f in s)
    print(f"  {lab:<34} {len(s):>4} 帧/{len({f['day'] for f in s}):>2} 天  方向命中 {hit}/{len(s)} = {hit/len(s)*100:3.0f}%  顺 charm 均 {pnl:+5.2f} 点")
print(f"{len({f['day'] for f in F})} 天，{len(F)} 帧；|charm| 中位 {st.median([abs(f['ch']) for f in F]):.1f}（每 5 分钟口径）\n")
row("全部", F)
for lo, hi in ((0, 10), (10, 25), (25, 1e9)):
    row(f"|charm| {lo}–{hi if hi < 1e9 else '∞'}", [f for f in F if lo <= abs(f["ch"]) < hi])
flat = [f for f in F if abs(f["pret"]) <= 5 and f["pdv"] is not None and abs(f["pdv"]) <= 0.15]
print("\n前 30 分钟价格 |Δ| ≤5 点 且 VIX |Δ| ≤0.15（价格、IV 都没动）")
row("全部", flat); row("|charm| ≥10", [f for f in flat if abs(f["ch"]) >= 10])
print("\n按时段")
for a, b in (("0940", "1100"), ("1100", "1430"), ("1430", "1531")):
    row(f"{a[:2]}:{a[2:]}–{b[:2]}:{b[2:]}", [f for f in F if a <= f["hm"] < b])
    row(f"  其中 |charm| ≥10", [f for f in F if a <= f["hm"] < b and abs(f["ch"]) >= 10])
print("\n按月"); [row(m, [f for f in F if f["day"].startswith(m)]) for m in ("2026-09", "2026-10")]

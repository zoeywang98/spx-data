"""B：GEX defines potential; VIX defines reality。尾盘 GEX 真空入场（5 分钟一读、20%、连续两次、一天一次/时段、持有到 16:00），
按入场时 VIX 30 分钟变化分：同向（信号↑且 VIX 跌 / 信号↓且 VIX 涨）、走平、反向。VIX：≤10-09 用 tv_vix1d 5m（收线 = 开盘+5），≥10-12 用 TV layout 每分钟。"""
import datetime as dt, json, csv, sys, statistics as st
import bt_vac_dn as B
from zoneinfo import ZoneInfo
ET = ZoneInfo("America/New_York")
TH = float(next((a.split("=")[1] for a in sys.argv if a.startswith("--th=")), 0.10))
V5 = [(dt.datetime.fromtimestamp(b[0], ET) + dt.timedelta(minutes=5), b[4]) for b in json.load(open("/Users/yuwang/skylit-learn/backtest/tv_vix1d/raw_VIX_5m.json"))]
def vix_series(day):
    if day <= "2026-10-09":
        return [x for x in V5 if x[0].date().isoformat() == day]
    out = []
    for r in csv.DictReader(open(f"/Users/yuwang/.openclaw/workspace-claw-general/tv_prices/layouts/aE4H0b7t/history/VIX/{day}.csv")):
        t = dt.datetime.fromisoformat(r["time"]).astimezone(ET)
        if r["price"] and dt.time(9, 30) <= t.time() <= dt.time(16, 1): out.append((t, float(r["price"])))
    return out
def vat(xs, T):
    b = [x for x in xs if x[0] <= T]; return b[-1] if b and (T - b[-1][0]).total_seconds() <= 600 else None
WINS = [(dt.time(14, 30), dt.time(15)), (dt.time(15), dt.time(15, 30)), (dt.time(15, 30), dt.time(16))]
rows = []
for day, src in B.days():
    if day < "2026-08-24": continue
    heat = B.heat_hm(day) if src == "hm" else B.heat_series(day)
    bars = B.bars_replay(day) if src == "hm" else B.bars_kl(day)
    if src == "ser" and bars[-1][0].time() < dt.time(16): bars = [(t, sp) for t, sp, g in heat]
    vx = vix_series(day)
    if not vx: continue
    D = dt.date.fromisoformat(day)
    ca = lambda T: ([c for t, c in bars if t <= T] or [None])[-1]
    c16 = ca(dt.datetime.combine(D, dt.time(16), ET))
    def sig(T):
        xs = [h for h in heat if h[0] <= T]
        return B.gex_dir(xs[-1][2], xs[-1][1]) if xs and (T - xs[-1][0]).total_seconds() <= 300 else None
    for wi, (a, b) in enumerate(WINS):
        for d in (1, -1):
            T = dt.datetime.combine(D, a, ET); E = dt.datetime.combine(D, b, ET); prev = None
            while T < E:
                s = sig(T)
                if s == d and prev == d:
                    v0, v1 = vat(vx, T - dt.timedelta(minutes=30)), vat(vx, T)
                    dv = (v1[1] - v0[1]) if v0 and v1 else None
                    reg = None if dv is None else ("同向" if -d * dv >= TH else "反向" if d * dv >= TH else "走平")
                    rows.append(dict(day=day, w=wi, d=d, pnl=(c16 - ca(T)) * d, reg=reg, dv=dv)); break
                prev = s; T += dt.timedelta(minutes=5)
fmt = lambda s: f"{sum(r['pnl']>0 for r in s)}/{len(s)} = {sum(r['pnl']>0 for r in s)/len(s)*100:.0f}% 均 {st.mean(r['pnl'] for r in s):+.1f}" if s else "—"
print(f"样本 {len({r['day'] for r in rows})} 个有信号的交易日（08-24→10-23）；VIX 门槛 ±{TH}\n")
print(f"{'':16}{'全部':>22}{'VIX 同向':>22}{'VIX 走平':>22}{'VIX 反向':>22}")
for wi, w in enumerate(WINS):
    for d, dn in ((-1, "空"), (1, "多")):
        s = [r for r in rows if r["w"] == wi and r["d"] == d]
        print(f"{w[0].strftime('%H:%M')} {dn:<9}" + "".join(f"{fmt([r for r in s if reg is None or r['reg'] == reg]):>22}" for reg in (None, "同向", "走平", "反向")))
print("-" * 104)
for d, dn in ((-1, "空"), (1, "多"), (0, "多+空")):
    s = [r for r in rows if d == 0 or r["d"] == d]
    print(f"三窗合计 {dn:<6}" + "".join(f"{fmt([r for r in s if reg is None or r['reg'] == reg]):>22}" for reg in (None, "同向", "走平", "反向")))
miss = sum(r["reg"] is None for r in rows); print(f"\n无 VIX 数据的入场 {miss} 笔（计入「全部」）")

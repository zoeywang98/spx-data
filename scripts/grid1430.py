"""14:30–15:00 入场 · 连续两次同向 → 入场 · 一天一次 · 持有到 16:00。网格：读数间隔 × 强度门槛（下方/上方净 ≥ 合计 |GEX| 的 x%）。"""
import datetime as dt, sys
import bt_vac_dn as B
from zoneinfo import ZoneInfo
ET = ZoneInfo("America/New_York")
INTS = [1, 2, 3, 5, 10]; PCTS = [0, 10, 15, 20, 25, 30, 40]

def gdir(g, S, st):
    W = B.W
    ga = sum(v for k, v in g.items() if S < k <= S + W)
    gb = sum(v for k, v in g.items() if S - W <= k < S)
    gt = sum(abs(v) for k, v in g.items() if abs(k - S) <= W) or 1
    return 1 if gb > 0 and ga <= 0 and gb >= st * gt else -1 if ga > 0 and gb <= 0 and ga >= st * gt else 0

DAYS = []
for day, src in B.days():
    heat = B.heat_hm(day) if src == "hm" else B.heat_series(day)
    bars = B.bars_replay(day) if src == "hm" else B.bars_kl(day)
    if src == "ser" and bars[-1][0].time() < dt.time(16, 0):
        bars = [(t, sp) for t, sp, g in heat]
    DAYS.append((day, heat, bars))

def close_at(bars, T):
    xs = [c for t, c in bars if t <= T]; return xs[-1] if xs else None

def frame(heat, T):
    xs = [h for h in heat if h[0] <= T]
    return xs[-1] if xs and (T - xs[-1][0]).total_seconds() <= 300 else None

res = {}
for day, heat, bars in DAYS:
    D = dt.date.fromisoformat(day); c16 = close_at(bars, dt.datetime.combine(D, dt.time(16), ET))
    a, b = dt.datetime.combine(D, dt.time(14, 30), ET), dt.datetime.combine(D, dt.time(15, 0), ET)
    fr = {}; T = a
    while T < b: fr[T] = frame(heat, T); T += dt.timedelta(minutes=1)
    for iv in INTS:
        ts = [a + dt.timedelta(minutes=m) for m in range(0, 30, iv)]
        for p in PCTS:
            for d in (-1, 1):
                prev = None
                for T in ts:
                    f = fr[T]; s = gdir(f[2], f[1], p / 100) if f else None
                    if s == d and prev == d:
                        pnl = (c16 - close_at(bars, T)) * d
                        res.setdefault((iv, p, d), []).append((day, pnl)); break
                    prev = s

for d, name in ((-1, "向下（做空）"), (1, "向上（做多）")):
    print(f"\n### {name}   格子 = 胜/笔 胜率 均点数")
    print("间隔\\门槛 " + "".join(f"{p:>20}%" for p in PCTS))
    for iv in INTS:
        row = f"{iv:>3} 分钟  "
        for p in PCTS:
            r = res.get((iv, p, d), []); n = len(r); w = sum(x[1] > 0 for x in r)
            row += f"{f'{w}/{n} {w/n*100:.0f}% {sum(x[1] for x in r)/n:+.1f}' if n else '—':>21}"
        print(row)
    print("（去掉 09-30）")
    for iv in INTS:
        row = f"{iv:>3} 分钟  "
        for p in PCTS:
            r = [x for x in res.get((iv, p, d), []) if x[0] != "2026-09-30"]; n = len(r); w = sum(x[1] > 0 for x in r)
            row += f"{f'{w}/{n} {w/n*100:.0f}% {sum(x[1] for x in r)/n:+.1f}' if n else '—':>21}"
        print(row)
import json; json.dump({f"{k[0]}|{k[1]}|{k[2]}": v for k, v in res.items()}, open("grid1430.json", "w"))

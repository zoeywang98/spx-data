"""大 King Node → 回归磁铁。07-15→10-23，只用 GEX。
GEX：7–9 月 heatmap（0DTE 列；--all 用全到期列，只 7–9 月），10 月 Nightwatch series 0DTE。spot = 同帧页面 spot。
King = spot±50 内（5 点格）|GEX| 最大的 strike；大 = ≥ 第二名 ×R（默认 2）。帧 09:45–15:25 每 5 分钟。
结果：30 / 60 分钟后离 King 更近（收盘价距离缩小）；60 分钟内碰到（1m 高低越过 King）。"""
import datetime as dt, json, statistics as st, sys, collections
import bt_vac_dn as B, cross1 as C1
from zoneinfo import ZoneInfo
ET = ZoneInfo("America/New_York")
ALL = "--all" in sys.argv; R = float(next((a.split("=")[1] for a in sys.argv if a.startswith("--r=")), 2))
F = []
for day, src in B.days():
    if ALL and src != "hm": continue
    if src == "hm":
        heat = [(t, sp, {k: v[1 if ALL else 0] for k, v in g.items()}) for t, sp, g in C1.heat_full(day)]
        j = json.load(open(f"{B.BT}/nw_replay/SPX_{day}.json"))
        bars = [(dt.datetime.fromtimestamp(b[0] / 1000, ET) + dt.timedelta(minutes=1), b[2], b[3], b[4]) for b in j["bars"]]
    else:
        heat = B.heat_series(day)
        j = json.load(open(f"{B.KL}/{day}.json"))
        bars = [(dt.datetime.fromisoformat(x["time"]).astimezone(ET) + dt.timedelta(minutes=1), x["high"], x["low"], x["close"]) for x in j["bars"]]
        if bars[-1][0].time() < dt.time(16): bars = [(t, s, s, s) for t, s, g in heat]
    D = dt.date.fromisoformat(day); end = dt.datetime.combine(D, dt.time(16), ET)
    ca = lambda T: ([c for t, h, l, c in bars if t <= T] or [None])[-1]
    T = dt.datetime.combine(D, dt.time(9, 45), ET); hi = 0
    while T.time() <= dt.time(15, 25):
        while hi + 1 < len(heat) and heat[hi + 1][0] <= T: hi += 1
        t0, S, g = heat[hi]
        if t0 <= T and (T - t0).seconds <= 300:
            near = {k: v for k, v in g.items() if abs(k - S) <= 50 and k % 5 == 0 and v}
            if len(near) >= 2:
                srt = sorted(near, key=lambda k: -abs(near[k])); K, K2 = srt[0], srt[1]
                c0 = ca(T); e30, e60 = min(T + dt.timedelta(minutes=30), end), min(T + dt.timedelta(minutes=60), end)
                path = [(h, l) for t, h, l, c in bars if T < t <= e60]
                if c0 and path:
                    F.append(dict(day=day, T=T, S=c0, K=K, K2=K2, dom=abs(near[K]) / abs(near[K2]), sign=1 if near[K] > 0 else -1,
                                  c30=ca(e30), c60=ca(e60), touch=any(l <= K <= h for h, l in path),
                                  touch2=any(l <= K2 <= h for h, l in path)))
        T += dt.timedelta(minutes=5)
def stat(s, key="K", tk="touch"):
    if not s: return "—"
    n = len(s); a = sum(abs(f["c30"] - f[key]) < abs(f["S"] - f[key]) for f in s); b = sum(abs(f["c60"] - f[key]) < abs(f["S"] - f[key]) for f in s)
    t = sum(f[tk] for f in s); g = st.mean(abs(f["S"] - f[key]) - abs(f["c60"] - f[key]) for f in s)
    return f"{n:>5} 帧/{len({f['day'] for f in s}):>2} 天  30 分钟更近 {a/n*100:3.0f}%  60 分钟更近 {b/n*100:3.0f}%  60 分钟内碰到 {t/n*100:3.0f}%  60 分钟平均靠近 {g:+5.1f} 点"
inb = lambda f, key: 5 <= abs(f[key] - f["S"]) <= 40
big = [f for f in F if f["dom"] >= R and inb(f, "K")]
print(f"{len({f['day'] for f in F})} 天 {min(f['day'] for f in F)}→{max(f['day'] for f in F)}，{len(F)} 帧；GEX = {'全到期（7–9 月）' if ALL else '0DTE'}；大 King = ≥ 第二名 ×{R:g}，距现价 5–40 点\n")
print("大 King          " + stat(big))
print("对照 第二大节点   " + stat([f for f in F if inb(f, "K2")], "K2", "touch2"))
print("对照 King <×R     " + stat([f for f in F if f["dom"] < R and inb(f, "K")]))
print("\n大 King 分组：")
for lab, cond in (("+GEX King", lambda f: f["sign"] > 0), ("−GEX King", lambda f: f["sign"] < 0),
                  ("King 在上方", lambda f: f["K"] > f["S"]), ("King 在下方", lambda f: f["K"] < f["S"]),
                  ("距离 5–15", lambda f: abs(f["K"] - f["S"]) < 15), ("距离 15–25", lambda f: 15 <= abs(f["K"] - f["S"]) < 25), ("距离 25–40", lambda f: abs(f["K"] - f["S"]) >= 25),
                  ("09:45–11:00", lambda f: f["T"].time() < dt.time(11)), ("11:00–14:30", lambda f: dt.time(11) <= f["T"].time() < dt.time(14, 30)), ("14:30–15:25", lambda f: f["T"].time() >= dt.time(14, 30))):
    print(f"  {lab:<14}" + stat([f for f in big if cond(f)]))
print("\n按月：")
for m in ("07", "08", "09", "10"):
    s = [f for f in big if f["day"][5:7] == m]; c = [f for f in F if f["day"][5:7] == m and inb(f, "K2")]
    if s: print(f"  {m} 月 大 King   " + stat(s)); print(f"       对照第二  " + stat(c, "K2", "touch2"))
by = collections.defaultdict(list)
for f in big: by[f["day"]].append(abs(f["c60"] - f["K"]) < abs(f["S"] - f["K"]))
days = sorted(by); maj = sum(sum(v) > len(v) / 2 for v in by.values())
print(f"\n按天：有大 King 的 {len(days)} 天里，60 分钟更近占多数的 {maj} 天；最集中的一天占 {max(len(v) for v in by.values())}/{len(big)} 帧")

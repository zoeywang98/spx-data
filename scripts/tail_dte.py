"""尾盘真空规则 + 0–5DTE GEX / 7–78DTE VEX（10-12→10-23，分到期全表）。
入场：5 分钟一读、门槛 20%、过滤后信号连续两次同向 → 入场、每时段每方向一天一次、持有到 16:00。
GEX 源：0DTE = 全表 dte==0 列；0–5DTE = dte≤5 加总。spot = 同帧页面 spot。价格 = 1m K（10-22 缺 → 页面 spot）。
VEX 过滤（7–78DTE）：
  pos同向 / pos不反向：spot±50 内 +VEX 一侧占 ≥2/3（L3 口径）→ 上/下；要求与信号同向 / 不反向
  净号：做多要求 spot±30 净 VEX >0，做空要求 <0（截图：+VEX vol 跌买、−VEX vol 跌卖）"""
import datetime as dt, json, glob, gzip, statistics as st
import bt_vac_dn as B
from zoneinfo import ZoneInfo
ET = ZoneInfo("America/New_York")
NW = "/Users/yuwang/.openclaw/workspace-claw-general/nightwatch/data/history/SPX"
DAYS = [d for d in sorted(__import__("os").listdir(NW)) if "2026-10-12" <= d <= "2026-10-23"]
def grids(day, metric):
    out = []
    for p in sorted(glob.glob(f"{NW}/{day}/SPX_{metric}_*.json.gz")):
        hm = p[-13:-8]
        if not ("142000" <= p[-14:-8] <= "160100"): continue
        d = json.load(gzip.open(p)); t = dt.datetime.fromisoformat(d["captured_at"]).astimezone(ET)
        z = [i for i, x in enumerate(d["dte"]) if x == 0]; f = [i for i, x in enumerate(d["dte"]) if x <= 5]; b = [i for i, x in enumerate(d["dte"]) if 7 <= x <= 78]
        sm = lambda r, ix: sum(r[i] or 0 for i in ix)
        out.append((t, d["page"].get("spot"), {k: (sm(r, z), sm(r, f), sm(r, b)) for k, r in zip(d["strikes"], d["values"])}))
    return out
def at(xs, T):
    b = [x for x in xs if x[0] <= T]; return b[-1] if b and (T - b[-1][0]).total_seconds() <= 300 else None
def vexpos(v, S):
    pos = {k: x for k, x in v.items() if abs(k - S) <= 50 and x > 0}; tot = sum(pos.values()) or 1
    up = sum(x for k, x in pos.items() if k > S); dn = sum(x for k, x in pos.items() if k < S)
    return 1 if up >= 2 / 3 * tot else -1 if dn >= 2 / 3 * tot else 0
VARS = {"0DTE（原规则）": (0, None), "0–5DTE": (1, None),
        "0DTE + VEX pos 不反向": (0, "nopp"), "0DTE + VEX pos 同向": (0, "same"), "0DTE + VEX 净号": (0, "net"),
        "0–5DTE + VEX pos 不反向": (1, "nopp"), "0–5DTE + VEX pos 同向": (1, "same"), "0–5DTE + VEX 净号": (1, "net")}
WINS = [(dt.time(14, 30), dt.time(15)), (dt.time(15), dt.time(15, 30)), (dt.time(15, 30), dt.time(16)), (dt.time(14, 30), dt.time(16))]
res = {}
for day in DAYS:
    gx, vx = grids(day, "GEX"), grids(day, "VEX")
    bars = B.bars_kl(day)
    if bars[-1][0].time() < dt.time(16): bars = [(t, sp) for t, sp, g in B.heat_series(day)]
    D = dt.date.fromisoformat(day); ca = lambda T: ([c for t, c in bars if t <= T] or [None])[-1]
    c16 = ca(dt.datetime.combine(D, dt.time(16), ET))
    def sig(T, gi, flt):
        g = at(gx, T)
        if not g or not g[1]: return None
        S = g[1]; d = B.gex_dir({k: v[gi] for k, v in g[2].items()}, S)
        if d == 0 or flt is None: return d
        v = at(vx, T)
        if not v: return None
        vb = {k: x[2] for k, x in v[2].items()}
        if flt == "net":
            n = sum(x for k, x in vb.items() if abs(k - S) <= 30); return d if (n > 0) == (d > 0) else 0
        p = vexpos(vb, S)
        return d if (p == d if flt == "same" else p != -d) else 0
    for name, (gi, flt) in VARS.items():
        cache = {}
        for wi, (a, b) in enumerate(WINS):
            for d in (-1, 1):
                T = dt.datetime.combine(D, a, ET); E = dt.datetime.combine(D, b, ET); prev = None
                while T < E:
                    s = cache.setdefault(T, sig(T, gi, flt))
                    if s == d and prev == d:
                        res.setdefault((name, wi, d), []).append((day, T.strftime("%H:%M"), (c16 - ca(T)) * d)); break
                    prev = s; T += dt.timedelta(minutes=5)
fmt = lambda s: f"{sum(x[2]>0 for x in s)}/{len(s)} {sum(x[2]>0 for x in s)/len(s)*100:3.0f}% {st.mean(x[2] for x in s):+5.1f}" if s else "—"
print(f"{len(DAYS)} 天 {DAYS[0]}→{DAYS[-1]}；格子 = 胜/笔 胜率 均点数\n")
hdr = ["14:30–15:00", "15:00–15:30", "15:30–16:00", "14:30–16:00 一天一次"]
for d, dn in ((-1, "做空"), (1, "做多"), (0, "多+空")):
    print(f"### {dn}")
    print(f"{'':26}" + "".join(f"{h:>22}" for h in hdr))
    for name in VARS:
        cells = [res.get((name, wi, d), []) if d else res.get((name, wi, -1), []) + res.get((name, wi, 1), []) for wi in range(4)]
        print(f"{name:<26}" + "".join(f"{fmt(c):>22}" for c in cells))
    print()
json.dump({f"{k[0]}|{k[1]}|{k[2]}": v for k, v in res.items()}, open("tail_dte.json", "w"), ensure_ascii=False)

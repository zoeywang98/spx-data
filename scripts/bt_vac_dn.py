"""GEX 真空向下 · 尾盘三窗 · 5 分钟一读 · 连续两次 → 入场（第二次读数时 1 分钟收盘）· 一天一次 · 持有到 16:00 收盘。
Jul–Sep: nw_heatmap 0DTE (分钟 m 帧在 m+1 可见, spot=同帧页面 spot) + nw_replay 1m K。
Oct: nightwatch series dte=0 (spot=记录 spot) + spx_kline history 1m K。
--carry: 连续计数允许跨窗口起点（窗口前一读也算）。"""
import datetime as dt, json, glob, os, sys
from zoneinfo import ZoneInfo
ET = ZoneInfo("America/New_York")
BT = "/Users/yuwang/skylit-learn/backtest"
NWS = "/Users/yuwang/.openclaw/workspace-claw-general/nightwatch/data/series/SPX"
KL = "/Users/yuwang/.openclaw/workspace-claw-0tde/spx_kline/history/SPX"
W, STRONG = 30, 0.20
CARRY = "--carry" in sys.argv
DIR = 1 if "--up" in sys.argv else -1

def gex_dir(g, S):
    ga = sum(v for k, v in g.items() if S < k <= S + W)
    gb = sum(v for k, v in g.items() if S - W <= k < S)
    gt = sum(abs(v) for k, v in g.items() if abs(k - S) <= W) or 1
    return 1 if gb > 0 and ga <= 0 and gb >= STRONG * gt else -1 if ga > 0 and gb <= 0 and ga >= STRONG * gt else 0

def heat_hm(day):
    d = json.load(open(f"{BT}/nw_heatmap/SPX_gex_{day}.json")); out = []
    for hm, sp, f in zip(d["minutes"], d["spot"], d["frames"]):
        if hm and sp and f:
            t = dt.datetime.fromisoformat(hm).astimezone(ET) if "T" in hm else dt.datetime.fromisoformat(f"{day}T{hm}").replace(tzinfo=ET)
            out.append((t + dt.timedelta(minutes=1), sp, {s: (v or 0) for s, v in zip(f[0], f[1])}))
    return out

def heat_series(day):
    out = []
    for line in open(f"{NWS}/{day}.jsonl"):
        try: r = json.loads(line)
        except ValueError: continue
        if r.get("dte") != 0 or not r.get("spot"): continue
        out.append((dt.datetime.fromisoformat(r["t"]).astimezone(ET), r["spot"], {k: v for k, v in r["k"]}))
    return sorted(out, key=lambda x: x[0])

def bars_replay(day):
    j = json.load(open(f"{BT}/nw_replay/SPX_{day}.json"))
    return [(dt.datetime.fromtimestamp(b[0] / 1000, ET) + dt.timedelta(minutes=1), b[4]) for b in j["bars"]]

def bars_kl(day):
    j = json.load(open(f"{KL}/{day}.json"))
    return [(dt.datetime.fromisoformat(b["time"]).astimezone(ET) + dt.timedelta(minutes=1), b["close"]) for b in j["bars"]]

def days():
    out = []
    for f in sorted(glob.glob(f"{BT}/nw_heatmap/SPX_gex_2026-0*.json")):
        d = f[-15:-5]
        if os.path.exists(f"{BT}/nw_replay/SPX_{d}.json"): out.append((d, "hm"))
    for f in sorted(glob.glob(f"{NWS}/2026-10-*.jsonl")):
        d = f[-16:-6]
        if d <= "2026-10-23" and os.path.exists(f"{KL}/{d}.json"): out.append((d, "ser"))
    return out

WINS = [(dt.time(14, 30), dt.time(15, 0)), (dt.time(15, 0), dt.time(15, 30)), (dt.time(15, 30), dt.time(16, 0))]

def run():
    res = {w: [] for w in WINS}; nodata = []
    for day, src in days():
        heat = heat_hm(day) if src == "hm" else heat_series(day)
        bars = bars_replay(day) if src == "hm" else bars_kl(day)
        if src == "ser" and bars[-1][0].time() < dt.time(16, 0):  # K 线不完整（10-22 停在 11:18）→ 用 Nightwatch 页面 spot
            bars = [(t, sp) for t, sp, g in heat]; print(f"  {day}: K 线不完整，价格改用 Nightwatch 页面 spot")
        def close_at(T):
            xs = [c for t, c in bars if t <= T]; return xs[-1] if xs else None
        def sig(T):
            xs = [h for h in heat if h[0] <= T]
            if not xs or (T - xs[-1][0]).total_seconds() > 300: return None
            return gex_dir(xs[-1][2], xs[-1][1])
        D = dt.date.fromisoformat(day)
        c16 = close_at(dt.datetime.combine(D, dt.time(16, 0), ET))
        if c16 is None: nodata.append(day); continue
        for w in WINS:
            a, b = (dt.datetime.combine(D, x, ET) for x in w)
            T = a - dt.timedelta(minutes=5) if CARRY else a
            prev, entry = None, None
            while T < b:
                s = sig(T)
                if s == DIR and prev == DIR and T >= a and T < dt.datetime.combine(D, dt.time(16, 0), ET):
                    entry = T; break
                prev = s; T += dt.timedelta(minutes=5)
            if entry:
                px = close_at(entry); pnl = (c16 - px) * DIR  # 顺信号方向点数
                res[w].append((day, entry.strftime("%H:%M"), px, c16, pnl))
    return res, nodata

if __name__ == "__main__":
    res, nodata = run()
    ds = days(); print(f"样本 {len(ds)} 天 {ds[0][0]}→{ds[-1][0]}  无 16:00 K: {nodata}  carry={CARRY} 方向={'向上' if DIR == 1 else '向下'}")
    for w, rows in res.items():
        n = len(rows); win = sum(r[4] > 0 for r in rows)
        avg = sum(r[4] for r in rows) / n if n else 0
        print(f"\n== {w[0].strftime('%H:%M')}–{w[1].strftime('%H:%M')}  入场 {n} 天  胜 {win}/{n} = {win/n*100 if n else 0:.0f}%  均 {avg:+.1f} 点  合计 {sum(r[4] for r in rows):+.1f}")
        by = {}
        for r in rows: by.setdefault(r[0][:7], []).append(r[4])
        print("   按月: " + "  ".join(f"{m} {sum(x>0 for x in v)}/{len(v)} 均{sum(v)/len(v):+.1f}" for m, v in by.items()))
        for r in rows: print(f"   {r[0]} {r[1]} 入 {r[2]:.2f} → 收 {r[3]:.2f}  {r[4]:+.1f} {'✔' if r[4] > 0 else '✘'}")

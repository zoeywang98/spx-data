"""截图 4 种 configuration。0DTE GEX（7–9 heatmap / 10 月 series），spot±30，节点 = |GEX| ≥ 该范围最大 40%。
区间 = 下方最近节点 kb … 上方最近节点 ka。帧 09:45–15:25 每 5 分钟，结果 30 分钟。
vol 状态 = 同一 30 分钟内 ΔVIX：平 |Δ|<0.10，升 ≥+0.15，降 ≤−0.15（VIX 仅 08-24 起）。
突破 = 30 分钟内越出区间；假突破 = 越出后 30 分钟收盘回到区间内；大突破 = 收盘在区间外且离边 ≥5 点。"""
import datetime as dt, json, statistics as st, collections, io, contextlib
import bt_vac_dn as B
with contextlib.redirect_stdout(io.StringIO()):
    import cross1 as C1, potential as P
from zoneinfo import ZoneInfo
ET = ZoneInfo("America/New_York")
F = []
for day, src in B.days():
    if src == "hm":
        heat = [(t, sp, {k: v[0] for k, v in g.items()}) for t, sp, g in C1.heat_full(day)]
        j = json.load(open(f"{B.BT}/nw_replay/SPX_{day}.json"))
        bars = [(dt.datetime.fromtimestamp(b[0] / 1000, ET) + dt.timedelta(minutes=1), b[2], b[3], b[4]) for b in j["bars"]]
    else:
        heat = B.heat_series(day); j = json.load(open(f"{B.KL}/{day}.json"))
        bars = [(dt.datetime.fromisoformat(x["time"]).astimezone(ET) + dt.timedelta(minutes=1), x["high"], x["low"], x["close"]) for x in j["bars"]]
        if bars[-1][0].time() < dt.time(16): bars = [(t, s, s, s) for t, s, g in heat]
    vx = P.vix_series(day) if day >= "2026-08-24" else []
    D = dt.date.fromisoformat(day); end = dt.datetime.combine(D, dt.time(16), ET)
    ca = lambda T: ([c for t, h, l, c in bars if t <= T] or [None])[-1]
    T = dt.datetime.combine(D, dt.time(9, 45), ET); hi = 0
    while T.time() <= dt.time(15, 25):
        while hi + 1 < len(heat) and heat[hi + 1][0] <= T: hi += 1
        t0, S0, g = heat[hi]
        if t0 <= T and (T - t0).seconds <= 300:
            S = ca(T); E = min(T + dt.timedelta(minutes=30), end)
            near = {k: v for k, v in g.items() if abs(k - S) <= 30 and k % 5 == 0 and v}
            path = [(h, l, c) for t, h, l, c in bars if T < t <= E]
            if S and near and path:
                mx = max(abs(v) for v in near.values()); nd = {k: v for k, v in near.items() if abs(v) >= 0.4 * mx}
                a = [k for k in nd if k > S]; b = [k for k in nd if k < S]
                if a and b:
                    ka, kb = min(a), max(b); c1 = ca(E)
                    v0, v1 = P.vat(vx, T), P.vat(vx, E) if vx else (None, None)
                    dv = (v1[1] - v0[1]) if vx and v0 and v1 and v1[0] > v0[0] else None
                    srt = sorted(near, key=lambda k: -abs(near[k]))
                    k1, k2 = srt[0], srt[1]
                    out = any(h > ka or l < kb for h, l, c in path)
                    F.append(dict(day=day, S=S, ka=ka, kb=kb, sa=1 if nd[ka] > 0 else -1, sb=1 if nd[kb] > 0 else -1, w=ka - kb,
                                  rng=max(p[0] for p in path) - min(p[1] for p in path), ret=c1 - S, dv=dv,
                                  brk=out, fake=out and kb <= c1 <= ka, big=c1 > ka + 5 or c1 < kb - 5,
                                  trap=(k1 - S) * (k2 - S) < 0 and abs(near[k2]) >= 0.5 * abs(near[k1]), k1=k1, k2=k2,
                                  stay60=None, pret=(S - ca(T - dt.timedelta(minutes=15))) if ca(T - dt.timedelta(minutes=15)) else None))
        T += dt.timedelta(minutes=5)
def st_(s):
    if not s: return "—"
    n = len(s); br = sum(f["brk"] for f in s)
    return (f"{n:>4} 帧/{len({f['day'] for f in s}):>2} 天  宽 {st.median([f['w'] for f in s]):3.0f}  振幅 {st.median([f['rng'] for f in s]):4.1f}  "
            f"出区间 {br/n*100:3.0f}%  假突破 {sum(f['fake'] for f in s)}/{br}={sum(f['fake'] for f in s)/br*100 if br else 0:3.0f}%  大突破 {sum(f['big'] for f in s)/n*100:3.0f}%  均 {st.mean(f['ret'] for f in s):+4.1f}")
CONF = [("① 下 +GEX / 上 −GEX", 1, -1), ("② 下 −GEX / 上 +GEX", -1, 1), ("   对照 下+ 上+", 1, 1), ("   对照 下− 上−", -1, -1)]
print(f"{len({f['day'] for f in F})} 天 {F[0]['day']}→{F[-1]['day']}，{len(F)} 帧（两侧都有节点）\n")
print("全部（不看 vol）")
for lab, b, a in CONF: print(f"  {lab:<18}" + st_([f for f in F if f["sb"] == b and f["sa"] == a]))
for vl, cond in (("vol 平 |ΔVIX|<0.10", lambda f: f["dv"] is not None and abs(f["dv"]) < 0.10), ("vol 升 ≥+0.15", lambda f: f["dv"] is not None and f["dv"] >= 0.15), ("vol 降 ≤−0.15", lambda f: f["dv"] is not None and f["dv"] <= -0.15)):
    print(f"\n{vl}（08-24 起）")
    for lab, b, a in CONF: print(f"  {lab:<18}" + st_([f for f in F if f["sb"] == b and f["sa"] == a and cond(f)]))
print("\n① 的 dealer 行为：下方 + 买跌、上方 − 追涨 → 跌后反弹、涨后续涨？（见 cross1 帧口径，这里用 30 分钟收盘相对区间中点）")
print("\n④ 夹在两个 King 之间（最大、第二大 |GEX| 分处现价两侧，第二 ≥ 第一 50%）")
tr = [f for f in F if f["trap"]]; nt = [f for f in F if not f["trap"]]
def stay(s):
    if not s: return "—"
    ins = sum(min(f["k1"], f["k2"]) <= f["S"] + f["ret"] <= max(f["k1"], f["k2"]) for f in s)
    return f"{len(s):>4} 帧/{len({f['day'] for f in s}):>2} 天  两 King 间宽中位 {st.median([abs(f['k1']-f['k2']) for f in s]):.0f}  30 分钟收盘仍在两 King 之间 {ins}/{len(s)}={ins/len(s)*100:.0f}%  振幅 {st.median([f['rng'] for f in s]):.1f}"
print("  夹住        " + stay(tr))
print("  vol 平      " + stay([f for f in tr if f["dv"] is not None and abs(f["dv"]) < 0.10]))
print("  vol 不平    " + stay([f for f in tr if f["dv"] is not None and abs(f["dv"]) >= 0.10]))
# 对照：不是夹住的帧里，以最近上下节点为区间、宽度相近
for lo, hi_ in ((0, 20), (20, 35), (35, 61)):
    a_ = [f for f in tr if lo <= abs(f["k1"] - f["k2"]) < hi_]; b_ = [f for f in nt if lo <= f["w"] < hi_]
    ia = sum(min(f["k1"], f["k2"]) <= f["S"] + f["ret"] <= max(f["k1"], f["k2"]) for f in a_); ib = sum(f["kb"] <= f["S"] + f["ret"] <= f["ka"] for f in b_)
    print(f"  宽 {lo}–{hi_}: 夹住 {ia}/{len(a_)}={ia/len(a_)*100 if a_ else 0:.0f}%   对照（非夹住，最近上下节点同宽）{ib}/{len(b_)}={ib/len(b_)*100 if b_ else 0:.0f}%")
json.dump(F, open("config4.json", "w"))

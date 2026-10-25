import sys, statistics as st
sys.argv = [a for a in sys.argv]
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    import vexrows as R
F = R.F
def absret(s): return f"|涨跌|中位 {st.median([abs(f['ret']) for f in s]):.1f} 振幅中位 {st.median([f['rng'] for f in s]):.1f}" if s else "—"
def line(n, s, fn): print(f"  {n}: {len(s)} 帧/{len({f['day'] for f in s})} 天  {fn(s)}")

print("① 对照：同为净 +GEX，簇是否同区")
pos = [f for f in F if f["g_net"] > 0 and f["kg"] and f["kv"]]
line("同区 ≤10", [f for f in pos if abs(f["kg"] - f["kv"]) <= 10], absret)
line("不同区 >10", [f for f in pos if abs(f["kg"] - f["kv"]) > 10], absret)
line("净 −GEX（全部）", [f for f in F if f["g_net"] < 0], absret)

print("\n② 放宽：净 −GEX 且 下方 VEX 净 >0 且 > 上方")
up = lambda s: f"上涨 {sum(f['ret']>0 for f in s)}/{len(s)} = {sum(f['ret']>0 for f in s)/len(s)*100:.0f}% 均 {st.mean(f['ret'] for f in s):+.1f}；VIX 跌 {sum((f['dvix'] or 0)<0 for f in s)}/{sum(f['dvix'] is not None for f in s)}" if s else "—"
neg = [f for f in F if f["g_net"] < 0]
line("触发", [f for f in neg if f["v_below"] > 0 and f["v_below"] > f["v_above"]], up)
line("净 −GEX 其余", [f for f in neg if not (f["v_below"] > 0 and f["v_below"] > f["v_above"])], up)
for d in sorted({f["day"] for f in neg if f["v_below"] > 0 and f["v_below"] > f["v_above"]}):
    s = [f for f in neg if f["day"] == d and f["v_below"] > 0 and f["v_below"] > f["v_above"]]
    print(f"    {d}: {len(s)} 帧 上涨 {sum(f['ret']>0 for f in s)}  均 {st.mean(f['ret'] for f in s):+.1f}")

print("\n③ 对照：净 +GEX、有上方天花板，按天花板距离分档；VIX 崩 vs 不崩")
held = lambda s: f"没碰 {sum(f['S']+f['hi']<f['ceil'] for f in s)}/{len(s)} = {sum(f['S']+f['hi']<f['ceil'] for f in s)/len(s)*100:.0f}%" if s else "—"
base = [f for f in F if f["g_net"] > 0 and f["ceil"]]
for lo, hi in ((0, 8), (8, 16), (16, 31)):
    b = [f for f in base if lo <= f["ceil"] - f["S"] < hi]
    print(f"  天花板 {lo}–{hi} 点:  上方 −VEX {held([f for f in b if f['v_above'] < 0])}   |  上方 VEX ≥0 {held([f for f in b if f['v_above'] >= 0])}")
for lab, cond in (("上方 −VEX", lambda f: f["v_above"] < 0), ("上方 VEX ≥0", lambda f: f["v_above"] >= 0)):
    b = [f for f in base if cond(f) and f["dvix"] is not None]
    print(f"  {lab}: VIX≤−0.3 {held([f for f in b if f['dvix'] <= -0.3])}   VIX>−0.3 {held([f for f in b if f['dvix'] > -0.3])}")

print("\n④ 放宽：|VEX|/|GEX| 比值分三档（spot±30），看 SPX 跟 VIX 的程度")
s = sorted([f for f in F if f["dvix"] is not None and f["g_abs"] > 0], key=lambda f: f["v_abs"] / f["g_abs"])
n = len(s)
for i, lab in enumerate(("比值低（GEX 主导）", "中", "比值高（VEX 主导）")):
    sub = s[i * n // 3:(i + 1) * n // 3]
    c = st.correlation([f["dvix"] for f in sub], [f["ret"] for f in sub])
    mv = [f for f in sub if abs(f["dvix"]) >= 0.1]; opp = sum((f["dvix"] > 0) != (f["ret"] > 0) for f in mv)
    beta = sum(f["dvix"] * f["ret"] for f in sub) / sum(f["dvix"] ** 2 for f in sub)
    print(f"  {lab}: {len(sub)} 帧/{len({f['day'] for f in sub})} 天  corr {c:+.2f}  每 1 点 VIX 对应 SPX {beta:+.1f} 点  VIX 动 ≥0.1 时反向 {opp}/{len(mv)} = {opp/len(mv)*100:.0f}%  |涨跌|中位 {st.median([abs(f['ret']) for f in sub]):.1f}")

print("\n⑤ 换号位离现价更近（≤5 点）vs 没有换号")
near = [f for f in F if any(abs((a + b) / 2 - f["S"]) <= 5 for a, b in f["flip"])]
line("换号位 ≤5 点", near, absret)
line("没有换号", [f for f in F if not f["flip"]], absret)
gflip = [f for f in F if not f["flip"]]

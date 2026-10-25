"""截图 alignment 四态，GEX = 0–5DTE 净、VEX = 7–78DTE 净（spot±30）。指标与 align.py 相同。"""
import io, contextlib, statistics as st
with contextlib.redirect_stdout(io.StringIO()):
    import worlds as Wd
F = [f for f in Wd.R.F if "GEX_f" in f and "VEX_b" in f]
sg = lambda x: 1 if x > 0 else -1
def beta(s): b = [f for f in s if f["dvix"] is not None]; return sum(f["dvix"] * f["ret"] for f in b) / sum(f["dvix"] ** 2 for f in b)
m_ = lambda s: st.mean(f["ret"] for f in s) if s else 0
print(f"{len({f['day'] for f in F})} 天 {min(f['day'] for f in F)}→{max(f['day'] for f in F)}，{len(F)} 帧\n")
for name, g, v, claim in (("对齐 +GEX +VEX", 1, 1, "低吸高抛；vol 跌买"), ("对齐 −GEX −VEX", -1, -1, "追涨杀跌；vol 跌卖"),
                          ("错位 +GEX −VEX", 1, -1, "低吸；vol 跌卖"), ("错位 −GEX +VEX", -1, 1, "杀跌；vol 跌买")):
    s = [f for f in F if sg(f["GEX_f"]) == g and sg(f["VEX_b"]) == v]
    m = [f for f in s if f["pret"] is not None and abs(f["pret"]) >= 3]; rev = sum(sg(f["ret"]) != sg(f["pret"]) for f in m)
    dips = [f for f in m if f["pret"] < 0]; rips = [f for f in m if f["pret"] > 0]
    c = [f for f in s if f["dvix"] is not None and f["dvix"] <= -0.15]
    p = [f for f in s if f["pdvix"] is not None and f["pdvix"] <= -0.15]
    print(f"■ {name}（截图：{claim}）：{len(s)} 帧 / {len({f['day'] for f in s})} 天；振幅中位 {st.median([f['rng'] for f in s]):.1f}")
    print(f"   gamma：反转 {rev}/{len(m)} = {rev/len(m)*100:.0f}%；跌后 30 分钟均 {m_(dips):+.1f}（{len(dips)}）、涨后均 {m_(rips):+.1f}（{len(rips)}）")
    print(f"   vanna 同期：VIX 跌 ≥0.15 时 SPX 涨 {sum(f['ret']>0 for f in c)}/{len(c)} 均 {m_(c):+.1f}；β {beta(s):+.1f}")
    print(f"   vanna 领先：VIX 先跌 ≥0.15 → SPX 涨 {sum(f['ret']>0 for f in p)}/{len(p)} 均 {m_(p):+.1f}")
    print("   按天: " + " ".join(f"{d[5:]}:{sum(f['day']==d for f in s)}" for d in sorted({f['day'] for f in s})))

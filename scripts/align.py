import io, contextlib, statistics as st, sys
with contextlib.redirect_stdout(io.StringIO()):
    import vexrows as R
F = R.F
ST = [("对齐 +GEX +VEX", 1, 1), ("对齐 −GEX −VEX", -1, -1), ("错位 +GEX −VEX", 1, -1), ("错位 −GEX +VEX", -1, 1)]
sg = lambda x: 1 if x > 0 else -1
def beta(xs, ys): return sum(x * y for x, y in zip(xs, ys)) / sum(x * x for x in xs) if xs else float("nan")
print(f"{len(R.DAYS)} 天 {R.DAYS[0]}→{R.DAYS[-1]}，{len(F)} 帧；GEX=0DTE 净（spot±30），VEX={'0DTE' if R.VEX0 else '全到期'} 净（spot±30）\n")
for name, g, v in ST:
    s = [f for f in F if sg(f["g_net"]) == g and sg(f["v_net"]) == v]
    if not s: print(name, "无帧"); continue
    nd = len({f["day"] for f in s})
    # gamma：前 15 分钟走势 → 后 30 分钟，反转率
    m = [f for f in s if f["pret"] is not None and abs(f["pret"]) >= 3]
    rev = sum(sg(f["ret"]) != sg(f["pret"]) for f in m)
    dips = [f for f in m if f["pret"] < 0]; rips = [f for f in m if f["pret"] > 0]
    # vanna：同期 VIX 跌时 SPX 方向；VIX 先跌（前 15 分钟）→ 后 30 分钟 SPX
    c = [f for f in s if f["dvix"] is not None and f["dvix"] <= -0.15]
    p = [f for f in s if f["pdvix"] is not None and f["pdvix"] <= -0.15]
    b = [f for f in s if f["dvix"] is not None]
    print(f"■ {name}：{len(s)} 帧 / {nd} 天")
    print(f"   gamma：前 15 分钟动 ≥3 点后，30 分钟反转 {rev}/{len(m)} = {rev/len(m)*100 if m else 0:.0f}%；"
          f"跌后 30 分钟均 {st.mean(f['ret'] for f in dips) if dips else 0:+.1f}（{len(dips)}）、涨后均 {st.mean(f['ret'] for f in rips) if rips else 0:+.1f}（{len(rips)}）")
    print(f"   vanna 同期：VIX 30 分钟跌 ≥0.15 时 SPX 涨 {sum(f['ret']>0 for f in c)}/{len(c)}，均 {st.mean(f['ret'] for f in c) if c else 0:+.1f}；每 1 点 VIX 对应 SPX {beta([f['dvix'] for f in b],[f['ret'] for f in b]):+.1f}")
    print(f"   vanna 领先：前 15 分钟 VIX 跌 ≥0.15 后，30 分钟 SPX 涨 {sum(f['ret']>0 for f in p)}/{len(p)}，均 {st.mean(f['ret'] for f in p) if p else 0:+.1f}")
    print("   按天帧数: " + " ".join(f"{d[5:]}:{sum(f['day']==d for f in s)}" for d in sorted({f['day'] for f in s})))

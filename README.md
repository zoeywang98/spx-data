# SPX backtest data (2026-07-15 → 2026-10-23)

SPX 0DTE GEX/VEX 回测（尾盘真空、King Node、Stacked Nodes 等）所用的全部原始数据。

| 目录 | 来源 | 内容 |
|---|---|---|
| `nightwatch/nw_heatmap/` | Nightwatch Dealer Heatmap REPLAY 页面抓取 | 7–9 月逐分钟 GEX：0DTE / 1DTE / 5–30DTE / 全到期，含页面 spot |
| `nightwatch/nw_replay/` | Nightwatch Replay Lab | 7–9 月 SPX 1 分钟 K |
| `nightwatch/series_SPX/` | Nightwatch series | 10 月逐分钟 0DTE GEX（含 spot），jsonl |
| `nightwatch/history_SPX/` | Nightwatch history grid | 分到期 per-strike GEX（10-12 起）/ VEX（10-08 起），最长 78DTE，json.gz |
| `volsignals/charm_SPX/` | VolSignals MM | 0DTE charm，10 分钟一格，09-25 起 |
| `tradingview/vix1d_5m/` | TradingView | VIX 5 分钟（08-24 → 10-09） |
| `tradingview/vix_1m_history/` | TradingView TVC:VIX（Bar Replay 抓取） | VIX 1 分钟 K，07-15 → 10-05；time = bar 开盘，值不变的分钟无 bar（需前值填充） |
| `tradingview/vix_1m/` | TradingView layout | VIX 逐分钟 CSV（10-04 起） |
| `kline/spx_1m/` | VolSignals spx_kline | 10 月 SPX 1 分钟 K（10-22 不完整，止于 11:18） |

符号口径：Nightwatch / VolSignals 为 dealer 方向。

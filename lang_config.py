# lang_config.py - Issac Terminal 智库文案库 (v35.0 终极补全版)
LANG = {
    "CN": {
        "title": "🍎 Issac 机构级投研研究终端",
        "search_label": "🔍 个股透视 (回车搜索)",
        "sidebar_header": "⚙️ 专家级筛选参数",
        "pe_label": "最高 P/E (建议 < 25)",
        "peg_label": "最高 PEG (建议 < 1.2)",
        "roe_label": "最低 ROE % (建议 > 15)",
        "fcf_label": "最低 FCF $B (建议 > 0.5)",
        "scan_range": "📊 批量扫描范围",
        "scan_btn": "开始批量扫描",
        "match_only": "🔍 只看符合条件的股票",
        "snapshot_title": "📊 核心参数快照",
        "report_title": "深度投资研报 (Confidential)",
        
        "chart_title": "📈 股价与 200 日均线 (MA200) 趋势对比",
        "chart_close": "收盘价", "chart_ma200": "200日均线", "chart_date": "日期",
        
        "rs_title": "⚔️ 相对强度 (RS) 动能博弈",
        "rs_label_spy": "标普 500 (SPY)",
        "rs_desc_leader": "🔥 **领头羊 (Leader)**：近 3 个月表现超越大盘 `{diff:.1f}%`。",
        "rs_desc_laggard": "🐌 **拖油瓶 (Laggard)**：近 3 个月表现落后大盘 `{diff:.1f}%`。",
        
        "earnings_label": "🚦 **财报高危预警**：将于 {days} 天后 ({date}) 公布财报。建议离场观望，防止“财报杀”。",
        
        "moat_title": "🏰 商业模式与护城河深度透视",
        "moat_elite": "💎 **护城河评级：顶级 (Elite)**。极高 ROE 意味着强大的定价权。",
        "moat_wide": "🛡️ **护城河评级：宽阔 (Wide)**。拥有成熟壁垒，盈利质量高。",
        "moat_narrow": "🚧 **护城河评级：较窄 (Narrow)**。面临激烈竞争，需警惕利润。",
        
        "fin_title": "🏛️ 盈利质量与财务安全评价",
        "consistency_label": "· **ROE 稳定性审计**: **{curr}%** (当前) vs **{prev}%** (ref)。盈利模式具备连贯性。",
        
        "growth_title": "📉 成长动能与现金含量",
        "risk_title": "🚩 筹码博弈、趋势与风险预警",
        "trend_bear": "❌ **趋势雷达**：股价处于 MA200 下方，多头动能瓦解。",
        "trend_bull": "📈 **趋势雷达**：股价站稳 MA200 上方，多头行情确立。",
        
        "stop_loss_title": "🛡️ Issac 实战风控：止损建议",
        "stop_loss_label": "建议离场位 (基于 MA200 支撑)",
        "stop_loss_note": "注：该价位取 MA200 下方 3% 为缓冲区。若收盘价跌破此位，建议强制离场。",
        
        "verdict_title": "🏆 Issac 级终极研判",
        "verdicts": ["观望 (C)","持有 (B)","买入 (A)","强力买入 (A+)"],
        "strategies": ["⚠️ 趋势极弱，场外等候。","⚖️ 缺乏动能，仅适合极轻仓。","✅ 趋势向好，逢低建仓。","🔥 极品资产，量价齐飞，建议果断持股！"],
        "strategy_label": "💡 机构级操盘建议"
    },
    "EN": {
        "title": "🍎 Issac Investment Research Terminal",
        "search_label": "🔍 Manual Ticker Search (Enter)",
        "sidebar_header": "⚙️ Expert Filter Settings",
        "pe_label": "Max P/E (Ref < 25)",
        "peg_label": "Max PEG (Ref < 1.2)",
        "roe_label": "Min ROE % (Ref > 15)",
        "fcf_label": "Min FCF $B (Ref > 0.5)",
        "scan_range": "📊 Auto-Scan Range",
        "scan_btn": "Start Batch Scan",
        "match_only": "🔍 Show Matches Only",
        "snapshot_title": "📊 Core Metrics Snapshot",
        "report_title": "Deep Institutional Report",
        
        "chart_title": "📈 Price vs 200D Moving Average (MA200)",
        "chart_close": "Close Price", "chart_ma200": "MA200 Line", "chart_date": "Date",
        
        "rs_title": "⚔️ Relative Strength (RS) Momentum",
        "rs_label_spy": "S&P 500 (SPY)",
        "rs_desc_leader": "🔥 **Leader**: Outperformed S&P 500 by `{diff:.1f}%` over past 3 months.",
        "rs_desc_laggard": "🐌 **Laggard**: Underperformed S&P 500 by `{diff:.1f}%` over past 3 months.",
        
        "earnings_label": "🚦 **Earnings Alert**: Upcoming on {date} ({days} days away). Recommend waiting.",
        
        "moat_title": "🏰 Business Model & Moat Insight",
        "moat_elite": "💎 **Moat Rating: Elite**. Exceptional ROE indicates dominance.",
        "moat_wide": "🛡️ **Moat Rating: Wide**. Mature barriers with high earnings quality.",
        "moat_narrow": "🚧 **Moat Rating: Narrow**. Stiff competition; monitor margins.",
        
        "fin_title": "🏛️ Fundamentals & Financial Safety",
        "consistency_label": "· **ROE Stability Audit**: **{curr}%** (Curr) vs **{prev}%** (Ref). Profit model is consistent.",
        
        "growth_title": "📉 Growth Momentum & FCF Yield",
        "risk_title": "🚩 Risk, Sentiment & Trend Radar",
        "trend_bear": "❌ **Trend Radar**: Price is below MA200 (Bearish).",
        "trend_bull": "📈 **Trend Radar**: Price is supported by MA200 (Bullish).",
        
        "stop_loss_title": "🛡️ Issac Risk Control: Stop-Loss",
        "stop_loss_label": "Exit Target (MA200 Based)",
        "stop_loss_note": "Note: Buffer set at 3% below MA200. Execute exit if closed below.",
        
        "verdict_title": "🏆 Issac Level Verdict",
        "verdicts": ["Wait (C)", "Hold (B)", "Buy (A)", "STRONG BUY (A+)"],
        "strategies": ["Wait for signals.", "Monitor only.", "Accumulate on dips.", "Strong conviction hold."],
        "strategy_label": "💡 Strategy"
    }
}

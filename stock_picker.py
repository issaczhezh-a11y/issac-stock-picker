import streamlit as st
import yfinance as yf
import pandas as pd
import time
from datetime import datetime
import pytz

# --- 1. 全中文专业金融字典 ---
LANG = {
    "CN": {
        "title": "🍎 Issac 机构级投研研究终端",
        "search_label": "🔍 个股深度透视 (输入代码并回车)",
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
        "moat_title": "🏰 商业模式与护城河透视",
        "fin_title": "🏛️ 财务健康度与盈利质量",
        "risk_title": "🚩 筹码博弈与趋势雷达",
        "verdict_title": "🏆 JPMorgan 级终极研判",
        "strategy_label": "💡 机构级操盘策略",
        "strategies": [
            "⚠️ 趋势极弱且量价背离，建议场外等候放量信号。",
            "⚖️ 基本面尚可但缺乏动能，仅适合极轻仓位观察。",
            "✅ 优质资产且趋势已确立，建议逢低分批建仓。",
            "🔥 极品资产，量价护城河齐备，建议作为核心仓位持有！"
        ]
    },
    "EN": {
        "title": "🍎 Issac Investment Research Terminal",
        "search_label": "🔍 Manual Ticker Search (Enter to Search)",
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
        "moat_title": "🏰 Business Model & Moat Analysis",
        "fin_title": "🏛️ Fundamental & Moat Assessment",
        "risk_title": "🚩 Risk, Sentiment & Trend Radar",
        "verdict_title": "🏆 Institutional Verdict",
        "strategy_label": "💡 Trading Strategy",
        "strategies": [
            "Wait for bottom signals.",
            "Monitor with small position.",
            "Accumulate on dips.",
            "Strong conviction hold."
        ]
    }
}

st.set_page_config(page_title="Issac Terminal", layout="wide")
lang_choice = st.sidebar.radio("🌐 语言选择 / Language", ["CN", "EN"], horizontal=True)
t = LANG[lang_choice]
st.title(t["title"])

# --- 2. 侧边栏设置 ---
st.sidebar.header(t["sidebar_header"])
search_ticker = st.sidebar.text_input(t["search_label"], "").upper().strip()
st.sidebar.divider()
target_pe = st.sidebar.number_input(t["pe_label"], value=25.0)
target_peg = st.sidebar.number_input(t["peg_label"], value=1.2)
min_roe = st.sidebar.number_input(t["roe_label"], value=15.0)
min_fcf = st.sidebar.number_input(t["fcf_label"], value=0.5)
st.sidebar.divider()
idx_mode = st.sidebar.selectbox(t["scan_range"], ["S&P 500", "Nasdaq 100"])
scan_btn = st.sidebar.button(t["scan_btn"])

# --- 3. 分析引擎 ---
def get_analysis(s):
    try:
        tk = yf.Ticker(s)
        h = tk.history(period="1y")
        if len(h) < 200: return None
        inf = tk.info
        p, m200 = h['Close'].iloc[-1], h['Close'].rolling(200).mean().iloc[-1]
        v_r = ((h['Volume'].iloc[-1] / h['Volume'].iloc[-8:-1].mean()) - 1) * 100
        pe, peg = inf.get('forwardPE', 0), (inf.get('pegRatio') or inf.get('trailingPegRatio') or 0)
        roe, fcf = (inf.get('returnOnEquity') or 0)*100, (inf.get('freeCashflow') or 0)/1e9
        debt, sh = (inf.get('debtToEquity') or 0), (inf.get('shortPercentOfFloat') or 0)*100
        
        ok = (0 < pe < target_pe and 0 <= peg < target_peg and roe > min_roe and fcf > min_fcf)
        return {
            "代码":s, "价格":round(p,2), "MA200":round(m200,2), "P/E":pe, "PEG":peg, 
            "ROE%":round(roe,1), "FCF$B":round(fcf,1), "负债率%":round(debt,1), 
            "做空率":f"{sh:.1f}%", "量比":f"{v_r:+.1f}%", "结果":"✅ 符合" if ok else "❌ 不符",
            "_p":p, "_m":m200, "_sh":sh, "_v":v_r, 
            "_summary":inf.get('longBusinessSummary', "暂无简介"), 
            "_industry":inf.get('industry', "未知行业")
        }
    except: return None

def render_report(s):
    # 🎯 物理过滤展示列
    display_cols = ["代码", "价格", "MA200", "P/E", "PEG", "ROE%", "FCF$B", "负债率%", "做空率", "量比", "结果"]
    st.subheader(f"{t['snapshot_title']} - {s['代码']}")
    st.dataframe(pd.DataFrame([s])[display_cols], use_container_width=True, hide_index=True)
    
    with st.expander(f"📑 {s['代码']} - {t['report_title']}", expanded=True):
        # 1. 商业模式
        st.markdown(f"### {t['moat_title']}")
        st.write(f"**细分行业：** `{s['_industry']}`")
        st.write(f"**核心业务：** {s['_summary'][:800]}...")
        
        if s['ROE%'] > 35: moat_eval = "💎 **护城河评级：顶级资产 (Elite)**。超高的 ROE 意味着极强的定价权和技术垄断。对比你的 M5 Max 配置，这就是算力界的王者。"
        elif s['ROE%'] > 18: moat_eval = "🛡️ **护城河评级：宽阔 (Wide)**。具备显著的竞争优势，能够持续抵御行业波动。"
        else: moat_eval = "🚧 **护城河评级：窄 (Narrow)**。虽然盈利，但需警惕行业同质化竞争导致利润缩水。"
        st.info(moat_eval)

        st.markdown("---")
        # 2. 财务深度
        st.markdown(f"### {t['fin_title']}")
        c1, c2, c3 = st.columns(3)
        c1.metric("PEG (估值平衡)", s['PEG'], delta="极佳" if s['PEG'] < 0.7 else None)
        c2.metric("ROE (资本效率)", f"{s['ROE%']}%", delta="强劲" if s['ROE%'] > 25 else None)
        c3.metric("FCF (现金余力)", f"${s['FCF$B']}B")
        
        debt_status = "🟢 极其健康" if s['负债率%'] < 40 else ("🟡 风险可控" if s['负债率%'] < 100 else "🔴 财务杠杆偏高")
        st.write(f"· **杠杆健康度**: 负债权益比 `{s['负债率%']}%` — {debt_status}")
        st.write(f"· **现金含金量**: 自由现金流达 ${s['FCF$B']}B，足以为回购和抵御衰退提供充足缓冲。")

        st.markdown("---")
        # 3. 筹码与趋势
        st.markdown(f"### {t['risk_title']}")
        r1, r2 = st.columns(2)
        with r1:
            if s['_sh'] > 5: st.error(f"⚠️ **空头警示**：做空比例达 {s['_sh']:.1f}%，机构卖压正在堆积。")
            else: st.success(f"✅ **筹码稳健**：空头比例仅为 {s['_sh']:.1f}%，市场信心坚定。")
        with r2:
            if s['_p'] < s['_m']: st.error("❌ **弱势趋势**：当前股价处于 MA200 牛熊分界线下方。")
            else: st.success("📈 **强势趋势**：股价站稳 200 日线上方，正处于大牛行情。")

        st.divider()
        # 4. 终极结论
        score = (1 if s['PEG'] < 0.7 else 0) + (1 if s['ROE%'] > 25 else 0) + (1 if s['_p'] > s['_m'] else 0)
        st.success(f"### {t['verdict_title']}: {['观望 (C)','持有 (B)','买入 (A)','强力买入 (A+)'][score]}")
        st.info(f"💡 **{t['strategy_label']}：** {t['strategies'][score]}")

# --- 4. 逻辑控制流程 ---
if search_ticker:
    res = get_analysis(search_ticker)
    if res: render_report(res)
    else: st.error("未找到代码，请确认代码正确（如 NVDA）。")

if scan_btn:
    import urllib.request
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies' if idx_mode=="S&P 500" else 'https://en.wikipedia.org/wiki/Nasdaq-100'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as r: 
        tks = pd.read_html(r)[0 if idx_mode=="S&P 500" else 4].iloc[:, 0].tolist()
    batch_res = []
    bar = st.progress(0)
    for i, ticker in enumerate(tks):
        item = get_analysis(str(ticker).replace('.','-'))
        if item: batch_res.append(item)
        bar.progress((i+1)/len(tks))
    st.session_state.batch_res = batch_res

if 'batch_res' in st.session_state:
    st.divider()
    df = pd.DataFrame(st.session_state.batch_res)
    display_cols = ["代码", "价格", "MA200", "P/E", "PEG", "ROE%", "FCF$B", "负债率%", "做空率", "量比", "结果"]
    m_df = df[df["结果"].str.contains("✅")]
    if not m_df.empty:
        st.subheader("🏙️ 批量扫描结果研判中心")
        sel = st.selectbox("选择扫描出的标的进行深度透视:", m_df["代码"].tolist())
        target_s = df[df["代码"] == sel].iloc[0]
        render_report(target_s)
    st.dataframe(m_df[display_cols] if st.checkbox(t["match_only"], value=True) else df[display_cols], use_container_width=True, hide_index=True)

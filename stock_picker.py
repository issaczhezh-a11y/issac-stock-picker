import streamlit as st
import yfinance as yf
import pandas as pd
import time
from datetime import datetime
import pytz

# --- 1. 深度多语言字典 ---
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
        "report_title": "深度投研报告",
        "moat_title": "🏰 商业模式与护城河",
        "industry": "行业",
        "summary": "业务简介",
        "moat_high": "🔥 **核心竞争力：** 极高 ROE 显示其拥有极强的市场垄断力或技术壁垒。",
        "moat_mid": "✅ **竞争优势：** 盈利能力稳健，具备一定的不可替代性。",
        "moat_low": "⚠️ **提醒：** 护城河尚浅，需关注竞争对手动态。",
        "fin_title": "🏛️ 核心财务评估",
        "risk_title": "🚩 风险与趋势",
        "short_warn": "⚠️ **空头警示**：做空率 {sh:.1f}%，抛压大。",
        "short_ok": "✅ **筹码稳固**：做空率低。",
        "trend_warn": "❌ **趋势信号**：价格在均线下方。",
        "trend_ok": "📈 **多头信号**：股价稳立于均线上方。",
        "verdict_title": "🏆 终极评级",
        "strategy_label": "💡 操盘建议",
        "strategies": ["建议等待放量信号。", "适合底仓观察。", "建议分批布局。", "建议果断加仓！"]
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
        "report_title": "Deep Research Report",
        "moat_title": "🏰 Business Model & Moat",
        "industry": "Industry",
        "summary": "Business Summary",
        "moat_high": "🔥 **Core Competency:** High ROE indicates strong market dominance or technical barriers.",
        "moat_mid": "✅ **Competitive Advantage:** Robust profitability with significant switching costs.",
        "moat_low": "⚠️ **Notice:** Narrow moat; keep an eye on competitors.",
        "fin_title": "🏛️ Core Fundamental Assessment",
        "risk_title": "🚩 Risk & Trend Radar",
        "short_warn": "⚠️ **Short Warning**: Short interest at {sh:.1f}%. High pressure.",
        "short_ok": "✅ **Stable Sentiment**: Low short interest.",
        "trend_warn": "❌ **Bearish**: Price is below MA200.",
        "trend_ok": "📈 **Bullish**: Price supported by MA200.",
        "verdict_title": "🏆 Final Verdict",
        "strategy_label": "💡 Strategy",
        "strategies": ["Wait for volume signals.", "Monitor closely.", "Accumulate on dips.", "Strong conviction, add position!"]
    }
}

st.set_page_config(page_title="Issac Terminal", layout="wide")

# 初始化状态
if 'show_batch' not in st.session_state: st.session_state.show_batch = False

lang_choice = st.sidebar.radio("🌐 Language / 语言", ["CN", "EN"], horizontal=True)
t = LANG[lang_choice]
st.title(t["title"])

# --- 2. 侧边栏 ---
st.sidebar.header(t["sidebar_header"])
search_ticker = st.sidebar.text_input(t["search_label"], key="search_box").upper().strip()

st.sidebar.divider()
target_pe = st.sidebar.number_input(t["pe_label"], value=25.0)
target_peg = st.sidebar.number_input(t["peg_label"], value=1.2)
min_roe = st.sidebar.number_input(t["roe_label"], value=15.0)
min_fcf = st.sidebar.number_input(t["fcf_label"], value=0.5)

st.sidebar.divider()
idx_mode = st.sidebar.selectbox(t["scan_range"], ["S&P 500", "Nasdaq 100"])

# --- 3. 分析函数 ---
def get_analysis(s):
    try:
        tk = yf.Ticker(s)
        h = tk.history(period="1y")
        if len(h) < 200: return None
        inf = tk.info
        p, m200 = h['Close'].iloc[-1], h['Close'].rolling(200).mean().iloc[-1]
        v_r = ((h['Volume'].iloc[-1] / h['Volume'].iloc[-8:-1].mean()) - 1) * 100
        pe = inf.get('forwardPE', 0)
        peg = inf.get('pegRatio') or inf.get('trailingPegRatio') or 0
        roe = (inf.get('returnOnEquity') or 0) * 100
        fcf = (inf.get('freeCashflow') or 0) / 1e9
        debt, sh = (inf.get('debtToEquity') or 0), (inf.get('shortPercentOfFloat') or 0) * 100
        sum_raw, ind_raw = inf.get('longBusinessSummary', "N/A"), inf.get('industry', "N/A")

        ok = (0 < pe < target_pe and 0 <= peg < target_peg and roe > min_roe and fcf > min_fcf)
        return {"Symbol":s, "Price":round(p,2), "MA200":round(m200,2), "P/E":pe, "PEG":peg, "ROE%":round(roe,1), "FCF$B":round(fcf,1), "D/E":round(debt,1), "Short%":f"{sh:.1f}%", "Vol%":f"{v_r:+.1f}%", "Match":"✅" if ok else "❌", "_p":p, "_m":m200, "_sh":sh, "_v":v_r, "_summary":sum_raw, "_industry":ind_raw}
    except: return None

def show_deep_report(s):
    st.subheader(f"{t['snapshot_title']} - {s['Symbol']}")
    clean_display = {k: v for k, v in s.items() if not k.startswith('_')}
    st.dataframe(pd.DataFrame([clean_display]), use_container_width=True, hide_index=True)
    with st.expander(f"📑 {s['Symbol']} - {t['report_title']}", expanded=True):
        st.markdown(f"### {t['moat_title']}")
        st.write(f"**{t['industry']}:** `{s['_industry']}`")
        st.write(f"**{t['summary']}:** {s['_summary'][:800]}...")
        st.info(t['moat_high'] if s['ROE%'] > 30 else (t['moat_mid'] if s['ROE%'] > 15 else t['moat_low']))
        st.markdown("---")
        st.markdown(f"### {t['fin_title']}")
        c1, c2, c3 = st.columns(3)
        c1.metric("PEG", s['PEG'], delta="Value" if s['PEG'] < 0.8 else None)
        c2.metric("ROE", f"{s['ROE%']}%", delta="High" if s['ROE%'] > 25 else None)
        c3.metric("FCF", f"${s['FCF$B']}B")
        st.markdown("---")
        st.markdown(f"### {t['risk_title']}")
        r1, r2 = st.columns(2)
        with r1:
            if s['_sh'] > 5: st.error(t['short_warn'].format(sh=s['_sh']))
            else: st.success(t['short_ok'])
        with r2:
            if s['_p'] < s['_m']: st.error(t['trend_warn'])
            else: st.success(t['trend_ok'])
        st.divider()
        score = (1 if s['PEG'] < 0.7 else 0) + (1 if s['ROE%'] > 25 else 0) + (1 if s['_p'] > s['_m'] else 0)
        st.success(f"### {t['verdict_title']}: {['Wait (C)','Hold (B)','Buy (A)','STRONG BUY (A+)'][score]}")
        st.info(f"{t['strategy_label']}: {t['strategies'][score]}")

# --- 4. 逻辑控制 ---
if st.sidebar.button(t["scan_btn"]):
    st.session_state.show_batch = True
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

# 展示逻辑：如果用户在输入框打字，则强制展示个股并“隐藏”批量研报（但保留表格）
if search_ticker:
    st.divider()
    res = get_analysis(search_ticker)
    if res: show_deep_report(res)
    else: st.error("Ticker not found.")
elif st.session_state.show_batch and 'batch_res' in st.session_state:
    st.divider()
    df = pd.DataFrame(st.session_state.batch_res)
    m_df = df[df["Match"].str.contains("✅")]
    if not m_df.empty:
        st.subheader("🏙️ Batch Scan Intelligence")
        sel = st.selectbox("Select Target Stock:", m_df["Symbol"].tolist())
        s_target = df[df["Symbol"] == sel].iloc[0]
        show_deep_report(s_target)
    st.dataframe(m_df if st.checkbox(t["match_only"], value=True) else df, use_container_width=True, hide_index=True)

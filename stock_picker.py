import streamlit as st
import yfinance as yf
import pandas as pd
import time
from datetime import datetime
import pytz

# --- 1. 字典配置 ---
LANG = {
    "CN": {
        "title": "🍎 Issac 价值投资研究终端", "sidebar_header": "筛选设置",
        "search_label": "🔍 个股深度搜索 (输入代码)", "ma200_label": "📈 仅限 MA200 上方",
        "pe_label": "最高 P/E", "peg_label": "最高 PEG", "fcf_label": "最低 FCF (10亿$)",
        "roe_label": "最低 ROE (%)", "debt_label": "最高负债率 (%)",
        "index_label": "📊 自动扫描范围", "scan_btn": "开始批量扫描",
        "matching_only": "🔍 只看符合条件的股票",
        "col_code": "代码", "col_price": "价格", "col_ma200": "MA200",
        "col_pe": "P/E", "col_peg": "PEG", "col_roe": "ROE(%)", "col_fcf": "FCF($B)", 
        "col_debt": "负债率", "col_rsi": "RSI", "col_macd": "MACD", 
        "col_vol": "量比(7D)", "col_short": "做空率", "col_res": "结果",
        "last_up": "⏱️ 最后更新: "
    },
    "EN": {
        "title": "🍎 Issac Investment Terminal", "sidebar_header": "Settings",
        "search_label": "🔍 Manual Ticker Search", "ma200_label": "📈 Above MA200 Only",
        "pe_label": "Max P/E", "peg_label": "Max PEG", "fcf_label": "Min FCF ($B)",
        "roe_label": "Min ROE (%)", "debt_label": "Max Debt (%)",
        "index_label": "📊 Auto-Scan Range", "scan_btn": "Start Batch Scan",
        "matching_only": "🔍 Matches Only",
        "col_code": "Symbol", "col_price": "Price", "col_ma200": "MA200",
        "col_pe": "P/E", "col_peg": "PEG", "col_roe": "ROE(%)", "col_fcf": "FCF($B)", 
        "col_debt": "D/E (%)", "col_rsi": "RSI", "col_macd": "MACD", 
        "col_vol": "Vol/7D", "col_short": "Short %", "col_res": "Result",
        "last_up": "⏱️ Last Updated: "
    }
}

st.set_page_config(page_title="Issac Terminal", layout="wide")
lang = st.sidebar.radio("🌐 Language", ["CN", "EN"], horizontal=True)
t = LANG[lang]
st.title(t["title"])

# --- 2. 侧边栏：手动搜索 & 批量筛选 ---
st.sidebar.subheader(t["search_label"])
manual_search = st.sidebar.text_input("Example: TSLA, BABA, NVDA", "").upper().strip()

st.sidebar.divider()
st.sidebar.subheader(t["sidebar_header"])
above_m200_check = st.sidebar.checkbox(t["ma200_label"], value=False)
target_pe = st.sidebar.slider(t["pe_label"], 5.0, 100.0, 25.0)
target_peg = st.sidebar.slider(t["peg_label"], 0.1, 3.0, 1.2) 
min_fcf = st.sidebar.number_input(t["fcf_label"], value=0.5)
min_roe = st.sidebar.slider(t["roe_label"], 0.0, 50.0, 15.0)
max_debt = st.sidebar.slider(t["debt_label"], 0.0, 300.0, 100.0)

# --- 3. 核心工具函数 ---
def get_stock_data(symbol, t_pe, t_peg, m_roe, m_fcf, m_debt, m200_check):
    try:
        tk = yf.Ticker(symbol)
        h = tk.history(period="1y")
        if len(h) < 35: return None
        
        cur_p, m200 = h['Close'].iloc[-1], h['Close'].rolling(200).mean().iloc[-1]
        v_r = ((h['Volume'].iloc[-1] / h['Volume'].iloc[-8:-1].mean()) - 1) * 100
        
        diff = h['Close'].diff()
        g, l = diff.where(diff > 0, 0).rolling(14).mean().iloc[-1], -diff.where(diff < 0, 0).rolling(14).mean().iloc[-1]
        rsi = 100 - (100 / (1 + (g/l))) if l != 0 else 50
        
        e12, e26 = h['Close'].ewm(span=12).mean(), h['Close'].ewm(span=26).mean()
        macd_v = e12 - e26
        macd_txt = "▲ 金叉" if macd_v.iloc[-1] > macd_v.ewm(span=9).mean().iloc[-1] else "▼ 死叉"
        
        inf = tk.info
        pe, peg = inf.get('forwardPE'), inf.get('pegRatio') or inf.get('trailingPegRatio')
        roe, fcf, debt = (inf.get('returnOnEquity') or 0)*100, (inf.get('freeCashflow') or 0)/1e9, inf.get('debtToEquity') or 0
        sh = (inf.get('shortPercentOfFloat') or 0)*100
        
        f_m = (pe and 0 < pe < t_pe) and (peg is not None and peg < t_peg) and (roe > m_roe) and (fcf > m_fcf) and (debt < m_debt)
        ok = "✅ 符合" if (f_m and cur_p > m200 if m200_check else f_m) else "❌ 不符"
        
        return {
            t["col_code"]:symbol, t["col_price"]:round(cur_p, 2), t["col_ma200"]:round(m200, 2), 
            t["col_pe"]:pe, t["col_peg"]:peg, t["col_roe"]:round(roe,1), t["col_fcf"]:round(fcf,1), 
            t["col_debt"]:round(debt,1), t["col_rsi"]:round(rsi,1), t["col_macd"]:macd_txt, 
            t["col_short"]:f"{sh:.1f}%", t["col_vol"]:f"{v_r:+.1f}%", t["col_res"]:ok, 
            "h_p":cur_p, "h_m":m200, "h_sh":sh, "h_v":v_r
        }
    except: return None

@st.cache_data
def get_tk(idx_name):
    import urllib.request
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies' if idx_name == "S&P 500" else 'https://en.wikipedia.org/wiki/Nasdaq-100'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        df = pd.read_html(resp)[0 if idx_name == "S&P 500" else 4]
    return [str(s).replace('.', '-') for s in df.iloc[:, 0].tolist()]

# --- 4. 深度报告展示组件 ---
def show_pro_report(s, t_lang):
    with st.expander(f"📜 {s[t['col_code']]} - JPMorgan 级机构投研报告", expanded=True):
        c1, c2, c3 = st.columns(3)
        c1.metric("PEG / 性价比", s[t['col_peg']] if s[t['col_peg']] else "N/A", delta="Low Val" if s[t['col_peg']] and s[t['col_peg']] < 0.8 else None)
        c2.metric("ROE / 回报率", f"{s[t['col_roe']]}%", delta="Elite" if s[t['col_roe']] > 25 else None)
        c3.metric("FCF / 现金流", f"${s[t['col_fcf']]}B", delta="Strong" if s[t['col_fcf']] > 3 else None)
        
        st.markdown("---")
        st.markdown("#### 🏛️ 护城河分析 (Fundamental Moat)")
        st.write(f"· P/E 为 `{s[t['col_pe']]}`。管理层资本回报率达 `{s[t['col_roe']]}%`，{'显示出极强的行业护城河。' if s[t['col_roe']] > 20 else '盈利能力处于行业稳健水平。'}")
        
        st.markdown("#### 🚩 筹码与动能 (Sentiment & Risk)")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            if s['h_sh'] > 5: st.error(f"⚠️ **空头警示**: 做空率 {s['h_sh']:.1f}%，抛压极大。")
            else: st.success(f"✅ **筹码稳固**: 做空风险较低 ({s['h_sh']:.1f}%)。")
        with col_r2:
            if s['h_p'] < s['h_m']: st.error("❌ **趋势破位**: 股价位于 MA200 牛熊线下方。")
            else: st.success("📈 **强势多头**: 股价获得 200 日均线有力支撑。")

        st.markdown("#### 📉 择时信号 (Technical Timing)")
        v_msg = "🔥 **大资金流入**" if s['h_v'] > 50 else ("💤 **洗盘盘整**" if s['h_v'] < -30 else "量能平稳")
        st.write(f"· **7日量比**: `{s[t['col_vol']]}` — {v_msg}")
        st.write(f"· **指标**: MACD `{s[t['col_macd']]}` | RSI `{s[t['col_rsi']]}`")
        
        st.divider()
        score = (1 if s[t['col_peg']] and s[t['col_peg']] < 0.7 else 0) + (1 if s[t['col_roe']] > 25 else 0) + (1 if s['h_p'] > s['h_m'] else 0)
        st.success(f"### 🏆 最终评级: {['Wait (C)','Hold (B)','Buy (A)','STRONG BUY (A+)'][score]}")

# --- 5. 主逻辑执行 ---
# 优先处理手动搜索
if manual_search:
    st.subheader(f"🔍 手动透视结果: {manual_search}")
    search_res = get_stock_data(manual_search, target_pe, target_peg, min_roe, min_fcf, max_debt, above_m200_check)
    if search_res:
        show_pro_report(search_res, lang)
    else:
        st.error(f"未能找到股票代码 {manual_search} 的数据，请检查输入是否正确。")

st.divider()
idx_mode = st.sidebar.selectbox(t["index_label"], ["S&P 500", "Nasdaq 100"])
if st.sidebar.button(t["scan_btn"]):
    tickers = get_tk(idx_mode)
    batch_data = []
    with st.spinner('Scanning...'):
        for s in tickers:
            res = get_stock_data(s, target_pe, target_peg, min_roe, min_fcf, max_debt, above_m200_check)
            if res: batch_data.append(res)
    st.session_state.res = batch_data
    st.session_state.up_t = datetime.now(pytz.timezone('America/Toronto')).strftime("%H:%M:%S")

if st.session_state.get('res'):
    df = pd.DataFrame(st.session_state.res)
    st.caption(f"{t['last_up']} {st.session_state.up_t}")
    clean_df = df.drop(columns=["h_p", "h_m", "h_sh", "h_v"])
    m_df = clean_df[clean_df[t["col_res"]].str.contains("✅")]
    
    if not m_df.empty:
        st.subheader("🏙️ 批量扫描研报中心")
        sel = st.selectbox("🎯 选择扫描出的个股进行深度研判:", m_df[t["col_code"]].tolist())
        s_data = df[df[t["col_code"]] == sel].iloc[0]
        show_pro_report(s_data, lang)
        
    st.dataframe(m_df if st.checkbox(t["matching_only"], value=True) else clean_df, use_container_width=True, hide_index=True)
st.set_page_config(page_title="Issac Terminal", layout="wide")
lang = st.sidebar.radio("🌐 Language", ["CN", "EN"], horizontal=True)
t = LANG[lang]
st.title(t["title"])

# --- 2. 侧边栏：手动搜索 & 批量筛选 ---
st.sidebar.subheader(t["search_label"])
manual_search = st.sidebar.text_input("Example: TSLA, BABA, NVDA", "").upper().strip()

st.sidebar.divider()
st.sidebar.subheader(t["sidebar_header"])
above_m200_check = st.sidebar.checkbox(t["ma200_label"], value=False)
target_pe = st.sidebar.slider(t["pe_label"], 5.0, 100.0, 25.0)
target_peg = st.sidebar.slider(t["peg_label"], 0.1, 3.0, 1.2) 
min_fcf = st.sidebar.number_input(t["fcf_label"], value=0.5)
min_roe = st.sidebar.slider(t["roe_label"], 0.0, 50.0, 15.0)
max_debt = st.sidebar.slider(t["debt_label"], 0.0, 300.0, 100.0)

# --- 3. 核心工具函数 ---
def get_stock_data(symbol, t_pe, t_peg, m_roe, m_fcf, m_debt, m200_check):
    try:
        tk = yf.Ticker(symbol)
        h = tk.history(period="1y")
        if len(h) < 35: return None
        
        cur_p, m200 = h['Close'].iloc[-1], h['Close'].rolling(200).mean().iloc[-1]
        v_r = ((h['Volume'].iloc[-1] / h['Volume'].iloc[-8:-1].mean()) - 1) * 100
        
        diff = h['Close'].diff()
        g, l = diff.where(diff > 0, 0).rolling(14).mean().iloc[-1], -diff.where(diff < 0, 0).rolling(14).mean().iloc[-1]
        rsi = 100 - (100 / (1 + (g/l))) if l != 0 else 50
        
        e12, e26 = h['Close'].ewm(span=12).mean(), h['Close'].ewm(span=26).mean()
        macd_v = e12 - e26
        macd_txt = "▲ 金叉" if macd_v.iloc[-1] > macd_v.ewm(span=9).mean().iloc[-1] else "▼ 死叉"
        
        inf = tk.info
        pe, peg = inf.get('forwardPE'), inf.get('pegRatio') or inf.get('trailingPegRatio')
        roe, fcf, debt = (inf.get('returnOnEquity') or 0)*100, (inf.get('freeCashflow') or 0)/1e9, inf.get('debtToEquity') or 0
        sh = (inf.get('shortPercentOfFloat') or 0)*100
        
        f_m = (pe and 0 < pe < t_pe) and (peg is not None and peg < t_peg) and (roe > m_roe) and (fcf > m_fcf) and (debt < m_debt)
        ok = "✅ 符合" if (f_m and cur_p > m200 if m200_check else f_m) else "❌ 不符"
        
        return {
            t["col_code"]:symbol, t["col_price"]:round(cur_p, 2), t["col_ma200

import streamlit as st
import yfinance as yf
import pandas as pd
import time
from datetime import datetime
import pytz

# --- 1. 字典配置 ---
LANG = {
    "CN": {
        "title": "🍎 Issac 价值投资筛选器", "sidebar_header": "筛选设置",
        "ma200_label": "📈 仅限 MA200 上方", "pe_label": "最高 P/E",
        "peg_label": "最高 PEG", "fcf_label": "最低 FCF (10亿$)",
        "roe_label": "最低 ROE (%)", "debt_label": "最高负债率 (%)",
        "index_label": "📊 扫描范围", "scan_btn": "开始扫描",
        "matching_only": "🔍 只看符合条件的股票",
        "col_code": "代码", "col_price": "价格", "col_ma200": "MA200",
        "col_pe": "P/E", "col_peg": "PEG", "col_roe": "ROE(%)", "col_fcf": "FCF($B)", 
        "col_debt": "负债率", "col_rsi": "RSI", "col_macd": "MACD", 
        "col_vol": "量比(7D)", "col_short": "做空率", "col_res": "结果",
        "last_up": "⏱️ 最后更新: "
    },
    "EN": {
        "title": "🍎 Issac Picker Pro", "sidebar_header": "Settings",
        "ma200_label": "📈 Above MA200 Only", "pe_label": "Max P/E",
        "peg_label": "Max PEG", "fcf_label": "Min FCF ($B)",
        "roe_label": "Min ROE (%)", "debt_label": "Max Debt (%)",
        "index_label": "📊 Select Index", "scan_btn": "Start Scan",
        "matching_only": "🔍 Matches Only",
        "col_code": "Symbol", "col_price": "Price", "col_ma200": "MA200",
        "col_pe": "P/E", "col_peg": "PEG", "col_roe": "ROE(%)", "col_fcf": "FCF($B)", 
        "col_debt": "D/E (%)", "col_rsi": "RSI", "col_macd": "MACD", 
        "col_vol": "Vol/7D", "col_short": "Short %", "col_res": "Result",
        "last_up": "⏱️ Last Updated: "
    }
}

st.set_page_config(page_title="Issac Picker", layout="wide")
lang = st.sidebar.radio("🌐 Language", ["CN", "EN"], horizontal=True)
t = LANG[lang]
st.title(t["title"])

# 侧边栏参数
above_m200_check = st.sidebar.checkbox(t["ma200_label"], value=False)
target_pe = st.sidebar.slider(t["pe_label"], 5.0, 50.0, 20.0)
target_peg = st.sidebar.slider(t["peg_label"], 0.1, 3.0, 1.0) 
min_fcf = st.sidebar.number_input(t["fcf_label"], value=1.0)
min_roe = st.sidebar.slider(t["roe_label"], 0.0, 50.0, 15.0)
max_debt = st.sidebar.slider(t["debt_label"], 0.0, 200.0, 100.0)

@st.cache_data
def get_tk(idx_name):
    import urllib.request
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies' if idx_name == "S&P 500" else 'https://en.wikipedia.org/wiki/Nasdaq-100'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        df = pd.read_html(resp)[0 if idx_name == "S&P 500" else 4]
    return [str(s).replace('.', '-') for s in df.iloc[:, 0].tolist()]

idx_mode = st.sidebar.selectbox(t["index_label"], ["S&P 500", "Nasdaq 100"])
tickers = get_tk(idx_mode)

if 'res' not in st.session_state: st.session_state.res, st.session_state.up_t = None, None

# --- 4. 扫描 ---
if st.button(t["scan_btn"]):
    data = []
    with st.spinner('Scanning Market...'):
        for s in tickers:
            try:
                tk = yf.Ticker(s)
                h = tk.history(period="1y")
                if len(h) < 35: continue
                
                cur_p, m200 = h['Close'].iloc[-1], h['Close'].rolling(200).mean().iloc[-1]
                v_avg = h['Volume'].iloc[-8:-1].mean()
                v_ratio = ((h['Volume'].iloc[-1] / v_avg) - 1) * 100 if v_avg > 0 else 0
                
                diff = h['Close'].diff()
                gain, loss = diff.where(diff > 0, 0).rolling(14).mean().iloc[-1], -diff.where(diff < 0, 0).rolling(14).mean().iloc[-1]
                rsi = 100 - (100 / (1 + (gain/loss))) if loss != 0 else 50
                
                ema12, ema26 = h['Close'].ewm(span=12).mean(), h['Close'].ewm(span=26).mean()
                macd_v = ema12 - ema26
                macd_txt = "▲ 金叉" if macd_v.iloc[-1] > macd_v.ewm(span=9).mean().iloc[-1] else "▼ 死叉"
                
                inf = tk.info
                # 🎯 修复 PEG：如果抓不到则显示为 None，不再默认为 0.1
                pe = inf.get('forwardPE')
                peg = inf.get('pegRatio') or inf.get('trailingPegRatio')
                roe = (inf.get('returnOnEquity') or 0) * 100
                fcf = (inf.get('freeCashflow') or 0) / 1e9
                debt = inf.get('debtToEquity') or 0
                sh = (inf.get('shortPercentOfFloat') or 0) * 100
                
                # 筛选条件判定 (兼容 None)
                f_m = (pe and 0 < pe < target_pe) and (peg is not None and peg < target_peg) and (roe > min_roe) and (fcf > min_fcf) and (debt < max_debt)
                ok = "✅ 符合" if (f_m and cur_p > m200 if above_m200_check else f_m) else "❌ 不符"
                
                data.append({
                    t["col_code"]:s, t["col_price"]:round(cur_p, 2), t["col_ma200"]:round(m200, 2), 
                    t["col_pe"]:pe, t["col_peg"]:peg, t["col_roe"]:round(roe,1), 
                    t["col_fcf"]:round(fcf,1), t["col_debt"]:round(debt,1), 
                    t["col_rsi"]:round(rsi,1), t["col_macd"]:macd_txt, t["col_short"]:f"{sh:.1f}%", 
                    t["col_vol"]:f"{v_ratio:+.1f}%", t["col_res"]:ok, 
                    "hidden_p":cur_p, "hidden_m":m200, "hidden_sh":sh, "hidden_v":v_ratio
                })
            except: pass
    st.session_state.res = data
    st.session_state.up_t = datetime.now(pytz.timezone('America/Toronto')).strftime("%Y-%m-%d %H:%M:%S")

# --- 5. 展示 ---
if st.session_state.res:
    df = pd.DataFrame(st.session_state.res)
    st.caption(f"{t['last_up']} {st.session_state.up_t}")
    
    # 🎯 彻底剔除右侧重复数据列
    clean_df = df.drop(columns=["hidden_p", "hidden_m", "hidden_sh", "hidden_v"])
    m_df = clean_df[clean_df[t["col_res"]].str.contains("✅")]
    
    if not m_df.empty:
        st.subheader("🤖 Issac AI Pro 深度研判")
        sel = st.selectbox("🎯 分析个股:", m_df[t["col_code"]].tolist())
        # 从原始 df 中读隐藏数据给 AI
        s = df[df[t["col_code"]] == sel].iloc[0]
        with st.expander(f"📊 {sel} - 深度研报", expanded=True):
            if s['hidden_sh'] > 5: st.error(f"⚠️ 高空头: {s['hidden_sh']:.1f}%")
            if s['hidden_p'] < s['hidden_m']: st.warning("❌ 处于均线下方")
            c1, c2, c3 = st.columns(3)
            c1.metric("PEG", s[t['col_peg']] if s[t['col_peg']] is not None else "N/A")
            c2.metric("ROE", f"{s[t['col_roe']]}%")
            c3.metric("FCF", f"${s[t['col_fcf']]}B")
            
            # 智能总结
            score = (1 if s[t['col_peg']] and s[t['col_peg']] < 0.7 else 0) + (1 if s[t['col_roe']] > 25 else 0) + (1 if s['hidden_p'] > s['hidden_m'] else 0)
            st.success(f"🏆 评级: {['Wait (C)','Hold (B)','Buy (A)','Strong Buy (A+)'][score]}")

    st.dataframe(m_df if st.checkbox(t["matching_only"], value=True) else clean_df, use_container_width=True, hide_index=True)

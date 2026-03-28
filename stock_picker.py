import streamlit as st
import yfinance as yf
import pandas as pd
import time
from datetime import datetime
import pytz

# --- 1. 语言配置 ---
LANG = {
    "CN": {
        "title": "🍎 Issac 价值投资筛选器", "sidebar_header": "筛选条件设置",
        "ma200_label": "📈 只看股价在 200 日均线上方", "pe_label": "最高市盈率 (P/E)",
        "peg_label": "最高 PEG (市盈增长比)", "fcf_label": "最低自由现金流 (10亿$)",
        "roe_label": "最低 ROE (%)", "debt_label": "最高资产负债率 (%)",
        "index_label": "📊 选择扫描范围", "scan_btn": "开始扫描股票池",
        "matching_only": "🔍 只显示符合要求的股票",
        "col_code": "代码", "col_price": "价格", "col_ma200": "MA200",
        "col_pe": "P/E", "col_peg": "PEG", "col_roe": "ROE(%)", "col_fcf": "FCF($B)", 
        "col_debt": "负债率(%)", "col_rsi": "RSI(14)", "col_macd": "MACD", 
        "col_vol_ratio": "量比(7D)", "col_short": "做空率", "col_result": "结果",
        "found_msg": "🎯 找到了 {n} 只优质资产：", "no_match": "⚠️ 暂无符合条件的股票。", "last_update": "⏱️ 最后更新时间 (多伦多): "
    },
    "EN": {
        "title": "🍎 Issac-Style Value Screener", "sidebar_header": "Screener Settings",
        "ma200_label": "📈 Above 200D Moving Average Only", "pe_label": "Max P/E Ratio",
        "peg_label": "Max PEG Ratio", "fcf_label": "Min Free Cash Flow ($B)",
        "roe_label": "Min ROE (%)", "debt_label": "Max Debt-to-Equity (%)",
        "index_label": "📊 Select Index", "scan_btn": "Start Scanning",
        "matching_only": "🔍 Show Matches Only",
        "col_code": "Symbol", "col_price": "Price", "col_ma200": "MA200",
        "col_pe": "P/E", "col_peg": "PEG", "col_roe": "ROE(%)", "col_fcf": "FCF($B)", 
        "col_debt": "D/E (%)", "col_rsi": "RSI(14)", "col_macd": "MACD", 
        "col_vol_ratio": "Vol/7D Avg", "col_short": "Short %", "col_result": "Result",
        "found_msg": "🎯 Found {n} quality assets:", "no_match": "⚠️ No matching stocks found.", "last_update": "⏱️ Last Updated (Toronto): "
    }
}

# --- 2. 核心配置 ---
st.set_page_config(page_title="Issac美股筛选器", layout="wide")
lang_choice = st.sidebar.radio("🌐 Language", ["CN", "EN"], horizontal=True)
t = LANG[lang_choice]
st.title(t["title"])

above_ma200_only = st.sidebar.checkbox(t["ma200_label"], value=False)
target_pe = st.sidebar.slider(t["pe_label"], 5.0, 50.0, 20.0)
target_peg = st.sidebar.slider(t["peg_label"], 0.1, 3.0, 1.0) 
min_fcf_input = st.sidebar.number_input(t["fcf_label"], value=1.0)
target_roe = st.sidebar.slider(t["roe_label"], 0.0, 50.0, 15.0)
max_debt_input = st.sidebar.slider(t["debt_label"], 0.0, 200.0, 100.0)

@st.cache_data
def get_tickers(index_name):
    import urllib.request
    def fetch(url, idx):
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response: return pd.read_html(response)[idx]
    return fetch('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', 0)['Symbol'].tolist() if index_name == "S&P 500" else fetch('https://en.wikipedia.org/wiki/Nasdaq-100', 4)['Ticker'].tolist()

index_mode = st.sidebar.selectbox(t["index_label"], ["S&P 500", "Nasdaq 100"])
tickers = [str(s).replace('.', '-') for s in get_tickers(index_mode)]

if 'scan_results' not in st.session_state: st.session_state.scan_results = None

# --- 4. 扫描逻辑 ---
if st.button(t["scan_btn"]):
    results = []
    with st.spinner('Scanning...'):
        for symbol in tickers:
            try:
                stock = yf.Ticker(symbol)
                hist = stock.history(period="1y")
                if len(hist) < 35: continue
                
                # 核心价格数据
                price = float(hist['Close'].iloc[-1])
                ma200 = float(hist['Close'].rolling(200).mean().iloc[-1])
                vol_ratio = ((hist['Volume'].iloc[-1] / hist['Volume'].iloc[-8:-1].mean()) - 1) * 100
                
                # 技术指标
                delta = hist['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rsi_val = 100 - (100 / (1 + gain/loss)).iloc[-1]
                
                # 财务数据 (数据清洗)
                info = stock.info
                pe = float(info.get('forwardPE', 0))
                peg = float(info.get('pegRatio', info.get('trailingPegRatio', 0)))
                roe = float(info.get('returnOnEquity', 0)) * 100
                fcf = float(info.get('freeCashflow', 0)) / 1e9
                debt = float(info.get('debtToEquity', 0))
                short_ratio = float(info.get('shortPercentOfFloat', 0)) * 100

                # 🎯 修复 PEG 0 值筛选逻辑
                f_match = (0 < pe < target_pe and 0 <= peg < target_peg and roe > target_roe and fcf > min_fcf_input and debt < max_debt_input)
                final_cond = (f_match and price > ma200) if above_ma200_only else f_match

                results.append({
                    t["col_code"]: symbol, t["col_price"]: f"${price:.2f}",
                    t["col_ma200"]: f"${ma200:.2f}", t["col_pe"]: round(pe, 2),
                    t["col_peg"]: round(peg, 2), t["col_roe"]: round(roe, 1),
                    t["col_fcf"]: round(fcf, 2), t["col_debt"]: round(debt, 1),
                    t["col_rsi"]: round(rsi_val, 1), 
                    t["col_short"]: f"{short_ratio:.2f}%",
                    t["col_vol_ratio"]: f"{vol_ratio:+.1f}%",
                    t["col_result"]: "✅ 符合" if final_cond else "❌ 不符",
                    # 🎯 隐藏数据字段（变量名前加下划线，Streamlit 默认会处理或手动排除）
                    "_short_val": short_ratio, "_price_val": price, "_ma200_val": ma200, "_vol_val": vol_ratio
                })
            except: pass
            time.sleep(0.01)
    st.session_state.scan_results = results
    st.session_state.update_time = datetime.now(pytz.timezone('America/Toronto')).strftime("%Y-%m-%d %H:%M:%S")

# --- 5. 展示逻辑 ---
if st.session_state.get('scan_results'):
    df = pd.DataFrame(st.session_state.scan_results)
    if not df.empty:
        st.divider()
        st.caption(f"{t['last_update']} {st.session_state.update_time}")
        
        # 🎯 只显示不带下划线的列
        display_cols = [c for c in df.columns if not c.startswith('_')]
        match_df = df[df[t["col_result"]].str.contains("符合|Match")]
        
        if not match_df.empty:
            st.subheader(f"🤖 Issac AI {'Stock Intelligence' if lang_choice=='EN' else '深度投资研判'}")
            selected_stock = st.selectbox(f"🎯 {'Analysis:' if lang_choice=='EN' else '个股研判：'}", match_df[t["col_code"]].tolist())
            
            if selected_stock:
                s = match_df[match_df[t["col_code"]] == selected_stock].iloc[0]
                with st.expander(f"📊 {selected_stock} - {'Report' if lang_choice=='EN' else '深度报告'}", expanded=True):
                    # 空头预警
                    if s['_short_val'] > 5:
                        st.error(f"⚠️ **{'Short Warning' if lang_choice=='EN' else '空头预警'}:** ({s['_short_val']:.1f}%) {'High bear pressure.' if lang_choice=='EN' else '空头集结，注意阴跌。'}")
                    # 趋势警告
                    if s['_price_val'] < s['_ma200_val']:
                        st.warning(f"❌ **{'Weak Trend' if lang_choice=='EN' else '趋势极弱'}:** {'Price below MA200.' if lang_choice=='EN' else '股价处于 MA200 下方。'}")
                    
                    st.write(f"💵 **PEG {s[t['col_peg']]}, ROE {s[t['col_roe']]}%.**")
                    st.write(f"📈 **RSI {s[t['col_rsi']]}, Vol {s[t['col_vol_ratio']]}.**")

        final_df = (match_df if st.checkbox(t["matching_only"], value=True) else df)[display_cols]
        st.dataframe(final_df, use_container_width=True, height=500, hide_index=True)

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
        "col_vol_ratio": "量比(7D)", "col_result": "结果",
        "found_msg": "🎯 找到了 {n} 只优质资产：", "no_match": "⚠️ 暂无符合条件的股票。", "all_msg": "📊 正在显示全部 {n} 只扫描结果：",
        "last_update": "⏱️ 最后更新时间 (多伦多): "
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
        "col_vol_ratio": "Vol/7D Avg", "col_result": "Result",
        "found_msg": "🎯 Found {n} quality assets:", "no_match": "⚠️ No matching stocks found.", "all_msg": "📊 Showing all {n} scan results:",
        "last_update": "⏱️ Last Updated (Toronto): "
    }
}

# --- 2. 核心配置 ---
st.set_page_config(page_title="Issac美股筛选器", layout="wide")
lang_choice = st.sidebar.radio("🌐 Language / 语言", ["CN", "EN"], horizontal=True)
t = LANG[lang_choice]

st.title(t["title"])
st.sidebar.header(t["sidebar_header"])

above_ma200_only = st.sidebar.checkbox(t["ma200_label"], value=False)
target_pe = st.sidebar.slider(t["pe_label"], 5.0, 50.0, 20.0)
target_peg = st.sidebar.slider(t["peg_label"], 0.1, 3.0, 1.0) 
min_fcf_input = st.sidebar.number_input(t["fcf_label"], value=1.0)
target_roe = st.sidebar.slider(t["roe_label"], 0.0, 50.0, 15.0)
max_debt_input = st.sidebar.slider(t["debt_label"], 0.0, 200.0, 100.0)

# --- 3. 获取名单函数 ---
@st.cache_data
def get_tickers(index_name):
    import urllib.request
    def fetch(url, idx):
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return pd.read_html(response)[idx]
    
    if index_name == "S&P 500":
        df = fetch('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', 0)
        return [str(s).replace('.', '-') for s in df['Symbol'].tolist()]
    else:
        df = fetch('https://en.wikipedia.org/wiki/Nasdaq-100', 4)
        return [str(tk).replace('.', '-') for tk in df['Ticker'].tolist()]

index_mode = st.sidebar.selectbox(t["index_label"], ["S&P 500", "Nasdaq 100"])
tickers = get_tickers(index_mode)

if 'scan_results' not in st.session_state: st.session_state.scan_results = None
if 'update_time' not in st.session_state: st.session_state.update_time = None

# --- 4. 扫描逻辑 ---
if st.button(t["scan_btn"]):
    results = []
    with st.spinner('Analyzing...'):
        for symbol in tickers:
            try:
                stock = yf.Ticker(symbol)
                hist = stock.history(period="1y")
                if len(hist) < 35: continue
                
                # 价格与成交量指标
                price = hist['Close'].iloc[-1]
                ma200 = hist['Close'].rolling(200).mean().iloc[-1] if len(hist) >= 200 else price
                
                # 🎯 7日量比计算
                vol_today = hist['Volume'].iloc[-1]
                vol_7d_avg = hist['Volume'].iloc[-8:-1].mean()
                vol_ratio = ((vol_today / vol_7d_avg) - 1) * 100 if vol_7d_avg > 0 else 0
                
                # 技术指标
                delta = hist['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rsi_val = 100 - (100 / (1 + gain/loss)).iloc[-1]
                
                ema12 = hist['Close'].ewm(span=12, adjust=False).mean()
                ema26 = hist['Close'].ewm(span=26, adjust=False).mean()
                macd_line = ema12 - ema26
                signal_line = macd_line.ewm(span=9, adjust=False).mean()
                macd_status = "▲ 金叉" if macd_line.iloc[-1] > signal_line.iloc[-1] else "▼ 死叉"
                
                # 财务
                info = stock.info
                pe, peg, roe = info.get('forwardPE', 0), info.get('pegRatio', info.get('trailingPegRatio', 0)), info.get('returnOnEquity', 0) * 100
                fcf_val, debt_val = info.get('freeCashflow', 0) / 1e9, info.get('debtToEquity', 0)
                
                f_match = (0 < pe < target_pe and 0 < peg < target_peg and roe > target_roe and fcf_val > min_fcf_input and debt_val < max_debt_input)
                final_cond = (f_match and price > ma200) if above_ma200_only else f_match

                results.append({
                    t["col_code"]: symbol, t["col_price"]: f"${price:.2f}",
                    t["col_ma200"]: f"${ma200:.2f}", t["col_pe"]: round(pe, 2),
                    t["col_peg"]: round(peg, 2), t["col_roe"]: round(roe, 1),
                    t["col_fcf"]: round(fcf_val, 2), t["col_debt"]: round(debt_val, 1),
                    t["col_rsi"]: round(rsi_val, 1), t["col_macd"]: macd_status,
                    t["col_vol_ratio"]: f"{vol_ratio:+.1f}%",
                    t["col_result"]: "✅ 符合" if final_cond else "❌ 不符",
                    "vol_num": vol_ratio # 隐藏字段用于 AI 分析
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
        
        show_only = st.checkbox(t["matching_only"], value=True)
        match_df = df[df[t["col_result"]].str.contains("符合|Match")]
        display_df = match_df if show_only else df
        
        # --- AI 分析 (新增成交量逻辑) ---
        if not match_df.empty:
            st.subheader(f"🤖 Issac AI {'Analysis' if lang_choice=='EN' else '深度分析'}")
            selected_stock = st.selectbox(f"🎯 {'Analyze:' if lang_choice=='EN' else '分析个股：'}", match_df[t["col_code"]].tolist())
            
            if selected_stock:
                s = match_df[match_df[t["col_code"]] == selected_stock].iloc[0]
                with st.expander(f"🔍 {selected_stock} - {'Report' if lang_choice=='EN' else '投资报告'}", expanded=True):
                    # 财务
                    st.write(f"🏛️ **{'Fundamental' if lang_choice=='EN' else '基本面'}:** PEG {s[t['col_peg']]}, ROE {s[t['col_roe']]}%. {'Value play.' if lang_choice=='EN' else '典型的价值成长组合。'}")
                    # 成交量 AI 研判
                    v_ratio = s['vol_num']
                    v_msg = ""
                    if v_ratio > 100: v_msg = f"🚀 **{'Huge Volume' if lang_choice=='EN' else '巨量突破'}:** {'Volume is 2x+ average! Strong institutional interest.' if lang_choice=='EN' else '成交量翻倍！极大概率有大资金进场。'}"
                    elif v_ratio > 30: v_msg = f"📈 **{'Increasing Volume' if lang_choice=='EN' else '温和放量'}:** {'Buying pressure is building up.' if lang_choice=='EN' else '买盘活跃度正在提升。'}"
                    elif v_ratio < -30: v_msg = f"💤 **{'Low Volume' if lang_choice=='EN' else '缩量盘整'}:** {'Market is waiting. Low volatility expected.' if lang_choice=='EN' else '交投清淡，目前处于洗盘或蓄势阶段。'}"
                    if v_msg: st.info(v_msg)
                    
                    # 技术
                    st.write(f"📈 **{'Technical' if lang_choice=='EN' else '技术面'}:** RSI {s[t['col_rsi']]}, MACD {s[t['col_macd']]}.")

        st.dataframe(display_df.drop(columns=['vol_num']), use_container_width=True, height=500, hide_index=True)

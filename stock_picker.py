import streamlit as st
import yfinance as yf
import pandas as pd
import time

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
        "col_kdj": "KDJ", "col_result": "结果",
        "found_msg": "🎯 找到了 {n} 只优质资产：", "no_match": "⚠️ 暂无符合条件的股票。", "all_msg": "📊 正在显示全部 {n} 只扫描结果："
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
        "col_kdj": "KDJ", "col_result": "Result",
        "found_msg": "🎯 Found {n} quality assets:", "no_match": "⚠️ No matching stocks found.", "all_msg": "📊 Showing all {n} scan results:"
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
def fetch_wiki_table(url, table_index=0):
    import urllib.request
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        return pd.read_html(response)[table_index]

@st.cache_data
def get_sp500():
    df = fetch_wiki_table('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', 0)
    return [str(s).replace('.', '-') for s in df['Symbol'].tolist()]

@st.cache_data
def get_ndq100():
    df = fetch_wiki_table('https://en.wikipedia.org/wiki/Nasdaq-100', 4)
    return [str(tk).replace('.', '-') for tk in df['Ticker'].tolist()]

st.sidebar.divider()
index_mode = st.sidebar.selectbox(t["index_label"], ["S&P 500", "Nasdaq 100"])
tickers = get_sp500() if index_mode == "S&P 500" else get_ndq100()
st.sidebar.write(f"Count: {len(tickers)}")

if 'scan_results' not in st.session_state:
    st.session_state.scan_results = None

# --- 4. 扫描逻辑 ---
if st.button(t["scan_btn"]):
    results = []
    with st.spinner('Analyzing...'):
        for symbol in tickers:
            try:
                stock = yf.Ticker(symbol)
                hist = stock.history(period="1y")
                if len(hist) < 35: continue
                
                # 价格与均线
                price = hist['Close'].iloc[-1]
                ma200 = hist['Close'].rolling(200).mean().iloc[-1] if len(hist) >= 200 else price
                
                # 1. RSI (14)
                delta = hist['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rsi_val = 100 - (100 / (1 + gain/loss)).iloc[-1]
                
                # 2. MACD (12, 26, 9)
                ema12 = hist['Close'].ewm(span=12, adjust=False).mean()
                ema26 = hist['Close'].ewm(span=26, adjust=False).mean()
                macd_line = ema12 - ema26
                signal_line = macd_line.ewm(span=9, adjust=False).mean()
                macd_status = "▲ 金叉" if macd_line.iloc[-1] > signal_line.iloc[-1] else "▼ 死叉"
                
                # 3. KDJ (9, 3, 3)
                low_9 = hist['Low'].rolling(9).min()
                high_9 = hist['High'].rolling(9).max()
                rsv = (hist['Close'] - low_9) / (high_9 - low_9) * 100
                k_val = rsv.ewm(com=2, adjust=False).mean().iloc[-1]
                kdj_status = "超卖" if k_val < 20 else ("超买" if k_val > 80 else "正常")
                
                # 4. 财务数据
                info = stock.info
                pe = info.get('forwardPE', 0)
                peg = info.get('pegRatio', info.get('trailingPegRatio', 0))
                roe = info.get('returnOnEquity', 0) * 100
                fcf_val = info.get('freeCashflow', 0) / 1e9
                debt_val = info.get('debtToEquity', 0)
                
                # 综合筛选逻辑
                f_match = (0 < pe < target_pe and 0 < peg < target_peg and roe > target_roe and fcf_val > min_fcf_input and debt_val < max_debt_input)
                final_cond = (f_match and price > ma200) if above_ma200_only else f_match
                res_text = "✅ 符合" if final_cond else "❌ 不符"

                # 🎯 补齐所有指标到结果列表
                results.append({
                    t["col_code"]: symbol,
                    t["col_price"]: f"${price:.2f}",
                    t["col_ma200"]: f"${ma200:.2f}",
                    t["col_pe"]: round(pe, 2),
                    t["col_peg"]: round(peg, 2),
                    t["col_roe"]: round(roe, 1),
                    t["col_fcf"]: round(fcf_val, 2),      # 补齐现金流
                    t["col_debt"]: round(debt_val, 1),    # 补齐负债率
                    t["col_rsi"]: round(rsi_val, 1),
                    t["col_macd"]: macd_status,
                    t["col_kdj"]: kdj_status,
                    t["col_result"]: res_text
                })
            except:
                pass
            time.sleep(0.01)
    st.session_state.scan_results = results

# --- 5. 展示逻辑 (冻结表头 + 自动美化版) ---
if st.session_state.get('scan_results'):
    df = pd.DataFrame(st.session_state.scan_results)
    st.divider()
    
    col1, col2 = st.columns([3, 1])
    with col1: 
        show_only = st.checkbox(t["matching_only"], value=False)
    with col2: 
        st.download_button("📥 CSV", df.to_csv(index=False).encode('utf-8-sig'), f"Issac_{time.strftime('%Y%m%d')}.csv")

    display_df = df[df[t["col_result"]].str.contains("符合")] if show_only else df
    
    if not display_df.empty:
        st.success(t["found_msg"].format(n=len(display_df)))
        
        # 🎯 关键改动：使用 st.dataframe 代替 st.table
        # height=600 可以确保表头固定，出现内部滚动条
        st.dataframe(
            display_df, 
            use_container_width=True, 
            height=600,
            hide_index=True # 隐藏最左边的 0, 1, 2 索引，更整洁
        )
    else:
        st.warning(t["no_match"])
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
        "col_kdj": "KDJ", "col_result": "结果",
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
        "col_kdj": "KDJ", "col_result": "Result",
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
def fetch_wiki_table(url, table_index=0):
    import urllib.request
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        return pd.read_html(response)[table_index]

@st.cache_data
def get_tickers(index_name):
    if index_name == "S&P 500":
        df = fetch_wiki_table('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', 0)
        return [str(s).replace('.', '-') for s in df['Symbol'].tolist()]
    else:
        df = fetch_wiki_table('https://en.wikipedia.org/wiki/Nasdaq-100', 4)
        return [str(tk).replace('.', '-') for tk in df['Ticker'].tolist()]

st.sidebar.divider()
index_mode = st.sidebar.selectbox(t["index_label"], ["S&P 500", "Nasdaq 100"])
tickers = get_tickers(index_mode)
st.sidebar.write(f"Count: {len(tickers)}")

# 初始化状态
if 'scan_results' not in st.session_state: st.session_state.scan_results = None
if 'update_time' not in st.session_state: st.session_state.update_time = None

# --- 4. 扫描逻辑 ---
if st.button(t["scan_btn"]):
    results = []
    with st.spinner('Analyzing Markets...'):
        for symbol in tickers:
            try:
                stock = yf.Ticker(symbol)
                hist = stock.history(period="1y")
                if len(hist) < 35: continue
                
                price = hist['Close'].iloc[-1]
                ma200 = hist['Close'].rolling(200).mean().iloc[-1] if len(hist) >= 200 else price
                
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
                
                low_9, high_9 = hist['Low'].rolling(9).min(), hist['High'].rolling(9).max()
                rsv = (hist['Close'] - low_9) / (high_9 - low_9) * 100
                k_val = rsv.ewm(com=2, adjust=False).mean().iloc[-1]
                kdj_status = "超卖" if k_val < 20 else ("超买" if k_val > 80 else "正常")
                
                # 财务数据
                info = stock.info
                pe = info.get('forwardPE', 0)
                peg = info.get('pegRatio', info.get('trailingPegRatio', 0))
                roe = info.get('returnOnEquity', 0) * 100
                fcf_val = info.get('freeCashflow', 0) / 1e9
                debt_val = info.get('debtToEquity', 0)
                
                f_match = (0 < pe < target_pe and 0 < peg < target_peg and roe > target_roe and fcf_val > min_fcf_input and debt_val < max_debt_input)
                final_cond = (f_match and price > ma200) if above_ma200_only else f_match
                res_text = "✅ 符合" if final_cond else "❌ 不符"

                results.append({
                    t["col_code"]: symbol, t["col_price"]: f"${price:.2f}",
                    t["col_ma200"]: f"${ma200:.2f}", t["col_pe"]: round(pe, 2),
                    t["col_peg"]: round(peg, 2), t["col_roe"]: round(roe, 1),
                    t["col_fcf"]: round(fcf_val, 2), t["col_debt"]: round(debt_val, 1),
                    t["col_rsi"]: round(rsi_val, 1), t["col_macd"]: macd_status,
                    t["col_kdj"]: kdj_status, t["col_result"]: res_text
                })
            except: pass
            time.sleep(0.01)
    
    st.session_state.scan_results = results
    # 🎯 设置多伦多时间
    toronto_tz = pytz.timezone('America/Toronto')
    st.session_state.update_time = datetime.now(toronto_tz).strftime("%Y-%m-%d %H:%M:%S")

# --- 5. 展示逻辑 (双语深度 AI 分析版) ---
if st.session_state.get('scan_results'):
    df = pd.DataFrame(st.session_state.scan_results)
    
    if not df.empty and t["col_result"] in df.columns:
        st.divider()
        if st.session_state.update_time:
            st.caption(f"{t['last_update']} {st.session_state.update_time}")
            
        col1, col2 = st.columns([3, 1])
        with col1: show_only = st.checkbox(t["matching_only"], value=False)
        with col2: st.download_button("📥 CSV", df.to_csv(index=False).encode('utf-8-sig'), f"Issac_{time.strftime('%Y%m%d')}.csv")

        match_df = df[df[t["col_result"]].str.contains("符合|Match")]
        display_df = match_df if show_only else df
        
        # --- 🤖 智能 AI 分析组件 (双语补完版) ---
        if not match_df.empty:
            st.subheader(f"🤖 Issac AI {'Deep Analysis' if lang_choice=='EN' else '深度个股分析'}")
            selected_stock = st.selectbox(f"🎯 {'Analyze Quality Stock:' if lang_choice=='EN' else '选择一只优质股进行深度分析：'}", match_df[t["col_code"]].tolist())
            
            if selected_stock:
                s = match_df[match_df[t["col_code"]] == selected_stock].iloc[0]
                with st.expander(f"🔍 {selected_stock} - Issac-Style {'Investment Report' if lang_choice=='EN' else '综合投资报告'}", expanded=True):
                    
                    # --- 1. 基本面评分 (Fundamental) ---
                    st.markdown(f"#### 🏛️ {'Fundamental Quality' if lang_choice=='EN' else '基本面护城河'}")
                    f_text = []
                    if s[t['col_peg']] < 0.6: 
                        f_text.append(f"🌟 **{'Undervalued Growth' if lang_choice=='EN' else '极速增长且低估'}:** PEG({s[t['col_peg']]}) {'suggests market is underestimating its earnings potential.' if lang_choice=='EN' else '显示市场严重低估了其增长动能。'}")
                    if s[t['col_roe']] > 30:
                        f_text.append(f"💰 **{'High Efficiency' if lang_choice=='EN' else '超强盈利能力'}:** ROE({s[t['col_roe']]}%) {'indicates a massive competitive moat and capital efficiency.' if lang_choice=='EN' else '显示出极强的护城河和资本运作效率。'}")
                    if s[t['col_fcf']] > 5:
                        f_text.append(f"💵 **{'Cash Cow' if lang_choice=='EN' else '现金奶牛'}:** FCF(${s[t['col_fcf']]}B) {'provides strong protection for buybacks or expansion.' if lang_choice=='EN' else '巨额自由现金流为回购或扩张提供了坚实盾牌。'}")
                    if s[t['col_debt']] < 30:
                        f_text.append(f"🛡️ **{'Solid Balance Sheet' if lang_choice=='EN' else '资产负债表极稳'}:** {'Very low leverage ensures resilience in high-rate environments.' if lang_choice=='EN' else '极低的财务杠杆使其在震荡市中具备极强的抗风险能力。'}")
                    st.write("\n".join(f_text) if f_text else ("Moderate fundamentals." if lang_choice=='EN' else "基本面表现稳健。"))

                    # --- 2. 技术面择时 (Technical) ---
                    st.markdown(f"#### 📈 {'Technical Timing' if lang_choice=='EN' else '技术面择时参考'}")
                    t_text = []
                    if s[t['col_rsi']] < 35:
                        t_text.append(f"🔥 **{'Deep Oversold' if lang_choice=='EN' else '超跌反弹信号'}:** RSI({s[t['col_rsi']]}% ) {'is near historical bottom. High probability of rebound.' if lang_choice=='EN' else '处于极低位，随时可能开启报复性反弹。'}")
                    elif s[t['col_rsi']] > 65:
                        t_text.append(f"⚠️ **{'Short-term Overheated' if lang_choice=='EN' else '短线过热'}:** RSI({s[t['col_rsi']]}) {'suggests waiting for a pullback before entry.' if lang_choice=='EN' else '显示短线追高风险大，建议回踩支撑位再看。'}")
                    
                    if "金叉" in s[t['col_macd']] or "▲" in s[t['col_macd']]:
                        t_text.append(f"🚀 **{'Momentum Up' if lang_choice=='EN' else '趋势反转向上'}:** MACD Golden Cross {'confirmed. The trend is currently your friend.' if lang_choice=='EN' else '已确认，上升通道可能已经开启。'}")
                    
                    if "超卖" in s[t['col_kdj']]:
                        t_text.append(f"💎 **{'KDJ Opportunity' if lang_choice=='EN' else '黄金入场点'}:** {'KDJ oversold state often signals a tactical buying opportunity.' if lang_choice=='EN' else 'KDJ 处于超卖状态，是极佳的短线分批入场时机。'}")
                    st.write("\n".join(t_text) if t_text else ("Trend is consolidating." if lang_choice=='EN' else "目前处于盘整蓄势阶段。"))

                    # --- 3. 最终判定 (Conclusion) ---
                    final_score = "Strong Buy (A+)" if s[t['col_peg']] < 0.7 and s[t['col_rsi']] < 45 else "Hold / Buy on Dips"
                    final_score_cn = "强力买入 (A+)" if s[t['col_peg']] < 0.7 and s[t['col_rsi']] < 45 else "稳健持有 / 回调买入"
                    st.success(f"📌 **{'Final Verdict' if lang_choice=='EN' else 'Issac 终极判定'}:** {final_score if lang_choice=='EN' else final_score_cn}")

        # 展示主表格
        if not display_df.empty:
            st.success(t["found_msg"].format(n=len(display_df)))
            st.dataframe(display_df, use_container_width=True, height=500, hide_index=True)
        else:
            st.warning(t["no_match"])

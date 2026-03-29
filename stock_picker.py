import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from lang_config import LANG 

# --- 1. 初始化设置 ---
st.set_page_config(page_title="Issac Terminal", layout="wide")
lang_choice = st.sidebar.radio("🌐 Language / 语言", ["CN", "EN"], horizontal=True)
t = LANG[lang_choice]
st.title(t["title"])

# 展示列
WHITE_LIST = ["Symbol", "Price", "Match", "P/E", "PEG", "ROE%", "Short%", "Upside"]

# --- 2. 侧边栏 ---
st.sidebar.header(t["sidebar_header"])
search_ticker = st.sidebar.text_input(t["search_label"], "").upper().strip()
st.sidebar.divider()
t_pe = st.sidebar.number_input(t["pe_label"], value=25.0)
t_peg = st.sidebar.number_input(t["peg_label"], value=1.2)
m_roe = st.sidebar.number_input(t["roe_label"], value=15.0)
m_fcf = st.sidebar.number_input(t["fcf_label"], value=0.5)
st.sidebar.divider()
idx_mode = st.sidebar.selectbox(t["scan_range"], ["S&P 500", "Nasdaq 100"])
scan_btn = st.sidebar.button(t["scan_btn"])

# --- 🎯 3. 分析引擎 (核心增强) ---
def get_analysis(s):
    try:
        tk = yf.Ticker(s)
        h = tk.history(period="1y")
        if len(h) < 200: return None
        inf = tk.info
        p = h['Close'].iloc[-1]
        m200_s = h['Close'].rolling(200).mean()
        m200_val = m200_s.iloc[-1]
        
        # 基础数据
        peg = inf.get('pegRatio') or inf.get('trailingPegRatio', 0)
        roe, fcf = (inf.get('returnOnEquity') or 0)*100, (inf.get('freeCashflow') or 0)/1e9
        target = inf.get('targetMeanPrice')
        upside = ((target / p) - 1) * 100 if target and p else 0
        
        # 🎯 (New 1) ⚔️ 相对强度计算 (RS) vs SPY (^GSPC)
        spy_tk = yf.Ticker("^GSPC")
        h_3m = tk.history(period="3mo")
        h_spy_3m = spy_tk.history(period="3mo")
        # 确保数据对齐
        if len(h_3m) < 60 or len(h_spy_3m) < 60: return None
        
        stock_ret_3m = ((h_3m['Close'].iloc[-1] / h_3m['Close'].iloc[0]) - 1) * 100
        spy_ret_3m = ((h_spy_3m['Close'].iloc[-1] / h_spy_3m['Close'].iloc[0]) - 1) * 100
        rs_diff = stock_ret_3m - spy_ret_3m
        rs_is_leader = rs_diff > 0

        # 🎯 (New 2) 📅 财报日程抓取与警示逻辑
        cal = tk.calendar
        days_to_earnings = 999
        upcoming_earnings_date = "N/A"
        # Calendar can be a list or a DataFrame depending on ticker type
        if isinstance(cal, pd.DataFrame) and 'Earnings Date' in cal.index:
            earn_date_obj = cal.loc['Earnings Date'].iloc[0]
            upcoming_earnings_date = earn_date_obj.strftime('%Y-%m-%d')
            delta = earn_date_obj - pd.Timestamp.now()
            days_to_earnings = delta.days

        # 🎯 (New 3) 🏛️ ROE 稳定性对比 (抓取上一完整财年)
        prev_year_roe = "N/A"
        yearly_financials = tk.yearly_financials
        yearly_balance_sheet = tk.yearly_balance_sheet
        if not yearly_financials.empty and not yearly_balance_sheet.empty:
            # 抓取最近完整财年的前一年数据进行对比
            if len(yearly_financials.columns) >= 2 and len(yearly_balance_sheet.columns) >= 2:
                try:
                    # 抓取第1列数据（0是TTM/TTT，1是去年完整财年）
                    prev_ni = yearly_financials.loc['Net Income'].iloc[1]
                    prev_equity = yearly_balance_sheet.loc['Stockholders Equity'].iloc[1]
                    if prev_equity > 0:
                        prev_year_roe = round((prev_ni / prev_equity) * 100, 1)
                except: pass

        ok = (0 < inf.get('forwardPE', 0) < t_pe and 0 < peg < t_peg and roe > m_roe and fcf > m_fcf)
        return {
            "Symbol": s, "Price": round(p, 2), "Match": "✅" if ok else "❌", "P/E": inf.get('forwardPE', 0), 
            "PEG": round(peg, 4), "ROE%": round(roe, 1), "FCF$B": round(fcf, 1), "Debt%": round(inf.get('debtToEquity', 0), 1), 
            "Short%": f"{(inf.get('shortPercentOfFloat') or 0)*100:.1f}%", "Upside": f"{upside:+.1f}%", 
            "_p": p, "_m": m200_val, "_h": h, "_m_s": m200_s, "_target": target, "_up_val": upside, "_inst": (inf.get('heldPercentInstitutions') or 0) * 100,
            "_sl": m200_val * 0.97,
            # (New) 数据打包
            "_stock_perf_3m": stock_ret_3m, "_spy_perf_3m": spy_ret_3m, "_rs_diff": rs_diff, "_rs_is_leader": rs_is_leader,
            "_earn_days": days_to_earnings, "_earn_date": upcoming_earnings_date,
            "_prev_year_roe": prev_year_roe, "_ind": inf.get('industry', "N/A"), "_sum": inf.get('longBusinessSummary', "N/A")
        }
    except: return None

# --- 🎯 4. 深度研报渲染 (修复 KeyError + 图文并貌增强) ---
def render_report(s):
    # 🎯 1. 红色高危预警 (放在最上方，图文并貌的第一块)
    if 0 <= s['_earn_days'] <= 7:
        st.error(t['earnings_label'].format(days=s['_earn_days'], date=s['_earn_date']))
        st.divider()

    # 2. 顶部参数与趋势图 (保持一致)
    st.subheader(f"{t['snapshot_title']} - {s['Symbol']}")
    st.dataframe(pd.DataFrame([s])[WHITE_LIST], use_container_width=True, hide_index=True)
    
    with st.expander(t['chart_title'], expanded=True):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=s['_h'].index, y=s['_h']['Close'], name=t['chart_close'], line=dict(color='#00d1ff', width=2.5)))
        fig.add_trace(go.Scatter(x=s['_m_s'].index, y=s['_m_s'], name=t['chart_ma200'], line=dict(color='#ffaa00', width=2, dash='dash')))
        fig.update_layout(template="plotly_dark", height=380, margin=dict(l=10, r=10, t=10, b=10),xaxis_title=t['chart_date'], yaxis_title=t['chart_close'])
        st.plotly_chart(fig, use_container_width=True)

    # 🎯 3. (New) ⚔️ 相对强度指数 (RS) 横向对比柱状图 (图文并貌核心强化)
    st.markdown(f"### {t['rs_title']}")
    fig_rs = go.Figure(go.Bar(
        x=[s['Symbol'], t['rs_label_spy']],
        y=[s['_stock_perf_3m'], s['_spy_perf_3m']],
        marker_color=['#00d1ff', '#cccccc'] # 你的天蓝色 vs SPY灰色
    ))
    fig_rs.update_layout(template="plotly_dark", height=280, yaxis_title="3M Perf %", margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_rs, use_container_width=True)
    
    if s['_rs_is_leader']:
        st.success(t['rs_desc_leader'].format(diff=s['_rs_diff']))
    else:
        st.error(t['rs_desc_laggard'].format(diff=abs(s['_rs_diff'])))

    # 4. 深度报告部分
    with st.expander(t['report_title'], expanded=True):
        st.markdown(f"#### {t['moat_title']}")
        st.write(f"**Industry**: `{s['_ind']}`")
        st.write(f"**Business**: {s['_sum'][:800]}...")
        st.info("🔥 Elite" if s['ROE%'] > 35 else ("🛡️ Wide Moat" if s['ROE%'] > 18 else "🚧 Narrow Moat"))
        
        st.markdown("---")
        # 5. 财务与ROE审计排版
        st.markdown(f"#### {t['fin_title']}")
        # 🎯 将去年 ROE 稳定性显示为 Delta 标签
        g1, g2 = st.columns(2)
        
        roe_sub_txt = f"{t['consistency_label'].format(curr=s['ROE%'], prev=s['_prev_year_roe'])}" if s['_prev_year_roe'] != "N/A" else f"· ROE%: **{s['ROE%']}%**"
        
        g1.metric("PEG Ratio", s['PEG'], delta="Value" if s['PEG'] < 0.7 else None)
        g2.metric("FCF $B", f"${s['FCF$B']}B")
        st.write(f"· **ROE% Profitability**: {roe_sub_txt}")

        st.write(f"· Target Price: ${round(s['_target'], 2)}" if s['_target'] else "N/A", delta=s['Upside'])
        d_status = t['debt_healthy'] if s['Debt%'] < 40 else (t['debt_mid'] if s['Debt%'] < 100 else t['debt_high'])
        st.write(f"· Debt Audit: D/E Ratio `{s['Debt%']}%` — {d_status}")

        st.markdown("---")
        # 6. 风控区域布局 (加入智能止损)
        st.markdown(f"#### {t['growth_title']} & {t['risk_title']}")
        r1, r2 = st.columns(2)
        inst_held = (s['_inst'] or 0) * 100
        inst_msg = f"Institutions hold {inst_held:.1f}%, stable sentiment." if inst_held > 70 else f" Institutions hold {inst_held:.1f}%."
        r1.caption(f"· Sentiment Radar: {inst_msg} (Short Ratio: {s['Short%']})")
        if s['Price'] < s['MA200']: r2.error("❌ **Trend Broken**: Below MA200.")
        else: r2.success("📈 **Bullish Trend**: Supported by MA200.")
        
        st.warning(f"🛡️ **{t['stop_loss_label']}**: `${round(s['_sl'], 2)}`")

        st.divider()
        # 🎯 Issac 风控核心评级逻辑 (保持一致)
        base_score = (1 if s['PEG'] < 0.7 else 0) + (1 if s['ROE%'] > 25 else 0) + (1 if s['_up_val'] > 15 else 0)
        
        if s['Price'] < s['_sl']:
            final_v = 1 # 强制锁定为 B (观望/持有)
            st.error(f"### {t['verdict_title']}：{t['verdicts'][final_v]} (Momentum Broken)")
            st.error("🚨 **Issac Risk Warning**: Company fundamentals are strong, but price momentum is broken. Rating is locked to Hold until trend recovers.")
        else:
            final_v = min(base_score + (1 if s['Price'] > s['MA200'] else 0), 3)
            st.success(f"### {t['verdict_title']}：{t['verdicts'][final_v]}")
            st.info(f"💡 {t['strategy_label']}：{t['strategies'][final_v]}")

# --- 5. 主逻辑流程 ---
if search_ticker:
    res = get_analysis(search_ticker)
    if res: render_report(res)
    else: st.error("Ticker not found.")

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
    # 强制白名单展示
    m_df = df[df["Match"]=="✅"][WHITE_LIST]
    if not m_df.empty:
        sel = st.selectbox("Select Target Stock:", m_df["Symbol"].tolist())
        target_s = df[df["Symbol"] == sel].iloc[0]
        render_report(target_s)
    st.dataframe(m_df, use_container_width=True, hide_index=True)

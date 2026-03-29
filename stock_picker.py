import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz
from lang_config import LANG 

# --- 1. 初始化设置 ---
st.set_page_config(page_title="Issac Terminal", layout="wide")
lang_choice = st.sidebar.radio("🌐 Language / 语言", ["CN", "EN"], horizontal=True)
t = LANG[lang_choice]
st.title(t["title"])

# 展示列
WHITE_LIST = ["Symbol", "Price", "Match", "P/E", "PEG", "ROE%", "Short%", "Upside"]

# --- 2. 侧边栏 ---
search_ticker = st.sidebar.text_input(t["search_label"], "").upper().strip()
st.sidebar.divider()
t_pe = st.sidebar.number_input(t["pe_label"], value=25.0)
t_peg = st.sidebar.number_input(t["peg_label"], value=1.2)
m_roe = st.sidebar.number_input(t["roe_label"], value=15.0)
m_fcf = st.sidebar.number_input(t["fcf_label"], value=0.5)
scan_btn = st.sidebar.button(t["scan_btn"])

# --- 🎯 3. 分析引擎 (核心增强) ---
def get_analysis(s):
    try:
        tk = yf.Ticker(s)
        inf = tk.info
        
        # A. 基础价格与趋势数据
        h = tk.history(period="1y")
        if len(h) < 200: return None
        p = h['Close'].iloc[-1]
        m200_s = h['Close'].rolling(200).mean()
        m200_val = m200_s.iloc[-1]
        
        # B. 核心财务 (修复 PEG)
        peg = inf.get('pegRatio') or inf.get('trailingPegRatio', 0)
        roe, fcf = (inf.get('returnOnEquity') or 0)*100, (inf.get('freeCashflow') or 0)/1e9
        target = inf.get('targetMeanPrice')
        upside = ((target / p) - 1) * 100 if target and p else 0
        
        # C. (New 1) ⚔️ 相对强度计算 (RS) vs ^GSPC
        spy_tk = yf.Ticker("^GSPC")
        h_3m = tk.history(period="3mo")
        h_spy_3m = spy_tk.history(period="3mo")
        if len(h_3m) < 60 or len(h_spy_3m) < 60: return None
        
        s_ret = ((h_3m['Close'].iloc[-1] / h_3m['Close'].iloc[0]) - 1) * 100
        spy_ret = ((h_spy_3m['Close'].iloc[-1] / h_spy_3m['Close'].iloc[0]) - 1) * 100
        rs_diff = s_ret - spy_ret
        rs_is_leader = rs_diff > 0

        # D. (New 2) 📅 财报日程获取
        cal = tk.calendar
        upcoming_earnings_date = "N/A"
        days_to_earnings = 999
        if isinstance(cal, pd.DataFrame) and 'Earnings Date' in cal.index:
            try:
                date_str = cal.loc['Earnings Date'].iloc[0].strftime('%Y-%m-%d')
                upcoming_earnings_date = date_str
                delta = cal.loc['Earnings Date'].iloc[0] - pd.Timestamp.now()
                days_to_earnings = delta.days
            except: pass

        # E. (New 3) 🏛️ 去年 ROE 稳定性对比 (抓取过去3年)
        prev_year_roe = "N/A"
        try:
            fin_history = tk.get_financials(proxy=None)
            # 抓取最近的 TTM 之前的那个完整财年的 ROE
            if not fin_history.empty and 'Net Income' in fin_history.index:
                net_income = fin_history.loc['Net Income'].iloc[1] # 去年净利润
                fin_balance = tk.get_balancesheet(proxy=None)
                if not fin_balance.empty and 'Stockholders Equity' in fin_balance.index:
                    equity = fin_balance.loc['Stockholders Equity'].iloc[1] # 去年股东权益
                    if equity > 0:
                        prev_year_roe = round((net_income / equity) * 100, 1)
        except: pass

        # F. 最终打包
        ok = (0 < inf.get('forwardPE', 0) < t_pe and 0 < peg < t_peg and roe > m_roe and fcf > m_fcf)
        return {
            "Symbol": s, "Price": round(p, 2), "Match": "✅" if ok else "❌", "P/E": inf.get('forwardPE', 0), 
            "PEG": round(peg, 4), "ROE%": round(roe, 1), "FCF$B": round(fcf, 1), "Debt%": round(inf.get('debtToEquity', 0), 1), 
            "Short%": f"{(inf.get('shortPercentOfFloat') or 0)*100:.1f}%", "Upside": f"{upside:+.1f}%", 
            "_p": p, "_m": m200_val, "_h": h, "_m_s": m200_s, "_target": target, "_up_val": upside, 
            "_inst": (inf.get('heldPercentInstitutions') or 0) * 100,
            "_sl": m200_val * 0.97,
            # New数据打包
            "_s_ret": s_ret, "_spy_ret": spy_ret, "_rs_diff": rs_diff, "_rs_is_l": rs_is_leader,
            "_earn_days": days_to_earnings, "_earn_date": upcoming_earnings_date,
            "_prev_roe": prev_year_roe, "_ind": inf.get('industry', "N/A"), "_sum": inf.get('longBusinessSummary', "N/A")
        }
    except: return None

# --- 🎯 4. 深度研报渲染 (修复 KeyError + 图文并貌增强) ---
def render_report(s):
    # 1. (New) 红色高危财报警示放在最上方
    if 0 <= s['_earn_days'] <= 7:
        st.error(t['earnings_label'].format(days=s['_earn_days'], date=s['_earn_date']))
        st.divider()

    # 2. 参数与趋势图 (保持一致)
    st.subheader(f"{t['snapshot_title']} - {s['Symbol']}")
    st.dataframe(pd.DataFrame([s])[WHITE_LIST], use_container_width=True, hide_index=True)
    
    with st.expander(t['chart_title'], expanded=True):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=s['_h'].index, y=s['_h']['Close'], name=t['chart_close'], line=dict(color='#00d1ff', width=2.5)))
        fig.add_trace(go.Scatter(x=s['_m_s'].index, y=s['_m_s'], name=t['chart_ma200'], line=dict(color='#ffaa00', width=2, dash='dash')))
        fig.update_layout(template="plotly_dark", height=380, margin=dict(l=10, r=10, t=10, b=10),xaxis_title=t['chart_date'], yaxis_title=t['chart_close'])
        st.plotly_chart(fig, use_container_width=True)

    # 3. 🛡️ 新增风控与止损建议 (Issac 风控核心)
    st.markdown("---")
    r1, r2 = st.columns(2)
    with r1:
        inst_held = (s['_inst'] or 0) * 100
        inst_msg = f"Institutions hold {inst_held:.1f}%, stable sentiment." if inst_held > 70 else f" Institutions hold {inst_held:.1f}%."
        st.caption(f"· Sentiment Radar: {inst_msg} (Short Ratio: {s['Short%']})")
    with r2:
        if s['Price'] < s['MA200']: st.error("❌ **Trend Broken**: Below MA200.")
        else: st.success("📈 **Bullish Trend**: Supported by MA200.")
    st.warning(f"🛡️ **{t['stop_loss_label']}**: `${round(s['_sl'], 2)}`")

    # 4. (New) ⚔️ 智库级深度功能排版
    # A. ⚔️ RS横向对比图 (图文并貌)
    st.markdown("---")
    st.markdown(f"### {t['rs_title']}")
    fig_rs = go.Figure(go.Bar(
        x=[s['Symbol'], t['rs_label_spy']],
        y=[s['_s_ret'], s['_spy_ret']],
        marker_color=['#00d1ff', '#cccccc']
    ))
    fig_rs.update_layout(template="plotly_dark", height=280, yaxis_title="3M Perf %", margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_rs, use_container_width=True)
    
    if s['_rs_is_l']: st.success(t['rs_desc_leader'].format(diff=s['_rs_diff']))
    else: st.error(t['rs_desc_laggard'].format(diff=abs(s['_rs_diff'])))

    # 5. 智库级深度研报
    with st.expander(t['report_title'], expanded=True):
        st.markdown(f"#### {t['moat_title']}")
        st.write(f"**Industry**: `{s['_ind']}`")
        st.write(f"**Business**: {s['_sum'][:800]}...")
        
        st.markdown(f"#### {t['growth_title']}")
        # 🏛️ (New) ROE 连贯性审计直接做进 Metric delta 标签里
        g1, g2 = st.columns(2)
        
        # 将去年 ROE 稳定性显示为 Delta
        roe_delta = None
        if isinstance(s['_prev_roe'], (int, float)):
            roe_delta = f"Ref Last Year: {s['_prev_roe']}%"
        g1.metric("ROE ( Profitability)", f"{s['ROE%']}%", delta=roe_delta)
        g2.metric("PEG ( Valuation )", s['PEG'], delta="Value" if s['PEG'] < 0.7 else None)
        
        d_status = t['debt_healthy'] if s['Debt%'] < 40 else (t['debt_mid'] if s['Debt%'] < 100 else t['debt_high'])
        st.write(f"· Debt Audit: D/E Ratio `{s['Debt%']}%` — {d_status}")
        
        st.markdown("---")
        # 🎯 Issac 风控评级逻辑
        base_score = (1 if s['PEG'] < 0.7 else 0) + (1 if s['ROE%'] > 25 else 0) + (1 if s['_up_val'] > 15 else 0)
        
        if s['Price'] < s['_sl']:
            final_v = 1 # 强制 B (Hold)
            st.error(f"### {t['verdict_title']}：{t['verdicts'][final_v]} (Momentum Broken)")
            st.error("🚨 **Issac Risk Alert**: Below MA200. Strategy locked to Hold until trend recovers.")
        else:
            final_v = min(base_score + (1 if s['Price'] > s['MA200'] else 0), 3)
            st.success(f"### {t['verdict_title']}：{t['verdicts'][final_v]}")
            st.info(f"💡 {t['strategy_label']}：{t['strategies'][final_v]}")

# --- 5. 主逻辑流程 ---
if search_ticker:
    res = get_analysis(search_ticker)
    if res: render_report(res)
    else: st.error("Ticker not found.")

if 'batch_res' in st.session_state:
    st.divider()
    df = pd.DataFrame(st.session_state.batch_res)
    m_df = df[df["Match"]=="✅"][WHITE_LIST]
    if not m_df.empty:
        sel = st.selectbox("Select Stock:", m_df["Symbol"].tolist())
        target_s = df[df["Symbol"] == sel].iloc[0]
        render_report(target_s)
    st.dataframe(m_df, use_container_width=True, hide_index=True)

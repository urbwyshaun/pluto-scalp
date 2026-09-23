import streamlit as st
import pandas as pd, requests, urllib.parse
import plotly.graph_objects as go

st.set_page_config(page_title="Pluto SCALP PRO", layout="wide", initial_sidebar_state="collapsed")
st.title("🔱 Pluto SCALP PRO (RR 1:2+)")

PHONE = st.secrets.get("WHATSAPP_PHONE", "")
APIKEY = st.secrets.get("WHATSAPP_APIKEY", "")

def send_wa(m):
    try:
        url = f"https://api.callmebot.com/whatsapp.php?phone={PHONE}&text={urllib.parse.quote(m)}&apikey={APIKEY}"
        requests.get(url, timeout=8)
    except: pass

@st.cache_data(ttl=20)
def get_data():
    base = "https://data-api.binance.vision"
    m1 = requests.get(f"{base}/api/v3/klines?symbol=PAXGUSDT&interval=1m&limit=100", timeout=7).json()
    m15 = requests.get(f"{base}/api/v3/klines?symbol=PAXGUSDT&interval=15m&limit=80", timeout=7).json()
    h1 = requests.get(f"{base}/api/v3/klines?symbol=PAXGUSDT&interval=1h&limit=80", timeout=7).json()
    def to_df(d):
        df=pd.DataFrame(d, columns=['T','O','H','L','C','V','CT','QV','Tr','TB','TQ','I'])
        df['T']=pd.to_datetime(df['T'], unit='ms')
        df[['O','H','L','C']]=df[['O','H','L','C']].astype(float)
        return df
    return float(pd.DataFrame(m15)[4].astype(float).iloc[-1]), to_df(h1), to_df(m15), to_df(m1)

try:
    with st.spinner("Loading GOLD..."):
        price,h1,m15,m1 = get_data()
except:
    st.error("Slow net - tap retry")
    if st.button("🔄 Retry"): st.cache_data.clear(); st.rerun()
    st.stop()

# LEVELS
h_hi=float(h1['H'].max()); h_lo=float(h1['L'].min())
buy_tp=h_lo+(h_hi-h_lo)*0.618; sell_tp=h_hi-(h_hi-h_lo)*0.618
m_hi=float(m15['H'].tail(60).max()); m_lo=float(m15['L'].tail(60).min())
buy_e_low=m_lo+(m_hi-m_lo)*0.236; buy_e_high=m_lo+(m_hi-m_lo)*0.382
sell_e_low=m_lo+(m_hi-m_lo)*0.618; sell_e_high=m_lo+(m_hi-m_lo)*0.764

mode = st.radio("Mode", ["SCALP 1m (Fast)", "Swing 15m"], horizontal=True)
ref_df = m1 if "SCALP" in mode else m15

def calc_rr(entry, sl, tp, is_buy):
    if is_buy:
        return (tp-entry)/(entry-sl) if entry!=sl else 0
    else:
        return (entry-tp)/(sl-entry) if sl!=entry else 0

rr_buy = calc_rr(price, m_lo-1.5, buy_tp, True) if buy_e_low <= price <= buy_e_high else 0
rr_sell = calc_rr(price, m_hi+1.5, sell_tp, False) if sell_e_low <= price <= sell_e_high else 0

if price < buy_tp and buy_e_low <= price <= buy_e_high and rr_buy >= 2.0:
    sig="BUY"; sl=m_lo-1.5; tp=buy_tp; rr=rr_buy
elif price > sell_tp and sell_e_low <= price <= sell_e_high and rr_sell >= 2.0:
    sig="SELL"; sl=m_hi+1.5; tp=sell_tp; rr=rr_sell
else:
    sig="WAIT"; sl=0; tp=0; rr=0

c1,c2,c3=st.columns(3)
c1.metric("GOLD", f"${price:.2f}"); c2.metric("BUY TP", f"${buy_tp:.1f}"); c3.metric("SELL TP", f"${sell_tp:.1f}")

if sig=="BUY":
    st.success(f"🔥 BUY NOW @ ${price:.2f}\n\nSL ${sl:.2f} | TP ${tp:.2f} | RR 1:{rr:.1f} (MAX PROFIT)")
    st.audio("https://actions.google.com/sounds/v1/alarms/beep_short.ogg")
    send_wa(f"🔥 BUY Gold ${price:.2f} SL {sl:.2f} TP {tp:.2f} RR 1:{rr:.1f}")
    st.balloons()
    st.code(f"Deriv: BUY XAUUSD 0.01 lot\nSL {sl:.2f}\nTP {tp:.2f}\nRR 1:{rr:.1f}", language="text")
elif sig=="SELL":
    st.error(f"🔻 SELL NOW @ ${price:.2f}\n\nSL ${sl:.2f} | TP ${tp:.2f} | RR 1:{rr:.1f} (MAX PROFIT)")
    st.audio("https://actions.google.com/sounds/v1/alarms/beep_short.ogg")
    send_wa(f"🔻 SELL Gold ${price:.2f} SL {sl:.2f} TP {tp:.2f} RR 1:{rr:.1f}")
    st.code(f"Deriv: SELL XAUUSD 0.01 lot\nSL {sl:.2f}\nTP {tp:.2f}\nRR 1:{rr:.1f}", language="text")
else:
    st.info(f"⏳ WAIT - RR < 1:2 filtered out\nPrice ${price:.2f}\nBUY {buy_e_low:.1f}-{buy_e_high:.1f} (RR {rr_buy:.1f})\nSELL {sell_e_low:.1f}-{sell_e_high:.1f} (RR {rr_sell:.1f})")

fig=go.Figure(data=[go.Candlestick(x=ref_df['T'], open=ref_df['O'], high=ref_df['H'], low=ref_df['L'], close=ref_df['C'])])
fig.add_hline(y=buy_tp, line_color="green", line_dash="dash"); fig.add_hline(y=sell_tp, line_color="red", line_dash="dash")
fig.add_hrect(y0=buy_e_low, y1=buy_e_high, fillcolor="green", opacity=0.3)
fig.add_hrect(y0=sell_e_low, y1=sell_e_high, fillcolor="red", opacity=0.15)
fig.update_layout(height=420, xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(l=0,r=0,t=5,b=0))
st.plotly_chart(fig, use_container_width=True)

col1,col2=st.columns(2)
with col1:
    if st.button("🔄 Refresh (3 sec)", use_container_width=True):
        st.cache_data.clear(); st.rerun()
with col2:
    if st.button("📲 Test WhatsApp", use_container_width=True):
        send_wa(f"✅ Pluto SCALP TEST OK Gold ${price:.2f} RR {rr:.1f}")
        st.success("Sent!")

st.markdown("<script>setTimeout(()=>{window.location.reload()}, 30000);</script>", unsafe_allow_html=True)

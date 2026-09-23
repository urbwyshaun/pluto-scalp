import streamlit as st
import pandas as pd, requests, urllib.parse
import plotly.graph_objects as go
from datetime import datetime
import pytz

st.set_page_config(page_title="Pluto SCALP ULTRA", layout="wide", initial_sidebar_state="collapsed")
st.title("🔱 Pluto ULTRA - All in One")

PHONE = st.secrets.get("WHATSAPP_PHONE", "")
APIKEY = st.secrets.get("WHATSAPP_APIKEY", "")

def send_wa(m):
    try:
        url = f"https://api.callmebot.com/whatsapp.php?phone={PHONE}&text={urllib.parse.quote(m)}&apikey={APIKEY}"
        requests.get(url, timeout=8)
    except: pass

# --- SETTINGS (MOBILE) ---
st.sidebar.header("💰 Your Account")
balance = st.sidebar.number_input("Balance $", value=50.0, step=5.0)
risk_pct = st.sidebar.slider("Risk % per trade", 1.0, 5.0, 2.0)

# --- TIME SESSION FILTER (SAST) ---
sast = pytz.timezone('Africa/Johannesburg')
now_sast = datetime.now(sast)
hour = now_sast.hour
is_london = 10 <= hour <= 18
is_ny = 15 <= hour <= 23
is_active = is_london or is_ny

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
    with st.spinner("Loading..."):
        price,h1,m15,m1 = get_data()
except:
    st.error("Slow net"); 
    if st.button("🔄 Retry"): st.cache_data.clear(); st.rerun()
    st.stop()

h_hi=float(h1['H'].max()); h_lo=float(h1['L'].min())
buy_tp=h_lo+(h_hi-h_lo)*0.618; sell_tp=h_hi-(h_hi-h_lo)*0.618
m_hi=float(m15['H'].tail(60).max()); m_lo=float(m15['L'].tail(60).min())
buy_e_low=m_lo+(m_hi-m_lo)*0.236; buy_e_high=m_lo+(m_hi-m_lo)*0.382
sell_e_low=m_lo+(m_hi-m_lo)*0.618; sell_e_high=m_lo+(m_hi-m_lo)*0.764

mode = st.radio("Mode", ["SCALP 1m", "Swing 15m"], horizontal=True)
ref_df = m1 if "SCALP" in mode else m15

def calc_rr(entry, sl, tp, is_buy):
    return (tp-entry)/(entry-sl) if is_buy and entry!=sl else (entry-tp)/(sl-entry) if sl!=entry else 0

rr_buy = calc_rr(price, m_lo-1.5, buy_tp, True) if buy_e_low <= price <= buy_e_high else 0
rr_sell = calc_rr(price, m_hi+1.5, sell_tp, False) if sell_e_low <= price <= sell_e_high else 0

if price < buy_tp and buy_e_low <= price <= buy_e_high and rr_buy >= 2.0:
    sig="BUY"; sl=m_lo-1.5; tp=buy_tp; rr=rr_buy
elif price > sell_tp and sell_e_low <= price <= sell_e_high and rr_sell >= 2.0:
    sig="SELL"; sl=m_hi+1.5; tp=sell_tp; rr=rr_sell
else:
    sig="WAIT"; sl=0; tp=0; rr=0

# --- LOT CALC ---
sl_dist = abs(price - sl) if sig!="WAIT" else 1.5
risk_money = balance * (risk_pct/100)
# For Gold: 0.01 lot = $0.10 per $0.10 move = $1 per $1 move. So lot = risk / distance
lot_raw = risk_money / sl_dist / 100 if sl_dist>0 else 0.01
lot = max(0.01, round(lot_raw, 2))

c1,c2,c3=st.columns(3)
c1.metric("GOLD", f"${price:.2f}"); c2.metric("Session", f"{'ACTIVE ✅' if is_active else 'SLEEPING 💤'}"); c3.metric("Time SAST", now_sast.strftime("%H:%M"))

if not is_active:
    st.warning(f"⏸️ MARKET SLEEPING ({now_sast.strftime('%H:%M')} SAST) - London 10-18h, NY 15-23h SAST is best. Skip trades now to protect ${balance}.")

if sig=="BUY" and is_active:
    st.success(f"🔥 BUY NOW @ ${price:.2f} | RR 1:{rr:.1f} | LOT {lot}")
    st.code(f"Balance ${balance} | Risk {risk_pct}% = ${risk_money:.2f}\nBUY XAUUSD {lot} lot\nSL {sl:.2f}\nTP {tp:.2f}\nDistance ${sl_dist:.2f}", language="text")
    st.audio("https://actions.google.com/sounds/v1/alarms/beep_short.ogg")
    send_wa(f"🔥 BUY Gold ${price:.2f} Lot {lot} SL {sl:.2f} TP {tp:.2f} RR 1:{rr:.1f}")
    st.balloons()
    # One-tap copy helper
    deriv_text = f"XAUUSD BUY {lot} SL {sl:.2f} TP {tp:.2f}"
    st.markdown(f"""<button onclick="navigator.clipboard.writeText('{deriv_text}')" style="width:100%;padding:15px;background:#00ff88;color:black;border-radius:10px;font-weight:bold;font-size:16px;">📋 1-TAP COPY FOR DERIV</button>""", unsafe_allow_html=True)
    st.link_button("🚀 OPEN DERIV MT5", "https://mt5.deriv.com/", use_container_width=True)

elif sig=="SELL" and is_active:
    st.error(f"🔻 SELL NOW @ ${price:.2f} | RR 1:{rr:.1f} | LOT {lot}")
    st.code(f"Balance ${balance} | Risk {risk_pct}% = ${risk_money:.2f}\nSELL XAUUSD {lot} lot\nSL {sl:.2f}\nTP {tp:.2f}\nDistance ${sl_dist:.2f}", language="text")
    st.audio("https://actions.google.com/sounds/v1/alarms/beep_short.ogg")
    send_wa(f"🔻 SELL Gold ${price:.2f} Lot {lot} SL {sl:.2f} TP {tp:.2f} RR 1:{rr:.1f}")
    deriv_text = f"XAUUSD SELL {lot} SL {sl:.2f} TP {tp:.2f}"
    st.markdown(f"""<button onclick="navigator.clipboard.writeText('{deriv_text}')" style="width:100%;padding:15px;background:#ff4444;color:white;border-radius:10px;font-weight:bold;font-size:16px;">📋 1-TAP COPY FOR DERIV</button>""", unsafe_allow_html=True)
    st.link_button("🚀 OPEN DERIV MT5", "https://mt5.deriv.com/", use_container_width=True)
else:
    st.info(f"⏳ WAIT - Price ${price:.2f}\nBUY zone {buy_e_low:.1f}-{buy_e_high:.1f} (RR {rr_buy:.1f})\nSELL zone {sell_e_low:.1f}-{sell_e_high:.1f} (RR {rr_sell:.1f})\nSuggested Lot if trade comes: {lot} (Risk ${risk_money:.2f})")

fig=go.Figure(data=[go.Candlestick(x=ref_df['T'], open=ref_df['O'], high=ref_df['H'], low=ref_df['L'], close=ref_df['C'])])
fig.add_hline(y=buy_tp, line_color="green", line_dash="dash"); fig.add_hline(y=sell_tp, line_color="red", line_dash="dash")
fig.add_hrect(y0=buy_e_low, y1=buy_e_high, fillcolor="green", opacity=0.3)
fig.add_hrect(y0=sell_e_low, y1=sell_e_high, fillcolor="red", opacity=0.15)
fig.update_layout(height=380, xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(l=0,r=0,t=5,b=0))
st.plotly_chart(fig, use_container_width=True)

col1,col2=st.columns(2)
with col1:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear(); st.rerun()
with col2:
    if st.button("📲 Test WhatsApp", use_container_width=True):
        send_wa(f"✅ Pluto ULTRA OK Gold ${price:.2f} Bal ${balance} Lot {lot}")
        st.success("Sent!")

st.markdown("<script>setTimeout(()=>{window.location.reload()}, 30000);</script>", unsafe_allow_html=True)

import streamlit as st
from basic_bot import BasicBot
import pandas as pd
import time


# Streamlit Config

st.set_page_config(
    page_title="Binance Futures Testnet Bot",
    page_icon="💹",
    layout="wide"
)

st.title("💹 Binance Futures Testnet Control Panel")


# API Credentials (from .streamlit/secrets.toml)

try:
    API_KEY = st.secrets = "   "
    API_SECRET = st.secrets ="  " 
except Exception:
    st.error("❌ Missing API credentials in .streamlit/secrets.toml")
    st.stop()

bot = BasicBot(API_KEY, API_SECRET, base_url="https://testnet.binancefuture.com")


# Helper functions


def get_balance():
    try:
        balances = bot._signed_request("GET", "/fapi/v2/balance")
        df = pd.DataFrame(balances)
        df = df[["asset", "balance", "availableBalance"]]
        df["balance"] = df["balance"].astype(float).round(2)
        df["availableBalance"] = df["availableBalance"].astype(float).round(2)
        return df
    except Exception as e:
        st.error(f"Error fetching balance: {e}")
        return pd.DataFrame()

def get_positions():
    try:
        positions = bot._signed_request("GET", "/fapi/v2/positionRisk")
        df = pd.DataFrame(positions)
        df = df[df["positionAmt"].astype(float) != 0.0]  # show only open positions
        if df.empty:
            return pd.DataFrame()
        df = df[["symbol", "positionSide", "positionAmt", "entryPrice", "unRealizedProfit", "leverage"]]
        df["positionAmt"] = df["positionAmt"].astype(float).round(4)
        df["entryPrice"] = df["entryPrice"].astype(float).round(2)
        df["unRealizedProfit"] = df["unRealizedProfit"].astype(float).round(2)
        return df
    except Exception as e:
        st.error(f"Error fetching positions: {e}")
        return pd.DataFrame()

def get_order_history(limit=10):
    try:
        orders = bot._signed_request("GET", "/fapi/v1/allOrders", payload={"symbol": "BTCUSDT", "limit": limit})
        df = pd.DataFrame(orders)
        if df.empty:
            return pd.DataFrame()
        df = df[["symbol", "side", "type", "status", "origQty", "executedQty", "price", "avgPrice", "updateTime"]]
        df["updateTime"] = pd.to_datetime(df["updateTime"], unit="ms")
        df = df.sort_values("updateTime", ascending=False)
        return df
    except Exception as e:
        st.error(f"Error fetching order history: {e}")
        return pd.DataFrame()


# Sidebar (Order Form)

st.sidebar.header("📊 Place an Order")

symbol = st.sidebar.text_input("Symbol", "BTCUSDT").upper()
side = st.sidebar.selectbox("Side", ["BUY", "SELL"])
order_type = st.sidebar.selectbox("Order Type", ["MARKET", "LIMIT"])
quantity = st.sidebar.number_input("Quantity", min_value=0.001, step=0.001)

price = None
if order_type == "LIMIT":
    price = st.sidebar.number_input("Limit Price", min_value=0.0, step=100.0)

if st.sidebar.button("🚀 Place Order"):
    with st.spinner("Placing order..."):
        try:
            resp = bot.place_order(symbol, side, order_type, quantity, price)
            st.sidebar.success("✅ Order placed successfully!")
            st.sidebar.json(resp)
        except Exception as e:
            st.sidebar.error(f"❌ {e}")


# Dashboard Layout

col1, col2, col3 = st.columns([1, 2, 2])

with col1:
    st.subheader("💰 Balance")
    balance_df = get_balance()
    if not balance_df.empty:
        st.dataframe(balance_df, use_container_width=True)
    else:
        st.info("No balance data found")

with col2:
    st.subheader("📈 Open Positions")
    pos_df = get_positions()
    if not pos_df.empty:
        st.dataframe(pos_df, use_container_width=True)
    else:
        st.info("No open positions")

with col3:
    st.subheader("🧾 Order History (Last 10)")
    orders_df = get_order_history()
    if not orders_df.empty:
        st.dataframe(orders_df, use_container_width=True)
    else:
        st.info("No recent orders")


# Auto-refresh option

st.markdown("---")
refresh_rate = st.slider("🔄 Auto-refresh (seconds)", 0, 60, 10)
if refresh_rate > 0:
    st.info(f"Auto-refreshing every {refresh_rate} seconds...")
    time.sleep(refresh_rate)
    st.rerun()

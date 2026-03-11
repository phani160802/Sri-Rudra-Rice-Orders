import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import urllib.parse
import pandas as pd

st.set_page_config(page_title="Sri Rudra Rice Order Form", layout="wide")

# -----------------------------
# Custom UI Styling
# -----------------------------
st.markdown("""
<style>

header {visibility: hidden;}
[data-testid="stToolbar"] {display:none;}

.stApp {
    background: linear-gradient(135deg,#f9f6e7,#DDC57A);
}

.block-container{
    max-width:1000px;
    padding-top:0.5rem;
    padding-bottom:0rem;
}

h1{
    text-align:center;
    color:#8B6F2F;
}

h3{
    text-align:center;
    color:#6B5B2A;
}

/* Footer styling */
.footer{
    width:100vw;
    margin-left:-50vw;
    left:50%;
    position:relative;
    text-align:center;
    padding:16px;
    margin-top:30px;
    background:#E7D283;
    font-size:14px;
    color:#4A3F1C;
}

div[data-testid="stForm"]{
    background:white;
    padding:20px;
    border-radius:15px;
    box-shadow:0px 5px 25px rgba(0,0,0,0.08);
}

/* Widget labels */
label, div[data-testid="stForm"] label, div[data-testid="stWidgetLabel"]{
    font-weight: bold !important;
    color:#2b2b2b !important;
}

/* Selectbox text color */
div[data-baseweb="select"] input[type="text"] {
    color: #000000 !important;
}

/* ---------------- MOBILE STYLE ---------------- */

@media (max-width:768px){

    h3, h2 {
        font-size:22px !important;
        font-weight:bold !important;
    }

    body, label, span, p {
        color:#2b2b2b !important;
    }

    .block-container{
        padding-left:12px !important;
        padding-right:12px !important;
    }

    h1{
        font-size:26px !important;
        text-align:center !important;
    }

    h3{
        font-size:18px !important;
        text-align:center !important;
    }

    img{
        max-width:150px !important;
        margin-left:120px !important;
    }

    /* METRIC VALUES */
    div[data-testid="stMetricValue"]{
        font-size:26px !important;
        color:#000000 !important;
        font-weight:normal !important;
    }

    /* METRIC LABELS */
    div[data-testid="stMetricLabel"]{
        font-size:20px !important;
        font-weight:bold !important;
        color:#2b2b2b !important;
    }

    /* Keep metrics side-by-side */
    div[data-testid="stHorizontalBlock"]{
        display:flex !important;
        flex-direction:row !important;
        gap:10px;
    }

    div[data-testid="stHorizontalBlock"] > div{
        flex:1 !important;
    }

    div[data-testid="stFormSubmitButton"] button{
        background-color:#8B6F2F !important;
        color:white !important;
        border:none !important;
        border-radius:8px !important;
        width:100%;
        margin-top:8px;
    }

    div.stButton > button{
        background-color:#8B6F2F !important;
        color:white !important;
        border:none !important;
        border-radius:8px !important;
        width:100%;
        margin-top:8px;
    }

}

/* Logo centering */
[data-testid="stImage"] {
    text-align:center !important;
    display:block !important;
    margin-left:auto !important;
    margin-right:auto !important;
}

[data-testid="stImage"] img {
    display:block !important;
    margin-left:auto !important;
    margin-right:auto !important;
}

/* Header styling */
.brand-title{
    color:#8B6F2F;
    font-size:42px !important;
    font-weight:bold;
    text-align:center;
    margin-left:6%;
    margin-bottom:0px;
}

.brand-subtitle{
    color:#6B5B2A;
    font-size:20px !important;
    text-align:center;
    margin-top:0px;
    margin-bottom:20px;
}

@media (max-width:768px){
    .brand-title{
        margin-left:0% !important;
    }
}

</style>
""", unsafe_allow_html=True)

# -----------------------------
# Rice varieties
# -----------------------------
rice_varieties = ["HMT","BPT","JSR","Broken","RNR","KNM","Other"]

# -----------------------------
# Google Sheets Connection
# -----------------------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=scope
)

client = gspread.authorize(creds)

spreadsheet = client.open_by_key("1dA4A8nbdwS_wcKVb3dA5ofqDlACw07SL3i0mtPYSo0Q")

items_sheet = spreadsheet.worksheet("Order_Items")
summary_sheet = spreadsheet.worksheet("Orders_Summary")

# -----------------------------
# Load shops
# -----------------------------
@st.cache_data(ttl=100)
def load_shops():
    records = items_sheet.get_all_records()
    shop_phone = {}
    shop_agent = {}
    for r in records:
        shop = str(r.get("Shop Name","")).strip()
        if shop != "":
            shop_phone[shop] = str(r.get("Phone",""))
            shop_agent[shop] = str(r.get("Agent Name",""))
    return shop_phone, shop_agent

shop_phone, shop_agent = load_shops()
existing_shops = sorted(shop_phone.keys())

# -----------------------------
# Session state
# -----------------------------
if "rice_items" not in st.session_state:
    st.session_state.rice_items = 2

# -----------------------------
# Logo
# -----------------------------
col1, col2, col3 = st.columns([1.2,1,1])
with col2:
    st.image("logo.PNG", width=200)

st.markdown("""
<div>
<div class="brand-title">Sri Rudra Rice 🌾</div>
<div class="brand-subtitle">Rice Order Management Portal</div>
</div>
""", unsafe_allow_html=True)

st.markdown("----")

# -----------------------------
# Navigation
# -----------------------------
page = st.radio(
"Select Page",
["📦 Order Booking","📊 Order Status"],
horizontal=True
)

# =====================================================
# ORDER STATUS DASHBOARD
# =====================================================

if page == "📊 Order Status":

    st.markdown("### 📊 Orders Dashboard")

    records = items_sheet.get_all_records()
    df = pd.DataFrame(records)

    if df.empty:
        st.info("No orders found")
        st.stop()

    grouped = df.groupby("Order ID")

    orders = []

    for order_id, group in grouped:

        shop = group["Shop Name"].iloc[0]
        total_qty = group["Quantity (Quintal)"].sum()

        varieties_list = []
        for i, row in group.iterrows():
            qty = float(row["Quantity (Quintal)"])
            varieties_list.append(f"{row['Variety']} – {qty:g}Q")

        varieties = ", ".join(varieties_list)

        status_values = group["STATUS"].astype(str).str.strip().replace("None", "")
        status_values = status_values[status_values != ""]

        status = "Order Accepted" if len(status_values) == 0 else status_values.iloc[0]

        orders.append({
            "Order ID": str(order_id),
            "Shop": shop,
            "Total Qty": total_qty,
            "Varieties": varieties,
            "STATUS": status
        })

    orders_df = pd.DataFrame(orders)

    pending_orders = orders_df[orders_df["STATUS"] != "Delivered"].shape[0]
    completed_orders = orders_df[orders_df["STATUS"] == "Delivered"].shape[0]

    col1, col2 = st.columns(2)

    col1.metric("Total Pending Orders", pending_orders)
    col2.metric("Total Completed Orders", completed_orders)

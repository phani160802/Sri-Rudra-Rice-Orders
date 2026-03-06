import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import urllib.parse

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

/* ---------------------------
   ALL WIDGET LABELS & PLACEHOLDER TEXT BLACK
   --------------------------- */
label, div[data-testid="stForm"] label, div[data-testid="stWidgetLabel"]{
    color:#2b2b2b !important;
}

div[data-baseweb="select"] input{
    color:#2b2b2b !important;
}

@media (max-width:768px){

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

    [data-testid="stMetricValue"]{
        color:#000000 !important;
        font-size:20px !important;
    }
    
    [data-testid="stMetricLabel"]{
        color:#2b2b2b !important;
    }

    div[data-testid="stFormSubmitButton"] button{
        background-color:#8B6F2F !important;
        color:white !important;
        border:none !important;
        border-radius:8px !important;
        width:100%;
        margin-top:8px;
    }

    div[data-testid="stFormSubmitButton"] button p{
        color:white !important;
    }

    div.stButton > button{
        background-color:#8B6F2F !important;
        color:white !important;
        border:none !important;
        border-radius:8px !important;
        width:100%;
        margin-top:8px;
    }

    div.stButton > button p{
        color:white !important;
    }
}

/* Logo centering */
[data-testid="stImage"] {
    text-align: center !important;
    display: block !important;
    margin-left: auto !important;
    margin-right: auto !important;
}

[data-testid="stImage"] img {
    display:block !important;
    margin-left:auto !important;
    margin-right:auto !important;
}

/* Force the headers to center relative to the whole page */
.main-header {
    text-align: center;
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
}

/* Header text styling */
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

/* Mobile fix */
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
@st.cache_data
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

# Header Text
st.markdown("""
<div>
    <div class="brand-title">Sri Rudra Rice 🌾</div>
    <div class="brand-subtitle">Rice Order Management Portal</div>
</div>
""", unsafe_allow_html=True)


st.markdown("----")

# -----------------------------
# Shop Details
# -----------------------------
st.markdown("### 🏪 Shop Details")

col1, col2, col3 = st.columns(3)
with col1:
    shop_name = st.selectbox(
        "Shop Name",
        options=existing_shops,
        index=None,
        placeholder="Type shop name...",
        accept_new_options=True,
        key="shop_name"
    )

if shop_name in shop_phone:
    st.session_state.contact_number = shop_phone.get(shop_name,"")
    st.session_state.agent_name = shop_agent.get(shop_name,"")

with col2:
    contact_number = st.text_input("Contact Number", key="contact_number")
with col3:
    agent_name = st.text_input("Agent Name", key="agent_name")

st.markdown("---")

# -----------------------------
# Order Form
# -----------------------------
with st.form("order_form"):

    st.markdown("### 🌾 Rice Varieties")
    grand_total = 0
    order_details = []

    for i in range(st.session_state.rice_items):
        st.markdown(f"#### Item {i+1}")
        col1, col2, col3 = st.columns([3,2,2])
        with col1:
            variety = st.selectbox("Rice Variety", options=rice_varieties, key=f"variety_{i}")
            if variety=="Other":
                variety = st.text_input("Enter Rice Variety", key=f"custom_variety_{i}")
        with col2:
            quantity = st.number_input("Quantity (Quintals)", min_value=0.0, step=0.5, key=f"qty_{i}")
        with col3:
            price = st.number_input("Price per Quintal (₹)", min_value=0.0, step=100.0, key=f"price_{i}")
        item_total = quantity * price
        grand_total += item_total
        order_details.append({"variety":variety,"quantity":quantity,"price":price,"total":item_total})
        st.write(f"Item Total: ₹ {item_total:,.2f}")
        st.markdown("---")

    st.markdown("## 💰 Order Summary")
    col1, col2 = st.columns(2)
    with col1:
        valid_items_count = len([i for i in order_details if i["quantity"]>0])
        st.metric("Total Items", valid_items_count)
    with col2:
        st.metric("Grand Total ₹", f"{grand_total:,.2f}")
    st.markdown("---")

    add_more = st.form_submit_button("➕ Add Another Rice Variety")
    col1, col2, col3 = st.columns([1.9,2,1])
    with col2:
        submit_button = st.form_submit_button("Submit Order")

# -----------------------------
# Add more rice slots
# -----------------------------
if add_more:
    st.session_state.rice_items += 1
    st.rerun()

# -----------------------------
# Submit order
# -----------------------------
if submit_button:
    valid_items = [i for i in order_details if i["quantity"]>0]
    if shop_name=="" or contact_number=="" or not valid_items:
        st.warning("Please complete all required fields.")
        st.stop()
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        last = items_sheet.col_values(2)[1:]
        order_id = str(int(last[-1])+1) if last else "1"
    except:
        order_id="1"
    for item in valid_items:
        items_sheet.append_row([today, order_id, shop_name, contact_number, agent_name,
                                item["variety"], item["quantity"], item["price"], item["total"]],
                                value_input_option="USER_ENTERED")
    total_quantity = sum(i["quantity"] for i in valid_items)
    summary_sheet.append_row([today, order_id, shop_name, agent_name, total_quantity, grand_total],
                             value_input_option="USER_ENTERED")
    # WhatsApp confirmation
    phone = "".join(filter(str.isdigit,contact_number))
    if len(phone)==10:
        phone="91"+phone
    lines = [f"Hi {shop_name} 👋","Order Confirmed ✅","Order Details:"]
    for item in valid_items:
        total = item["quantity"]*item["price"]
        lines.append(f"{item['variety']} : {item['quantity']} QTL x ₹{item['price']} = ₹{total:,.0f}")
    lines.append(f"Grand Total : ₹{grand_total:,.0f}")
    lines.append("Thank you, Sri Rudra Rice 🌾")
    msg = urllib.parse.quote("\n".join(lines))
    wa_link = f"https://wa.me/{phone}?text={msg}"
    st.success(f"✅ Order Confirmed | Order ID : {order_id}")
    st.markdown(f"[📱 Send WhatsApp Confirmation]({wa_link})")

# -----------------------------
# New Order
# -----------------------------
if st.button("➕ New Order"):
    st.session_state.rice_items = 2
    for k in list(st.session_state.keys()):
        if k.startswith(("qty_","price_","variety_","custom_variety_")):
            del st.session_state[k]
    st.rerun()

# -----------------------------
# Footer
# -----------------------------
st.markdown("""
<div class="footer">
Sri Lakshmi Venkateswara Rice Industries, Erraguntapalli, Chintalapudi(M), Andhra Pradesh, India
</div>
""", unsafe_allow_html=True)


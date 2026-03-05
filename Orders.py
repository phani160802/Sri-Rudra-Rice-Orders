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

/* Remove streamlit header */
header {visibility: hidden;}
[data-testid="stToolbar"] {display: none;}
[data-testid="stDecoration"] {display: none;}

/* Remove extra container padding */
.block-container{
    padding-top:2rem !important;
    padding-bottom:0rem !important;
}

/* Background */
.stApp {
    background: linear-gradient(135deg,#f9f6e7,#DDC57A);
}

/* Main container */
.main .block-container{
    max-width:1000px;
    padding-top:0.1rem;
    padding-bottom:0rem;
}

/* Form card */
div[data-testid="stForm"]{
    background:white;
    padding:20px;
    border-radius:15px;
    box-shadow:0px 5px 25px rgba(0,0,0,0.08);
}

/* Main title */
h1{
    text-align:center;
    color:#8B6F2F;
    margin-top:0px;
}

/* Subheaders */
h3{
    text-align:left;
    color:#6B5B2A;
}

/* Inputs */
.stTextInput input,
.stNumberInput input,
.stSelectbox div{
    border-radius:8px;
}

/* Buttons */
.stButton>button,
.stFormSubmitButton>button{
    background:#C9AE5D;
    color:black;
    border:none;
    border-radius:8px;
    height:44px;
    font-weight:600;
}

/* Button hover */
.stButton>button:hover,
.stFormSubmitButton>button:hover{
    background:#B89C4C;
    color:black;
}

/* Move submit button slightly right */
div[data-testid="stForm"] .stFormSubmitButton{
    display:flex;
    justify-content:center;
    margin-left:120px;
}

/* Footer */
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

/* Remove streamlit footer */
footer {visibility:hidden;}

/* ----------------------------- */
/* MOBILE FIXES */
/* ----------------------------- */

@media (max-width:768px){

    /* Fix white text issue */
    body, label, span, p, div {
        color:#2b2b2b !important;
    }

    /* Reduce side padding */
    .block-container{
        padding-left:12px !important;
        padding-right:12px !important;
    }

    /* Mobile titles */
    h1{
        font-size:26px !important;
    }

    h3{
        font-size:18px !important;
    }

    /* Smaller logo */
    img{
        max-width:150px !important;
        margin-left: 100px;
    }

}

</style>
""", unsafe_allow_html=True)

# -----------------------------
# Rice Varieties
# -----------------------------
rice_varieties = ["HMT", "BPT", "JSR", "Broken", "Other"]

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
# Session State
# -----------------------------
if "rice_items" not in st.session_state:
    st.session_state.rice_items = 2

# -----------------------------
# Logo
# -----------------------------
st.markdown("<div style='padding-top:20px'></div>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1.9,2,1])

with col2:
    st.image("logo.PNG", width=200)

# -----------------------------
# Title
# -----------------------------
st.markdown(
"<h1 style='text-align:center;'>Sri Rudra Rice 🌾</h1>",
unsafe_allow_html=True
)

st.markdown(
"<h3 style='text-align:center;'>Rice Order Management Portal</h3>",
unsafe_allow_html=True
)

st.markdown("---")

# -----------------------------
# FORM
# -----------------------------
with st.form("order_form"):

    st.markdown("### 🏪 Shop Details")

    col1, col2 = st.columns(2)

    with col1:
        shop_name = st.text_input("Shop Name", key="shop_name")

    with col2:
        contact_number = st.text_input("Contact Number", key="contact_number")

    st.markdown("---")
    st.markdown("### 🌾 Rice Varieties")

    grand_total = 0
    order_details = []

    for i in range(st.session_state.rice_items):

        st.markdown(f"#### Item {i+1}")

        col1, col2, col3 = st.columns([3,2,2])

        with col1:
            variety = st.selectbox(
                "Rice Variety",
                options=rice_varieties,
                key=f"variety_{i}"
            )

            if variety == "Other":
                variety = st.text_input(
                    "Enter Rice Variety",
                    key=f"custom_variety_{i}"
                )

        with col2:
            quantity = st.number_input(
                "Quantity (Quintals)",
                min_value=0.0,
                step=0.5,
                key=f"qty_{i}"
            )

        with col3:
            price = st.number_input(
                "Price per Quintal (₹)",
                min_value=0.0,
                step=100.0,
                key=f"price_{i}"
            )

        item_total = quantity * price
        grand_total += item_total

        order_details.append({
            "variety": variety,
            "quantity": quantity,
            "price": price,
            "total": item_total
        })

        st.write(f"Item Total: ₹ {item_total:,.2f}")
        st.markdown("---")

    # -----------------------------
    # Order Summary
    # -----------------------------
    st.markdown("## 💰 Order Summary")

    col1, col2 = st.columns(2)

    with col1:
        valid_items_count = len([item for item in order_details if item["quantity"] > 0])
        st.metric("Total Items", valid_items_count)

    with col2:
        st.metric("Grand Total ₹", f"{grand_total:,.2f}")

    st.markdown("---")

    add_more = st.form_submit_button("➕ Add Another Rice Variety")

    col1,col2,col3 = st.columns([1,2,1])
    with col2:
        submit_button = st.form_submit_button("Submit Order")

# -----------------------------
# Add More Items
# -----------------------------
if add_more:
    st.session_state.rice_items += 1
    st.rerun()

# -----------------------------
# Submit Order
# -----------------------------
if submit_button:

    valid_items = [
        item for item in order_details
        if item["variety"] != "" and item["quantity"] > 0
    ]

    if shop_name == "" or contact_number == "" or not valid_items:
        st.warning("Please complete all required fields.")
        st.stop()

    today_date = datetime.now().strftime("%Y-%m-%d")

    try:
        last_order = items_sheet.col_values(2)[1:]
        order_id = str(int(last_order[-1]) + 1) if last_order else "1"
    except:
        order_id = "1"

    for item in valid_items:

        items_sheet.append_row([
            today_date,
            order_id,
            shop_name,
            contact_number,
            item["variety"],
            item["quantity"],
            item["price"],
            item["total"]
        ], value_input_option="USER_ENTERED")

    total_quantity = sum(item["quantity"] for item in valid_items)

    summary_sheet.append_row([
        today_date,
        order_id,
        shop_name,
        total_quantity,
        grand_total
    ], value_input_option="USER_ENTERED")

    # WhatsApp message
    phone = "".join(filter(str.isdigit, contact_number))

    if len(phone) == 10:
        phone = "91" + phone

    message_lines = [
        f"Hi {shop_name} 👋",
        "Order Confirmed ✅",
        "Order Details:"
    ]

    for item in valid_items:
        item_total = item['quantity'] * item['price']
        message_lines.append(
            f"{item['variety']}: {item['quantity']} QTL x ₹{item['price']:,.2f} = ₹{item_total:,.2f}"
        )

    message_lines.append(f"Grand Total: ₹ {grand_total:,.2f}")
    message_lines.append("Thank you, Sri Rudra Rice 🌾")

    message = "\n".join(message_lines)
    encoded_msg = urllib.parse.quote(message)

    whatsapp_link = f"https://wa.me/{phone}?text={encoded_msg}"

    st.success(
        f"✅ Order Confirmed! Order ID: {order_id} | Grand Total: ₹ {grand_total:,.2f}"
    )

    st.markdown(f"[📱 Open WhatsApp with Order]({whatsapp_link})")

# -----------------------------
# New Order
# -----------------------------
if st.button("➕ New Order"):

    st.session_state.rice_items = 2
    st.session_state["shop_name"] = ""
    st.session_state["contact_number"] = ""

    for i in range(10):
        st.session_state[f"variety_{i}"] = ""
        st.session_state[f"custom_variety_{i}"] = ""
        st.session_state[f"qty_{i}"] = 0.0
        st.session_state[f"price_{i}"] = 0.0

    st.rerun()

# -----------------------------
# Footer
# -----------------------------
st.markdown("""
<div class="footer">
Sri Lakshmi Venkateswara Rice Industries, Erraguntapalli, Chintalapudi(M), Andhra Pradesh, India
</div>
""", unsafe_allow_html=True)





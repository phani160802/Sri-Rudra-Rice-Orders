import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import urllib.parse
import pandas as pd

st.set_page_config(page_title="Sri Rudra Rice Order Form", layout="wide")

# -----------------------------
# Custom UI Styling (UNCHANGED)
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

label, div[data-testid="stForm"] label, div[data-testid="stWidgetLabel"]{
    font-weight: bold !important;
    color:#2b2b2b !important;
}

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

# -----------------------------
# Logo + Header (ORIGINAL)
# -----------------------------
col1, col2, col3 = st.columns([1.2, 1, 1])
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
horizontal=True,
index=0
)

# =====================================================
# ORDER BOOKING PAGE
# =====================================================
if page == "📦 Order Booking":

    if "rice_items" not in st.session_state:
        st.session_state.rice_items = 2

    st.markdown("### 🏪 Shop Details")

    col1, col2, col3 = st.columns(3)

    with col1:
        shop_name = st.text_input("Shop Name")

    with col2:
        contact_number = st.text_input("Contact Number")

    with col3:
        agent_name = st.text_input("Agent Name")

    st.markdown("---")

    with st.form("order_form"):

        st.markdown("### 🌾 Rice Varieties")

        grand_total = 0
        order_details = []

        for i in range(st.session_state.rice_items):

            st.markdown(f"#### Item {i+1}")

            col1, col2, col3 = st.columns([3,2,2])

            with col1:
                variety = st.selectbox("Rice Variety", rice_varieties, key=f"variety_{i}")
                if variety == "Other":
                    variety = st.text_input("Enter Rice Variety", key=f"custom_{i}")

            with col2:
                quantity = st.number_input("Quantity (Quintals)",min_value=0.0,step=0.5,key=f"qty_{i}")

            with col3:
                price = st.number_input("Price per Quintal (₹)",min_value=0.0,step=100.0,key=f"price_{i}")

            item_total = quantity * price
            grand_total += item_total

            order_details.append({
                "variety":variety,
                "quantity":quantity,
                "price":price,
                "total":item_total
            })

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

    if add_more:
        st.session_state.rice_items += 1
        st.rerun()

    if submit_button:

        valid_items = [i for i in order_details if i["quantity"]>0]

        if shop_name=="" or contact_number=="":
            st.warning("Please complete required fields")
            st.stop()

        today = datetime.now().strftime("%Y-%m-%d")

        try:
            last = items_sheet.col_values(2)[1:]
            order_id = str(int(last[-1])+1)
        except:
            order_id="1"

        for item in valid_items:

            items_sheet.append_row([
                today,
                order_id,
                shop_name,
                contact_number,
                agent_name,
                item["variety"],
                item["quantity"],
                item["price"],
                item["total"],
                "Order Accepted"
            ])

        st.success(f"✅ Order Confirmed | Order ID : {order_id}")


   
# =====================================================
# ORDER STATUS DASHBOARD
# =====================================================

else:

    st.markdown("### 📊 Orders Dashboard")

    records = items_sheet.get_all_records()
    df = pd.DataFrame(records)

    if df.empty:
        st.info("No orders found")
        st.stop()

    # -----------------------------
    # Group orders by Order ID
    # -----------------------------
    grouped = df.groupby("Order ID")

    orders = []

    for order_id, group in grouped:

        shop = group["Shop Name"].iloc[0]
        total_qty = group["Quantity (Quintal)"].sum()

        # Clean variety display
        varieties_list = []
        for i, row in group.iterrows():
            qty = float(row["Quantity (Quintal)"])
            varieties_list.append(f"{row['Variety']} – {qty:g}Q")

        varieties = ", ".join(varieties_list)

        # Clean status
        status_values = group["STATUS"].astype(str).str.strip().replace("None", "")
        status_values = status_values[status_values != ""]

        if len(status_values) == 0:
            status = "Order Accepted"
        else:
            status = status_values.iloc[0]

        orders.append({
            "Order ID": str(order_id),
            "Shop": shop,
            "Total Qty": total_qty,
            "Varieties": varieties,
            "STATUS": status
        })

    orders_df = pd.DataFrame(orders)

    # -----------------------------
    # Dashboard Metrics
    # -----------------------------
    pending_orders = orders_df[orders_df["STATUS"] != "Delivered"].shape[0]
    completed_orders = orders_df[orders_df["STATUS"] == "Delivered"].shape[0]

    col1, col2 = st.columns(2)

    col1.metric("Total Pending Orders", pending_orders)
    col2.metric("Total Completed Orders", completed_orders)

    st.markdown("---")

    st.markdown("### 📦 Update Order Status")

    # -----------------------------
    # Filter only NON-delivered orders
    # -----------------------------
    pending_orders_df = orders_df[orders_df["STATUS"] != "Delivered"].copy()

    # -----------------------------
    # Session State
    # -----------------------------
    if "orders_table" not in st.session_state:
        st.session_state.orders_table = pending_orders_df.copy()

    # -----------------------------
    # FORM (prevents rerun)
    # -----------------------------
    with st.form("status_update_form"):

        edited_df = st.data_editor(
            st.session_state.orders_table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "STATUS": st.column_config.SelectboxColumn(
                    "STATUS",
                    options=[
                        "Order Accepted",
                        "Packed",
                        "Out for Delivery",
                        "Delivered"
                    ],
                    required=True
                )
            },
            disabled=["Order ID", "Shop", "Total Qty", "Varieties"]
        )

        save_button = st.form_submit_button("Save Status Updates")

    # store edited table
    st.session_state.orders_table = edited_df

    # -----------------------------
    # SAVE STATUS TO GOOGLE SHEET
    # -----------------------------
    if save_button:

        updated_df = st.session_state.orders_table

        for i, row in updated_df.iterrows():

            order_id = row["Order ID"]
            new_status = row["STATUS"]

            matches = items_sheet.findall(order_id)

            for cell in matches:

                row_values = items_sheet.row_values(cell.row)

                if len(row_values) > 1 and row_values[1] == order_id:

                    items_sheet.update_cell(cell.row, 10, new_status)

        st.success("All statuses updated successfully")

        st.rerun()

# -----------------------------
# Footer
# -----------------------------
st.markdown("""
<div class="footer">
Sri Lakshmi Venkateswara Rice Industries, Erraguntapalli, Chintalapudi(M), Andhra Pradesh, India
</div>
""", unsafe_allow_html=True)

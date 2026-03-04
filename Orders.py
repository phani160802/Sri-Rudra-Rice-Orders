import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import urllib.parse

st.set_page_config(page_title="Sri Rudra Rice Mills Order Form", layout="wide")

# -----------------------------
# Predefined rice varieties
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
# Session State Initialization
# -----------------------------
if "rice_items" not in st.session_state:
    st.session_state.rice_items = 2

# -----------------------------
# Title
# -----------------------------
st.title("Sri Rudra Rice Mills 🌾")
st.subheader("Order Form")

# -----------------------------
# FORM
# -----------------------------
with st.form("order_form"):

    # Customer Details
    col1, col2 = st.columns(2)
    with col1:
        shop_name = st.text_input("Shop Name", key="shop_name")
    with col2:
        contact_number = st.text_input("Contact Number", key="contact_number")

    st.markdown("---")
    st.markdown("### Rice Varieties")

    grand_total = 0
    order_details = []

    # Loop over rice items
    for i in range(st.session_state.rice_items):
        st.markdown(f"#### Item {i+1}")
        col1, col2, col3 = st.columns([3, 2, 2])

        with col1:
            variety = st.selectbox("Rice Variety", options=rice_varieties, key=f"variety_{i}")
            if variety == "Other":
                variety = st.text_input("Enter Rice Variety", key=f"custom_variety_{i}")

        with col2:
            quantity = st.number_input("Quantity (Quintals)", min_value=0.0, step=0.5, key=f"qty_{i}")
        with col3:
            price = st.number_input("Price per Quintal (₹)", min_value=0.0, step=100.0, key=f"price_{i}")

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

    # Display Grand Total dynamically
    st.markdown("## 💰 Total Amount")
    st.info(f"Grand Total: ₹ {grand_total:,.2f}")

    # Form Buttons
    add_more = st.form_submit_button("➕ Add Another Rice Variety")
    submit_button = st.form_submit_button("Submit Order")

# -----------------------------
# Add Another Rice Variety
# -----------------------------
if add_more:
    st.session_state.rice_items += 1
    st.rerun()

# -----------------------------
# Submit Order + WhatsApp Link
# -----------------------------
if submit_button:

    # Validate input
    valid_items = [item for item in order_details if item["variety"] != "" and item["quantity"] > 0]
    if shop_name == "" or contact_number == "" or not valid_items:
        st.warning("Please complete all required fields.")
        st.stop()

    today_date = datetime.now().strftime("%Y-%m-%d")

    # Generate numeric Order ID
    try:
        last_order = items_sheet.col_values(2)[1:]
        order_id = str(int(last_order[-1]) + 1) if last_order else "1"
    except:
        order_id = "1"

    # Append items to Google Sheets
    if not items_sheet.row_values(1):
        items_sheet.append_row(["Date", "Order ID", "Shop Name", "Phone", "Variety", "Quantity", "Price", "Item Total"])

    for item in valid_items:
        items_sheet.append_row([
            today_date, order_id, shop_name, contact_number,
            item["variety"], item["quantity"], item["price"], item["total"]
        ], value_input_option="USER_ENTERED")

    # Append summary with Order ID
    total_quantity = sum(item["quantity"] for item in valid_items)
    if not summary_sheet.row_values(1):
        summary_sheet.append_row(["Date", "Order ID", "Shop Name", "Total Quantity(QTL)", "Grand Total"])

    summary_sheet.append_row([
        today_date, order_id, shop_name, total_quantity, grand_total
    ], value_input_option="USER_ENTERED")

    # -----------------------------
    # WhatsApp Redirect Link
    # -----------------------------
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
            f"{item['variety']}: {item['quantity']} quintal(s) x ₹{item['price']:,.2f} = ₹{item_total:,.2f}"
        )
    message_lines.append(f"Grand Total: ₹ {grand_total:,.2f}")
    message_lines.append("Thank you, Sri Rudra Rice Mills 🌾")

    message = "\n".join(message_lines)
    encoded_msg = urllib.parse.quote(message)
    whatsapp_link = f"https://wa.me/{phone}?text={encoded_msg}"

    st.success(f"✅ Order Confirmed! Order ID: {order_id} | Grand Total: ₹ {grand_total:,.2f}")

    # Direct link to open WhatsApp Web with message
    st.markdown(f"[📱 Open WhatsApp with Order]({whatsapp_link})", unsafe_allow_html=True)

# -----------------------------
# New Order button
# -----------------------------
if st.button("➕ New Order"):
    # Reset rice items
    st.session_state["rice_items"] = 2

    # Delete all input-related keys
    keys_to_delete = []
    for key in st.session_state.keys():
        if key.startswith("variety_") or key.startswith("custom_variety_") \
           or key.startswith("qty_") or key.startswith("price_") \
           or key in ["shop_name", "contact_number"]:
            keys_to_delete.append(key)
    for key in keys_to_delete:
        del st.session_state[key]

    # Rerun app to clear inputs
    st.rerun()
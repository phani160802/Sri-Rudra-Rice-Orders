import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import urllib.parse
import pandas as pd
import uuid

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(page_title="Sri Rudra Rice Order Form", layout="wide")

# =====================================================
# STYLING
# =====================================================
st.markdown("""
<style>
header {visibility: hidden;}
[data-testid="stToolbar"] {display:none;}

.stApp {
    background: linear-gradient(135deg,#f9f6e7,#DDC57A);
}
.block-container {
    max-width:1000px;
    padding-top:0rem;
    padding-bottom:0rem;
}
h1 { text-align:center; color:#8B6F2F; }
h3 { text-align:center; color:#6B5B2A; }

.footer {
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
div[data-testid="stForm"] {
    background:white;
    padding:20px;
    border-radius:15px;
    box-shadow:0px 5px 25px rgba(0,0,0,0.08);
}
label, div[data-testid="stForm"] label, div[data-testid="stWidgetLabel"]{
    font-weight: bold !important;
    color:#2b2b2b !important;
}

div[data-baseweb="select"] input[type="text"] {
    color: #000000 !important;
}
.brand-title {
    color:#8B6F2F;
    font-size:42px !important;
    font-weight:bold;
    text-align:center;
    margin-top:0px;
    margin-bottom:0px;
    line-height:1.1;
}
.brand-subtitle {
    color:#6B5B2A;
    font-size:20px !important;
    text-align:center;
    margin-top:4px;
    margin-bottom:4px;
}
.item-card {
    background:#fffdf3;
    border:1px solid #e0c96e;
    border-radius:10px;
    padding:12px 16px;
    margin-bottom:12px;
}
.status-badge {
    display:inline-block;
    padding:3px 10px;
    border-radius:12px;
    font-size:13px;
    font-weight:600;
}

/* Mobile */
@media (max-width:768px) {

    h3, h2 {
        font-size: 22px !important;
        font-weight: bold !important;
    }

    div[data-testid="stMarkdownContainer"] h3 {
        font-size: 22px !important;
        font-weight: bold !important;
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

    div[data-testid="stHorizontalBlock"]{
        display:flex !important;
        flex-direction:row !important;
    }

    div[data-testid="stHorizontalBlock"] > div{
        flex:1 !important;
    }

    [data-testid="stMetricLabel"]{
        font-size:20px !important;
        font-weight:bold !important;
        color:#2b2b2b !important;
    }

    div[data-testid="stMetricValue"]{
        font-size:24px !important;
        font-weight:normal !important;
        color:#000 !important;
    }

    div[role="listbox"] div[role="option"] {
        color: #2b2b2b !important;
        font-size: 16px !important;
        font-weight: normal !important;
        background-color: white !important;
    }

    .stDataFrameContainer div[data-baseweb="select"] div[class*="singleValue"] {
        color: #2b2b2b !important;
        font-weight: normal !important;
        font-size: 16px !important;
    }

    .stDataFrameContainer div[data-baseweb="select"] div[class*="option"] {
        color: #2b2b2b !important;
        font-weight: normal !important;
        font-size: 16px !important;
    }

    .stDataFrameContainer div[data-baseweb="select"] div[class*="menu"] {
        color: #2b2b2b !important;
        font-size: 16px !important;
        font-weight: normal !important;
    }

    .brand-title{
        margin-left:0% !important;
    }

    [data-testid="stImage"] img{
        max-width:150px !important;
        margin-left:110px !important;
        margin-right:0 !important;
    }
}

[data-testid="stImage"] img {
    display:block !important;
    margin-left:auto !important;
    margin-right:auto !important;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# CONSTANTS
# =====================================================
RICE_VARIETIES = ["HMT", "BPT", "JSR", "Broken", "RNR", "KNM", "Other"]
STATUS_OPTIONS = ["Order Accepted", "Packed", "Out for Delivery", "Partial Delivery", "Delivered"]
SHEET_KEY = "1dA4A8nbdwS_wcKVb3dA5ofqDlACw07SL3i0mtPYSo0Q"
ITEMS_SHEET = "Order_Items"
SUMMARY_SHEET = "Orders_Summary"
ITEMS_HEADERS = [
    "Date", "Order ID", "Shop Name", "Phone", "Agent Name",
    "Variety", "Quantity (Quintal)", "Price (₹/Quintal)", "Item Total",
    "Delivered Qty", "Pending Qty", "Delivery Date", "STATUS"
]

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def clean_number(value) -> float:
    """Safely parse a number from a cell value."""
    if value is None or value == "":
        return 0.0
    return float(str(value).replace("₹", "").replace(",", "").strip())


def generate_order_id(sheet) -> str:
    """
    Generate a collision-safe order ID by reading the latest value
    from the sheet at submission time, not cached.
    Falls back to a UUID fragment if the sheet is unreadable.
    """
    try:
        values = sheet.col_values(2)[1:]  # col B = Order ID
        existing = [int(v) for v in values if v.strip().isdigit()]
        return str(max(existing) + 1) if existing else "1"
    except Exception:
        return str(uuid.uuid4().int)[:8]


def build_whatsapp_link(contact: str, shop: str, items: list, grand_total: float) -> str:
    """Build a WhatsApp pre-filled message link."""
    phone = "".join(filter(str.isdigit, contact))
    if len(phone) == 10:
        phone = "91" + phone
    lines = [f"Hi {shop} 👋", "Order Confirmed ✅", "Order Details:"]
    for item in items:
        total = item["quantity"] * item["price"]
        lines.append(f"{item['variety']} : {item['quantity']} QTL x ₹{item['price']} = ₹{total:,.0f}")
    lines.append(f"Grand Total : ₹{grand_total:,.0f}")
    lines.append("Thank you, Sri Rudra Rice 🌾")
    return f"https://wa.me/{phone}?text={urllib.parse.quote(chr(10).join(lines))}"


def determine_order_status(status_values: list) -> str:
    """Derive the display status for an order from its line-item statuses."""
    statuses = [str(s).strip() for s in status_values]
    if all(s == "Delivered" for s in statuses):
        return "Delivered"
    elif any(s == "Partial Delivery" for s in statuses):
        return "Partial Delivery"
    elif any(s == "Out for Delivery" for s in statuses):
        return "Out for Delivery"
    elif any(s == "Packed" for s in statuses):
        return "Packed"
    return "Order Accepted"


def write_order_to_sheet(items_sheet, summary_sheet, order_id: str, shop: str,
                          contact: str, agent: str, valid_items: list, grand_total: float):
    """Append all line items + summary row for a new order."""
    today = datetime.now().strftime("%Y-%m-%d")
    rows = [
        [
            today, order_id, shop, contact, agent,
            item["variety"], item["quantity"], item["price"], item["total"],
            0, item["quantity"], "", "Order Accepted"
        ]
        for item in valid_items
    ]
    items_sheet.append_rows(rows, value_input_option="USER_ENTERED")
    summary_sheet.append_row(
        [today, order_id, shop, agent, sum(i["quantity"] for i in valid_items), grand_total],
        value_input_option="USER_ENTERED"
    )


def push_sheet_update(items_sheet, df_sheet: pd.DataFrame, headers: list):
    """Overwrite the sheet in-place from row 1 — no appends, no duplicates."""
    df_sheet = df_sheet.replace([float("inf"), -float("inf")], "").fillna("")
    df_sheet = df_sheet[headers]
    # Coerce all values to plain Python types so gspread doesn't choke
    rows = [[str(v) if v != "" else "" for v in row] for row in df_sheet.values.tolist()]
    items_sheet.update("A1", [headers] + rows, value_input_option="USER_ENTERED")


# =====================================================
# GOOGLE SHEETS CONNECTION
# =====================================================
@st.cache_resource
def get_sheets():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SHEET_KEY)
    return (
        spreadsheet.worksheet(ITEMS_SHEET),
        spreadsheet.worksheet(SUMMARY_SHEET)
    )

items_sheet, summary_sheet = get_sheets()


@st.cache_data(ttl=60)
def load_shops():
    """Load shop → phone/agent lookup from the sheet."""
    records = items_sheet.get_all_records()
    shop_phone, shop_agent = {}, {}
    for r in records:
        shop = str(r.get("Shop Name", "")).strip()
        if shop:
            shop_phone[shop] = str(r.get("Phone", ""))
            shop_agent[shop] = str(r.get("Agent Name", ""))
    return shop_phone, shop_agent


shop_phone, shop_agent = load_shops()
existing_shops = sorted(shop_phone.keys())

# =====================================================
# SESSION STATE DEFAULTS
# =====================================================
if "rice_items" not in st.session_state:
    st.session_state.rice_items = 2
if "last_order_id" not in st.session_state:
    st.session_state.last_order_id = None
if "last_wa_link" not in st.session_state:
    st.session_state.last_wa_link = None

# =====================================================
# HEADER
# =====================================================

# Logo alignment CSS (separate block, matching original)
st.markdown(
    """
    <style>
    /* Center the column containing the logo */
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) {
        display: flex !important;
        justify-content: center !important;
    }

    [data-testid="stImage"] {
        display: flex !important;
        justify-content: center !important;
    }

    [data-testid="stImage"] img {
        display: block !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }

    @media (max-width:768px){
        [data-testid="stImage"] img{
            max-width: 150px !important;
            margin-left: auto !important;
            margin-right: auto !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

col1, col2, col3 = st.columns([1.2, 1, 1])
with col2:
    st.image("logo.PNG", width=200)

st.markdown("""
<div style="text-align:center; margin-top:12px; margin-bottom:0px;">
    <div class="brand-title">Sri Rudra Rice 🌾</div>
    <div class="brand-subtitle">Rice Order Management Portal</div>
    <hr style="margin-top:10px; margin-bottom:0px; border:none; border-top:1px solid #c8b56e;">
</div>
""", unsafe_allow_html=True)

# =====================================================
# NAVIGATION
# =====================================================
page = st.radio(
    "Select Page",
    ["📦 Order Booking", "📊 Order Status", "🔍 Order History"],
    horizontal=True,
    index=0
)

# =====================================================
# PAGE: ORDER BOOKING
# =====================================================
if page == "📦 Order Booking":

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

    # Auto-fill known shop details
    if shop_name in shop_phone:
        st.session_state.contact_number = shop_phone.get(shop_name, "")
        st.session_state.agent_name = shop_agent.get(shop_name, "")

    with col2:
        contact_number = st.text_input("Contact Number", key="contact_number")
    with col3:
        agent_name = st.text_input("Agent Name", key="agent_name")

    st.markdown("---")

    # ── Live summary placeholders (rendered BEFORE the form) ──
    # ── Order Form ──────────────────────────────────
    with st.form("order_form"):
        st.markdown("### 🌾 Rice Varieties")
        grand_total = 0.0
        order_details = []

        for i in range(st.session_state.rice_items):
            with st.container():
                st.markdown(f'<div class="item-card">', unsafe_allow_html=True)
                st.markdown(f"**Item {i + 1}**")
                col1, col2, col3 = st.columns([3, 2, 2])
                with col1:
                    variety = st.selectbox("Rice Variety", options=RICE_VARIETIES, key=f"variety_{i}")
                    if variety == "Other":
                        variety = st.text_input("Enter Rice Variety", key=f"custom_variety_{i}")
                with col2:
                    quantity = st.number_input("Quantity (Quintals)", min_value=0.0, step=0.5, key=f"qty_{i}")
                with col3:
                    price = st.number_input("Price per Quintal (₹)", min_value=0.0, step=100.0, key=f"price_{i}")
                item_total = quantity * price
                grand_total += item_total
                order_details.append({"variety": variety, "quantity": quantity, "price": price, "total": item_total})
                if quantity > 0:
                    st.caption(f"Item Total: ₹ {item_total:,.2f}")
                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("## 💰 Order Summary")
        valid_count = len([i for i in order_details if i["quantity"] > 0])
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Items", valid_count)
        with col2:
            st.metric("Grand Total ₹", f"{grand_total:,.2f}")
        st.markdown("---")

        col_a, col_b, col_c = st.columns([1, 1, 1])
        with col_a:
            add_more = st.form_submit_button("➕ Add Item")
        with col_b:
            remove_one = st.form_submit_button("➖ Remove Last Item")
        with col_c:
            submit_button = st.form_submit_button("✅ Submit Order", type="primary")

    # ── Form action handlers ─────────────────────────
    if add_more:
        st.session_state.rice_items += 1
        st.rerun()

    if remove_one and st.session_state.rice_items > 1:
        last = st.session_state.rice_items - 1
        for key in [f"qty_{last}", f"price_{last}", f"variety_{last}", f"custom_variety_{last}"]:
            st.session_state.pop(key, None)
        st.session_state.rice_items -= 1
        st.rerun()

    if submit_button:
        valid_items = [i for i in order_details if i["quantity"] > 0]

        # Validation
        errors = []
        if not shop_name:
            errors.append("Shop Name is required.")
        if not contact_number:
            errors.append("Contact Number is required.")
        if not valid_items:
            errors.append("At least one rice item with quantity > 0 is required.")

        if errors:
            for e in errors:
                st.error(e)
            st.stop()

        # Submit
        order_id = generate_order_id(items_sheet)
        write_order_to_sheet(items_sheet, summary_sheet, order_id, shop_name,
                             contact_number, agent_name, valid_items, grand_total)

        # Invalidate shop cache so new shops appear
        load_shops.clear()

        st.session_state.last_order_id = order_id
        st.session_state.last_wa_link = build_whatsapp_link(contact_number, shop_name, valid_items, grand_total)

        st.success(f"✅ Order Confirmed | Order ID : {order_id}")
        st.markdown(f"[📱 Send WhatsApp Confirmation]({st.session_state.last_wa_link})")

    # Show previous success message if rerun happened
    elif st.session_state.last_order_id:
        st.success(f"✅ Last Order ID : {st.session_state.last_order_id}")
        if st.session_state.last_wa_link:
            st.markdown(f"[📱 Send WhatsApp Confirmation]({st.session_state.last_wa_link})")

    if st.button("➕ New Order"):
        st.session_state.rice_items = 2
        st.session_state.last_order_id = None
        st.session_state.last_wa_link = None
        for k in list(st.session_state.keys()):
            if k.startswith(("qty_", "price_", "variety_", "custom_variety_",
                             "shop_name", "contact_number", "agent_name")):
                st.session_state.pop(k, None)
        st.rerun()

# =====================================================
# PAGE: ORDER STATUS
# =====================================================
elif page == "📊 Order Status":

    st.markdown("### 📊 Orders Dashboard")

    records = items_sheet.get_all_records()
    df = pd.DataFrame(records)

    if df.empty:
        st.info("No orders found.")
        st.stop()

    # ── Metrics ─────────────────────────────────────
    grouped_status = df.groupby("Order ID")["STATUS"].apply(list)
    completed_orders = sum(1 for s in grouped_status if all(x.strip() == "Delivered" for x in s))
    pending_orders = len(grouped_status) - completed_orders

    col1, col2, col3 = st.columns(3)
    col1.metric("Pending Orders", pending_orders)
    col2.metric("Completed Orders", completed_orders)
    col3.metric("Total Orders", len(grouped_status))
    st.markdown("---")

    # ── Search / Filter ──────────────────────────────
    all_shops_in_orders = sorted(df["Shop Name"].dropna().unique().tolist())
    col_search1, col_search2 = st.columns([2, 1])
    with col_search1:
        selected_shop = st.selectbox(
            "🏪 Filter by Shop Name",
            options=["All Shops"] + all_shops_in_orders,
            index=0,
            key="status_shop_filter"
        )
    with col_search2:
        search_query = st.text_input("🔍 Search by Order ID", placeholder="e.g. 42")

    # ── Build dashboard table ────────────────────────
    grouped = df.groupby("Order ID")
    orders = []

    for order_id, group in grouped:
        statuses = [str(s).strip() for s in group["STATUS"].tolist()]
        if all(s == "Delivered" for s in statuses):
            continue

        pending_total = 0.0
        varieties_list = []

        for _, row in group.iterrows():
            total_qty = clean_number(row["Quantity (Quintal)"])
            delivered = clean_number(row.get("Delivered Qty", 0))
            pending = max(total_qty - delivered, 0)
            pending_total += pending
            if pending > 0:
                varieties_list.append(f"{row['Variety']} – {pending:g}Q")

        orders.append({
            "Order ID": str(order_id),
            "Shop": group["Shop Name"].iloc[0],
            "Agent": group["Agent Name"].iloc[0],
            "Date": group["Date"].iloc[0],
            "Total Qty": pending_total,
            "Varieties": ", ".join(varieties_list),
            "STATUS": determine_order_status(statuses)
        })

    orders_df = pd.DataFrame(orders)

    if orders_df.empty:
        st.success("🎉 All orders delivered!")
        st.stop()

    # Apply shop dropdown filter
    if selected_shop != "All Shops":
        orders_df = orders_df[orders_df["Shop"] == selected_shop]

    # Apply Order ID text filter
    if search_query:
        orders_df = orders_df[orders_df["Order ID"].str.contains(search_query.strip())]

    if orders_df.empty:
        st.warning("No matching orders found.")
        st.stop()

    st.markdown("### 📦 Update Order Status")

    edited_df = st.data_editor(
        orders_df,
        use_container_width=True,
        hide_index=True,
        key="orders_editor",
        column_config={
            "STATUS": st.column_config.SelectboxColumn("STATUS", options=STATUS_OPTIONS)
        },
        disabled=["Order ID", "Shop", "Agent", "Date", "Total Qty", "Varieties"]
    )

    # ── Partial Delivery Form ────────────────────────
    # Only show if user *changed* a status to Partial Delivery in this session
    original_statuses = {str(row["Order ID"]): str(row["STATUS"]) for _, row in orders_df.iterrows()}

    selected_order = None
    for _, row in edited_df.iterrows():
        order_id_str = str(row["Order ID"])
        new_status = str(row["STATUS"]).strip()
        old_status = original_statuses.get(order_id_str, "").strip()
        if new_status == "Partial Delivery" and old_status != "Partial Delivery":
            selected_order = order_id_str
            break

    delivery_updates = []

    if selected_order:
        st.markdown("---")
        st.markdown(f"### 🚚 Partial Delivery – Order {selected_order}")
        order_rows = df[df["Order ID"] == int(selected_order)]
        delivery_date = st.date_input("Delivery Date")

        for i, row in order_rows.iterrows():
            variety = row["Variety"]
            total_qty = clean_number(row["Quantity (Quintal)"])
            delivered = clean_number(row.get("Delivered Qty", 0))
            pending = max(total_qty - delivered, 0)
            if pending <= 0:
                continue
            col1, col2, col3 = st.columns([2, 1, 1])
            col1.write(f"**{variety}**")
            col2.write(f"Pending: {pending}Q")
            deliver_now = col3.number_input(
                f"Deliver {variety}", min_value=0.0, max_value=pending, step=1.0, key=f"deliver_{i}"
            )
            delivery_updates.append({
                "variety": variety, "deliver_now": deliver_now,
                "pending": pending, "delivered": delivered
            })

    # ── Update Button ────────────────────────────────
    if st.button("💾 Update Orders", type="primary"):
        sheet_data = items_sheet.get_all_values()
        headers = sheet_data[0]
        df_sheet = pd.DataFrame(sheet_data[1:], columns=headers)

        # Normalise Order ID column to string for safe comparison
        df_sheet["Order ID"] = df_sheet["Order ID"].astype(str).str.strip()

        # Apply status changes
        for _, row in edited_df.iterrows():
            df_sheet.loc[df_sheet["Order ID"] == str(row["Order ID"]).strip(), "STATUS"] = row["STATUS"]

        # Apply partial delivery quantities
        if selected_order:
            for update in delivery_updates:
                if update["deliver_now"] <= 0:
                    continue
                new_delivered = update["delivered"] + update["deliver_now"]
                new_pending = update["pending"] - update["deliver_now"]
                new_status = "Delivered" if new_pending <= 0 else "Partial Delivery"
                mask = (
                    (df_sheet["Order ID"] == str(selected_order).strip()) &
                    (df_sheet["Variety"] == update["variety"])
                )
                df_sheet.loc[mask, "Delivered Qty"] = new_delivered
                df_sheet.loc[mask, "Pending Qty"] = max(new_pending, 0)
                df_sheet.loc[mask, "Delivery Date"] = str(delivery_date)
                df_sheet.loc[mask, "STATUS"] = new_status

        push_sheet_update(items_sheet, df_sheet, headers)
        st.success("✅ Orders updated successfully!")
        st.rerun()

# =====================================================
# PAGE: ORDER HISTORY
# =====================================================
elif page == "🔍 Order History":

    st.markdown("### 🔍 Order History")

    records = items_sheet.get_all_records()
    df = pd.DataFrame(records)

    if df.empty:
        st.info("No orders found.")
        st.stop()

    # ── Filters ──────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        shop_filter = st.selectbox("Filter by Shop", ["All"] + sorted(df["Shop Name"].unique().tolist()))
    with col2:
        status_filter = st.selectbox("Filter by Status", ["All"] + STATUS_OPTIONS)
    with col3:
        agent_filter = st.selectbox("Filter by Agent", ["All"] + sorted(df["Agent Name"].unique().tolist()))

    filtered = df.copy()
    if shop_filter != "All":
        filtered = filtered[filtered["Shop Name"] == shop_filter]
    if status_filter != "All":
        filtered = filtered[filtered["STATUS"] == status_filter]
    if agent_filter != "All":
        filtered = filtered[filtered["Agent Name"] == agent_filter]

    # ── Detect total column name (handles "Item Total", "Item Total", etc.) ──
    total_col = next((c for c in filtered.columns if "total" in c.lower()), None)

    # ── Summary metrics ──────────────────────────────
    total_qty = filtered["Quantity (Quintal)"].apply(clean_number).sum() if "Quantity (Quintal)" in filtered.columns else 0
    total_value = filtered[total_col].apply(clean_number).sum() if total_col else 0
    unique_orders = filtered["Order ID"].nunique()

    col1, col2, col3 = st.columns(3)
    col1.metric("Matching Orders", unique_orders)
    col2.metric("Total Quintals", f"{total_qty:,.1f}")
    col3.metric("Total Value ₹", f"{total_value:,.0f}")

    st.markdown("---")

    # ── Table ────────────────────────────────────────
    display_cols = ["Date", "Order ID", "Shop Name", "Agent Name", "Variety",
                    "Quantity (Quintal)", "Price (₹/Quintal)", total_col, "STATUS"]
    display_cols = [c for c in display_cols if c]  # remove None if total_col not found
    available = [c for c in display_cols if c in filtered.columns]
    st.dataframe(filtered[available], use_container_width=True, hide_index=True)

    # ── CSV Export ───────────────────────────────────
    csv = filtered[available].to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download as CSV",
        data=csv,
        file_name=f"orders_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )

# =====================================================
# FOOTER
# =====================================================
st.markdown("""
<div class="footer">
Sri Lakshmi Venkateswara Rice Industries, Erraguntapalli, Chintalapudi(M), Andhra Pradesh, India
</div>
""", unsafe_allow_html=True)

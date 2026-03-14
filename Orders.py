import streamlit as st
import streamlit.components.v1 as components
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import urllib.parse
import pandas as pd
import uuid

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="Sri Rudra Rice Order Form",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# FONT STYLE — injected into every components.html iframe
# =====================================================
FONT_STYLE = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@400;600;700&display=swap');
  * { font-family: 'Source Sans Pro', sans-serif; box-sizing: border-box; margin: 0; padding: 0; }
  body { background: transparent; overflow: hidden; }
</style>
"""

# =====================================================
# SIDEBAR NAVIGATION
# =====================================================
st.sidebar.image("logo.PNG", width=120)
st.sidebar.markdown("## Sri Rudra Rice 🌾")
st.sidebar.markdown("---")
selected = st.sidebar.radio(
    "Navigate",
    ["📦 Orders Page", "🔐 Admin Page"],
    index=0,
    label_visibility="collapsed"
)

# =====================================================
# CONSTANTS
# =====================================================
RICE_VARIETIES = ["HMT", "BPT", "JSR", "Broken", "RNR", "KNM", "Other"]
STATUS_OPTIONS = ["Order Accepted", "Packed", "Out for Delivery", "Partial Delivery", "Delivered"]
SHEET_KEY = "1dA4A8nbdwS_wcKVb3dA5ofqDlACw07SL3i0mtPYSo0Q"
ITEMS_SHEET = "Order_Items"
SUMMARY_SHEET = "Orders_Summary"

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def clean_number(value) -> float:
    if value is None or value == "":
        return 0.0
    return float(str(value).replace("₹", "").replace(",", "").strip())

def generate_order_id(sheet) -> str:
    try:
        values = sheet.col_values(2)[1:]
        existing = [int(v) for v in values if v.strip().isdigit()]
        return str(max(existing) + 1) if existing else "1"
    except Exception:
        return str(uuid.uuid4().int)[:8]

def build_whatsapp_link(contact: str, shop: str, items: list, grand_total: float) -> str:
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

def write_order_to_sheet(items_sheet, summary_sheet, order_id, shop, contact, agent, valid_items, grand_total):
    today = datetime.now().strftime("%Y-%m-%d")
    rows = [[today, order_id, shop, contact, agent,
             item["variety"], item["quantity"], item["price"], item["total"],
             0, item["quantity"], "", "Order Accepted"] for item in valid_items]
    items_sheet.append_rows(rows, value_input_option="USER_ENTERED")
    summary_sheet.append_row(
        [today, order_id, shop, agent, sum(i["quantity"] for i in valid_items), grand_total],
        value_input_option="USER_ENTERED"
    )

def html_block(html: str, height: int, scrolling: bool = False):
    """Render an HTML block with consistent font injection."""
    components.html(FONT_STYLE + html, height=height, scrolling=scrolling)

def card_list_height(n_items: int, item_px: int = 90, padding: int = 20) -> int:
    """Calculate tight height for a vertical list of n cards."""
    return n_items * item_px + padding

# =====================================================
# GOOGLE SHEETS CONNECTION
# =====================================================
@st.cache_resource
def get_sheets():
    scope = ["https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SHEET_KEY)
    return spreadsheet.worksheet(ITEMS_SHEET), spreadsheet.worksheet(SUMMARY_SHEET)

items_sheet, summary_sheet = get_sheets()

@st.cache_data(ttl=60)
def load_shops():
    records = items_sheet.get_all_records()
    shop_phone, shop_agent = {}, {}
    for r in records:
        shop = str(r.get("Shop Name", "")).strip()
        if shop:
            shop_phone[shop] = str(r.get("Phone", ""))
            shop_agent[shop] = str(r.get("Agent Name", ""))
    return shop_phone, shop_agent

# =====================================================
# SHARED CSS  —  fixes applied:
#   1. body, label, span, p  →  dark text on mobile  (was missing)
#   2. metric label/value overrides  →  pure black    (was missing)
#   3. [data-testid="stImage"] img  →  restored original
#      margin-left:110px on mobile  (was broken to auto)
# =====================================================
SHARED_CSS = """
<style>
header[data-testid="stHeader"] {
    background: transparent !important;
    position: fixed !important;
    top: 0 !important;
    z-index: 999 !important;
}
[data-testid="stToolbarActions"] { display: none !important; }
[data-testid="stDecoration"]     { display: none !important; }
#MainMenu                        { display: none !important; }
footer                           { display: none !important; }
.block-container {
    max-width: 1000px;
    padding-top: 0.5rem !important;
    margin-top: 0 !important;
    padding-bottom: 0;
}
[data-testid="stSidebarCollapsedControl"] {
    position: fixed !important;
    top: 50% !important;
    left: 0 !important;
    transform: translateY(-50%) !important;
    z-index: 99999 !important;
    background-color: #8B6F2F !important;
    border-radius: 0 10px 10px 0 !important;
    padding: 10px 6px !important;
    box-shadow: 2px 2px 6px rgba(0,0,0,0.3) !important;
}
[data-testid="stSidebarCollapsedControl"] button {
    color: white !important; background: transparent !important; border: none !important;
}
[data-testid="stSidebarCollapsedControl"] button svg {
    fill: white !important; stroke: white !important;
}
[data-testid="stSidebar"] { background-color: #f5edd6 !important; }
.stApp { background: linear-gradient(135deg, #f9f6e7, #DDC57A); }
h1 { text-align: center; color: #8B6F2F; }
h3 { text-align: center; color: #6B5B2A; }
[data-testid="stMetricLabel"] { color: #000000 !important; font-weight: 700 !important; }
[data-testid="stMetricValue"] { color: #000000 !important; }
.footer-bar {
    text-align: center; padding: 16px; margin-top: 30px;
    background: #E7D283; font-size: 14px; color: #4A3F1C; border-radius: 8px;
}
div[data-testid="stForm"] {
    background: white; padding: 20px; border-radius: 15px;
    box-shadow: 0px 5px 25px rgba(0,0,0,0.08);
}
label,
div[data-testid="stForm"] label,
div[data-testid="stWidgetLabel"] { font-weight: bold !important; color: #2b2b2b !important; }
div[data-baseweb="select"] input[type="text"] { color: #000000 !important; }
.brand-title {
    color: #8B6F2F; font-size: 42px !important; font-weight: bold;
    text-align: center; margin: 0; line-height: 1.1;
}
.brand-subtitle {
    color: #6B5B2A; font-size: 20px !important; text-align: center; margin: 4px 0;
}
.item-card {
    background: #fffdf3; border: 1px solid #e0c96e;
    border-radius: 10px; padding: 12px 16px; margin-bottom: 12px;
}
.metrics-row > div[data-testid="stHorizontalBlock"] {
    display: flex !important; flex-direction: row !important;
    flex-wrap: nowrap !important; gap: 6px !important;
}
.metrics-row > div[data-testid="stHorizontalBlock"] > div {
    flex: 1 1 0 !important; min-width: 0 !important;
}

/* Desktop logo centering */
[data-testid="stImage"] img {
    display: block !important;
    margin-left: auto !important;
    margin-right: auto !important;
}

@media (max-width: 768px) {
    h3, h2 { font-size: 22px !important; font-weight: bold !important; }

    div[data-testid="stMarkdownContainer"] h3 {
        font-size: 22px !important;
        font-weight: bold !important;
    }

    /* FIX 1: Restore dark text for all elements on mobile */
    body, label, span, p {
        color: #2b2b2b !important;
    }

    /* FIX 2: Metric labels and values must stay pure black on mobile
       (these come AFTER the body rule so they take precedence) */
    body [data-testid="stMetricLabel"],
    body [data-testid="stMetricLabel"] p,
    body [data-testid="stMetricLabel"] span,
    body [data-testid="stMetricValue"],
    body [data-testid="stMetricValue"] p,
    body [data-testid="stMetricValue"] span,
    body [data-testid="stMetricValue"] div {
        color: #000000 !important;
    }

    .block-container {
        padding-left: 12px !important;
        padding-right: 12px !important;
    }

    h1 { font-size: 26px !important; text-align: center !important; }
    h3 { font-size: 18px !important; text-align: center !important; }

    /* FIX 3: Restore original logo position on mobile */
    [data-testid="stImage"] img {
        max-width: 150px !important;
        margin-left: 110px !important;
        margin-right: 0 !important;
    }

    div[data-testid="stFormSubmitButton"] button,
    div.stButton > button {
        background-color: #8B6F2F !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        width: 100%;
        margin-top: 8px;
    }
    div[data-testid="stFormSubmitButton"] button p,
    div.stButton > button p { color: white !important; }

    div[data-testid="stHorizontalBlock"] { display: flex !important; flex-direction: row !important; }
    div[data-testid="stHorizontalBlock"] > div { flex: 1 !important; }

    div[role="listbox"] div[role="option"] {
        color: #2b2b2b !important;
        font-size: 16px !important;
        background-color: white !important;
    }

    .stDataFrameContainer div[data-baseweb="select"] div[class*="singleValue"],
    .stDataFrameContainer div[data-baseweb="select"] div[class*="option"],
    .stDataFrameContainer div[data-baseweb="select"] div[class*="menu"] {
        color: #2b2b2b !important;
        font-weight: normal !important;
        font-size: 16px !important;
    }

    .brand-title { margin-left: 0% !important; }

    /* metrics-row: bigger, bolder, pure black on mobile */
    .metrics-row [data-testid="stMetricLabel"],
    .metrics-row [data-testid="stMetricLabel"] * {
        font-size: 14px !important;
        font-weight: 700 !important;
        color: #000000 !important;
        white-space: normal !important;
        word-break: break-word !important;
    }

    .metrics-row [data-testid="stMetricValue"],
    .metrics-row [data-testid="stMetricValue"] * {
        font-size: 18px !important;
        font-weight: 700 !important;
        color: #000000 !important;
        word-break: break-word !important;
    }

    .metrics-row {
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
    }
}
</style>
"""

# =====================================================
# ORDERS PAGE
# =====================================================
if selected == "📦 Orders Page":

    st.markdown(SHARED_CSS, unsafe_allow_html=True)

    shop_phone, shop_agent = load_shops()
    existing_shops = sorted(shop_phone.keys())

    if "rice_items" not in st.session_state:
        st.session_state.rice_items = 2
    if "last_order_id" not in st.session_state:
        st.session_state.last_order_id = None
    if "last_wa_link" not in st.session_state:
        st.session_state.last_wa_link = None

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

    page = st.radio("Select Page",
                    ["📦 Order Booking", "📊 Order Status", "🔍 Order History"],
                    horizontal=True, index=0)

    if page == "📦 Order Booking":
        st.markdown("### 🏪 Shop Details")
        col1, col2, col3 = st.columns(3)
        with col1:
            shop_name = st.selectbox("Shop Name", options=existing_shops, index=None,
                                      placeholder="Type shop name...", accept_new_options=True, key="shop_name")
        if shop_name in shop_phone:
            st.session_state.contact_number = shop_phone.get(shop_name, "")
            st.session_state.agent_name = shop_agent.get(shop_name, "")
        with col2:
            contact_number = st.text_input("Contact Number", key="contact_number")
        with col3:
            agent_name = st.text_input("Agent Name", key="agent_name")
        st.markdown("---")

        with st.form("order_form"):
            st.markdown("### 🌾 Rice Varieties")
            grand_total = 0.0
            order_details = []
            for i in range(st.session_state.rice_items):
                with st.container():
                    st.markdown('<div class="item-card">', unsafe_allow_html=True)
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
            errors = []
            if not shop_name:      errors.append("Shop Name is required.")
            if not contact_number: errors.append("Contact Number is required.")
            if not valid_items:    errors.append("At least one rice item with quantity > 0 is required.")
            if errors:
                for e in errors: st.error(e)
                st.stop()
            order_id = generate_order_id(items_sheet)
            write_order_to_sheet(items_sheet, summary_sheet, order_id, shop_name,
                                 contact_number, agent_name, valid_items, grand_total)
            load_shops.clear()
            st.session_state.last_order_id = order_id
            st.session_state.last_wa_link = build_whatsapp_link(contact_number, shop_name, valid_items, grand_total)
            st.success(f"✅ Order Confirmed | Order ID : {order_id}")
            st.markdown(f"[📱 Send WhatsApp Confirmation]({st.session_state.last_wa_link})")
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

    elif page == "📊 Order Status":
        st.markdown("### 📊 Orders Dashboard")
        records = items_sheet.get_all_records()
        df = pd.DataFrame(records)
        if df.empty:
            st.info("No orders found.")
            st.stop()

        grouped_status = df.groupby("Order ID")["STATUS"].apply(list)
        completed_orders = sum(1 for s in grouped_status if all(x.strip() == "Delivered" for x in s))
        pending_orders = len(grouped_status) - completed_orders

        st.markdown('<div class="metrics-row">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        col1.metric("Pending Orders", pending_orders)
        col2.metric("Completed Orders", completed_orders)
        col3.metric("Total Orders", len(grouped_status))
        st.markdown('</div><hr style="margin-top:8px;margin-bottom:8px;border:none;border-top:1px solid #c8b56e;">', unsafe_allow_html=True)

        all_shops_in_orders = sorted(df["Shop Name"].dropna().unique().tolist())
        col_search1, col_search2 = st.columns([2, 1])
        with col_search1:
            selected_shop = st.selectbox("🏪 Filter by Shop Name",
                                          options=["All Shops"] + all_shops_in_orders,
                                          index=0, accept_new_options=True, key="status_shop_filter")
            if selected_shop not in (["All Shops"] + all_shops_in_orders):
                selected_shop = "All Shops"
        with col_search2:
            search_query = st.text_input("🔍 Search by Order ID", placeholder="e.g. 42")

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
                "Order ID": str(order_id), "Shop": group["Shop Name"].iloc[0],
                "Agent": group["Agent Name"].iloc[0], "Date": group["Date"].iloc[0],
                "Total Qty": pending_total, "Varieties": ", ".join(varieties_list),
                "STATUS": determine_order_status(statuses)
            })

        orders_df = pd.DataFrame(orders)
        if orders_df.empty:
            st.success("🎉 All orders delivered!")
            st.stop()
        if selected_shop != "All Shops":
            orders_df = orders_df[orders_df["Shop"] == selected_shop]
        if search_query:
            orders_df = orders_df[orders_df["Order ID"].str.contains(search_query.strip())]
        if orders_df.empty:
            st.warning("No matching orders found.")
            st.stop()

        st.markdown("### 📦 Update Order Status")
        original_statuses = {str(row["Order ID"]): str(row["STATUS"]) for _, row in orders_df.iterrows()}
        edited_df = st.data_editor(
            orders_df, use_container_width=True, hide_index=True, key="orders_editor",
            column_config={"STATUS": st.column_config.SelectboxColumn("STATUS", options=STATUS_OPTIONS)},
            disabled=["Order ID", "Shop", "Agent", "Date", "Total Qty", "Varieties"]
        )

        newly_partial = [
            str(row["Order ID"]) for _, row in edited_df.iterrows()
            if str(row["STATUS"]).strip() == "Partial Delivery"
            and original_statuses.get(str(row["Order ID"]), "").strip() != "Partial Delivery"
        ]
        already_partial = [
            str(row["Order ID"]) for _, row in edited_df.iterrows()
            if str(row["STATUS"]).strip() == "Partial Delivery"
            and original_statuses.get(str(row["Order ID"]), "").strip() == "Partial Delivery"
        ]
        delivery_updates = {}

        for selected_order in newly_partial:
            st.markdown("---")
            st.markdown(f"### 🚚 Partial Delivery – Order {selected_order}")
            order_rows = df[df["Order ID"].astype(str).str.strip() == selected_order.strip()]
            delivery_date = st.date_input("Delivery Date", key=f"partial_delivery_date_{selected_order}")
            order_updates = []
            for i, row in order_rows.iterrows():
                variety = row["Variety"]
                total_qty = clean_number(row["Quantity (Quintal)"])
                delivered = clean_number(row.get("Delivered Qty", 0))
                pending = max(total_qty - delivered, 0)
                if pending <= 0: continue
                col1, col2, col3 = st.columns([2, 1, 1])
                col1.write(f"**{variety}**")
                col2.write(f"Pending: {pending}Q")
                deliver_now = col3.number_input(f"Deliver {variety}", min_value=0.0, max_value=pending,
                                                 step=1.0, key=f"deliver_{selected_order}_{i}")
                order_updates.append({"variety": variety, "deliver_now": deliver_now,
                                       "pending": pending, "delivered": delivered, "delivery_date": delivery_date})
            delivery_updates[selected_order] = order_updates

        st.markdown("---")
        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
            if already_partial and st.button("➕ Add Partial Delivery", type="secondary"):
                st.session_state.show_add_partial = not st.session_state.get("show_add_partial", False)
        with col_btn2:
            update_clicked = st.button("💾 Update Orders", type="primary")

        if st.session_state.get("show_add_partial", False) and already_partial:
            st.markdown("#### 🚚 Record Partial Delivery")
            partial_shop_options = {}
            for oid in already_partial:
                rows_for = edited_df[edited_df["Order ID"] == oid]
                if not rows_for.empty:
                    partial_shop_options[f"Order {oid} — {rows_for['Shop'].values[0]}"] = oid
            selected_label = st.selectbox("Select Order", options=list(partial_shop_options.keys()), key="add_partial_select")
            selected_partial_id = partial_shop_options[selected_label]
            order_rows = df[df["Order ID"].astype(str).str.strip() == selected_partial_id]
            delivery_date_ap = st.date_input("Delivery Date", key="add_partial_date")
            order_updates_ap = []
            for i, row in order_rows.iterrows():
                variety = row["Variety"]
                total_qty = clean_number(row["Quantity (Quintal)"])
                delivered = clean_number(row.get("Delivered Qty", 0))
                pending = max(total_qty - delivered, 0)
                if pending <= 0: continue
                col1, col2, col3 = st.columns([2, 1, 1])
                col1.write(f"**{variety}**")
                col2.write(f"Pending: {pending}Q")
                deliver_now = col3.number_input(f"Deliver {variety}", min_value=0.0, max_value=pending,
                                                 step=1.0, key=f"add_partial_deliver_{i}")
                order_updates_ap.append({"variety": variety, "deliver_now": deliver_now,
                                          "pending": pending, "delivered": delivered, "delivery_date": delivery_date_ap})
            delivery_updates[selected_partial_id] = order_updates_ap

        if update_clicked:
            sheet_data = items_sheet.get_all_values()
            raw_headers = sheet_data[0]
            headers = [h.strip() for h in raw_headers]
            df_sheet = pd.DataFrame(sheet_data[1:], columns=headers)
            df_sheet = df_sheet.applymap(lambda x: x.strip() if isinstance(x, str) else x)
            df_sheet["Order ID"] = df_sheet["Order ID"].astype(str).str.strip()
            for _, row in edited_df.iterrows():
                order_id_str = str(row["Order ID"]).strip()
                new_status = str(row["STATUS"]).strip()
                old_status = original_statuses.get(order_id_str, "").strip()
                df_sheet.loc[df_sheet["Order ID"] == order_id_str, "STATUS"] = new_status
                if new_status == "Delivered" and old_status != "Delivered":
                    delivery_date_str = datetime.now().strftime("%Y-%m-%d")
                    for idx in df_sheet[df_sheet["Order ID"] == order_id_str].index:
                        total_qty = clean_number(df_sheet.at[idx, "Quantity (Quintal)"])
                        df_sheet.at[idx, "Delivered Qty"] = str(total_qty)
                        df_sheet.at[idx, "Pending Qty"] = "0"
                        df_sheet.at[idx, "Delivery Date"] = delivery_date_str
            if delivery_updates:
                for selected_order, updates in delivery_updates.items():
                    for update in updates:
                        if update["deliver_now"] <= 0: continue
                        new_delivered = update["delivered"] + update["deliver_now"]
                        new_pending = max(update["pending"] - update["deliver_now"], 0)
                        new_status = "Delivered" if new_pending <= 0 else "Partial Delivery"
                        mask = ((df_sheet["Order ID"] == str(selected_order).strip()) &
                                (df_sheet["Variety"].str.strip() == str(update["variety"]).strip()))
                        if mask.sum() == 0:
                            st.warning(f"⚠️ No matching row for Order {selected_order}, Variety '{update['variety']}'")
                            continue
                        df_sheet.loc[mask, "Delivered Qty"] = str(new_delivered)
                        df_sheet.loc[mask, "Pending Qty"] = str(new_pending)
                        df_sheet.loc[mask, "Delivery Date"] = str(update["delivery_date"])
                        df_sheet.loc[mask, "STATUS"] = new_status
            df_sheet = df_sheet.replace([float("inf"), -float("inf")], "").fillna("")
            rows_out = [[str(v) if v != "" else "" for v in row] for row in df_sheet.values.tolist()]
            items_sheet.update("A1", [raw_headers] + rows_out, value_input_option="USER_ENTERED")
            st.success("✅ Orders updated successfully!")
            st.session_state.show_add_partial = False
            st.rerun()

    elif page == "🔍 Order History":
        st.markdown("### 🔍 Order History")
        records = items_sheet.get_all_records()
        df = pd.DataFrame(records)
        if df.empty:
            st.info("No orders found.")
            st.stop()

        col1, col2, col3 = st.columns(3)
        with col1:
            shop_filter = st.selectbox("Filter by Shop",
                                        options=["All"] + sorted(df["Shop Name"].unique().tolist()),
                                        index=0, accept_new_options=True, key="history_shop_filter")
            if shop_filter not in (["All"] + sorted(df["Shop Name"].unique().tolist())):
                shop_filter = "All"
        with col2:
            status_filter = st.selectbox("Filter by Status", ["All"] + STATUS_OPTIONS)
        with col3:
            agent_filter = st.selectbox("Filter by Agent", ["All"] + sorted(df["Agent Name"].unique().tolist()))

        filtered = df.copy()
        if shop_filter != "All": filtered = filtered[filtered["Shop Name"] == shop_filter]
        if status_filter != "All": filtered = filtered[filtered["STATUS"] == status_filter]
        if agent_filter != "All": filtered = filtered[filtered["Agent Name"] == agent_filter]

        total_col = next((c for c in filtered.columns if "total" in c.lower()), None)
        total_qty   = filtered["Quantity (Quintal)"].apply(clean_number).sum() if "Quantity (Quintal)" in filtered.columns else 0
        total_value = filtered[total_col].apply(clean_number).sum() if total_col else 0
        unique_orders = filtered["Order ID"].nunique()

        st.markdown('<div class="metrics-row">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        col1.metric("Matching Orders", unique_orders)
        col2.metric("Total Quintals", f"{total_qty:,.1f}")
        col3.metric("Total Value ₹", f"{total_value:,.0f}")
        st.markdown('</div><hr style="margin-top:8px;margin-bottom:8px;border:none;border-top:1px solid #c8b56e;">', unsafe_allow_html=True)

        display_cols = ["Date", "Order ID", "Shop Name", "Agent Name", "Variety",
                        "Quantity (Quintal)", "Price (₹/Quintal)", total_col, "STATUS"]
        display_cols = [c for c in display_cols if c]
        available = [c for c in display_cols if c in filtered.columns]
        st.dataframe(filtered[available], use_container_width=True, hide_index=True)
        csv = filtered[available].to_csv(index=False).encode("utf-8")
        st.download_button(label="⬇️ Download as CSV", data=csv,
                            file_name=f"orders_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                            mime="text/csv")

    st.markdown('<div class="footer-bar">Sri Lakshmi Venkateswara Rice Industries, Erraguntapalli, Chintalapudi(M), Andhra Pradesh, India</div>',
                unsafe_allow_html=True)


# =====================================================
# ADMIN PAGE
# =====================================================
elif selected == "🔐 Admin Page":

    st.markdown(SHARED_CSS, unsafe_allow_html=True)

    ADMIN_CODE = "7777"

    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False

    if not st.session_state.admin_authenticated:
        st.markdown("## 🔐 Admin Access")
        st.markdown("This page is restricted. Enter the admin code to continue.")
        code_input = st.text_input("Admin Code", type="password", key="admin_code_input")
        if st.button("🔓 Unlock", type="primary"):
            if code_input == ADMIN_CODE:
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("❌ Incorrect code. Please try again.")
        st.stop()

    st.markdown("## 📊 Admin Dashboard")
    st.markdown("""
    <style>
    div[data-testid="stButton"]:has(button[kind="secondary"]#admin_logout_btn) {
        display: flex; justify-content: flex-end;
    }
    </style>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([3, 1, 1])
    with col3:
        if st.button("🔒 Logout", key="admin_logout_btn"):
            st.session_state.admin_authenticated = False
            st.session_state.pop("admin_code_input", None)
            st.rerun()

    @st.cache_data(ttl=60)
    def load_admin_data():
        return items_sheet.get_all_records()

    df_all = pd.DataFrame(load_admin_data())
    if df_all.empty:
        st.info("No data available.")
        st.stop()

    df_all["Quantity (Quintal)"] = df_all["Quantity (Quintal)"].apply(clean_number)
    df_all["Delivered Qty"]      = df_all["Delivered Qty"].apply(clean_number)
    # FIX: dayfirst=True so DD/MM/YYYY dates parse correctly
    df_all["Delivery Date"]      = pd.to_datetime(df_all["Delivery Date"], dayfirst=True, errors="coerce")
    df_all["Date"]               = pd.to_datetime(df_all["Date"], dayfirst=True, errors="coerce").dt.normalize()
    if "Payment Status" not in df_all.columns:
        df_all["Payment Status"] = "Pending"
    df_all["Payment Status"]     = df_all["Payment Status"].fillna("Pending").astype(str)
    if "Price (₹/Quintal)" in df_all.columns:
        df_all["Price (₹/Quintal)"] = df_all["Price (₹/Quintal)"].apply(clean_number)
    total_col_a = next((c for c in df_all.columns if "total" in c.lower()), None)
    if total_col_a:
        df_all[total_col_a] = df_all[total_col_a].apply(clean_number)

    st.markdown("---")
    st.markdown("#### 💰 Overall Sales Summary")
    total_revenue  = df_all[total_col_a].sum() if total_col_a else 0
    total_quintals = df_all["Quantity (Quintal)"].sum()
    total_orders   = df_all["Order ID"].nunique()
    received_mask  = df_all["Payment Status"].str.strip().str.lower() == "received"
    collected_rev  = df_all.loc[received_mask, total_col_a].sum() if total_col_a else 0
    pending_rev    = total_revenue - collected_rev

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Orders",    total_orders)
    c2.metric("Total Quintals",  f"{total_quintals:,.1f}")
    c3.metric("Total Revenue ₹", f"{total_revenue:,.0f}")
    c4.metric("Collected ₹",     f"{collected_rev:,.0f}")
    c5.metric("Pending ₹",       f"{pending_rev:,.0f}")
    st.markdown("---")

    tab_sales, tab_payments, tab_employee = st.tabs(["📈 Sales", "💳 Payments", "👤 Employee Performance"])

    # ══════════════════════════════
    # TAB 1 — SALES
    # ══════════════════════════════
    with tab_sales:

        # ── Rice Variety Cards ──
        st.markdown("#### 🌾 Sales by Rice Variety")
        variety_sales = (
            df_all.groupby("Variety")
            .agg(Total_Quintals=("Quantity (Quintal)", "sum"),
                 Total_Revenue=(total_col_a, "sum") if total_col_a else ("Quantity (Quintal)", "sum"))
            .sort_values("Total_Revenue", ascending=False).reset_index()
        )
        max_rev = variety_sales["Total_Revenue"].max() if not variety_sales.empty else 1
        avg_qty = variety_sales["Total_Quintals"].mean() if not variety_sales.empty else 0

        all_cards_html = '<div style="display:flex; flex-wrap:wrap; gap:16px; margin-bottom:4px;">'
        for idx, row in variety_sales.iterrows():
            bar_pct = int((row["Total_Revenue"] / max_rev) * 100)
            is_slow = row["Total_Quintals"] < (avg_qty * 0.4)
            border_color = "#e74c3c" if is_slow else "#8B6F2F"
            slow_badge = '<div style="font-size:11px;background:#fdecea;color:#e74c3c;border-radius:4px;padding:2px 6px;display:inline-block;margin-top:4px;">⚠️ Slow Moving</div>' if is_slow else ""
            all_cards_html += f"""
            <div style="background:white;border-radius:12px;padding:16px 14px;
                        box-shadow:0 2px 10px rgba(0,0,0,0.08);
                        border-left:5px solid {border_color};flex:1 1 180px;min-width:160px;max-width:240px;">
                <div style="font-size:18px;font-weight:700;color:{border_color};">{row['Variety']}</div>
                {slow_badge}
                <div style="font-size:12px;color:#666;margin-top:6px;">Quintals Sold</div>
                <div style="font-size:22px;font-weight:700;color:#2b2b2b;">{row['Total_Quintals']:,.1f} Q</div>
                <div style="font-size:12px;color:#666;margin-top:4px;">Revenue</div>
                <div style="font-size:17px;font-weight:600;color:#4A7C59;">&#8377;{row['Total_Revenue']:,.0f}</div>
                <div style="background:#f0e8d0;border-radius:6px;height:8px;margin-top:10px;">
                    <div style="background:{border_color};width:{bar_pct}%;height:8px;border-radius:6px;"></div>
                </div>
            </div>"""
        all_cards_html += '</div>'

        rows_of_cards = (len(variety_sales) + 3) // 4
        cards_height = rows_of_cards * 175 + 30
        html_block(all_cards_html, height=cards_height)

        st.markdown("---")

        # ── Sales Trend ──
        st.markdown("#### 📅 Sales Trend")
        trend_period = st.radio("View by", ["Monthly", "Weekly"], horizontal=True, key="trend_period")
        df_trend = df_all.dropna(subset=["Date"]).copy()
        if trend_period == "Monthly":
            df_trend["Period"] = df_trend["Date"].dt.to_period("M").astype(str)
        else:
            df_trend["Period"] = df_trend["Date"].dt.to_period("W").apply(lambda r: str(r.start_time.date()))

        trend_data = (
            df_trend.groupby("Period")
            .agg(Revenue=(total_col_a, "sum") if total_col_a else ("Quantity (Quintal)", "sum"),
                 Orders=("Order ID", "nunique"),
                 Quintals=("Quantity (Quintal)", "sum"))
            .reset_index().sort_values("Period")
        )

        if not trend_data.empty:
            max_trend_rev = trend_data["Revenue"].max()
            bars_html = ""
            for _, tr in trend_data.iterrows():
                h = max(int((tr["Revenue"] / max_trend_rev) * 140), 4)
                bars_html += f"""
                <div style="display:flex; flex-direction:column; align-items:center; flex:1; min-width:50px;">
                    <div style="font-size:11px; color:#4A7C59; font-weight:600; margin-bottom:4px;">
                        &#8377;{tr['Revenue']/1000:.0f}K
                    </div>
                    <div style="background:#8B6F2F; width:70%; height:{h}px; border-radius:6px 6px 0 0;"></div>
                    <div style="font-size:10px; color:#888; margin-top:4px; text-align:center;
                                word-break:break-all;">{tr['Period']}</div>
                    <div style="font-size:10px; color:#aaa;">{tr['Orders']} orders</div>
                </div>"""

            chart_html = f"""
            <div style="background:white;border-radius:12px;padding:20px;
                        box-shadow:0 2px 10px rgba(0,0,0,0.08);overflow-x:auto;">
                <div style="display:flex;align-items:flex-end;gap:6px;min-height:180px;padding-bottom:8px;">
                    {bars_html}
                </div>
            </div>"""
            html_block(chart_html, height=240)

        st.markdown("---")

        # ── Top 5 by Revenue ──
        st.markdown("#### 🏆 Top 5 Shops by Revenue")
        shop_rev = (
            df_all.groupby("Shop Name")
            .agg(Revenue=(total_col_a, "sum") if total_col_a else ("Quantity (Quintal)", "sum"),
                 Orders=("Order ID", "nunique"),
                 Quintals=("Quantity (Quintal)", "sum"))
            .sort_values("Revenue", ascending=False).head(5).reset_index()
        )
        top_revenue_html = ""
        for rank, row in shop_rev.iterrows():
            bar_pct = int((row["Revenue"] / shop_rev["Revenue"].max()) * 100)
            medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][rank]
            top_revenue_html += f"""
            <div style="background:white; border-radius:10px; padding:14px 18px; margin-bottom:8px;
                        box-shadow:0 2px 8px rgba(0,0,0,0.06); display:flex; align-items:center; gap:16px;">
                <div style="font-size:28px;">{medal}</div>
                <div style="flex:1;">
                    <div style="font-weight:700; font-size:16px; color:#2b2b2b;">{row['Shop Name']}</div>
                    <div style="background:#f0e8d0; border-radius:4px; height:6px; margin-top:6px;">
                        <div style="background:#8B6F2F; width:{bar_pct}%; height:6px; border-radius:4px;"></div>
                    </div>
                </div>
                <div style="text-align:right; min-width:120px;">
                    <div style="font-size:17px; font-weight:700; color:#4A7C59;">&#8377;{row['Revenue']:,.0f}</div>
                    <div style="font-size:12px; color:#888;">{row['Orders']} orders · {row['Quintals']:,.1f} Q</div>
                </div>
            </div>"""
        html_block(top_revenue_html, height=card_list_height(len(shop_rev), item_px=82))

        st.markdown("---")

        # ── Top 5 by Repeat Orders ──
        st.markdown("#### 🔁 Top 5 Shops by Repeat Orders")
        shop_repeat = (
            df_all.groupby("Shop Name")
            .agg(Orders=("Order ID", "nunique"),
                 Revenue=(total_col_a, "sum") if total_col_a else ("Quantity (Quintal)", "sum"),
                 Quintals=("Quantity (Quintal)", "sum"))
            .sort_values("Orders", ascending=False).head(5).reset_index()
        )
        repeat_html = ""
        for rank, row in shop_repeat.iterrows():
            bar_pct = int((row["Orders"] / shop_repeat["Orders"].max()) * 100)
            medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][rank]
            repeat_html += f"""
            <div style="background:white; border-radius:10px; padding:14px 18px; margin-bottom:8px;
                        box-shadow:0 2px 8px rgba(0,0,0,0.06); display:flex; align-items:center; gap:16px;">
                <div style="font-size:28px;">{medal}</div>
                <div style="flex:1;">
                    <div style="font-weight:700; font-size:16px; color:#2b2b2b;">{row['Shop Name']}</div>
                    <div style="background:#f0e8d0; border-radius:4px; height:6px; margin-top:6px;">
                        <div style="background:#C08030; width:{bar_pct}%; height:6px; border-radius:4px;"></div>
                    </div>
                </div>
                <div style="text-align:right; min-width:120px;">
                    <div style="font-size:17px; font-weight:700; color:#C08030;">{row['Orders']} orders</div>
                    <div style="font-size:12px; color:#888;">&#8377;{row['Revenue']:,.0f} · {row['Quintals']:,.1f} Q</div>
                </div>
            </div>"""
        html_block(repeat_html, height=card_list_height(len(shop_repeat), item_px=82))

    # ══════════════════════════════
    # TAB 2 — PAYMENTS
    # ══════════════════════════════
    with tab_payments:

        st.markdown("#### 💳 Update Payment Status")

        sheet_data_pay  = items_sheet.get_all_values()
        raw_headers_pay = sheet_data_pay[0]
        headers_pay     = [h.strip() for h in raw_headers_pay]
        df_pay          = pd.DataFrame(sheet_data_pay[1:], columns=headers_pay)
        df_pay          = df_pay.applymap(lambda x: x.strip() if isinstance(x, str) else x)
        if "Payment Status" not in df_pay.columns:
            df_pay["Payment Status"] = "Pending"

        df_pay_eligible = df_pay[
            df_pay["STATUS"].str.strip().isin(["Delivered", "Partial Delivery"])
        ].copy()

        if df_pay_eligible.empty:
            st.info("No delivered orders to update.")
        else:
            order_options = {}
            for order_id, grp in df_pay_eligible.groupby("Order ID"):
                shop  = grp["Shop Name"].iloc[0]
                label = f"Order {order_id} — {shop}"
                order_options[label] = str(order_id)

            selected_label = st.selectbox(
                "🔍 Search Order",
                options=list(order_options.keys()),
                index=None,
                placeholder="Type order ID or shop name...",
                key="pay_order_select"
            )

            if selected_label:
                selected_order_id = order_options[selected_label]
                order_rows = df_pay_eligible[
                    df_pay_eligible["Order ID"].astype(str) == selected_order_id
                ]

                st.markdown(f"**Order {selected_order_id} — {order_rows['Shop Name'].iloc[0]}**")
                st.caption(f"Agent: {order_rows['Agent Name'].iloc[0]}")
                st.markdown("")

                updated_statuses = {}
                for _, row in order_rows.iterrows():
                    with st.container():
                        st.markdown(f"""
                        <div style="background:#fffdf3; border:1px solid #e0c96e; border-radius:10px;
                                    padding:10px 14px; margin-bottom:4px;">
                            <div style="font-weight:700; font-size:15px; color:#2b2b2b;">{row['Variety']}</div>
                            <div style="font-size:13px; color:#666; margin-top:2px;">
                                {row['Delivered Qty']} Q &nbsp;&middot;&nbsp; &#8377;{row['Price (&#8377;/Quintal)']}/Q
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        current = str(row["Payment Status"]).strip()
                        new_status = st.selectbox(
                            "Payment Status",
                            options=["Pending", "Received"],
                            index=0 if current.lower() != "received" else 1,
                            key=f"pay_status_{selected_order_id}_{row['Variety']}",
                            label_visibility="collapsed"
                        )
                        updated_statuses[row["Variety"]] = new_status

                st.markdown("")
                if st.button("💾 Save Payment Status", type="primary", key="save_payment_btn"):
                    sheet_data_write = items_sheet.get_all_values()
                    raw_hdrs         = sheet_data_write[0]
                    hdrs             = [h.strip() for h in raw_hdrs]
                    df_write         = pd.DataFrame(sheet_data_write[1:], columns=hdrs)
                    df_write         = df_write.applymap(lambda x: x.strip() if isinstance(x, str) else x)
                    if "Payment Status" not in df_write.columns:
                        df_write["Payment Status"] = "Pending"
                    for variety, status in updated_statuses.items():
                        mask = (
                            (df_write["Order ID"].astype(str).str.strip() == selected_order_id) &
                            (df_write["Variety"].str.strip() == variety)
                        )
                        df_write.loc[mask, "Payment Status"] = status
                    df_write = df_write.replace([float("inf"), -float("inf")], "").fillna("")
                    rows_out = [[str(v) if v != "" else "" for v in r] for r in df_write.values.tolist()]
                    items_sheet.update("A1", [raw_hdrs] + rows_out, value_input_option="USER_ENTERED")
                    load_admin_data.clear()
                    st.success(f"✅ Payment status updated for Order {selected_order_id}!")
                    st.rerun()

        st.markdown("---")

        # ── Outstanding by Shop ──
        st.markdown("#### 🏪 Outstanding Amount by Shop")
        today = pd.Timestamp(datetime.now().date())
        due_eligible = df_all[
            (df_all["STATUS"].str.strip().isin(["Delivered", "Partial Delivery"])) &
            (df_all["Delivery Date"].notna())
        ].copy()

        if not due_eligible.empty:
            due_eligible["Days Since Delivery"] = (today - due_eligible["Delivery Date"]).dt.days
            shop_outstanding = {}
            for (order_id, shop, agent), grp in due_eligible.groupby(["Order ID", "Shop Name", "Agent Name"]):
                unpaid_rows = grp[grp["Payment Status"].str.strip().str.lower() != "received"]
                if unpaid_rows.empty:
                    continue
                unpaid_val = (unpaid_rows["Delivered Qty"] * unpaid_rows["Price (₹/Quintal)"]).sum()
                if shop not in shop_outstanding:
                    shop_outstanding[shop] = 0
                shop_outstanding[shop] += unpaid_val

            if shop_outstanding:
                max_out = max(shop_outstanding.values())
                outstanding_html = ""
                for shop_name, amount in sorted(shop_outstanding.items(), key=lambda x: -x[1]):
                    bar_pct = int((amount / max_out) * 100)
                    outstanding_html += f"""
                    <div style="background:white; border-radius:10px; padding:12px 16px; margin-bottom:8px;
                                box-shadow:0 2px 6px rgba(0,0,0,0.06); display:flex; align-items:center; gap:14px;">
                        <div style="font-size:20px;">🏪</div>
                        <div style="flex:1;">
                            <div style="font-weight:600; font-size:15px; color:#2b2b2b;">{shop_name}</div>
                            <div style="background:#fdecea; border-radius:4px; height:6px; margin-top:6px;">
                                <div style="background:#e74c3c; width:{bar_pct}%; height:6px; border-radius:4px;"></div>
                            </div>
                        </div>
                        <div style="font-size:16px; font-weight:700; color:#e74c3c; min-width:110px; text-align:right;">
                            &#8377;{amount:,.0f}
                        </div>
                    </div>"""
                html_block(outstanding_html, height=card_list_height(len(shop_outstanding), item_px=72))
            else:
                st.success("🎉 No outstanding amounts!")

        st.markdown("---")
        st.markdown("#### ⏰ Payment Due Tracker")
        st.caption("Delivered orders with outstanding payments — colour coded by urgency.")

        if due_eligible.empty:
            st.info("No delivered orders found.")
        else:
            order_groups = due_eligible.groupby(["Order ID", "Shop Name", "Agent Name"])
            due_rows = []
            for (order_id, shop, agent), grp in order_groups:
                unpaid_rows = grp[grp["Payment Status"].str.strip().str.lower() != "received"]
                if unpaid_rows.empty:
                    continue
                latest_date  = grp["Delivery Date"].max()
                days_since   = (today - latest_date).days
                total_value  = grp[total_col_a].sum() if total_col_a else 0
                unpaid_value = (unpaid_rows["Delivered Qty"] * unpaid_rows["Price (₹/Quintal)"]).sum()
                due_rows.append({
                    "order_id":    str(order_id),
                    "shop":        shop,
                    "agent":       agent,
                    "latest_date": latest_date.strftime("%Y-%m-%d"),
                    "total_value": total_value,
                    "unpaid":      unpaid_value,
                    "days":        days_since,
                })

            if not due_rows:
                st.success("🎉 All payments received!")
            else:
                due_rows_sorted = sorted(due_rows, key=lambda x: -x["days"])
                due_tracker_html = ""
                for r in due_rows_sorted:
                    if r["days"] > 15:
                        bg, border, badge = "#fff5f5", "#e74c3c", f'<span style="background:#e74c3c; color:white; border-radius:4px; padding:2px 8px; font-size:11px;">🔴 Overdue {r["days"]}d</span>'
                    elif r["days"] > 7:
                        bg, border, badge = "#fffbf0", "#f39c12", f'<span style="background:#f39c12; color:white; border-radius:4px; padding:2px 8px; font-size:11px;">🟡 Due {r["days"]}d</span>'
                    else:
                        bg, border, badge = "#f9f9f9", "#95a5a6", f'<span style="background:#95a5a6; color:white; border-radius:4px; padding:2px 8px; font-size:11px;">🟢 {r["days"]}d</span>'
                    due_tracker_html += f"""
                    <div style="background:{bg}; border-left:4px solid {border}; border-radius:8px;
                                padding:12px 16px; margin-bottom:8px; box-shadow:0 1px 4px rgba(0,0,0,0.05);">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <span style="font-weight:700; font-size:15px;">Order {r['order_id']}</span>
                                &nbsp;·&nbsp;<span style="color:#555;">{r['shop']}</span>
                                &nbsp;·&nbsp;<span style="color:#888; font-size:13px;">{r['agent']}</span>
                            </div>
                            {badge}
                        </div>
                        <div style="display:flex; gap:24px; margin-top:8px; font-size:13px; color:#666;">
                            <span>📅 Delivered: {r['latest_date']}</span>
                            <span>🧾 Order: &#8377;{r['total_value']:,.0f}</span>
                            <span style="font-weight:700; color:#e74c3c;">💸 Unpaid: &#8377;{r['unpaid']:,.0f}</span>
                        </div>
                    </div>"""
                html_block(due_tracker_html, height=card_list_height(len(due_rows), item_px=88), scrolling=True)

    # ══════════════════════════════
    # TAB 3 — EMPLOYEE PERFORMANCE
    # ══════════════════════════════
    with tab_employee:
        st.markdown("#### 👤 Agent Performance")

        from datetime import date
        import calendar
        today_date = date.today()
        this_year  = today_date.year
        this_month = today_date.month
        last_month = this_month - 1 if this_month > 1 else 12
        last_year  = this_year if this_month > 1 else this_year - 1

        this_ym = f"{this_year}-{this_month:02d}"
        last_ym = f"{last_year}-{last_month:02d}"

        df_all_valid = df_all.dropna(subset=["Date"]).copy()
        df_all_valid["YearMonth"] = df_all_valid["Date"].dt.strftime("%Y-%m")

        df_this = df_all_valid[df_all_valid["YearMonth"] == this_ym]
        df_last = df_all_valid[df_all_valid["YearMonth"] == last_ym]

        this_month_label = f"{calendar.month_abbr[this_month]} {this_year}"
        last_month_label = f"{calendar.month_abbr[last_month]} {last_year}"

        def agent_summary(df):
            if df.empty:
                return pd.DataFrame(columns=["Agent Name", "Orders", "Quintals", "Revenue"])
            return (
                df.groupby("Agent Name")
                .agg(Orders=("Order ID", "nunique"),
                     Quintals=("Quantity (Quintal)", "sum"),
                     Revenue=(total_col_a, "sum") if total_col_a else ("Quantity (Quintal)", "sum"))
                .reset_index()
            )

        this_m = agent_summary(df_this).set_index("Agent Name")
        last_m = agent_summary(df_last).set_index("Agent Name")
        agent_perf = (
            df_all.groupby("Agent Name")
            .agg(Orders=("Order ID", "nunique"),
                 Quintals=("Quantity (Quintal)", "sum"),
                 Revenue=(total_col_a, "sum") if total_col_a else ("Quantity (Quintal)", "sum"))
            .sort_values("Revenue", ascending=False).reset_index()
        )
        max_agent_rev = agent_perf["Revenue"].max() if not agent_perf.empty else 1

        agent_perf_html = ""
        for _, row in agent_perf.iterrows():
            agent   = row["Agent Name"]
            bar_pct = int((row["Revenue"] / max_agent_rev) * 100)

            tm_orders = int(this_m.loc[agent, "Orders"])   if agent in this_m.index else 0
            lm_orders = int(last_m.loc[agent, "Orders"])   if agent in last_m.index else 0
            tm_rev    = this_m.loc[agent, "Revenue"]        if agent in this_m.index else 0
            lm_rev    = last_m.loc[agent, "Revenue"]        if agent in last_m.index else 0

            order_diff  = tm_orders - lm_orders
            rev_diff    = tm_rev - lm_rev
            order_arrow = (f'<span style="color:#27ae60;">▲ {order_diff}</span>'      if order_diff > 0 else
                           f'<span style="color:#e74c3c;">▼ {abs(order_diff)}</span>' if order_diff < 0 else
                           '<span style="color:#888;">━ 0</span>')
            rev_arrow   = (f'<span style="color:#27ae60;">▲ &#8377;{rev_diff:,.0f}</span>'      if rev_diff > 0 else
                           f'<span style="color:#e74c3c;">▼ &#8377;{abs(rev_diff):,.0f}</span>' if rev_diff < 0 else
                           '<span style="color:#888;">━ &#8377;0</span>')

            agent_perf_html += f"""
            <div style="background:white; border-radius:12px; padding:12px 18px; margin-bottom:8px;
                        box-shadow:0 2px 8px rgba(0,0,0,0.06);">
                <div style="display:flex; align-items:center; gap:14px;">
                    <div style="font-size:28px;">👤</div>
                    <div style="flex:1;">
                        <div style="font-weight:700; font-size:16px; color:#2b2b2b;">{agent}</div>
                        <div style="font-size:12px; color:#888; margin-top:1px;">
                            {row['Orders']} total orders · {row['Quintals']:,.1f} Q total
                        </div>
                        <div style="background:#f0e8d0; border-radius:4px; height:5px; margin-top:6px;">
                            <div style="background:#8B6F2F; width:{bar_pct}%; height:5px; border-radius:4px;"></div>
                        </div>
                    </div>
                    <div style="text-align:right; min-width:120px;">
                        <div style="font-size:18px; font-weight:700; color:#4A7C59;">&#8377;{row['Revenue']:,.0f}</div>
                        <div style="font-size:12px; color:#888;">All time revenue</div>
                    </div>
                </div>
                <div style="display:flex; gap:0; margin-top:8px; border-top:1px solid #f0e8d0; padding-top:8px;">
                    <div style="flex:1; text-align:center; border-right:1px solid #f0e8d0;">
                        <div style="font-size:11px; color:#888;">{this_month_label} Orders</div>
                        <div style="font-size:15px; font-weight:700; color:#2b2b2b;">{tm_orders}</div>
                        <div style="font-size:11px;">{order_arrow} vs {last_month_label}</div>
                    </div>
                    <div style="flex:1; text-align:center;">
                        <div style="font-size:11px; color:#888;">{this_month_label} Revenue</div>
                        <div style="font-size:15px; font-weight:700; color:#2b2b2b;">&#8377;{tm_rev:,.0f}</div>
                        <div style="font-size:11px;">{rev_arrow} vs {last_month_label}</div>
                    </div>
                </div>
            </div>"""

        html_block(agent_perf_html, height=len(agent_perf) * 158 + 10, scrolling=True)

    st.markdown("---")
    st.download_button(label="⬇️ Download Full Data as CSV",
                        data=df_all.to_csv(index=False).encode("utf-8"),
                        file_name=f"full_data_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv")

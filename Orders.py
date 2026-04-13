import streamlit as st
import streamlit.components.v1 as components
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import urllib.parse
import pandas as pd
import uuid
import calendar as cal_module

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="Sri Rudra Rice Order Form",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# FONT STYLE
# =====================================================
FONT_STYLE = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@400;600;700&display=swap');
  * { font-family: 'Source Sans Pro', sans-serif; box-sizing: border-box; margin: 0; padding: 0; }
  body { background: transparent; overflow-x: auto; overflow-y: hidden; }
</style>
"""

FONT_STYLE_SCROLL = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@400;600;700&display=swap');
  * { font-family: 'Source Sans Pro', sans-serif; box-sizing: border-box; margin: 0; padding: 0; }
  body { background: transparent; overflow-x: auto; overflow-y: auto; }
  ::-webkit-scrollbar { height: 6px; width: 6px; }
  ::-webkit-scrollbar-track { background: #f0e8d0; border-radius: 3px; }
  ::-webkit-scrollbar-thumb { background: #c8b56e; border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: #8B6F2F; }
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
SHEET_KEY      = "1dA4A8nbdwS_wcKVb3dA5ofqDlACw07SL3i0mtPYSo0Q"
ITEMS_SHEET    = "Order_Items"
SUMMARY_SHEET  = "Orders_Summary"

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def clean_number(value) -> float:
    if value is None or value == "":
        return 0.0
    cleaned = str(value).replace("₹", "").replace(",", "").strip()
    if not cleaned:
        return 0.0
    HEADER_STRINGS = {
        "quantity (quintal)", "price (₹/quintal)", "price (rs/quintal)",
        "delivered qty", "pending qty", "amount received",
        "n/a", "none", "-", "—", "na"
    }
    if cleaned.lower() in HEADER_STRINGS:
        return 0.0
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0


def format_inr(value: float) -> str:
    value = int(round(value))
    s = str(abs(value))
    if len(s) <= 3:
        result = s
    else:
        last3 = s[-3:]
        rest  = s[:-3]
        parts = []
        while len(rest) > 2:
            parts.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.append(rest)
        result = last3
        for p in parts:
            result = p + "," + result
    return ("-" if value < 0 else "") + result


def generate_order_id(sheet) -> str:
    try:
        values   = sheet.col_values(2)[1:]
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
        lines.append(f"{item['variety']} : {item['quantity']} QTL x ₹{item['price']} = ₹{format_inr(total)}")
    lines.append(f"Grand Total : ₹{format_inr(grand_total)}")
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


def write_order_to_sheet(items_ws, summary_ws, order_id, shop, contact, agent, valid_items, grand_total):
    today = datetime.now().strftime("%Y-%m-%d")
    rows  = [[today, order_id, shop, contact, agent,
              item["variety"], item["quantity"], item["price"], item["total"],
              0, item["quantity"], "", "Order Accepted"] for item in valid_items]
    items_ws.append_rows(rows, value_input_option="USER_ENTERED")
    summary_ws.append_row(
        [today, order_id, shop, agent, sum(i["quantity"] for i in valid_items), grand_total],
        value_input_option="USER_ENTERED"
    )


def html_block(html: str, height: int, scrolling: bool = False):
    components.html(FONT_STYLE + html, height=height, scrolling=scrolling)


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if "Order ID" in df.columns:
        df = df[df["Order ID"].astype(str).str.strip().replace("", pd.NA).notna()]
        df = df[df["Order ID"].astype(str).str.strip() != ""]
    return df.reset_index(drop=True)


# =====================================================
# MONTHLY SHEET MANAGEMENT
# =====================================================

MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]

def get_monthly_sheet_name() -> str:
    now = datetime.now()
    return f"{MONTH_NAMES[now.month - 1]} Orders"


def is_monthly_sheet(name: str) -> bool:
    if name == ITEMS_SHEET:
        return True
    parts = name.split(" ")
    return len(parts) == 2 and parts[0] in MONTH_NAMES and parts[1] == "Orders"


def ensure_monthly_sheet(ss, template_ws):
    sheet_name = get_monthly_sheet_name()
    try:
        return ss.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        new_ws  = ss.add_worksheet(title=sheet_name, rows=1000, cols=20)
        headers = template_ws.row_values(1)
        if headers:
            new_ws.append_row(headers, value_input_option="USER_ENTERED")
        return new_ws


def get_all_monthly_records(ss):
    all_records = []
    for ws in ss.worksheets():
        if is_monthly_sheet(ws.title):
            try:
                records = ws.get_all_records()
                all_records.extend(records)
            except Exception:
                pass
    return all_records


# =====================================================
# GOOGLE SHEETS CONNECTION
# =====================================================
@st.cache_resource
def get_sheets():
    scope  = ["https://www.googleapis.com/auth/spreadsheets",
               "https://www.googleapis.com/auth/drive"]
    creds  = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    ss         = client.open_by_key(SHEET_KEY)
    items_ws   = ss.worksheet(ITEMS_SHEET)
    summary_ws = ss.worksheet(SUMMARY_SHEET)
    return ss, items_ws, summary_ws


spreadsheet, items_sheet, summary_sheet = get_sheets()


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


@st.cache_data(ttl=60)
def load_all_records():
    return get_all_monthly_records(spreadsheet)


# =====================================================
# SHARED CSS
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
[data-testid="stImage"] img {
    display: block !important;
    margin-left: auto !important;
    margin-right: auto !important;
}
@media (max-width: 768px) {
    h3, h2 { font-size: 22px !important; font-weight: bold !important; }
    div[data-testid="stMarkdownContainer"] h3 { font-size: 22px !important; font-weight: bold !important; }
    body, label, span, p { color: #2b2b2b !important; }
    body [data-testid="stMetricLabel"],
    body [data-testid="stMetricLabel"] p,
    body [data-testid="stMetricLabel"] span,
    body [data-testid="stMetricValue"],
    body [data-testid="stMetricValue"] p,
    body [data-testid="stMetricValue"] span,
    body [data-testid="stMetricValue"] div { color: #000000 !important; }
    .block-container { padding-left: 12px !important; padding-right: 12px !important; }
    h1 { font-size: 26px !important; text-align: center !important; }
    h3 { font-size: 18px !important; text-align: center !important; }
    [data-testid="stImage"] img { max-width: 150px !important; margin-left: 110px !important; margin-right: 0 !important; }
    div[data-testid="stFormSubmitButton"] button,
    div.stButton > button {
        background-color: #8B6F2F !important; color: white !important;
        border: none !important; border-radius: 8px !important; width: 100%; margin-top: 8px;
    }
    div[data-testid="stFormSubmitButton"] button p,
    div.stButton > button p { color: white !important; }
    div[data-testid="stHorizontalBlock"] { display: flex !important; flex-direction: row !important; }
    div[data-testid="stHorizontalBlock"] > div { flex: 1 !important; }
    div[role="listbox"] div[role="option"] { color: #2b2b2b !important; font-size: 16px !important; background-color: white !important; }
    .stDataFrameContainer div[data-baseweb="select"] div[class*="singleValue"],
    .stDataFrameContainer div[data-baseweb="select"] div[class*="option"],
    .stDataFrameContainer div[data-baseweb="select"] div[class*="menu"] { color: #2b2b2b !important; font-weight: normal !important; font-size: 16px !important; }
    .brand-title { margin-left: 0% !important; }
    .metrics-row [data-testid="stMetricLabel"],
    .metrics-row [data-testid="stMetricLabel"] * { font-size: 14px !important; font-weight: 700 !important; color: #000000 !important; white-space: normal !important; word-break: break-word !important; }
    .metrics-row [data-testid="stMetricValue"],
    .metrics-row [data-testid="stMetricValue"] * { font-size: 18px !important; font-weight: 700 !important; color: #000000 !important; word-break: break-word !important; }
    .metrics-row { margin-bottom: 0px !important; padding-bottom: 0px !important; }
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
                    ["📦 Order Booking", "📊 Order Status", "✏️ Edit Order", "🔍 Order History"],
                    horizontal=True, index=0)

    # ══════════════════════════════════════════════════
    # ORDER BOOKING
    # ══════════════════════════════════════════════════
    if page == "📦 Order Booking":
        st.markdown("### 🏪 Shop Details")
        col1, col2, col3 = st.columns(3)
        with col1:
            shop_name = st.selectbox("Shop Name", options=existing_shops, index=None,
                                      placeholder="Type shop name...", accept_new_options=True, key="shop_name")
        if shop_name in shop_phone:
            st.session_state.contact_number = shop_phone.get(shop_name, "")
            st.session_state.agent_name     = shop_agent.get(shop_name, "")
        with col2:
            contact_number = st.text_input("Contact Number", key="contact_number")
        with col3:
            agent_name = st.text_input("Agent Name", key="agent_name")
        st.markdown("---")

        with st.form("order_form"):
            st.markdown("### 🌾 Rice Varieties")
            grand_total   = 0.0
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
                    item_total   = quantity * price
                    grand_total += item_total
                    order_details.append({"variety": variety, "quantity": quantity, "price": price, "total": item_total})
                    if quantity > 0:
                        st.caption(f"Item Total: ₹ {format_inr(item_total)}")
                    st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("## 💰 Order Summary")
            valid_count = len([i for i in order_details if i["quantity"] > 0])
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Items", valid_count)
            with col2:
                st.metric("Grand Total ₹", f"{format_inr(grand_total)}")
            st.markdown("---")
            col_a, col_b, col_c = st.columns([1, 1, 1])
            with col_a:
                add_more      = st.form_submit_button("➕ Add Item")
            with col_b:
                remove_one    = st.form_submit_button("➖ Remove Last Item")
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
            if not valid_items:    errors.append("At least one rice item with quantity > 0 is required.")
            if errors:
                for e in errors:
                    st.error(e)
                st.stop()
            monthly_ws = ensure_monthly_sheet(spreadsheet, items_sheet)
            order_id   = generate_order_id(items_sheet)
            write_order_to_sheet(monthly_ws, summary_sheet, order_id, shop_name,
                                 contact_number, agent_name, valid_items, grand_total)
            load_shops.clear()
            load_all_records.clear()
            st.session_state.last_order_id = order_id
            st.session_state.last_wa_link  = build_whatsapp_link(contact_number, shop_name, valid_items, grand_total)
            st.success(f"✅ Order Confirmed | Order ID : {order_id}")
            st.markdown(f"[📱 Send WhatsApp Confirmation]({st.session_state.last_wa_link})")
        elif st.session_state.last_order_id:
            st.success(f"✅ Last Order ID : {st.session_state.last_order_id}")
            if st.session_state.last_wa_link:
                st.markdown(f"[📱 Send WhatsApp Confirmation]({st.session_state.last_wa_link})")
        if st.button("➕ New Order"):
            st.session_state.rice_items    = 2
            st.session_state.last_order_id = None
            st.session_state.last_wa_link  = None
            for k in list(st.session_state.keys()):
                if k.startswith(("qty_", "price_", "variety_", "custom_variety_",
                                 "shop_name", "contact_number", "agent_name")):
                    st.session_state.pop(k, None)
            st.rerun()

    # ══════════════════════════════════════════════════
    # ORDER STATUS
    # ══════════════════════════════════════════════════
    elif page == "📊 Order Status":
        st.markdown("### 📊 Orders Dashboard")
        records = load_all_records()
        df      = pd.DataFrame(records)
        df      = clean_dataframe(df)
        if df.empty:
            st.info("No orders found.")
            st.stop()

        grouped_status   = df.groupby("Order ID")["STATUS"].apply(list)
        completed_orders = sum(1 for s in grouped_status if all(x.strip() == "Delivered" for x in s))
        pending_orders   = len(grouped_status) - completed_orders

        st.markdown('<div class="metrics-row">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        col1.metric("Pending Orders",   pending_orders)
        col2.metric("Completed Orders", completed_orders)
        col3.metric("Total Orders",     len(grouped_status))
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
        orders  = []
        for order_id, group in grouped:
            statuses = [str(s).strip() for s in group["STATUS"].tolist()]
            if all(s == "Delivered" for s in statuses):
                continue
            pending_total  = 0.0
            varieties_list = []
            for _, row in group.iterrows():
                total_qty = clean_number(row["Quantity (Quintal)"])
                delivered = clean_number(row.get("Delivered Qty", 0))
                pending   = max(total_qty - delivered, 0)
                pending_total += pending
                if pending > 0:
                    varieties_list.append(f"{row['Variety']} – {pending:g}Q")
            orders.append({
                "Order ID":  str(order_id),
                "Shop":      group["Shop Name"].iloc[0],
                "Agent":     group["Agent Name"].iloc[0],
                "Date":      group["Date"].iloc[0],
                "Total Qty": pending_total,
                "Varieties": ", ".join(varieties_list),
                "STATUS":    determine_order_status(statuses)
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

        # ── Status Update table ──
        st.markdown("### 📦 Update Order Status")
        original_statuses = {str(row["Order ID"]): str(row["STATUS"]) for _, row in orders_df.iterrows()}
        edited_df = st.data_editor(
            orders_df, use_container_width=True, hide_index=True, key="orders_editor",
            column_config={"STATUS": st.column_config.SelectboxColumn("STATUS", options=STATUS_OPTIONS)},
            disabled=["Order ID", "Shop", "Agent", "Date", "Total Qty", "Varieties"]
        )

        newly_partial  = [
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
            order_rows    = df[df["Order ID"].astype(str).str.strip() == selected_order.strip()]
            delivery_date = st.date_input("Delivery Date", key=f"partial_delivery_date_{selected_order}")
            order_updates = []
            for i, row in order_rows.iterrows():
                variety   = row["Variety"]
                total_qty = clean_number(row["Quantity (Quintal)"])
                delivered = clean_number(row.get("Delivered Qty", 0))
                pending   = max(total_qty - delivered, 0)
                if pending <= 0:
                    continue
                col1, col2, col3 = st.columns([2, 1, 1])
                col1.write(f"**{variety}**")
                col2.write(f"Pending: {pending}Q")
                deliver_now = col3.number_input(f"Deliver {variety}", min_value=0.0, max_value=pending,
                                                 step=1.0, key=f"deliver_{selected_order}_{i}")
                order_updates.append({"variety": variety, "deliver_now": deliver_now,
                                       "pending": pending, "delivered": delivered,
                                       "delivery_date": delivery_date})
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
            selected_label      = st.selectbox("Select Order", options=list(partial_shop_options.keys()), key="add_partial_select")
            selected_partial_id = partial_shop_options[selected_label]
            order_rows          = df[df["Order ID"].astype(str).str.strip() == selected_partial_id]
            delivery_date_ap    = st.date_input("Delivery Date", key="add_partial_date")
            order_updates_ap    = []
            for i, row in order_rows.iterrows():
                variety   = row["Variety"]
                total_qty = clean_number(row["Quantity (Quintal)"])
                delivered = clean_number(row.get("Delivered Qty", 0))
                pending   = max(total_qty - delivered, 0)
                if pending <= 0:
                    continue
                col1, col2, col3 = st.columns([2, 1, 1])
                col1.write(f"**{variety}**")
                col2.write(f"Pending: {pending}Q")
                deliver_now = col3.number_input(f"Deliver {variety}", min_value=0.0, max_value=pending,
                                                 step=1.0, key=f"add_partial_deliver_{i}")
                order_updates_ap.append({"variety": variety, "deliver_now": deliver_now,
                                          "pending": pending, "delivered": delivered,
                                          "delivery_date": delivery_date_ap})
            delivery_updates[selected_partial_id] = order_updates_ap

        if update_clicked:
            # Build map of all sheets with order data
            all_ws_map = {}
            for ws in spreadsheet.worksheets():
                name = ws.title
                if is_monthly_sheet(name):
                    try:
                        ws_vals = ws.get_all_values()
                        if len(ws_vals) < 2:
                            continue
                        hdrs_tmp = [h.strip() for h in ws_vals[0]]
                        df_tmp   = pd.DataFrame(ws_vals[1:], columns=hdrs_tmp)
                        df_tmp   = df_tmp.applymap(lambda x: x.strip() if isinstance(x, str) else x)
                        df_tmp["Order ID"] = df_tmp["Order ID"].astype(str).str.strip()
                        all_ws_map[name]   = {"ws": ws, "raw_headers": ws_vals[0], "df": df_tmp}
                    except Exception:
                        pass

            orders_to_update = {str(row["Order ID"]).strip(): str(row["STATUS"]).strip()
                                 for _, row in edited_df.iterrows()}

            for sheet_name, meta in all_ws_map.items():
                df_sheet = meta["df"].copy()
                raw_hdrs = meta["raw_headers"]
                ws_obj   = meta["ws"]
                changed  = False

                for oid, new_status in orders_to_update.items():
                    if oid not in df_sheet["Order ID"].values:
                        continue
                    old_status = original_statuses.get(oid, "").strip()
                    df_sheet.loc[df_sheet["Order ID"] == oid, "STATUS"] = new_status
                    changed = True
                    if new_status == "Delivered" and old_status != "Delivered":
                        delivery_date_str = datetime.now().strftime("%Y-%m-%d")
                        for idx in df_sheet[df_sheet["Order ID"] == oid].index:
                            total_qty = clean_number(df_sheet.at[idx, "Quantity (Quintal)"])
                            df_sheet.at[idx, "Delivered Qty"] = str(total_qty)
                            df_sheet.at[idx, "Pending Qty"]   = "0"
                            df_sheet.at[idx, "Delivery Date"] = delivery_date_str

                if delivery_updates:
                    for sel_order, updates in delivery_updates.items():
                        if sel_order not in df_sheet["Order ID"].values:
                            continue
                        for update in updates:
                            if update["deliver_now"] <= 0:
                                continue
                            new_delivered = update["delivered"] + update["deliver_now"]
                            new_pending   = max(update["pending"] - update["deliver_now"], 0)
                            new_st        = "Delivered" if new_pending <= 0 else "Partial Delivery"
                            mask = ((df_sheet["Order ID"] == str(sel_order).strip()) &
                                    (df_sheet["Variety"].str.strip() == str(update["variety"]).strip()))
                            if mask.sum() == 0:
                                continue
                            df_sheet.loc[mask, "Delivered Qty"] = str(new_delivered)
                            df_sheet.loc[mask, "Pending Qty"]   = str(new_pending)
                            df_sheet.loc[mask, "Delivery Date"] = str(update["delivery_date"])
                            df_sheet.loc[mask, "STATUS"]        = new_st
                            changed = True

                if changed:
                    df_sheet  = df_sheet.replace([float("inf"), -float("inf")], "").fillna("")
                    rows_out  = [[str(v) if v != "" else "" for v in r] for r in df_sheet.values.tolist()]
                    ws_obj.update("A1", [raw_hdrs] + rows_out, value_input_option="USER_ENTERED")

            load_all_records.clear()
            st.success("✅ Orders updated successfully!")
            st.session_state.show_add_partial = False
            st.rerun()

    # ══════════════════════════════════════════════════
    # EDIT ORDER PAGE
    # ══════════════════════════════════════════════════
    elif page == "✏️ Edit Order":
        st.markdown("### ✏️ Edit Existing Order")
        records = load_all_records()
        df      = pd.DataFrame(records)
        df      = clean_dataframe(df)
        if df.empty:
            st.info("No orders found.")
            st.stop()

        # Build pending orders list (not fully delivered)
        grouped = df.groupby("Order ID")
        pending_orders_list = []
        for order_id, group in grouped:
            statuses = [str(s).strip() for s in group["STATUS"].tolist()]
            if all(s == "Delivered" for s in statuses):
                continue
            pending_orders_list.append({
                "Order ID": str(order_id),
                "Shop":     group["Shop Name"].iloc[0],
            })

        if not pending_orders_list:
            st.success("🎉 No pending orders to edit.")
            st.stop()

        # Selectbox dropdown showing Order ID + Shop Name
        edit_options = [f"#{o['Order ID']} — {o['Shop']}" for o in pending_orders_list]
        edit_selection = st.selectbox(
            "Select Order to Edit",
            options=edit_options,
            index=None,
            placeholder="Type order ID or shop name...",
            key="edit_order_select_page"
        )

        if not edit_selection:
            st.info("Select an order above to edit it.")
            st.stop()

        edit_order_id = edit_selection.split(" — ")[0].lstrip("#")

        edit_rows    = df[df["Order ID"].astype(str).str.strip() == edit_order_id.strip()].copy()
        edit_shop    = edit_rows["Shop Name"].iloc[0]
        edit_contact = edit_rows["Phone"].iloc[0] if "Phone" in edit_rows.columns else ""
        edit_agent   = edit_rows["Agent Name"].iloc[0]

        # Auto-filled details row
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_input("Shop Name", value=edit_shop, disabled=True, key="edit_autofill_shop")
        with col2:
            st.text_input("Contact Number", value=str(edit_contact), disabled=True, key="edit_autofill_contact")
        with col3:
            st.text_input("Agent Name", value=edit_agent, disabled=True, key="edit_autofill_agent")
        st.markdown("---")

        edit_count_key = f"edit_item_count_{edit_order_id}"
        if edit_count_key not in st.session_state:
            st.session_state[edit_count_key] = len(edit_rows)

        n_edit = st.session_state[edit_count_key]

        with st.form(f"edit_order_form_{edit_order_id}"):
            st.markdown("#### 🌾 Edit Rice Items")
            edit_details = []
            for i in range(n_edit):
                with st.container():
                    st.markdown('<div class="item-card">', unsafe_allow_html=True)
                    st.markdown(f"**Item {i + 1}**")
                    if i < len(edit_rows):
                        ex_row     = edit_rows.iloc[i]
                        ex_variety = str(ex_row["Variety"]) if str(ex_row["Variety"]) in RICE_VARIETIES else "Other"
                        ex_qty     = clean_number(ex_row["Quantity (Quintal)"])
                        price_col_key = "Price (₹/Quintal)" if "Price (₹/Quintal)" in ex_row.index else ex_row.index[ex_row.index.str.lower().str.contains("price")][0] if any(ex_row.index.str.lower().str.contains("price")) else None
                        ex_price   = clean_number(ex_row[price_col_key]) if price_col_key else 0.0
                        ex_custom  = str(ex_row["Variety"]) if str(ex_row["Variety"]) not in RICE_VARIETIES else ""
                    else:
                        ex_variety = RICE_VARIETIES[0]
                        ex_qty     = 0.0
                        ex_price   = 0.0
                        ex_custom  = ""

                    col1, col2, col3 = st.columns([3, 2, 2])
                    with col1:
                        variety_idx = RICE_VARIETIES.index(ex_variety) if ex_variety in RICE_VARIETIES else RICE_VARIETIES.index("Other")
                        variety_sel = st.selectbox("Rice Variety", options=RICE_VARIETIES,
                                                    index=variety_idx, key=f"edit_variety_{edit_order_id}_{i}")
                        if variety_sel == "Other":
                            variety_sel = st.text_input("Enter Rice Variety",
                                                         value=ex_custom,
                                                         key=f"edit_custom_{edit_order_id}_{i}")
                    with col2:
                        qty_val = st.number_input("Quantity (Quintals)", min_value=0.0, step=0.5,
                                                   value=float(ex_qty), key=f"edit_qty_{edit_order_id}_{i}")
                    with col3:
                        price_val = st.number_input("Price per Quintal (₹)", min_value=0.0, step=100.0,
                                                     value=float(ex_price), key=f"edit_price_{edit_order_id}_{i}")
                    st.markdown("</div>", unsafe_allow_html=True)
                    edit_details.append({"variety": variety_sel, "quantity": qty_val,
                                          "price": price_val, "total": qty_val * price_val})

            edit_grand_total = sum(d["total"] for d in edit_details)
            st.metric("Revised Grand Total ₹", format_inr(edit_grand_total))
            st.markdown("---")
            col_ea, col_eb, col_ec = st.columns([1, 1, 1])
            with col_ea:
                edit_add    = st.form_submit_button("➕ Add Item")
            with col_eb:
                edit_remove = st.form_submit_button("➖ Remove Last")
            with col_ec:
                edit_save   = st.form_submit_button("💾 Save Changes", type="primary")

        if edit_add:
            st.session_state[edit_count_key] += 1
            st.rerun()
        if edit_remove and st.session_state[edit_count_key] > 1:
            st.session_state[edit_count_key] -= 1
            st.rerun()

        if edit_save:
            valid_edit_items = [d for d in edit_details if d["quantity"] > 0]
            if not valid_edit_items:
                st.error("At least one item with quantity > 0 is required.")
            else:
                target_ws = None
                for ws in spreadsheet.worksheets():
                    name = ws.title
                    if is_monthly_sheet(name):
                        try:
                            ws_vals     = ws.get_all_values()
                            if len(ws_vals) < 2:
                                continue
                            hdrs_ws     = [h.strip() for h in ws_vals[0]]
                            df_ws_check = pd.DataFrame(ws_vals[1:], columns=hdrs_ws)
                            df_ws_check = df_ws_check.applymap(lambda x: x.strip() if isinstance(x, str) else x)
                            if edit_order_id in df_ws_check["Order ID"].astype(str).str.strip().values:
                                target_ws = ws
                                break
                        except Exception:
                            pass

                if target_ws is None:
                    st.error("Could not find the sheet containing this order.")
                else:
                    ws_vals  = target_ws.get_all_values()
                    raw_hdrs = ws_vals[0]
                    hdrs     = [h.strip() for h in raw_hdrs]
                    df_ws    = pd.DataFrame(ws_vals[1:], columns=hdrs)
                    df_ws    = df_ws.applymap(lambda x: x.strip() if isinstance(x, str) else x)
                    df_ws    = df_ws[df_ws["Order ID"].astype(str).str.strip() != ""]
                    df_ws["Order ID"] = df_ws["Order ID"].astype(str).str.strip()

                    original_date = edit_rows["Date"].iloc[0] if "Date" in edit_rows.columns else datetime.now().strftime("%Y-%m-%d")
                    df_ws = df_ws[df_ws["Order ID"] != edit_order_id]

                    new_rows_data = []
                    for item in valid_edit_items:
                        row_dict = {h: "" for h in hdrs}
                        row_dict.update({
                            "Date":               str(original_date),
                            "Order ID":           edit_order_id,
                            "Shop Name":          edit_shop,
                            "Phone":              str(edit_contact),
                            "Agent Name":         edit_agent,
                            "Variety":            item["variety"],
                            "Quantity (Quintal)": str(item["quantity"]),
                            "Delivered Qty":      "0",
                            "Pending Qty":        str(item["quantity"]),
                            "Delivery Date":      "",
                            "STATUS":             "Order Accepted",
                            "Payment Status":     "",
                            "Amount Received":    "0",
                        })
                        for h in hdrs:
                            if "price" in h.lower() and "quintal" in h.lower():
                                row_dict[h] = str(item["price"])
                        for h in hdrs:
                            if "total" in h.lower():
                                row_dict[h] = str(item["total"])
                        new_rows_data.append(row_dict)

                    new_df = pd.DataFrame(new_rows_data, columns=hdrs)
                    df_ws  = pd.concat([df_ws, new_df], ignore_index=True)
                    df_ws  = df_ws.replace([float("inf"), -float("inf")], "").fillna("")
                    rows_out = [[str(v) if v != "" else "" for v in r] for r in df_ws.values.tolist()]
                    target_ws.update("A1", [raw_hdrs] + rows_out, value_input_option="USER_ENTERED")

                    try:
                        sum_vals  = summary_sheet.get_all_values()
                        sum_hdrs  = [h.strip() for h in sum_vals[0]]
                        df_sum    = pd.DataFrame(sum_vals[1:], columns=sum_hdrs)
                        df_sum    = df_sum.applymap(lambda x: x.strip() if isinstance(x, str) else x)
                        df_sum["Order ID"] = df_sum["Order ID"].astype(str).str.strip()
                        mask_sum  = df_sum["Order ID"] == edit_order_id
                        if mask_sum.any():
                            new_total_qty = sum(d["quantity"] for d in valid_edit_items)
                            new_total_rev = sum(d["total"]    for d in valid_edit_items)
                            for h in sum_hdrs:
                                if "qty" in h.lower() or "quintal" in h.lower():
                                    df_sum.loc[mask_sum, h] = str(new_total_qty)
                                elif "total" in h.lower() or "value" in h.lower() or "amount" in h.lower():
                                    df_sum.loc[mask_sum, h] = str(new_total_rev)
                            df_sum   = df_sum.replace([float("inf"), -float("inf")], "").fillna("")
                            rows_sum = [[str(v) for v in r] for r in df_sum.values.tolist()]
                            summary_sheet.update("A1", [sum_vals[0]] + rows_sum, value_input_option="USER_ENTERED")
                    except Exception:
                        pass

                    load_all_records.clear()
                    st.session_state.pop(edit_count_key, None)
                    st.success(f"✅ Order {edit_order_id} updated successfully!")
                    st.rerun()

    # ══════════════════════════════════════════════════
    # ORDER HISTORY
    # ══════════════════════════════════════════════════
    elif page == "🔍 Order History":
        st.markdown("### 🔍 Order History")
        records = load_all_records()
        df      = pd.DataFrame(records)
        df      = clean_dataframe(df)
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
        if shop_filter   != "All": filtered = filtered[filtered["Shop Name"] == shop_filter]
        if status_filter != "All": filtered = filtered[filtered["STATUS"]     == status_filter]
        if agent_filter  != "All": filtered = filtered[filtered["Agent Name"] == agent_filter]

        total_col     = next((c for c in filtered.columns if "total" in c.lower()), None)
        total_qty     = filtered["Quantity (Quintal)"].apply(clean_number).sum() if "Quantity (Quintal)" in filtered.columns else 0
        total_value   = filtered[total_col].apply(clean_number).sum() if total_col else 0
        unique_orders = filtered["Order ID"].nunique()

        st.markdown('<div class="metrics-row">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        col1.metric("Matching Orders", unique_orders)
        col2.metric("Total Quintals",  f"{total_qty:,.1f}")
        col3.metric("Total Value ₹",   f"{format_inr(total_value)}")
        st.markdown('</div><hr style="margin-top:8px;margin-bottom:8px;border:none;border-top:1px solid #c8b56e;">', unsafe_allow_html=True)

        display_cols = ["Date", "Order ID", "Shop Name", "Agent Name", "Variety",
                        "Quantity (Quintal)", "Price (₹/Quintal)", total_col, "STATUS"]
        display_cols = [c for c in display_cols if c]
        available    = [c for c in display_cols if c in filtered.columns]
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
        return get_all_monthly_records(spreadsheet)

    df_all = pd.DataFrame(load_admin_data())
    df_all = clean_dataframe(df_all)
    if df_all.empty:
        st.info("No data available.")
        st.stop()

    df_all["Quantity (Quintal)"] = df_all["Quantity (Quintal)"].apply(clean_number)
    df_all["Delivered Qty"]      = df_all["Delivered Qty"].apply(clean_number)
    df_all["Delivery Date"]      = pd.to_datetime(df_all["Delivery Date"], dayfirst=True, errors="coerce")
    df_all["Date"]               = pd.to_datetime(df_all["Date"], dayfirst=True, errors="coerce").dt.normalize()
    if "Payment Status" not in df_all.columns:
        df_all["Payment Status"] = "Pending"
    df_all["Payment Status"] = df_all["Payment Status"].fillna("Pending").astype(str)
    if "Price (₹/Quintal)" in df_all.columns:
        df_all["Price (₹/Quintal)"] = df_all["Price (₹/Quintal)"].apply(clean_number)
    total_col_a = next((c for c in df_all.columns if "total" in c.lower()), None)
    if total_col_a:
        df_all[total_col_a] = df_all[total_col_a].apply(clean_number)

    st.markdown("---")
    # Current month filter for summary metrics
    _now        = datetime.now()
    _this_month = f"{_now.year}-{_now.month:02d}"
    _month_name = MONTH_NAMES[_now.month - 1]
    df_month    = df_all[df_all["Date"].dt.strftime("%Y-%m") == _this_month] if not df_all["Date"].isna().all() else df_all

    st.markdown(f"#### 💰 {_month_name} Sales Summary")
    total_revenue  = df_month[total_col_a].sum() if total_col_a else 0
    total_quintals = df_month["Quantity (Quintal)"].sum()
    total_orders   = df_month["Order ID"].nunique()
    received_mask  = df_month["Payment Status"].str.strip().str.lower() == "received"
    collected_rev  = df_month.loc[received_mask, total_col_a].sum() if total_col_a else 0
    # Pending payments across ALL months (outstanding dues don't reset monthly)
    all_received_mask = df_all["Payment Status"].str.strip().str.lower() == "received"
    all_collected_rev = df_all.loc[all_received_mask, total_col_a].sum() if total_col_a else 0
    all_total_rev     = df_all[total_col_a].sum() if total_col_a else 0
    pending_rev       = all_total_rev - all_collected_rev

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Orders",    total_orders)
    c2.metric("Total Quintals",  f"{total_quintals:,.1f}")
    c3.metric("Total Revenue ₹", f"{format_inr(total_revenue)}")
    c4.metric("Collected ₹",     f"{format_inr(collected_rev)}")
    c5.metric("Pending ₹",       f"{format_inr(pending_rev)}")
    st.markdown("---")

    tab_sales, tab_payments, tab_employee = st.tabs(["📈 Sales", "💳 Payments", "👤 Employee Performance"])

    # ══════════════════════════════
    # TAB 1 — SALES
    # ══════════════════════════════
    with tab_sales:

        # ── Rice Variety Cards — FIX: scrollable, generous height for mobile ──
        st.markdown(f"#### 🌾 {_month_name} Sales by Rice Variety")
        variety_sales = (
            df_month.groupby("Variety")
            .agg(Total_Quintals=("Quantity (Quintal)", "sum"),
                 Total_Revenue=(total_col_a, "sum") if total_col_a else ("Quantity (Quintal)", "sum"))
            .sort_values("Total_Revenue", ascending=False).reset_index()
        )
        max_rev = variety_sales["Total_Revenue"].max() if not variety_sales.empty else 1
        avg_qty = variety_sales["Total_Quintals"].mean() if not variety_sales.empty else 0

        n_cards      = len(variety_sales)
        # Calculate height based on rows of cards (approx 2-3 cards per row on desktop)
        cards_per_row = max(1, min(n_cards, 4))
        n_rows        = -(-n_cards // cards_per_row)  # ceiling division
        cards_height  = min(max(n_rows * 200 + 40, 220), 700)

        all_cards_html = '<div style="display:flex;flex-wrap:wrap;gap:16px;margin-bottom:4px;padding:4px;">'
        for idx, row in variety_sales.iterrows():
            bar_pct      = int((row["Total_Revenue"] / max_rev) * 100)
            is_slow      = row["Total_Quintals"] < (avg_qty * 0.4)
            border_color = "#e74c3c" if is_slow else "#8B6F2F"
            slow_badge   = ('<div style="font-size:11px;background:#fdecea;color:#e74c3c;border-radius:4px;'
                            'padding:2px 6px;display:inline-block;margin-top:4px;">⚠️ Slow Moving</div>') if is_slow else ""
            all_cards_html += f"""
            <div style="background:white;border-radius:12px;padding:16px 14px;
                        box-shadow:0 2px 10px rgba(0,0,0,0.08);
                        border-left:5px solid {border_color};flex:1 1 150px;min-width:148px;max-width:240px;">
                <div style="font-size:18px;font-weight:700;color:{border_color};">{row['Variety']}</div>
                {slow_badge}
                <div style="font-size:12px;color:#666;margin-top:6px;">Quintals Sold</div>
                <div style="font-size:22px;font-weight:700;color:#2b2b2b;">{row['Total_Quintals']:,.1f} Q</div>
                <div style="font-size:12px;color:#666;margin-top:4px;">Revenue</div>
                <div style="font-size:17px;font-weight:600;color:#4A7C59;">&#8377;{format_inr(row['Total_Revenue'])}</div>
                <div style="background:#f0e8d0;border-radius:6px;height:8px;margin-top:10px;">
                    <div style="background:{border_color};width:{bar_pct}%;height:8px;border-radius:6px;"></div>
                </div>
            </div>"""
        all_cards_html += '</div>'

        # scrolling=True so mobile never clips cards
        components.html(FONT_STYLE_SCROLL + all_cards_html, height=cards_height, scrolling=True)

        st.markdown("---")

        # ── Sales Trend ──
        st.markdown("#### 📅 Sales Trend")
        trend_period = st.radio("View by", ["Monthly", "Weekly"], horizontal=True, key="trend_period")
        df_trend     = df_all.dropna(subset=["Date"]).copy()
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
            bars_html     = ""
            for _, tr in trend_data.iterrows():
                h = max(int((tr["Revenue"] / max_trend_rev) * 140), 4)
                bars_html += f"""
                <div style="display:flex;flex-direction:column;align-items:center;flex:1;min-width:50px;">
                    <div style="font-size:11px;color:#4A7C59;font-weight:600;margin-bottom:4px;">
                        &#8377;{format_inr(tr['Revenue'])}
                    </div>
                    <div style="background:#8B6F2F;width:70%;height:{h}px;border-radius:6px 6px 0 0;"></div>
                    <div style="font-size:10px;color:#888;margin-top:4px;text-align:center;
                                word-break:break-all;">{tr['Period']}</div>
                    <div style="font-size:10px;color:#aaa;">{tr['Orders']} orders</div>
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
        for rank, row in shop_rev.iterrows():
            bar_pct = int((row["Revenue"] / shop_rev["Revenue"].max()) * 100)
            medal   = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][rank]
            st.markdown(f"""
            <div style="background:white;border-radius:10px;padding:14px 18px;margin-bottom:8px;
                        box-shadow:0 2px 8px rgba(0,0,0,0.06);display:flex;align-items:center;gap:16px;">
                <div style="font-size:28px;">{medal}</div>
                <div style="flex:1;">
                    <div style="font-weight:700;font-size:16px;color:#2b2b2b;">{row["Shop Name"]}</div>
                    <div style="background:#f0e8d0;border-radius:4px;height:6px;margin-top:6px;">
                        <div style="background:#8B6F2F;width:{bar_pct}%;height:6px;border-radius:4px;"></div>
                    </div>
                </div>
                <div style="text-align:right;min-width:120px;">
                    <div style="font-size:17px;font-weight:700;color:#4A7C59;">&#8377;{format_inr(row["Revenue"])}</div>
                    <div style="font-size:12px;color:#888;">{row["Orders"]} orders · {row["Quintals"]:,.1f} Q</div>
                </div>
            </div>""", unsafe_allow_html=True)

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
        for rank, row in shop_repeat.iterrows():
            bar_pct = int((row["Orders"] / shop_repeat["Orders"].max()) * 100)
            medal   = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][rank]
            st.markdown(f"""
            <div style="background:white;border-radius:10px;padding:14px 18px;margin-bottom:8px;
                        box-shadow:0 2px 8px rgba(0,0,0,0.06);display:flex;align-items:center;gap:16px;">
                <div style="font-size:28px;">{medal}</div>
                <div style="flex:1;">
                    <div style="font-weight:700;font-size:16px;color:#2b2b2b;">{row["Shop Name"]}</div>
                    <div style="background:#f0e8d0;border-radius:4px;height:6px;margin-top:6px;">
                        <div style="background:#C08030;width:{bar_pct}%;height:6px;border-radius:4px;"></div>
                    </div>
                </div>
                <div style="text-align:right;min-width:120px;">
                    <div style="font-size:17px;font-weight:700;color:#C08030;">{row["Orders"]} orders</div>
                    <div style="font-size:12px;color:#888;">&#8377;{format_inr(row["Revenue"])} · {row["Quintals"]:,.1f} Q</div>
                </div>
            </div>""", unsafe_allow_html=True)

    # ══════════════════════════════
    # TAB 2 — PAYMENTS
    # ══════════════════════════════
    with tab_payments:

        st.markdown("#### 💳 Record Payment from Shop")

        all_pay_records = get_all_monthly_records(spreadsheet)
        df_pay_all      = pd.DataFrame(all_pay_records)
        df_pay_all      = clean_dataframe(df_pay_all)

        if df_pay_all.empty:
            st.info("No delivered orders to update.")
        else:
            if "Payment Status"  not in df_pay_all.columns: df_pay_all["Payment Status"]  = "Pending"
            if "Amount Received" not in df_pay_all.columns: df_pay_all["Amount Received"] = "0"
            df_pay_all["Payment Status"] = df_pay_all["Payment Status"].fillna("Pending").astype(str)

            price_col_pay  = next((c for c in df_pay_all.columns if "price" in c.lower() and "quintal" in c.lower()), "Price (₹/Quintal)")
            item_total_col = next((c for c in df_pay_all.columns if "total" in c.lower()), None)

            df_pay_eligible = df_pay_all[
                df_pay_all["STATUS"].str.strip().isin(["Delivered", "Partial Delivery"])
            ].copy()

            def calc_billed(row):
                status = str(row["STATUS"]).strip()
                if status == "Partial Delivery":
                    return clean_number(row["Delivered Qty"]) * clean_number(row[price_col_pay])
                elif item_total_col:
                    val = clean_number(row[item_total_col])
                    if val == 0:
                        return clean_number(row["Delivered Qty"]) * clean_number(row[price_col_pay])
                    return val
                return clean_number(row["Delivered Qty"]) * clean_number(row[price_col_pay])

            df_pay_eligible["_billed"]   = df_pay_eligible.apply(calc_billed, axis=1)
            df_pay_eligible["_received"] = df_pay_eligible["Amount Received"].apply(clean_number)

            shop_list         = sorted(df_pay_eligible["Shop Name"].dropna().unique().tolist())
            selected_shop_pay = st.selectbox("🏪 Select Shop", options=shop_list, index=None,
                                              placeholder="Type shop name...", key="pay_shop_select")

            if selected_shop_pay:
                shop_orders = df_pay_eligible[df_pay_eligible["Shop Name"] == selected_shop_pay].copy()

                order_summary = []
                for order_id, grp in shop_orders.groupby("Order ID"):
                    billed   = grp["_billed"].sum()
                    received = clean_number(grp["Amount Received"].iloc[0])
                    balance  = max(billed - received, 0)
                    pay_stat = str(grp["Payment Status"].iloc[0]).strip()
                    if "Delivery Date" in grp.columns:
                        dated    = grp[grp["Delivery Date"].notna()]
                        raw_date = dated["Delivery Date"].max() if not dated.empty else pd.NaT
                        del_date = pd.to_datetime(raw_date, dayfirst=True, errors="coerce") if pd.notna(raw_date) else pd.NaT
                    else:
                        del_date = pd.NaT
                    if balance > 0:
                        order_summary.append({
                            "order_id": str(order_id),
                            "billed":   billed,
                            "received": received,
                            "balance":  balance,
                            "status":   pay_stat,
                            "del_date": del_date,
                        })

                all_orders_billed = [grp["_billed"].sum()                               for _, grp in shop_orders.groupby("Order ID")]
                all_orders_recv   = [clean_number(grp["Amount Received"].iloc[0])       for _, grp in shop_orders.groupby("Order ID")]
                total_balance     = sum(o["balance"] for o in order_summary)
                total_billed      = sum(all_orders_billed)
                total_recv        = sum(all_orders_recv)

                if not order_summary:
                    st.success(f"🎉 No outstanding payments for {selected_shop_pay}!")
                else:
                    def sort_key_pay(x):
                        try:
                            d = pd.to_datetime(x["del_date"], dayfirst=True, errors="coerce")
                            return (pd.isna(d), d if pd.notna(d) else pd.Timestamp.max)
                        except Exception:
                            return (True, pd.Timestamp.max)
                    order_summary_sorted = sorted(order_summary, key=sort_key_pay)

                    rows_html = ""
                    for o in order_summary_sorted:
                        billed_fmt   = format_inr(o["billed"])
                        received_fmt = format_inr(o["received"])
                        balance_fmt  = format_inr(o["balance"])
                        pay_stat     = o["status"]
                        if pay_stat.lower() == "partial":
                            badge_bg, badge_color, badge_text = "#FAEEDA", "#854F0B", "Partial"
                        elif pay_stat.lower() == "received":
                            badge_bg, badge_color, badge_text = "#EAF3DE", "#3B6D11", "Received"
                        else:
                            badge_bg, badge_color, badge_text = "#FCEBEB", "#A32D2D", "Pending"
                        try:
                            del_d    = pd.to_datetime(o["del_date"], dayfirst=True, errors="coerce")
                            date_str = del_d.strftime("%d-%m-%Y") if pd.notna(del_d) else "—"
                        except Exception:
                            date_str = "—"
                        rows_html += f"""
                        <tr style="border-bottom:0.5px solid #e8e0d0;">
                            <td style="padding:9px 12px;font-size:13px;font-weight:600;color:#1a1a1a;">Order {o["order_id"]}</td>
                            <td style="padding:9px 12px;font-size:13px;color:#333;text-align:center;">{date_str}</td>
                            <td style="padding:9px 12px;font-size:13px;font-weight:600;color:#1a1a1a;text-align:right;">&#8377;{billed_fmt}</td>
                            <td style="padding:9px 12px;font-size:13px;color:#3B6D11;font-weight:600;text-align:right;">&#8377;{received_fmt}</td>
                            <td style="padding:9px 12px;font-size:14px;font-weight:700;color:#8B1A1A;text-align:right;">&#8377;{balance_fmt}</td>
                            <td style="padding:9px 12px;text-align:center;">
                                <span style="background:{badge_bg};color:{badge_color};font-size:11px;font-weight:700;padding:3px 9px;border-radius:20px;">{badge_text}</span>
                            </td>
                        </tr>"""

                    # FIX: max-height + overflow:auto makes the table scrollable on desktop too
                    table_html = f"""
                    <div style="border-radius:10px;overflow:auto;max-height:380px;
                                border:0.5px solid #e0d8c8;margin-bottom:4px;-webkit-overflow-scrolling:touch;">
                        <table style="min-width:500px;width:100%;border-collapse:collapse;font-family:sans-serif;">
                            <thead style="position:sticky;top:0;z-index:2;background:#f5edd6;">
                                <tr style="border-bottom:1px solid #e0d8c8;">
                                    <th style="padding:9px 12px;font-size:12px;font-weight:700;color:#4A3510;text-align:left;">Order</th>
                                    <th style="padding:9px 12px;font-size:12px;font-weight:700;color:#4A3510;text-align:center;">Delivery</th>
                                    <th style="padding:9px 12px;font-size:12px;font-weight:700;color:#4A3510;text-align:right;">Billed</th>
                                    <th style="padding:9px 12px;font-size:12px;font-weight:700;color:#4A3510;text-align:right;">Received</th>
                                    <th style="padding:9px 12px;font-size:12px;font-weight:700;color:#4A3510;text-align:right;">Balance</th>
                                    <th style="padding:9px 12px;font-size:12px;font-weight:700;color:#4A3510;text-align:center;">Status</th>
                                </tr>
                            </thead>
                            <tbody>{rows_html}</tbody>
                            <tfoot>
                                <tr style="background:#f5edd6;border-top:1.5px solid #c8b56e;">
                                    <td colspan="2" style="padding:9px 12px;font-size:13px;font-weight:700;color:#4A3510;">Total</td>
                                    <td style="padding:9px 12px;font-size:13px;font-weight:700;color:#1a1a1a;text-align:right;">&#8377;{format_inr(total_billed)}</td>
                                    <td style="padding:9px 12px;font-size:13px;font-weight:700;color:#3B6D11;text-align:right;">&#8377;{format_inr(total_recv)}</td>
                                    <td style="padding:9px 12px;font-size:15px;font-weight:700;color:#8B1A1A;text-align:right;">&#8377;{format_inr(total_balance)}</td>
                                    <td></td>
                                </tr>
                            </tfoot>
                        </table>
                    </div>"""
                    tbl_iframe_h = min(len(order_summary) * 46 + 110, 420)
                    components.html(FONT_STYLE_SCROLL + table_html, height=tbl_iframe_h, scrolling=True)

                    st.markdown("")
                    st.markdown("##### 💰 Enter Payment Received")
                    amount_input = st.number_input(
                        f"Amount received from {selected_shop_pay} today (₹)",
                        min_value=0.0, step=100.0, key="pay_amount_input"
                    )

                    if st.button("💾 Apply Payment (FIFO by delivery date)", type="primary", key="save_payment_btn"):
                        if amount_input <= 0:
                            st.error("Please enter an amount greater than 0.")
                        else:
                            remaining = float(amount_input)
                            for ws in spreadsheet.worksheets():
                                name = ws.title
                                if not (is_monthly_sheet(name)):
                                    continue
                                try:
                                    ws_vals  = ws.get_all_values()
                                    raw_hdrs = ws_vals[0]
                                    hdrs     = [h.strip() for h in raw_hdrs]
                                    df_w     = pd.DataFrame(ws_vals[1:], columns=hdrs)
                                    df_w     = df_w.applymap(lambda x: x.strip() if isinstance(x, str) else x)
                                    df_w     = df_w[df_w["Order ID"].astype(str).str.strip() != ""]
                                    if "Payment Status"  not in df_w.columns: df_w["Payment Status"]  = "Pending"
                                    if "Amount Received" not in df_w.columns: df_w["Amount Received"] = "0"
                                except Exception:
                                    continue

                                changed = False
                                for o in order_summary_sorted:
                                    if remaining <= 0:
                                        break
                                    order_mask = df_w["Order ID"].astype(str).str.strip() == o["order_id"]
                                    if not order_mask.any():
                                        continue
                                    current_recv = clean_number(df_w.loc[order_mask, "Amount Received"].iloc[0])
                                    pay_now      = min(remaining, o["balance"])
                                    new_recv     = current_recv + pay_now
                                    new_balance  = o["billed"] - new_recv
                                    remaining   -= pay_now
                                    new_status   = "Received" if new_balance <= 0.01 else ("Partial" if new_recv > 0 else "Pending")
                                    df_w.loc[order_mask, "Amount Received"] = str(round(new_recv, 2))
                                    df_w.loc[order_mask, "Payment Status"]  = new_status
                                    changed = True

                                if changed:
                                    df_w     = df_w.replace([float("inf"), -float("inf")], "").fillna("")
                                    rows_out = [[str(v) if v != "" else "" for v in r] for r in df_w.values.tolist()]
                                    ws.update("A1", [raw_hdrs] + rows_out, value_input_option="USER_ENTERED")

                            load_admin_data.clear()
                            applied = float(amount_input) - remaining
                            if remaining > 0:
                                st.success(f"✅ ₹{format_inr(applied)} applied. ₹{format_inr(remaining)} exceeds balance — please verify.")
                            else:
                                st.success(f"✅ ₹{format_inr(applied)} applied successfully using FIFO!")
                            st.rerun()

        st.markdown("---")

        # ── Payment Due Tracker — FIX: sorted by days overdue (most overdue first) ──
        st.markdown("#### ⏰ Payment Due Tracker")
        today        = pd.Timestamp(datetime.now().date())
        due_eligible = df_all[df_all["STATUS"].str.strip().isin(["Delivered", "Partial Delivery"])].copy()

        if not due_eligible.empty:
            shop_due = {}
            for shop, grp in due_eligible.groupby("Shop Name"):
                unpaid_rows = grp[grp["Payment Status"].str.strip().str.lower() != "received"]
                if unpaid_rows.empty:
                    continue
                if "Amount Received" not in grp.columns:
                    grp = grp.copy()
                    grp["Amount Received"] = "0"
                item_total_col_dt = next((c for c in unpaid_rows.columns if "total" in c.lower()), None)

                def calc_billed_dt(row):
                    status = str(row["STATUS"]).strip()
                    if status == "Partial Delivery":
                        return clean_number(row["Delivered Qty"]) * clean_number(row["Price (₹/Quintal)"])
                    elif item_total_col_dt:
                        val = clean_number(row[item_total_col_dt])
                        if val == 0:
                            return clean_number(row["Delivered Qty"]) * clean_number(row["Price (₹/Quintal)"])
                        return val
                    return clean_number(row["Delivered Qty"]) * clean_number(row["Price (₹/Quintal)"])

                billed_value   = unpaid_rows.apply(calc_billed_dt, axis=1).sum()
                received_value = (grp.groupby("Order ID")["Amount Received"]
                                   .first().apply(clean_number).sum())
                unpaid_value   = max(billed_value - received_value, 0)
                dated_rows     = grp[grp["Delivery Date"].notna()]
                if not dated_rows.empty:
                    latest_date = dated_rows["Delivery Date"].max()
                    days_since  = (today - latest_date).days
                    date_str    = latest_date.strftime("%d-%m-%Y")
                else:
                    days_since  = 0
                    date_str    = "—"
                shop_due[shop] = {
                    "shop":    shop,
                    "agent":   grp["Agent Name"].iloc[0],
                    "latest_date": date_str,
                    "unpaid":  unpaid_value,
                    "days":    days_since,
                    "pending_orders": grp["Order ID"].nunique(),
                }

            if not shop_due:
                st.success("🎉 No outstanding amounts!")
            else:
                # FIX: sort by most days overdue descending
                due_rows_sorted = sorted(shop_due.values(), key=lambda x: -x["days"])
                grand_unpaid    = sum(r["unpaid"] for r in due_rows_sorted)
                grand_fmt       = format_inr(grand_unpaid)

                rows_html = ""
                for r in due_rows_sorted:
                    unpaid_fmt = format_inr(r["unpaid"])
                    if r["days"] > 15:
                        badge_bg, badge_color, badge_text = "#FCEBEB", "#A32D2D", f"Overdue {r['days']}d"
                        row_bg = "#fff8f8"
                    elif r["days"] > 7:
                        badge_bg, badge_color, badge_text = "#FAEEDA", "#854F0B", f"Due {r['days']}d"
                        row_bg = "#fffdf5"
                    else:
                        badge_bg, badge_color, badge_text = "#EAF3DE", "#3B6D11", f"{r['days']}d ago"
                        row_bg = "#ffffff"

                    rows_html += f"""
                    <tr style="background:{row_bg};border-bottom:0.5px solid #e8e0d0;">
                        <td style="padding:10px 14px;">
                            <div style="font-size:14px;font-weight:700;color:#1a1a1a;">{r["shop"]}</div>
                            <div style="font-size:12px;font-weight:600;color:#555;margin-top:2px;">{r["agent"]}</div>
                        </td>
                        <td style="padding:10px 14px;font-size:13px;font-weight:600;color:#333;text-align:center;">{r["latest_date"]}</td>
                        <td style="padding:10px 14px;text-align:center;">
                            <span style="background:{badge_bg};color:{badge_color};font-size:12px;font-weight:700;
                                         padding:4px 10px;border-radius:20px;">{badge_text}</span>
                        </td>
                        <td style="padding:10px 14px;font-size:15px;font-weight:700;color:#8B1A1A;text-align:right;">
                            &#8377;{unpaid_fmt}
                        </td>
                    </tr>"""

                # FIX: max-height + overflow:auto makes table scrollable on desktop
                table_html = f"""
                <div style="border-radius:10px;overflow:auto;max-height:480px;
                            border:0.5px solid #e0d8c8;margin-top:4px;-webkit-overflow-scrolling:touch;">
                    <table style="min-width:420px;width:100%;border-collapse:collapse;font-family:sans-serif;">
                        <thead style="position:sticky;top:0;z-index:2;background:#f5edd6;">
                            <tr style="border-bottom:1px solid #e0d8c8;">
                                <th style="padding:10px 14px;font-size:13px;font-weight:700;color:#4A3510;text-align:left;">Shop</th>
                                <th style="padding:10px 14px;font-size:13px;font-weight:700;color:#4A3510;text-align:center;">Last Delivery</th>
                                <th style="padding:10px 14px;font-size:13px;font-weight:700;color:#4A3510;text-align:center;">Status</th>
                                <th style="padding:10px 14px;font-size:13px;font-weight:700;color:#4A3510;text-align:right;">Unpaid Amount</th>
                            </tr>
                        </thead>
                        <tbody>{rows_html}</tbody>
                        <tfoot>
                            <tr style="background:#f5edd6;border-top:1.5px solid #c8b56e;">
                                <td colspan="3" style="padding:10px 14px;font-size:14px;font-weight:700;color:#4A3510;">
                                    Total Outstanding
                                </td>
                                <td style="padding:10px 14px;font-size:16px;font-weight:700;color:#8B1A1A;text-align:right;">
                                    &#8377;{grand_fmt}
                                </td>
                            </tr>
                        </tfoot>
                    </table>
                </div>"""
                table_height = min(len(due_rows_sorted) * 56 + 110, 520)
                components.html(FONT_STYLE_SCROLL + table_html, height=table_height, scrolling=True)

    # ══════════════════════════════
    # TAB 3 — EMPLOYEE PERFORMANCE
    # ══════════════════════════════
    with tab_employee:
        st.markdown("#### 👤 Agent Performance")

        from datetime import date
        today_date = date.today()
        this_year  = today_date.year
        this_month = today_date.month
        last_month = this_month - 1 if this_month > 1 else 12
        last_year  = this_year if this_month > 1 else this_year - 1
        this_ym    = f"{this_year}-{this_month:02d}"
        last_ym    = f"{last_year}-{last_month:02d}"

        df_all_valid = df_all.dropna(subset=["Date"]).copy()
        # Normalize agent names to title case so SATWIK == Satwik == satwik
        df_all_valid["Agent Name"] = df_all_valid["Agent Name"].astype(str).str.strip().str.title()
        df_all_valid["YearMonth"] = df_all_valid["Date"].dt.strftime("%Y-%m")

        df_this          = df_all_valid[df_all_valid["YearMonth"] == this_ym]
        df_last          = df_all_valid[df_all_valid["YearMonth"] == last_ym]
        this_month_label = f"{cal_module.month_abbr[this_month]} {this_year}"
        last_month_label = f"{cal_module.month_abbr[last_month]} {last_year}"

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

        this_m     = agent_summary(df_this).set_index("Agent Name")
        last_m     = agent_summary(df_last).set_index("Agent Name")
        agent_perf = (
            df_all.assign(**{"Agent Name": df_all["Agent Name"].astype(str).str.strip().str.title()})
            .groupby("Agent Name")
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
            tm_orders = int(this_m.loc[agent, "Orders"]) if agent in this_m.index else 0
            lm_orders = int(last_m.loc[agent, "Orders"]) if agent in last_m.index else 0
            tm_rev    = this_m.loc[agent, "Revenue"]      if agent in this_m.index else 0
            lm_rev    = last_m.loc[agent, "Revenue"]      if agent in last_m.index else 0
            order_diff  = tm_orders - lm_orders
            rev_diff    = tm_rev    - lm_rev
            order_arrow = (f'<span style="color:#27ae60;">▲ {order_diff}</span>'      if order_diff > 0 else
                           f'<span style="color:#e74c3c;">▼ {abs(order_diff)}</span>' if order_diff < 0 else
                           '<span style="color:#888;">━ 0</span>')
            rev_arrow   = (f'<span style="color:#27ae60;">▲ &#8377;{format_inr(rev_diff)}</span>'      if rev_diff > 0 else
                           f'<span style="color:#e74c3c;">▼ &#8377;{format_inr(abs(rev_diff))}</span>' if rev_diff < 0 else
                           '<span style="color:#888;">━ &#8377;0</span>')

            agent_perf_html += f"""
            <div style="background:white;border-radius:12px;padding:12px 18px;margin-bottom:8px;
                        box-shadow:0 2px 8px rgba(0,0,0,0.06);">
                <div style="display:flex;align-items:center;gap:14px;">
                    <div style="font-size:28px;">👤</div>
                    <div style="flex:1;">
                        <div style="font-weight:700;font-size:16px;color:#2b2b2b;">{agent}</div>
                        <div style="font-size:12px;color:#888;margin-top:1px;">
                            {row['Orders']} total orders · {row['Quintals']:,.1f} Q total
                        </div>
                        <div style="background:#f0e8d0;border-radius:4px;height:5px;margin-top:6px;">
                            <div style="background:#8B6F2F;width:{bar_pct}%;height:5px;border-radius:4px;"></div>
                        </div>
                    </div>
                    <div style="text-align:right;min-width:120px;">
                        <div style="font-size:18px;font-weight:700;color:#4A7C59;">&#8377;{format_inr(row['Revenue'])}</div>
                        <div style="font-size:12px;color:#888;">All time revenue</div>
                    </div>
                </div>
                <div style="display:flex;gap:0;margin-top:8px;border-top:1px solid #f0e8d0;padding-top:8px;">
                    <div style="flex:1;text-align:center;border-right:1px solid #f0e8d0;">
                        <div style="font-size:11px;color:#888;">{this_month_label} Orders</div>
                        <div style="font-size:15px;font-weight:700;color:#2b2b2b;">{tm_orders}</div>
                        <div style="font-size:11px;">{order_arrow} vs {last_month_label}</div>
                    </div>
                    <div style="flex:1;text-align:center;">
                        <div style="font-size:11px;color:#888;">{this_month_label} Revenue</div>
                        <div style="font-size:15px;font-weight:700;color:#2b2b2b;">&#8377;{format_inr(tm_rev)}</div>
                        <div style="font-size:11px;">{rev_arrow} vs {last_month_label}</div>
                    </div>
                </div>
            </div>"""

        html_block(agent_perf_html, height=min(len(agent_perf) * 158 + 10, 600), scrolling=True)

    st.markdown("---")
    st.download_button(label="⬇️ Download Full Data as CSV",
                        data=df_all.to_csv(index=False).encode("utf-8"),
                        file_name=f"full_data_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv")

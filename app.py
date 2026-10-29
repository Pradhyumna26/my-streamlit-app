## Event Budget Calculator (business idea: Event Management)
## Run with: streamlit run app.py
## Needs Python 3.10 or newer (match-case is used) and a recent Streamlit: pip install --upgrade streamlit
## The app has 3 pages (Home, Menu, Profile) and an icon bar at the bottom to move between them


## Import the libraries: html (safe text for the avatar), datetime (save time), pandas (chart data), streamlit (the app)
import html
from datetime import datetime

import pandas as pd
import streamlit as st


## ---------------------------------------------------------------
## 1. PRICE DATA AND LISTS
## ---------------------------------------------------------------

## Venue rent per day (in Rs.) for each venue type
venue_rates = {
    "Banquet Hall": 50000,
    "Hotel Ballroom": 120000,
    "Garden / Lawn": 35000,
    "Resort": 200000,
}

## Catering cost per guest per day (in Rs.) for each menu type
catering_rates = {
    "Veg": 900,
    "Non-Veg": 1100,
    "Veg + Non-Veg": 1200,
}

## Decoration cost per day (in Rs.) for each theme
decor_rates = {
    "Simple": 15000,
    "Floral": 40000,
    "Premium Theme": 90000,
}

## Add-on prices (in Rs.): three are charged per day, return gifts are charged per guest
addon_rates = {
    "DJ & Sound System": 25000,
    "Photography & Videography": 40000,
    "Stage & Lighting": 30000,
    "Return Gifts (per guest)": 150,
}

## GST rate (18%) and the highest total discount allowed (30%)
GST_RATE = 0.18
MAX_DISCOUNT_PERCENT = 30

## Lists of options used in the dropdowns, the phone check and the special request keywords
event_types = ["Wedding", "Birthday Party", "Corporate Event", "Conference"]
client_types = ["Regular", "Returning Client", "Corporate"]
event_times = ["Morning", "Afternoon", "Evening"]
mobile_start_digits = ["6", "7", "8", "9"]
planning_keywords = ["music", "band", "flower", "stage", "fireworks", "photo"]

## The 3 pages and the icon shown for each one in the bottom bar
pages = {"Home": "🏠", "Menu": "🍽️", "Profile": "👤"}


## ---------------------------------------------------------------
## 2. HELPER FUNCTIONS
## ---------------------------------------------------------------

## Show a number in Indian money format, e.g. 1457772 -> ₹14,57,772.00
def format_money(amount):
    sign = "-" if amount < 0 else ""
    amount = abs(amount)
    whole, decimals = f"{amount:.2f}".split(".")
    if len(whole) > 3:
        last_three = whole[-3:]
        rest = whole[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        whole = ",".join(groups + [last_three])
    return f"{sign}₹{whole}.{decimals}"


## Show a small uppercase section heading with a violet bar on the left
def section_title(text):
    st.markdown(f'<div class="section-title">{text}</div>', unsafe_allow_html=True)


## Remember which page should be shown (runs when a bottom bar button is clicked)
def go_to(page_name):
    st.session_state["page"] = page_name


## Save button clicked: open the box that asks for a name
def start_saving():
    st.session_state["asking_name"] = True
    st.session_state["save_error"] = ""


## Cancel button clicked: close the name box
def cancel_saving():
    st.session_state["asking_name"] = False
    st.session_state["save_error"] = ""


## Confirm button clicked: check the name, then save a copy of the estimate in the history list
def confirm_save():
    estimate = st.session_state["estimate"]
    new_name = st.session_state["save_name"].strip()

    saved_names = []
    for item in st.session_state["history"]:
        saved_names.append(item["name"].lower())

    if new_name == "":
        st.session_state["save_error"] = "Please type a name for this estimate."
    elif new_name.lower() in saved_names:
        st.session_state["save_error"] = f"You already saved an estimate called '{new_name}'. Try another name."
    else:
        saved = dict(estimate)
        saved["name"] = new_name[0].upper() + new_name[1:]
        saved["saved_on"] = datetime.now().strftime("%d %b %Y, %I:%M %p")
        st.session_state["history"].append(saved)
        estimate["saved_as"] = saved["name"]
        st.session_state["asking_name"] = False
        st.session_state["save_error"] = ""
        st.session_state["save_name"] = ""


## Delete one saved estimate (index is its position in the history list)
def delete_estimate(index):
    st.session_state["history"].pop(index)


## Update Expense clicked: check the edited values, then change that one expense (found by its ID)
def update_expense(expense_id):
    new_what = st.session_state[f"edit_what_{expense_id}"].strip()
    new_category = st.session_state[f"edit_cat_{expense_id}"]
    new_amount = st.session_state[f"edit_amt_{expense_id}"]

    if new_what == "":
        st.session_state["expense_message"] = ("error", "Please write what the expense was for.")
    elif new_amount <= 0:
        st.session_state["expense_message"] = ("error", "Amount must be more than 0.")
    else:
        for e in st.session_state["expenses"]:
            if e["id"] == expense_id:
                e["what"] = new_what[0].upper() + new_what[1:]
                e["category"] = new_category
                e["amount"] = new_amount
        st.session_state["expense_message"] = ("success", "Expense updated!")


## Delete This Expense clicked: keep every expense except the one with this ID
def delete_expense(expense_id):
    remaining = []
    for e in st.session_state["expenses"]:
        if e["id"] != expense_id:
            remaining.append(e)
    st.session_state["expenses"] = remaining
    st.session_state["expense_message"] = ("success", "Expense deleted.")


## ---------------------------------------------------------------
## 3. PAGE SETUP AND DARK THEME DESIGN
## ---------------------------------------------------------------

## Page title and icon shown in the browser tab
st.set_page_config(page_title="Event Budget Calculator", page_icon="🎉")

## Dark premium theme (CSS): colours, fonts, cards, inputs, buttons, tables, avatar and the fixed bottom bar
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@600;700;800&display=swap');

    html, body, .stApp, .stApp * { font-family: 'Inter', 'Segoe UI', sans-serif; }

    /* Hide default Streamlit menu and footer */
    #MainMenu, footer { visibility: hidden; }
    header[data-testid="stHeader"] { background: transparent; }

    /* Page background and space at the bottom so the icon bar never hides content */
    .stApp { background-color: #0b0f1a; }
    .block-container { max-width: 820px; padding-top: 2rem; padding-bottom: 10rem !important; }
    .bottom-space { height: 140px; }

    /* All normal text (light on dark) */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4 { color: #e6e9f2; }
    .stApp p, .stApp label, .stApp span, .stApp li,
    .stApp [data-testid="stMarkdownContainer"] p { color: #c3cadb; }
    .stApp [data-testid="stWidgetLabel"] p { font-weight: 500; color: #e6e9f2; }
    .stApp [data-testid="stCaptionContainer"] p { color: #7d88a0; font-size: 0.8rem; }
    .stApp [data-testid="stTooltipIcon"] svg { color: #98a2b8; }

    /* Hero banner */
    .hero {
        background: linear-gradient(135deg, #0f1530 0%, #2a1f6b 55%, #5b4bff 100%);
        padding: 38px 24px; border-radius: 18px; text-align: center;
        margin-bottom: 26px; border: 1px solid #2a3350;
        box-shadow: 0 10px 40px rgba(91,75,255,0.25);
    }
    .stApp .hero h1 {
        margin: 0; font-family: 'Playfair Display', Georgia, serif;
        font-size: clamp(1.6rem, 4.5vw, 2.5rem); font-weight: 700;
        color: #ffffff; letter-spacing: 0.5px; line-height: 1.25;
    }
    .stApp .hero p { margin: 10px 0 0 0; color: #c7c9ff; font-size: 1rem; }

    /* Section headings */
    .section-title {
        font-size: 0.78rem; font-weight: 700; letter-spacing: 1.2px;
        text-transform: uppercase; color: #a5a0ff;
        border-left: 4px solid #7c6cff; padding-left: 10px; margin: 6px 0 14px 0;
    }

    /* Cards (st.container with border) */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: #121826; border: 1px solid #232b3d !important;
        border-radius: 14px; box-shadow: 0 4px 14px rgba(0,0,0,0.35);
    }

    /* Input boxes: dark fill, light text, violet focus glow */
    .stApp input, .stApp textarea,
    .stApp div[data-baseweb="select"] > div,
    .stApp div[data-baseweb="input"],
    .stApp div[data-baseweb="base-input"],
    .stApp div[data-baseweb="textarea"] {
        background-color: #0e1422 !important;
        color: #e6e9f2 !important;
        border-color: #2a3350 !important;
        border-radius: 8px !important;
    }
    .stApp div[data-baseweb="input"]:focus-within,
    .stApp div[data-baseweb="textarea"]:focus-within,
    .stApp div[data-baseweb="select"] > div:focus-within {
        border-color: #7c6cff !important;
        box-shadow: 0 0 0 3px rgba(124,108,255,0.25) !important;
    }
    .stApp input::placeholder, .stApp textarea::placeholder {
        color: #66718a !important; opacity: 1;
    }
    .stApp div[data-baseweb="select"] span,
    .stApp div[data-baseweb="select"] svg { color: #e6e9f2 !important; fill: #e6e9f2 !important; }
    .stApp [data-testid="stNumberInput"] button {
        background-color: #1a2236 !important; color: #e6e9f2 !important; border-color: #2a3350 !important;
    }
    .stApp [data-testid="stNumberInput"] button svg { fill: #e6e9f2 !important; color: #e6e9f2 !important; }

    /* Dropdown list that opens when a selectbox is clicked */
    div[data-baseweb="popover"] ul,
    div[data-baseweb="popover"] li,
    div[data-baseweb="popover"] div[role="option"] {
        background-color: #121826 !important; color: #e6e9f2 !important;
    }
    div[data-baseweb="popover"] li:hover { background-color: #1f2747 !important; }

    /* Slider */
    [data-testid="stSliderThumbValue"] { color: #a5a0ff !important; font-weight: 600; }
    [data-testid="stTickBarMin"], [data-testid="stTickBarMax"] { color: #7d88a0 !important; }
    div[data-baseweb="slider"] div[role="slider"] { background-color: #7c6cff !important; }

    /* Main button: violet with glow */
    div.stButton > button {
        background-color: #7c6cff; color: #ffffff; border: none;
        border-radius: 10px; padding: 0.7rem 2rem; font-weight: 600; width: 100%;
        box-shadow: 0 4px 16px rgba(124,108,255,0.45); transition: all 0.15s ease;
    }
    div.stButton > button:hover {
        background-color: #6a59f5; color: #ffffff; transform: translateY(-1px);
        box-shadow: 0 6px 22px rgba(124,108,255,0.6);
    }
    div.stButton > button p { color: #ffffff !important; font-weight: 600; }

    /* Metric cards */
    [data-testid="stMetric"] {
        background: #121826; padding: 16px; border-radius: 12px;
        border: 1px solid #232b3d; border-top: 4px solid #7c6cff;
        box-shadow: 0 4px 14px rgba(0,0,0,0.35);
    }
    [data-testid="stMetricLabel"] * {
        color: #7d88a0 !important; font-size: 0.75rem !important;
        text-transform: uppercase; letter-spacing: 0.6px;
    }
    [data-testid="stMetricValue"] * { color: #ffffff !important; font-weight: 700; }

    /* Alert boxes (success / info / error) kept dark and readable */
    [data-testid="stAlert"] {
        background-color: #151c30 !important; border: 1px solid #2a3350; border-radius: 10px;
    }
    [data-testid="stAlert"] * { color: #e6e9f2 !important; }

    /* Tables (the last row is highlighted, e.g. TOTAL) */
    .stApp table { background: #121826; border-collapse: collapse; width: 100%; }
    .stApp th { background: #1d2550 !important; color: #ffffff !important; font-weight: 600; border-color: #2a3350 !important; }
    .stApp td { color: #c3cadb !important; background: #121826 !important; border-color: #232b3d !important; }
    .stApp tbody tr:nth-child(even) td { background: #0e1422 !important; }
    .stApp tbody tr:last-child td { background: #2a1f6b !important; color: #ffffff !important; font-weight: 700; }

    /* Expense form */
    [data-testid="stForm"] {
        background: #121826; border: 1px solid #232b3d; border-radius: 14px;
    }
    [data-testid="stFormSubmitButton"] > button {
        background-color: #7c6cff; color: #ffffff; border: none; border-radius: 10px;
        padding: 0.6rem 2rem; font-weight: 600; width: 100%;
        box-shadow: 0 4px 16px rgba(124,108,255,0.45);
    }
    [data-testid="stFormSubmitButton"] > button:hover { background-color: #6a59f5; color: #ffffff; }
    [data-testid="stFormSubmitButton"] > button p { color: #ffffff !important; }

    /* Saved estimates (expanders on the Profile page) */
    [data-testid="stExpander"] {
        background: #121826; border: 1px solid #232b3d !important; border-radius: 12px;
        margin-bottom: 10px;
    }
    [data-testid="stExpander"] summary, [data-testid="stExpander"] summary * {
        color: #e6e9f2 !important; font-weight: 600;
    }

    /* Profile avatar (circle with initials) */
    .avatar {
        width: 84px; height: 84px; border-radius: 50%; margin: 4px auto 8px auto;
        background: linear-gradient(135deg, #5b4bff, #a5a0ff); color: #ffffff;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.9rem; font-weight: 700; box-shadow: 0 6px 20px rgba(91,75,255,0.45);
    }
    .profile-name { text-align: center; color: #e6e9f2; font-weight: 600; font-size: 1.2rem; }
    .profile-sub { text-align: center; color: #7d88a0; font-size: 0.85rem; margin-bottom: 10px; }

    /* Bottom navigation bar: fixed to the bottom, 3 icon buttons in one row */
    .st-key-bottomnav {
        position: fixed; bottom: 0; left: 50%; transform: translateX(-50%);
        width: min(820px, 100%); z-index: 999; background: #0e1422;
        border-top: 1px solid #2a3350; padding: 8px 12px 10px 12px;
        box-shadow: 0 -6px 24px rgba(0,0,0,0.45);
    }
    .st-key-bottomnav [data-testid="stHorizontalBlock"] {
        flex-direction: row !important; flex-wrap: nowrap !important; gap: 8px;
    }
    .st-key-bottomnav [data-testid="stColumn"] {
        min-width: 0 !important; flex: 1 1 0 !important; width: auto !important;
    }
    .st-key-bottomnav div.stButton > button { padding: 0.55rem 0.4rem; border-radius: 12px; }
    .st-key-bottomnav div.stButton > button[data-testid="stBaseButton-secondary"],
    .st-key-bottomnav div.stButton > button[kind="secondary"] {
        background-color: transparent; box-shadow: none; border: 1px solid #232b3d;
    }
    .st-key-bottomnav div.stButton > button[data-testid="stBaseButton-secondary"] p,
    .st-key-bottomnav div.stButton > button[kind="secondary"] p { color: #98a2b8 !important; }
</style>
""", unsafe_allow_html=True)

## Keep typed values when you move to another page (Streamlit forgets a widget value when its page is not shown)
defaults = {
    "page": "Home",
    "history": [],
    "asking_name": False,
    "save_name": "",
    "save_error": "",
    "client_name": "", "city": "", "phone": "", "email": "", "client_type": "Regular",
    "event_type": "Wedding", "event_time": "Morning", "guests": 100, "days": 1,
    "venue": "Banquet Hall", "catering": "Veg", "decor": "Simple",
    "want_dj": False, "want_photo": False, "want_stage": False, "want_gifts": False,
    "discount_percent": 0, "special_requests": "",
    "expenses": [],
    "next_expense_id": 1,
    "expense_message": None,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value
    else:
        st.session_state[key] = st.session_state[key]

## Every expense needs its own ID, so one entry can be edited or deleted safely
for e in st.session_state["expenses"]:
    if "id" not in e:
        e["id"] = st.session_state["next_expense_id"]
        st.session_state["next_expense_id"] += 1

## Banner header shown on every page
st.markdown("""
<div class="hero">
    <h1> Event Budget Calculator</h1>
    <p>Bring your dream event to life with an instant budget estimate</p>
</div>
""", unsafe_allow_html=True)


## ---------------------------------------------------------------
## 4. HOME PAGE: SAVE AREA, ESTIMATE DISPLAY AND MAIN FUNCTION
## ---------------------------------------------------------------

## Save area under the estimate: Save button -> asks for a name -> saved message
def save_area(estimate):
    if estimate["saved_as"] != "":
        st.success(f"✅ Saved as '{estimate['saved_as']}'. Open the Profile page to see it in Saved Estimates.")
    elif not st.session_state["asking_name"]:
        st.button("💾 Save Estimate", key="start_save", on_click=start_saving)
    else:
        with st.container(border=True):
            section_title("Name This Estimate")
            st.text_input(
                "Estimate name", key="save_name",
                placeholder="e.g. rahul wedding - option 1",
            )
            if st.session_state["save_error"] != "":
                st.error(st.session_state["save_error"])
            s1, s2 = st.columns(2)
            with s1:
                st.button("Confirm Save", key="confirm_save", on_click=confirm_save)
            with s2:
                st.button("Cancel", key="cancel_save", on_click=cancel_saving)


## Draw the last calculated estimate from session_state (it stays on screen while you save, add expenses or change page)
def show_estimate():
    estimate = st.session_state["estimate"]
    st.caption("Showing your last calculated estimate. Press Calculate Budget again after changing any input.")
    st.success(f"Estimate for {estimate['name_text']}'s {estimate['event_type']}{estimate['place_text']} is ready! 🎊")

    ## Three big metric cards: total, cost per guest and discount saved
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Budget", format_money(estimate["total"]))
    m2.metric("Cost per Guest", format_money(estimate["cost_per_guest"]))
    m3.metric("Discount Saved", format_money(estimate["discount_amount"]))

    ## Save button (and the name box after clicking it)
    save_area(estimate)

    ## Event summary: booking ID, guests, tables, rating, add-ons, time plan and tip
    section_title("Event Summary")
    st.markdown(
        f"- **Booking ID:** {estimate['booking_id']}\n"
        f"- **Guests:** {estimate['guests']} ({estimate['guest_size']} event, about {estimate['tables']} tables of 10)\n"
        f"- **Budget rating:** {estimate['budget_rating']}\n"
        f"- **Add-ons chosen ({estimate['addon_count']}):** {estimate['addons_text']}\n"
        f"- **Time plan:** {estimate['time_plan']}\n"
        f"- **Tip:** {estimate['event_tip']}"
    )

    ## Cost breakdown table (venue, catering, decoration, add-ons, subtotal, discount, GST, total)
    section_title("Cost Breakdown")
    breakdown = {
        "Item": ["Venue", "Catering", "Decoration", "Add-ons",
                 "Subtotal", f"Discount ({estimate['total_discount_percent']}%)",
                 "GST (18%)", "TOTAL"],
        "Amount": [format_money(estimate["venue_cost"]), format_money(estimate["catering_cost"]),
                   format_money(estimate["decor_cost"]), format_money(estimate["addon_cost"]),
                   format_money(estimate["subtotal"]), "-" + format_money(estimate["discount_amount"]),
                   format_money(estimate["gst"]), format_money(estimate["total"])],
    }
    st.table(breakdown)

    section_title("Where Your Money Goes")
    chart_names = ["Venue", "Catering", "Decor", "Add-ons"]
    chart_costs = [estimate["venue_cost"], estimate["catering_cost"],
                   estimate["decor_cost"], estimate["addon_cost"]]
    chart_colors = ["#7c6cff", "#2dd4bf", "#fb923c", "#facc15"]
    chart_values = {}
    for position, name in enumerate(chart_names):
        column_values = [0, 0, 0, 0]
        column_values[position] = chart_costs[position]
        chart_values[name] = column_values

    chart_data = pd.DataFrame(chart_values, index=chart_names)
    st.bar_chart(chart_data, color=chart_colors)
    
    ## Show the special request back to the user with spotted keywords and a music tip
    if estimate["request_text"] != "":
        st.info(f"📝 Special request noted ({estimate['word_count']} words): {estimate['request_text']}")
        if len(estimate["found_keywords"]) > 0:
            st.caption("Keywords spotted: " + ", ".join(estimate["found_keywords"]))
        if estimate["music_tip"]:
            st.caption("Tip: you mentioned music, so DJ & Sound System or Stage & Lighting may help.")

    ## Notes about which discounts were included
    if estimate["bulk_discount_percent"] > 0:
        st.caption(f"Includes a {estimate['bulk_discount_percent']}% bulk-booking discount.")
    if estimate["client_discount_percent"] > 0:
        st.caption(f"Includes a {estimate['client_discount_percent']}% {estimate['client_type'].lower()} discount.")
    if estimate["total_discount_percent"] == MAX_DISCOUNT_PERCENT:
        st.caption(f"Total discount is capped at {MAX_DISCOUNT_PERCENT}%.")


## Home page: event inputs, Calculate button, estimate display and expense tracker
def home_page():

    ## Reminder to fill the Profile page when no client name is saved yet
    if st.session_state["client_name"].strip() == "":
        st.info("👤 Tip: add your name and contact details on the Profile page.")

    ## Card 1: event type, event time, number of guests and number of days
    with st.container(border=True):
        section_title("Event Details")

        event_type = st.selectbox("Event Type", event_types, key="event_type")
        event_time = st.selectbox("Event Time", event_times, key="event_time")

        col1, col2 = st.columns(2)
        with col1:
            guests = st.number_input(
                "Number of Guests", min_value=0, max_value=5000, step=10, key="guests",
                help="e.g. 150 for a medium wedding, 50 for a birthday party",
            )
            st.caption("e.g. 150 guests")
        with col2:
            days = st.number_input(
                "Number of Days", min_value=1, max_value=7, key="days",
                help="e.g. 3 days for a wedding with mehendi, sangeet and wedding",
            )
            st.caption("e.g. 1 to 7 days")

    ## Card 2: venue, catering menu and decoration theme
    with st.container(border=True):
        section_title("Venue, Food and Decor")

        c1, c2, c3 = st.columns(3)
        with c1:
            venue = st.selectbox("Venue Type", list(venue_rates.keys()), key="venue")
        with c2:
            catering = st.selectbox("Catering Menu", list(catering_rates.keys()), key="catering")
        with c3:
            decor = st.selectbox("Decoration Theme", list(decor_rates.keys()), key="decor")

    ## Card 3: add-on checkboxes, manual discount slider and special requests
    with st.container(border=True):
        section_title("Add-on Services")

        want_dj = st.checkbox("DJ & Sound System (+₹25,000/day)", key="want_dj")
        want_photo = st.checkbox("Photography & Videography (+₹40,000/day)", key="want_photo")
        want_stage = st.checkbox("Stage & Lighting (+₹30,000/day)", key="want_stage")
        want_gifts = st.checkbox("Return Gifts (+₹150/guest)", key="want_gifts")

        discount_percent = st.slider(
            "Discount offered (%)", min_value=0, max_value=20, key="discount_percent"
        )

        special_requests = st.text_area(
            "Special Requests (optional)", key="special_requests",
            placeholder="e.g. need a stage with flower backdrop and live music band",
        )

    ## Calculate Budget button: runs the whole calculation when clicked
    if st.button("Calculate Budget"):

        ## Remove the old estimate first, so an error never shows old numbers
        st.session_state.pop("estimate", None)

        try:
            ## Read the client details from the Profile page
            client_name = st.session_state["client_name"]
            city = st.session_state["city"]
            phone = st.session_state["phone"]
            email = st.session_state["email"]
            client_type = st.session_state["client_type"]

            ## Clean the text: capital letters for name and city, no spaces or dashes in the phone number, lower case email
            clean_name = client_name.strip().title()
            clean_city = city.strip().title()
            phone_clean = phone.strip().replace(" ", "").replace("-", "")
            if phone_clean.startswith("+91"):
                phone_clean = phone_clean[3:]
            email_clean = email.strip().lower()

            ## Check the phone number (10 digits, starts with 6 to 9) and the email (one @, a dot after it), only if they were typed
            phone_ok = True
            if phone_clean != "":
                if len(phone_clean) != 10 or not phone_clean.isdigit():
                    phone_ok = False
                elif phone_clean[0] not in mobile_start_digits:
                    phone_ok = False

            email_ok = True
            if email_clean != "":
                at_pos = email_clean.find("@")
                if email_clean.count("@") != 1 or at_pos == 0:
                    email_ok = False
                elif "." not in email_clean[at_pos:] or email_clean[at_pos + 1:].startswith("."):
                    email_ok = False
                elif email_clean.endswith("."):
                    email_ok = False

            ## Stop with an error message if the guests, phone or email are wrong
            if guests == 0:
                st.error("Please enter at least 1 guest.")
            elif not phone_ok:
                st.error("Mobile number must be 10 digits and start with 6, 7, 8 or 9. Fix it on the Profile page.")
            elif not email_ok:
                st.error("Please enter a valid email, e.g. rahul@gmail.com. Fix it on the Profile page.")
            else:
                ## Base costs: venue and decoration per day, catering per guest per day
                venue_cost = venue_rates[venue] * days
                catering_cost = catering_rates[catering] * guests * days
                decor_cost = decor_rates[decor] * days

                ## Add-on costs: only the ticked add-ons are added, and their names are collected in a list
                addon_cost = 0
                selected_addons = []
                if want_dj:
                    addon_cost += addon_rates["DJ & Sound System"] * days
                    selected_addons.append("DJ & Sound System")
                if want_photo:
                    addon_cost += addon_rates["Photography & Videography"] * days
                    selected_addons.append("Photography & Videography")
                if want_stage:
                    addon_cost += addon_rates["Stage & Lighting"] * days
                    selected_addons.append("Stage & Lighting")
                if want_gifts:
                    addon_cost += addon_rates["Return Gifts (per guest)"] * guests
                    selected_addons.append("Return Gifts")

                ## Discount rules: bulk booking (200+ guests 5%, 500+ guests 10%) and client type (returning 3%, corporate 5%)
                if guests >= 500:
                    bulk_discount_percent = 10
                elif guests >= 200:
                    bulk_discount_percent = 5
                else:
                    bulk_discount_percent = 0

                if client_type == "Corporate":
                    client_discount_percent = 5
                elif client_type == "Returning Client":
                    client_discount_percent = 3
                else:
                    client_discount_percent = 0

                ## Total discount = bulk + client type + slider, never more than 30%
                subtotal = venue_cost + catering_cost + decor_cost + addon_cost
                total_discount_percent = bulk_discount_percent + client_discount_percent + discount_percent
                total_discount_percent = MAX_DISCOUNT_PERCENT if total_discount_percent > MAX_DISCOUNT_PERCENT else total_discount_percent

                ## GST is charged on the amount after discount
                discount_amount = subtotal * total_discount_percent / 100
                taxable_amount = subtotal - discount_amount
                gst = taxable_amount * GST_RATE
                total = taxable_amount + gst
                cost_per_guest = total / guests

                ## Event size group by number of guests
                if guests >= 500:
                    guest_size = "Grand"
                elif guests >= 200:
                    guest_size = "Large"
                elif guests >= 50:
                    guest_size = "Medium"
                else:
                    guest_size = "Small"

                ## Budget rating by cost per guest
                if cost_per_guest >= 6000:
                    budget_rating = "Luxury"
                elif cost_per_guest >= 3000:
                    budget_rating = "Premium"
                elif cost_per_guest >= 1800:
                    budget_rating = "Standard"
                else:
                    budget_rating = "Economy"

                ## Plan for the chosen time of the day
                if event_time == "Evening":
                    time_plan = "Evening shows off lighting and DJ nights best."
                elif event_time == "Afternoon":
                    time_plan = "Afternoon suits a lunch menu and outdoor lawns."
                else:
                    time_plan = "Morning works well for rituals and brunch."

                ## Tip for the chosen event type
                match event_type:
                    case "Wedding":
                        event_tip = "Weddings usually need extra days for mehendi and sangeet."
                    case "Birthday Party":
                        event_tip = "Birthday parties look great with a simple theme and return gifts."
                    case "Corporate Event":
                        event_tip = "Corporate events need good sound and a proper stage."
                    case _:
                        event_tip = "Conferences need seating, stage and sound set-up."

                ## Number of tables of 10 guests (rounded up when some guests are left over)
                if guests % 10 == 0:
                    tables = guests // 10
                else:
                    tables = guests // 10 + 1

                ## Booking ID from the first 3 letters of the name and city, and the number of guests
                short_name = clean_name.replace(" ", "")
                short_city = clean_city.replace(" ", "")
                name_code = short_name[:3].upper() if short_name else "CLI"
                city_code = short_city[:3].upper() if short_city else "NA"
                booking_id = f"{name_code}-{city_code}-{guests}"

                ## Texts used in the output: client name, place and add-on list
                name_text = clean_name if clean_name else "Client"
                place_text = f" in {clean_city}" if clean_city else ""
                addons_text = ", ".join(selected_addons) if len(selected_addons) > 0 else "None"

                ## Look at the special request: word count, planning keywords found and a music tip
                request_text = special_requests.strip()
                request_lower = request_text.lower()
                word_count = len(request_text.split())
                if request_text != "":
                    request_text = request_text[0].upper() + request_text[1:]

                found_keywords = []
                for word in planning_keywords:
                    if word in request_lower:
                        found_keywords.append(word)

                music_tip = ("band" in request_lower or "music" in request_lower) and not (want_dj or want_stage)

                ## Keep the category amounts for the expense tracker
                st.session_state["budget"] = {
                    "categories": {
                        "Venue": venue_cost,
                        "Catering": catering_cost,
                        "Decoration": decor_cost,
                        "Add-ons": addon_cost,
                        "Other": 0,
                    },
                    "total": total,
                }

                ## Keep the whole estimate in session_state so it can be shown and saved
                st.session_state["estimate"] = {
                    "booking_id": booking_id,
                    "name_text": name_text,
                    "place_text": place_text,
                    "client_name": clean_name,
                    "client_city": clean_city,
                    "client_type": client_type,
                    "event_type": event_type,
                    "event_time": event_time,
                    "guests": guests,
                    "days": days,
                    "venue": venue,
                    "catering": catering,
                    "decor": decor,
                    "addons_text": addons_text,
                    "addon_count": len(selected_addons),
                    "guest_size": guest_size,
                    "tables": tables,
                    "budget_rating": budget_rating,
                    "time_plan": time_plan,
                    "event_tip": event_tip,
                    "venue_cost": venue_cost,
                    "catering_cost": catering_cost,
                    "decor_cost": decor_cost,
                    "addon_cost": addon_cost,
                    "subtotal": subtotal,
                    "bulk_discount_percent": bulk_discount_percent,
                    "client_discount_percent": client_discount_percent,
                    "total_discount_percent": total_discount_percent,
                    "discount_amount": discount_amount,
                    "gst": gst,
                    "total": total,
                    "cost_per_guest": cost_per_guest,
                    "request_text": request_text,
                    "word_count": word_count,
                    "found_keywords": found_keywords,
                    "music_tip": music_tip,
                    "saved_as": "",
                }

                ## A new estimate starts with a closed name box
                st.session_state["asking_name"] = False
                st.session_state["save_error"] = ""
                st.session_state["save_name"] = ""

        except Exception as error:
            ## Safety net so the app never crashes on unexpected input
            st.error(f"Something went wrong: {error}")

    ## Show the estimate (it stays visible while you save, add expenses or change page)
    if "estimate" in st.session_state:
        show_estimate()

    ## Expense tracker: shown only after a budget has been calculated
    if "budget" in st.session_state:
        budget_categories = st.session_state["budget"]["categories"]
        budget_total = st.session_state["budget"]["total"]

        st.markdown("---")
        section_title("Expense Tracker")
        st.caption("Note down every payment you make and compare it with the estimate.")

        ## Form to add one expense (the boxes are emptied after adding)
        with st.form("expense_form", clear_on_submit=True):
            what_for = st.text_input(
                "What was the money spent on?", placeholder="e.g. advance paid to caterer"
            )
            f1, f2 = st.columns(2)
            with f1:
                category = st.selectbox("Category", list(budget_categories.keys()))
            with f2:
                amount = st.number_input("Amount Spent (₹)", min_value=0, value=0, step=500)
            add_clicked = st.form_submit_button("Add Expense")

        ## Check the expense (description typed, amount above 0) and save it with a capital first letter
        if add_clicked:
            if what_for.strip() == "":
                st.error("Please write what the expense was for.")
            elif amount <= 0:
                st.error("Amount must be more than 0.")
            else:
                clean_what = what_for.strip()
                clean_what = clean_what[0].upper() + clean_what[1:]
                st.session_state["expenses"].append(
                    {"id": st.session_state["next_expense_id"], "what": clean_what,
                     "category": category, "amount": amount}
                )
                st.session_state["next_expense_id"] += 1
                st.success("Expense added!")

        ## Message from the last edit or delete (shown once)
        message = st.session_state["expense_message"]
        if message is not None:
            if message[0] == "error":
                st.error(message[1])
            else:
                st.success(message[1])
            st.session_state["expense_message"] = None

        expenses = st.session_state["expenses"]

        if len(expenses) == 0:
            st.info("No expenses added yet. Add your first one above.")
        else:
            ## Table of all expenses entered so far
            section_title("Your Expenses")
            st.table({
                "No.": list(range(1, len(expenses) + 1)),
                "Spent On": [e["what"] for e in expenses],
                "Category": [e["category"] for e in expenses],
                "Amount": [format_money(e["amount"]) for e in expenses],
            })

            ## Edit or remove any expense: choose the entry, change its details and update, or delete it
            with st.expander("✏️ Edit or Remove an Expense"):
                expense_ids = []
                expense_labels = {}
                for position, e in enumerate(expenses, start=1):
                    expense_ids.append(e["id"])
                    expense_labels[e["id"]] = f"{position}. {e['what']} · {format_money(e['amount'])}"

                if st.session_state.get("manage_id") not in expense_ids:
                    st.session_state["manage_id"] = expense_ids[0]

                selected_id = st.selectbox(
                    "Choose the entry", expense_ids,
                    format_func=lambda i: expense_labels[i], key="manage_id",
                )
                for e in expenses:
                    if e["id"] == selected_id:
                        selected = e

                with st.form("edit_expense_form"):
                    st.text_input(
                        "What was the money spent on?", value=selected["what"],
                        key=f"edit_what_{selected_id}",
                    )
                    g1, g2 = st.columns(2)
                    with g1:
                        st.selectbox(
                            "Category", list(budget_categories.keys()),
                            index=list(budget_categories.keys()).index(selected["category"]),
                            key=f"edit_cat_{selected_id}",
                        )
                    with g2:
                        st.number_input(
                            "Amount Spent (₹)", min_value=0, value=selected["amount"], step=500,
                            key=f"edit_amt_{selected_id}",
                        )
                    st.form_submit_button(
                        "Update Expense", on_click=update_expense, args=(selected_id,)
                    )

                st.button(
                    "Delete This Expense", key="delete_expense",
                    on_click=delete_expense, args=(selected_id,),
                )

            ## Add up the actual spending for each category
            spent_by_category = {}
            for name in budget_categories:
                spent_by_category[name] = 0
            for e in expenses:
                spent_by_category[e["category"]] += e["amount"]
            total_spent = sum(spent_by_category.values())
            difference = budget_total - total_spent

            ## Three summary cards: estimated, spent and remaining (or over budget)
            t1, t2, t3 = st.columns(3)
            t1.metric("Estimated Budget", format_money(budget_total))
            t2.metric("Actual Spent", format_money(total_spent))
            if difference >= 0:
                t3.metric("Remaining", format_money(difference))
            else:
                t3.metric("Over Budget By", format_money(-difference))

            ## Progress bar (capped at 100%)
            used = total_spent / budget_total if budget_total > 0 else 0
            st.progress(min(used, 1.0))
            st.caption(f"{used * 100:.0f}% of the estimated budget used")

            ## Overall budget alert: red above 100%, yellow from 80%, green otherwise
            if used > 1:
                st.error(f"🔴 You are over budget by {format_money(-difference)}.")
            elif used >= 0.8:
                st.warning(f"🟡 {used * 100:.0f}% of the budget is used. Spend carefully now.")
            else:
                st.success(f"🟢 Good going! {format_money(difference)} is still available.")

            ## Budget vs actual table for each category with a status
            section_title("Budget vs Actual")
            cat_names, cat_planned, cat_spent, cat_diff, cat_status = [], [], [], [], []
            for name, planned in budget_categories.items():
                spent = spent_by_category[name]
                cat_names.append(name)
                cat_planned.append(format_money(planned))
                cat_spent.append(format_money(spent))
                if spent == 0 and planned == 0:
                    cat_diff.append("-")
                    cat_status.append("No spending")
                elif spent > planned:
                    cat_diff.append("-" + format_money(spent - planned))
                    cat_status.append("🔴 Over budget")
                elif spent == planned:
                    cat_diff.append(format_money(0))
                    cat_status.append("🟡 On budget")
                else:
                    cat_diff.append(format_money(planned - spent))
                    cat_status.append("🟢 Under budget")
            st.table({
                "Category": cat_names,
                "Estimated": cat_planned,
                "Spent": cat_spent,
                "Difference": cat_diff,
                "Status": cat_status,
            })

            ## Buttons to undo mistakes: remove the last expense or clear all of them
            b1, b2 = st.columns(2)
            with b1:
                if st.button("Remove Last Expense"):
                    st.session_state["expenses"].pop()
                    st.rerun()
            with b2:
                if st.button("Clear All Expenses"):
                    st.session_state["expenses"] = []
                    st.rerun()


## ---------------------------------------------------------------
## 5. MENU PAGE
## ---------------------------------------------------------------

## Menu page: price list of venues, catering, decoration and add-ons, plus the discount rules
def menu_page():
    section_title("Our Menu and Price List")
    st.caption("All prices are before discount and 18% GST.")

    ## Venue prices
    with st.container(border=True):
        section_title("Venues")
        st.table({
            "Venue": list(venue_rates.keys()),
            "Price": [format_money(p) + " per day" for p in venue_rates.values()],
        })

    ## Catering prices
    with st.container(border=True):
        section_title("Catering")
        st.table({
            "Menu": list(catering_rates.keys()),
            "Price": [format_money(p) + " per guest, per day" for p in catering_rates.values()],
        })

    ## Decoration prices
    with st.container(border=True):
        section_title("Decoration")
        st.table({
            "Theme": list(decor_rates.keys()),
            "Price": [format_money(p) + " per day" for p in decor_rates.values()],
        })

    ## Add-on prices (return gifts are per guest, the others per day)
    with st.container(border=True):
        section_title("Add-on Services")
        addon_names = []
        addon_prices = []
        for name, price in addon_rates.items():
            addon_names.append(name.replace(" (per guest)", ""))
            unit = "per guest" if "per guest" in name else "per day"
            addon_prices.append(f"{format_money(price)} {unit}")
        st.table({"Service": addon_names, "Price": addon_prices})

    ## Discount rules
    st.caption("Discounts: 5% for 200+ guests, 10% for 500+ guests, 3% for returning clients, "
               "5% for corporate clients (total discount is capped at 30%).")


## ---------------------------------------------------------------
## 6. PROFILE PAGE
## ---------------------------------------------------------------

## Profile page: avatar, client details and the list of saved estimates
def profile_page():

    ## Avatar circle with the initials of the client name (first letter of first and last word)
    full_name = st.session_state["client_name"].strip().title()
    name_parts = full_name.split()
    if len(name_parts) >= 2:
        initials = name_parts[0][0] + name_parts[-1][0]
    elif len(name_parts) == 1:
        initials = name_parts[0][:2]
    else:
        initials = "?"
    shown_name = full_name if full_name else "Your Name"
    shown_city = st.session_state["city"].strip().title()

    st.markdown(
        f'<div class="avatar">{html.escape(initials.upper())}</div>'
        f'<div class="profile-name">{html.escape(shown_name)}</div>'
        f'<div class="profile-sub">{html.escape(shown_city) if shown_city else "City not added"}'
        f' · {st.session_state["client_type"]}</div>',
        unsafe_allow_html=True,
    )

    ## Client details card: name, city, phone, email and client type (used on the Home page)
    with st.container(border=True):
        section_title("My Details")
        st.text_input("Client Name", key="client_name", placeholder="e.g. rahul sharma")
        st.text_input("Event City", key="city", placeholder="e.g. sonipat, haryana")

        contact1, contact2 = st.columns(2)
        with contact1:
            st.text_input("Mobile Number (optional)", key="phone", placeholder="e.g. 98765 43210")
        with contact2:
            st.text_input("Email (optional)", key="email", placeholder="e.g. rahul@gmail.com")

        st.selectbox(
            "Client Type", client_types, key="client_type",
            help="Returning clients get 3% off and corporate clients get 5% off",
        )
    st.caption("Your details are saved automatically and used on the Home page.")

    ## Saved estimates: one card for each estimate saved with the Save button, newest first
    section_title("Saved Estimates")
    history = st.session_state["history"]
    if len(history) == 0:
        st.info("No saved estimates yet. Calculate a budget on the Home page and press Save Estimate.")
    else:
        st.caption(f"{len(history)} saved estimate(s), newest first.")

        for index in range(len(history) - 1, -1, -1):
            item = history[index]
            with st.expander(f"{item['name']}  ·  {format_money(item['total'])}"):
                ## Details of the saved estimate
                st.markdown(
                    f"- **Saved on:** {item['saved_on']}\n"
                    f"- **Booking ID:** {item['booking_id']}\n"
                    f"- **Client:** {item['name_text']}{item['place_text']} ({item['client_type']})\n"
                    f"- **Event:** {item['event_type']}, {item['event_time']}, "
                    f"{item['days']} day(s), {item['guests']} guests\n"
                    f"- **Venue / Menu / Decor:** {item['venue']} / {item['catering']} / {item['decor']}\n"
                    f"- **Add-ons:** {item['addons_text']}\n"
                    f"- **Budget rating:** {item['budget_rating']} ({format_money(item['cost_per_guest'])} per guest)"
                )
                ## Full cost breakdown of the saved estimate
                st.table({
                    "Item": ["Venue", "Catering", "Decoration", "Add-ons",
                             "Subtotal", f"Discount ({item['total_discount_percent']}%)",
                             "GST (18%)", "TOTAL"],
                    "Amount": [format_money(item["venue_cost"]), format_money(item["catering_cost"]),
                               format_money(item["decor_cost"]), format_money(item["addon_cost"]),
                               format_money(item["subtotal"]), "-" + format_money(item["discount_amount"]),
                               format_money(item["gst"]), format_money(item["total"])],
                })
                ## Delete button for this saved estimate
                st.button(
                    "Delete This Estimate", key=f"delete_{index}",
                    on_click=delete_estimate, args=(index,),
                )


## ---------------------------------------------------------------
## 7. SHOW THE SELECTED PAGE AND THE BOTTOM ICON BAR
## ---------------------------------------------------------------

## Show the page that is selected: Home, Menu or Profile
current_page = st.session_state["page"]
if current_page == "Home":
    home_page()
elif current_page == "Menu":
    menu_page()
else:
    profile_page()

## Empty space at the end of every page, so the last button is never hidden by the bottom bar
st.markdown('<div class="bottom-space"></div>', unsafe_allow_html=True)

## Bottom icon bar: always visible, the open page is highlighted in violet
with st.container(key="bottomnav"):
    nav_columns = st.columns(len(pages))
    for column, (page_name, icon) in zip(nav_columns, pages.items()):
        with column:
            st.button(
                f"{icon} {page_name}",
                key=f"nav_{page_name}",
                on_click=go_to,
                args=(page_name,),
                type="primary" if current_page == page_name else "secondary",
                use_container_width=True,
            )

## Royal Event Budget Calculator (business idea: Event Management)
## Run with: streamlit run app.py
## Needs Python 3.10 or newer (match-case is used) and a recent Streamlit: pip install --upgrade streamlit
## The app has a TOP menu bar (like the Streamlit Playground site) with 5 pages:
##   Calculator, Price List, Expenses, Saved and Profile


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

## The menu links shown in the top bar (the Profile button sits on the right side of the bar)
nav_pages = {
    "Calculator": "🧮",
    "Price List": "📜",
    "Expenses": "💰",
    "Saved": "💾",
}


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


## Show a section heading with a gold bar on the left
def section_title(text):
    st.markdown(f'<div class="section-title">{text}</div>', unsafe_allow_html=True)


## Show the title of a page (used on every page except the Calculator, which has the big banner)
def page_header(title, subtitle):
    st.markdown(
        f'<div class="page-header"><h2>{title}</h2><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )


## Remember which page should be shown (runs when a top bar button is clicked)
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
## 3. PAGE SETUP AND ROYAL THEME DESIGN
## ---------------------------------------------------------------
## Colours used: midnight violet #0a0714 (page), deep amethyst #140d26 (cards),
## royal purple #5b2fb5 (accent), antique gold #d4af37 (highlights), ivory #f3ecff (text)

## Page title and icon shown in the browser tab
st.set_page_config(page_title="Royal Event Budget Calculator", page_icon="👑", layout="wide")

## Royal theme (CSS): colours, fonts, cards, inputs, buttons, tables, avatar and the fixed top menu bar
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Cinzel:wght@500;600;700;800&display=swap');

    html, body, .stApp, .stApp * { font-family: 'Inter', 'Segoe UI', sans-serif; }

    /* Hide the default Streamlit header, menu and footer (our own top bar replaces them) */
    #MainMenu, footer { visibility: hidden; }
    header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }

    /* Page background and space at the top so the fixed menu bar never hides content */
    .stApp {
        background-color: #0a0714;
        background-image:
            radial-gradient(ellipse at 15% -10%, rgba(91,47,181,0.28) 0%, transparent 50%),
            radial-gradient(ellipse at 90% 0%, rgba(212,175,55,0.08) 0%, transparent 40%);
    }
    .block-container { max-width: 1000px; padding-top: 6.5rem !important; padding-bottom: 4rem !important; }

    /* Headings use a classic royal serif, body text stays clean */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4 { color: #f3ecff; font-family: 'Cinzel', Georgia, serif; }

    /* All normal text (light on dark) */
    .stApp p, .stApp label, .stApp span, .stApp li,
    .stApp [data-testid="stMarkdownContainer"] p { color: #cfc6ee; }
    .stApp [data-testid="stWidgetLabel"] p { font-weight: 500; color: #f3ecff; }
    .stApp [data-testid="stCaptionContainer"] p { color: #9a8fc0; font-size: 0.8rem; }
    .stApp [data-testid="stTooltipIcon"] svg { color: #b3a8d6; }
    .stApp hr { border-color: #2c1f4d; }

    /* ---------- TOP MENU BAR (fixed, like the Streamlit Playground site) ---------- */
    .st-key-topnav {
        position: fixed; top: 0; left: 0; right: 0; z-index: 1000;
        background: rgba(10,7,20,0.94); backdrop-filter: blur(10px);
        border-bottom: 1px solid rgba(212,175,55,0.35);
        padding: 8px max(14px, calc((100vw - 1000px) / 2));
        box-shadow: 0 6px 28px rgba(0,0,0,0.5);
    }
    .st-key-topnav [data-testid="stHorizontalBlock"] {
        flex-direction: row !important; flex-wrap: nowrap !important; align-items: center;
        gap: 4px; overflow-x: auto; scrollbar-width: none;
    }
    .st-key-topnav [data-testid="stHorizontalBlock"]::-webkit-scrollbar { display: none; }
    .st-key-topnav [data-testid="stColumn"] {
        flex: 0 0 auto !important; width: auto !important; min-width: 0 !important;
    }
    /* The empty 6th column pushes the Profile button to the far right */
    .st-key-topnav [data-testid="stColumn"]:nth-child(6) { flex: 1 1 auto !important; }

    /* Brand: crown + name on the left */
    .brand { display: flex; align-items: center; gap: 10px; padding-right: 22px; white-space: nowrap; }
    .brand-crown {
        width: 36px; height: 36px; border-radius: 10px; font-size: 1.15rem;
        display: flex; align-items: center; justify-content: center;
        background: linear-gradient(135deg, #5b2fb5, #8b5cf6);
        border: 1px solid rgba(212,175,55,0.6);
        box-shadow: 0 0 14px rgba(139,92,246,0.5);
    }
    .brand-text {
        font-family: 'Cinzel', Georgia, serif; font-weight: 700; font-size: 1.15rem;
        letter-spacing: 1px; color: #f3d98b;
    }

    /* Menu links: plain text, the open page gets a gold underline */
    .st-key-topnav div.stButton > button {
        background: transparent; box-shadow: none; transform: none;
        border: none; border-bottom: 2px solid transparent; border-radius: 0;
        padding: 0.65rem 0.95rem; width: auto; white-space: nowrap;
        color: #cfc6ee; font-size: 0.92rem;
    }
    .st-key-topnav div.stButton > button p { color: inherit !important; font-weight: 500; white-space: nowrap; }
    .st-key-topnav div.stButton > button:hover {
        background: rgba(212,175,55,0.08); color: #f3d98b; transform: none; box-shadow: none;
    }
    .st-key-topnav div.stButton > button[data-testid="stBaseButton-primary"],
    .st-key-topnav div.stButton > button[kind="primary"] {
        background: rgba(212,175,55,0.10); color: #f3d98b; border-bottom: 2px solid #d4af37;
    }
    .st-key-topnav div.stButton > button[data-testid="stBaseButton-primary"] p,
    .st-key-topnav div.stButton > button[kind="primary"] p { font-weight: 700; }

    /* Profile button on the right: gold outline, like the Free / Pro buttons in the sample */
    .st-key-nav_Profile div.stButton > button {
        border: 1px solid rgba(212,175,55,0.7) !important; border-radius: 10px !important;
        color: #f3d98b; padding: 0.5rem 1.1rem;
    }
    .st-key-nav_Profile div.stButton > button[data-testid="stBaseButton-primary"],
    .st-key-nav_Profile div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #f3d98b, #d4af37 55%, #b8901f) !important;
        color: #1a1033 !important; border: 1px solid #f3d98b !important;
    }

    /* ---------- BANNER AND HEADINGS ---------- */
    .hero {
        background: linear-gradient(135deg, #140a33 0%, #3b1d82 55%, #6d3fd1 100%);
        padding: 40px 24px; border-radius: 18px; text-align: center;
        margin-bottom: 26px; border: 1px solid rgba(212,175,55,0.55);
        box-shadow: 0 10px 40px rgba(91,47,181,0.35), inset 0 0 0 4px rgba(10,7,20,0.35);
    }
    .stApp .hero h1 {
        margin: 0; font-family: 'Cinzel', Georgia, serif;
        font-size: clamp(1.5rem, 4.2vw, 2.4rem); font-weight: 700;
        color: #f3d98b; letter-spacing: 1.5px; line-height: 1.25;
    }
    .stApp .hero p { margin: 12px 0 0 0; color: #ded6ff; font-size: 1rem; }

    .page-header { margin-bottom: 22px; padding-bottom: 14px; border-bottom: 1px solid #2c1f4d; }
    .stApp .page-header h2 {
        margin: 0; color: #f3d98b; font-size: clamp(1.4rem, 3.5vw, 1.9rem);
        font-weight: 700; letter-spacing: 1px;
    }
    .stApp .page-header p { margin: 6px 0 0 0; color: #9a8fc0; font-size: 0.95rem; }

    .section-title {
        font-family: 'Cinzel', Georgia, serif; font-size: 1.05rem; font-weight: 700;
        letter-spacing: 0.6px; color: #f3d98b;
        border-left: 4px solid #d4af37; padding-left: 12px; margin: 6px 0 14px 0;
    }

    /* ---------- CARDS ---------- */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: #140d26; border: 1px solid #2c1f4d !important;
        border-radius: 14px; box-shadow: 0 4px 18px rgba(0,0,0,0.4);
    }

    /* ---------- INPUTS ---------- */
    .stApp input, .stApp textarea,
    .stApp div[data-baseweb="select"] > div,
    .stApp div[data-baseweb="input"],
    .stApp div[data-baseweb="base-input"],
    .stApp div[data-baseweb="textarea"] {
        background-color: #0f0a1f !important;
        color: #f3ecff !important;
        border-color: #34265c !important;
        border-radius: 8px !important;
    }
    .stApp div[data-baseweb="input"]:focus-within,
    .stApp div[data-baseweb="textarea"]:focus-within,
    .stApp div[data-baseweb="select"] > div:focus-within {
        border-color: #d4af37 !important;
        box-shadow: 0 0 0 3px rgba(212,175,55,0.22) !important;
    }
    .stApp input::placeholder, .stApp textarea::placeholder { color: #75689b !important; opacity: 1; }
    .stApp div[data-baseweb="select"] span,
    .stApp div[data-baseweb="select"] svg { color: #f3ecff !important; fill: #f3ecff !important; }
    .stApp [data-testid="stNumberInput"] button {
        background-color: #1c1338 !important; color: #f3ecff !important; border-color: #34265c !important;
    }
    .stApp [data-testid="stNumberInput"] button svg { fill: #f3ecff !important; color: #f3ecff !important; }

    /* Dropdown list that opens when a selectbox is clicked */
    div[data-baseweb="popover"] ul,
    div[data-baseweb="popover"] li,
    div[data-baseweb="popover"] div[role="option"] {
        background-color: #140d26 !important; color: #f3ecff !important;
    }
    div[data-baseweb="popover"] li:hover { background-color: #2a1c52 !important; }

    /* Checkbox and slider */
    .stApp [data-testid="stCheckbox"] span[role="checkbox"],
    .stApp [data-baseweb="checkbox"] > span:first-child { border-color: #d4af37 !important; }
    [data-testid="stSliderThumbValue"] { color: #f3d98b !important; font-weight: 600; }
    [data-testid="stTickBarMin"], [data-testid="stTickBarMax"] { color: #9a8fc0 !important; }
    div[data-baseweb="slider"] div[role="slider"] { background-color: #d4af37 !important; }

    /* ---------- MAIN BUTTONS: gold with dark text ---------- */
    div.stButton > button {
        background: linear-gradient(135deg, #f3d98b, #d4af37 55%, #b8901f); color: #1a1033;
        border: none; border-radius: 10px; padding: 0.7rem 2rem; font-weight: 700; width: 100%;
        box-shadow: 0 4px 16px rgba(212,175,55,0.35); transition: all 0.15s ease;
    }
    div.stButton > button:hover {
        background: linear-gradient(135deg, #f8e4a3, #e0bb48 55%, #c79b26); color: #1a1033;
        transform: translateY(-1px); box-shadow: 0 6px 22px rgba(212,175,55,0.5);
    }
    div.stButton > button p { color: #1a1033 !important; font-weight: 700; }

    /* ---------- METRIC CARDS ---------- */
    [data-testid="stMetric"] {
        background: #140d26; padding: 16px; border-radius: 12px;
        border: 1px solid #2c1f4d; border-top: 4px solid #d4af37;
        box-shadow: 0 4px 14px rgba(0,0,0,0.4);
    }
    [data-testid="stMetricLabel"] * { color: #9a8fc0 !important; font-size: 0.8rem !important; letter-spacing: 0.4px; }
    [data-testid="stMetricValue"] * { color: #f3d98b !important; font-weight: 700; }

    /* ---------- ALERT BOXES ---------- */
    [data-testid="stAlert"] {
        background-color: #1a1233 !important; border: 1px solid #34265c; border-radius: 10px;
    }
    [data-testid="stAlert"] * { color: #f3ecff !important; }

    /* ---------- TABLES ---------- */
    .stApp table { background: #140d26; border-collapse: collapse; width: 100%; }
    .stApp th { background: #2a1c52 !important; color: #f3d98b !important; font-weight: 600; border-color: #34265c !important; }
    .stApp td { color: #cfc6ee !important; background: #140d26 !important; border-color: #2c1f4d !important; }
    .stApp tbody tr:nth-child(even) td { background: #0f0a1f !important; }
    /* Only the cost breakdown tables highlight their last row (TOTAL) */
    [class*="st-key-breakdown"] tbody tr:last-child td {
        background: #3b1d82 !important; color: #f3d98b !important; font-weight: 700;
    }

    /* ---------- FORMS AND EXPANDERS ---------- */
    [data-testid="stForm"] { background: #140d26; border: 1px solid #2c1f4d; border-radius: 14px; }
    [data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(135deg, #f3d98b, #d4af37 55%, #b8901f); color: #1a1033; border: none;
        border-radius: 10px; padding: 0.6rem 2rem; font-weight: 700; width: 100%;
        box-shadow: 0 4px 16px rgba(212,175,55,0.35);
    }
    [data-testid="stFormSubmitButton"] > button:hover { filter: brightness(1.08); color: #1a1033; }
    [data-testid="stFormSubmitButton"] > button p { color: #1a1033 !important; }

    [data-testid="stExpander"] {
        background: #140d26; border: 1px solid #2c1f4d !important; border-radius: 12px; margin-bottom: 10px;
    }
    [data-testid="stExpander"] summary, [data-testid="stExpander"] summary * {
        color: #f3ecff !important; font-weight: 600;
    }

    /* ---------- PROFILE AVATAR ---------- */
    .avatar {
        width: 88px; height: 88px; border-radius: 50%; margin: 4px auto 8px auto;
        background: linear-gradient(135deg, #5b2fb5, #8b5cf6); color: #f3d98b;
        border: 2px solid #d4af37;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Cinzel', Georgia, serif; font-size: 1.9rem; font-weight: 700;
        box-shadow: 0 6px 22px rgba(139,92,246,0.5);
    }
    .profile-name { text-align: center; color: #f3ecff; font-family: 'Cinzel', Georgia, serif; font-weight: 700; font-size: 1.3rem; }
    .profile-sub { text-align: center; color: #9a8fc0; font-size: 0.85rem; margin-bottom: 12px; }

    /* ---------- SMALL SCREENS ---------- */
    @media (max-width: 640px) {
        .brand-text { display: none; }
        .brand { padding-right: 8px; }
        .st-key-topnav div.stButton > button { padding: 0.6rem 0.6rem; font-size: 0.85rem; }
    }
</style>
""", unsafe_allow_html=True)

## Keep typed values when you move to another page (Streamlit forgets a widget value when its page is not shown)
defaults = {
    "page": "Calculator",
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


## ---------------------------------------------------------------
## 4. TOP MENU BAR
## ---------------------------------------------------------------

## Fixed bar at the top: brand on the left, menu links in the middle, Profile button on the right
def top_nav():
    current = st.session_state["page"]
    saved_count = len(st.session_state["history"])

    ## First name of the client for the Profile button (or just "Profile" when no name is added yet)
    name_parts = st.session_state["client_name"].strip().title().split()
    profile_label = f"👤 {name_parts[0]}" if name_parts else "👤 Profile"

    with st.container(key="topnav"):
        ## 1 brand + 4 menu links + 1 empty spacer + 1 profile button
        cols = st.columns([2.2, 1.2, 1.2, 1.2, 1.2, 0.3, 1.2])

        with cols[0]:
            st.markdown(
                '<div class="brand"><div class="brand-crown">👑</div>'
                '<div class="brand-text">Royal Events</div></div>',
                unsafe_allow_html=True,
            )

        for column, (page_name, icon) in zip(cols[1:5], nav_pages.items()):
            with column:
                label = f"{icon} {page_name}"
                if page_name == "Saved" and saved_count > 0:
                    label = f"{icon} Saved ({saved_count})"
                st.button(
                    label, key=f"nav_{page_name}", on_click=go_to, args=(page_name,),
                    type="primary" if current == page_name else "secondary",
                )

        with cols[6]:
            st.button(
                profile_label, key="nav_Profile", on_click=go_to, args=("Profile",),
                type="primary" if current == "Profile" else "secondary",
            )


## ---------------------------------------------------------------
## 5. CALCULATOR PAGE: SAVE AREA, ESTIMATE DISPLAY AND MAIN FUNCTION
## ---------------------------------------------------------------

## Save area under the estimate: Save button -> asks for a name -> saved message
def save_area(estimate):
    if estimate["saved_as"] != "":
        st.success(f"✅ Saved as '{estimate['saved_as']}'. Open the Saved page to see it.")
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


## Draw the last calculated estimate from session_state (it stays on screen while you save or change page)
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
    with st.container(key="breakdown_main"):
        st.table(breakdown)

    section_title("Where Your Money Goes")
    chart_names = ["Venue", "Catering", "Decor", "Add-ons"]
    chart_costs = [estimate["venue_cost"], estimate["catering_cost"],
                   estimate["decor_cost"], estimate["addon_cost"]]
    chart_colors = ["#d4af37", "#8b5cf6", "#e879a8", "#2dd4bf"]
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

    ## Next step: go and track the real payments
    st.caption("Next step: open the Expenses page to track every payment against this estimate.")


## Calculator page: banner, event inputs, Calculate button and estimate display
def calculator_page():

    ## Big banner (only on this page)
    st.markdown("""
    <div class="hero">
        <h1>👑 Royal Event Budget Calculator</h1>
        <p>Plan a celebration fit for royalty, with an instant and honest budget estimate</p>
    </div>
    """, unsafe_allow_html=True)

    ## Reminder to fill the Profile page when no client name is saved yet
    if st.session_state["client_name"].strip() == "":
        st.info("👤 Tip: add your name and contact details on the Profile page (top right).")

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

                ## Keep the category amounts for the expense tracker (Expenses page)
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

    ## Show the estimate (it stays visible while you save or change page)
    if "estimate" in st.session_state:
        show_estimate()


## ---------------------------------------------------------------
## 6. PRICE LIST PAGE
## ---------------------------------------------------------------

## Price list page: venues, catering, decoration and add-ons, plus the discount rules
def price_list_page():
    page_header("Royal Price List", "All prices are before discount and 18% GST.")

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
## 7. EXPENSES PAGE (EXPENSE TRACKER)
## ---------------------------------------------------------------

## Expenses page: note down every payment and compare it with the estimate
def expenses_page():
    page_header("Expense Tracker", "Note down every payment you make and compare it with your estimate.")

    ## The tracker needs a calculated budget, so ask the user to calculate one first
    if "budget" not in st.session_state:
        st.info("No budget yet. Calculate a budget on the Calculator page first, then come back here.")
        st.button("🧮 Go to Calculator", key="go_calc", on_click=go_to, args=("Calculator",))
        return

    budget_categories = st.session_state["budget"]["categories"]
    budget_total = st.session_state["budget"]["total"]

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
        return

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
## 8. SAVED ESTIMATES PAGE
## ---------------------------------------------------------------

## Saved page: one card for each estimate saved with the Save button, newest first
def saved_page():
    page_header("Saved Estimates", "Every estimate you saved from the Calculator, newest first.")

    history = st.session_state["history"]
    if len(history) == 0:
        st.info("No saved estimates yet. Calculate a budget on the Calculator page and press Save Estimate.")
        st.button("🧮 Go to Calculator", key="go_calc_saved", on_click=go_to, args=("Calculator",))
        return

    st.caption(f"{len(history)} saved estimate(s).")

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
            with st.container(key=f"breakdown_saved_{index}"):
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
## 9. PROFILE PAGE
## ---------------------------------------------------------------

## Profile page: avatar and client details (used on the Calculator page)
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

    ## Client details card: name, city, phone, email and client type
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
    st.caption("Your details are saved automatically and used on the Calculator page.")


## ---------------------------------------------------------------
## 10. DRAW THE TOP BAR AND SHOW THE SELECTED PAGE
## ---------------------------------------------------------------

## Top menu bar: always visible, the open page is underlined in gold
top_nav()

## Show the page that is selected
current_page = st.session_state["page"]
if current_page == "Calculator":
    calculator_page()
elif current_page == "Price List":
    price_list_page()
elif current_page == "Expenses":
    expenses_page()
elif current_page == "Saved":
    saved_page()
else:
    profile_page()

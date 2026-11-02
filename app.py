## Event Budget Calculator (business idea: Event Management)
## Run with: streamlit run app.py
## Needs Python 3.10 or newer (match-case is used) and a recent Streamlit: pip install --upgrade streamlit
## The app has a TOP menu bar (Apple-style black bar) with 6 pages:
##   Home, Calculator, Price List, Expenses, Saved and Profile
## The footer on the Home page also opens three extra pages: About, FAQ and Contact


## Import the libraries: html (safe text for the avatar), datetime (save time), pandas (chart data), streamlit (the app)
import html
import io
from datetime import datetime
from xml.sax.saxutils import escape

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


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

## GST rate (18%) and tiered booking discounts based on subtotal before discount/GST
GST_RATE = 0.18
DISCOUNT_TIERS = [(500000, 20), (300000, 10)]
BASE_DISCOUNT_PERCENT = 5


def get_discount_percent(subtotal):
    """Return the fixed discount rate based on the booking subtotal before discount and GST."""
    if subtotal >= 500000:
        return 20
    if subtotal >= 300000:
        return 10
    return BASE_DISCOUNT_PERCENT

## Lists of options used in the dropdowns, the phone check and the special request keywords
event_types = ["Wedding", "Birthday Party", "Corporate Event", "Conference"]
client_types = ["Regular", "Returning Client", "Corporate"]
event_times = ["Morning", "Afternoon", "Evening"]
mobile_start_digits = ["6", "7", "8", "9"]
planning_keywords = ["music", "band", "flower", "stage", "fireworks", "photo"]

## The menu links shown in the top bar (the Profile icon sits on the right side of the bar)
nav_pages = ["Home", "Calculator", "Price List", "Discounts", "Extra Expenses", "Saved"]

## Contact details (change them here and they update on the footer and the Contact page)
CONTACT_EMAIL = "hello@eventora.in"
CONTACT_PHONE = "+91 98765 43210"


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


## Show a section heading with a royal-blue bar on the left
def section_title(text):
    st.markdown(f'<div class="section-title">{text}</div>', unsafe_allow_html=True)


## Show the title of a page (used on every page except Home, which has the big hero)
def page_header(title, subtitle):
    st.markdown(
        f'<div class="page-header"><h2>{title}</h2><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )


## Remember which page should be shown (runs when a top bar button is clicked)
def go_to(page_name):
    st.session_state["page"] = page_name
    st.session_state["scroll_top"] = True   ## the new page opens from its top, not from the footer position


## Footer event-type link clicked: open the Calculator with that event type already selected
def go_to_event(event_type):
    st.session_state["event_type"] = event_type
    st.session_state["page"] = "Calculator"
    st.session_state["scroll_top"] = True


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
        st.session_state["expense_message"] = ("error", "Please describe the extra work or change requested.")
    elif new_amount <= 0:
        st.session_state["expense_message"] = ("error", "Extra cost must be more than 0.")
    else:
        for e in st.session_state["expenses"]:
            if e["id"] == expense_id:
                e["what"] = new_what[0].upper() + new_what[1:]
                e["category"] = new_category
                e["amount"] = new_amount
        st.session_state["expense_message"] = ("success", "Extra expense updated!")


## Delete This Expense clicked: keep every expense except the one with this ID
def delete_expense(expense_id):
    remaining = []
    for e in st.session_state["expenses"]:
        if e["id"] != expense_id:
            remaining.append(e)
    st.session_state["expenses"] = remaining
    st.session_state["expense_message"] = ("success", "Extra expense deleted.")


## ---------------------------------------------------------------
## 3. PAGE SETUP AND GREY + ROYAL BLUE THEME
## ---------------------------------------------------------------
## Colours used: black #000000 (page), graphite #111113 and #1c1c1e (cards, inputs),
## silver greys (text), royal blue #2e5bff (buttons, highlights)

## Page title and icon shown in the browser tab
st.set_page_config(page_title="Eventora | Event Budget Calculator", page_icon="👑", layout="wide")

## Grey and royal-blue theme (CSS): colours, fonts, cards, inputs, buttons, tables, avatar and the fixed top menu bar
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, .stApp, .stApp * { font-family: 'Inter', -apple-system, 'SF Pro Display', 'Segoe UI', sans-serif; }
    .stApp { color-scheme: dark; }
    .stApp, [data-testid="stMain"], [data-testid="stAppViewContainer"] { overflow-x: hidden; }

    /* Keep Streamlit's icon font for icons (expander arrows, etc.), otherwise the icon name shows as text */
    .stApp [data-testid="stIconMaterial"], .stApp [data-testid="stExpanderIcon"],
    .stApp span[class*="material-symbols"], .stApp span[class*="material-icons"] {
        font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons' !important;
        letter-spacing: normal; text-transform: none; white-space: nowrap;
    }

    /* Hide the default Streamlit header, menu and footer (our own top bar replaces them) */
    #MainMenu, footer { visibility: hidden; }
    header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }

    /* Page background: pure black with a soft royal-blue glow at the top */
    .stApp {
        background-color: #000000;
        background-image: radial-gradient(ellipse at 50% 0%, rgba(46,91,255,0.20) 0%, transparent 55%);
    }
    .block-container { max-width: 1000px; padding-top: 8rem !important; padding-bottom: 4rem !important; }

    /* Headings: clean, bold, tight spacing */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4 { color: #f5f5f7; letter-spacing: -0.02em; }

    /* All normal text (light grey on black) */
    .stApp p, .stApp label, .stApp span, .stApp li,
    .stApp [data-testid="stMarkdownContainer"] p { color: #c7c7cc; }
    .stApp [data-testid="stWidgetLabel"] p { font-weight: 500; color: #f5f5f7; }
    .stApp [data-testid="stCaptionContainer"] p { color: #86868b; font-size: 0.82rem; }
    .stApp [data-testid="stTooltipIcon"] svg { color: #98989d; }
    .stApp hr { border-color: #2c2c30; }

    /* ---------- TOP MENU BAR (black, fixed, evenly spaced links) + PROMO STRIP ---------- */
    .st-key-topnav {
        position: fixed; top: 0; left: 0; right: 0; z-index: 1000;
        gap: 0 !important; padding: 0;
        background: rgba(0,0,0,0.88); backdrop-filter: saturate(180%) blur(20px);
    }
    .st-key-topnav [data-testid="stHorizontalBlock"] {
        /* Flex rail: fixed logo/profile zones and six genuinely equal navigation slots. */
        display: flex !important;
        flex-flow: row nowrap !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 0 !important;
        width: min(100%, 1200px) !important;
        min-height: 58px;
        margin: 0 auto !important;
        padding: 0 12px !important;
        box-sizing: border-box;
        overflow: visible;
    }
    .st-key-topnav [data-testid="stColumn"] {
        min-width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        flex: 1 1 0% !important;
        width: 0 !important;
        box-sizing: border-box !important;
    }
    /* The logo and profile occupy compact fixed-width end zones. */
    .st-key-topnav [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child {
        flex: 0 0 155px !important; width: 155px !important;
    }
    .st-key-topnav [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {
        flex: 0 0 56px !important; width: 56px !important;
    }
    .st-key-topnav [data-testid="stColumn"] > div {
        width: 100% !important; min-width: 0; min-height: 58px !important; height: 58px !important;
        display: flex !important; align-items: center !important; justify-content: center !important;
        padding: 0 !important; margin: 0 !important; box-sizing: border-box !important;
    }
    .st-key-topnav [data-testid="stColumn"] [data-testid="stVerticalBlock"] {
        width: 100% !important; min-width: 0; min-height: 58px !important; height: 58px !important; gap: 0 !important;
        display: flex !important; align-items: center !important; justify-content: center !important; padding: 0 !important; margin: 0 !important;
    }

    /* Eventora logo is vertically centered within the same 58px navigation rail. */
    .brand { display: flex; align-items: center; justify-content: center; width: 100%; height: 58px; min-height: 58px; padding: 0 4px; overflow: hidden; box-sizing: border-box; line-height: 0; }
    .brand img { display: block; width: 145px; max-width: 100%; max-height: 36px; height: auto; object-fit: contain; margin: 0; transform: translateY(-1px); }

    /* Every navigation button fills its equal-width slot and centers text vertically/horizontally. */
    .st-key-topnav div.stButton { width: 100%; height: 58px; min-width: 0; display: flex; align-items: center; justify-content: center; }
    .st-key-topnav div.stButton > button {
        background: transparent; box-shadow: none; transform: none; width: 100%; height: 58px;
        min-height: 58px; display: flex; align-items: center; justify-content: center;
        margin: 0; border: none; border-bottom: 2px solid transparent; border-radius: 0;
        padding: 0 0.25rem; white-space: nowrap; color: #d2d2d7; font-size: 0.86rem;
    }
    .st-key-topnav div.stButton > button p { color: inherit !important; font-weight: 500; white-space: nowrap; font-size: 0.86rem; }
    .st-key-topnav div.stButton > button:hover { background: transparent; color: #ffffff; box-shadow: none; transform: none; }
    .st-key-topnav div.stButton > button[data-testid="stBaseButton-primary"],
    .st-key-topnav div.stButton > button[kind="primary"] {
        background: transparent; color: #ffffff; border-bottom: 2px solid #2e5bff;
    }
    .st-key-topnav div.stButton > button[data-testid="stBaseButton-primary"] p,
    .st-key-topnav div.stButton > button[kind="primary"] p { font-weight: 700; }
    .st-key-nav_Profile div.stButton > button p { font-size: 1.05rem; }

    /* Promo strip under the menu bar */
    .promo {
        background: #1d1d1f; text-align: center; padding: 14px 16px;
        font-size: 0.95rem; line-height: 1.35; color: #f5f5f7;
    }
    .stApp .promo, .stApp .promo span { color: #f5f5f7; }
    .stApp .promo b { color: #7a9bff; font-weight: 600; }

    /* ---------- HERO AND HEADINGS ---------- */
    .hero { text-align: center; padding: 28px 12px 8px 12px; margin-bottom: 4px; }
    .stApp .hero h1 {
        margin: 0;
        font-family: Georgia, "Times New Roman", serif;
        font-size: clamp(5rem, 13vw, 9rem);
        font-weight: 700;
        background: linear-gradient(115deg, #f5f7ff 0%, #b8c8ff 38%, #7898ff 72%, #d9e2ff 100%);
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        color: #cbd5ff;
        letter-spacing: -0.055em;
        line-height: 0.98;
        text-shadow: 0 10px 42px rgba(86, 121, 255, 0.18);
    }
    .stApp .hero .hero-note {
        margin: 20px 0 0 0;
        font-size: clamp(1.35rem, 3vw, 2rem);
        font-weight: 600;
        letter-spacing: -0.025em;
        color: #f5f5f7;
    }
    .stApp .hero .hero-sub {
        margin: 10px 0 0 0;
        font-size: clamp(0.82rem, 1.5vw, 1rem);
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.18em;
        color: #8da8ff;
    }
    .stApp .hero .hero-description { margin: 12px 0 0 0; font-size: clamp(0.92rem, 1.6vw, 1.05rem); color: #86868b; }

    .page-header { text-align: center; margin: 6px 0 26px 0; }
    .stApp .page-header h2 {
        margin: 0; color: #f5f5f7; font-size: clamp(1.8rem, 5vw, 2.6rem);
        font-weight: 700; letter-spacing: -0.03em;
    }
    .stApp .page-header p { margin: 8px 0 0 0; color: #86868b; font-size: 1.05rem; }

    .section-title {
        font-size: 1.1rem; font-weight: 700; letter-spacing: -0.01em; color: #f5f5f7;
        border-left: 3px solid #2e5bff; padding-left: 12px; margin: 6px 0 14px 0;
    }

    /* ---------- CARDS ---------- */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: #111113; border: 1px solid #2c2c30 !important;
        border-radius: 18px; box-shadow: none;
    }

    /* ---------- INPUTS ---------- */
    .stApp input, .stApp textarea,
    .stApp div[data-baseweb="select"] > div,
    .stApp div[data-baseweb="input"],
    .stApp div[data-baseweb="base-input"],
    .stApp div[data-baseweb="textarea"] {
        background-color: #1c1c1e !important;
        color: #f5f5f7 !important;
        border-color: #3a3a3f !important;
        border-radius: 10px !important;
    }
    .stApp div[data-baseweb="input"]:focus-within,
    .stApp div[data-baseweb="textarea"]:focus-within,
    .stApp div[data-baseweb="select"] > div:focus-within {
        border-color: #2e5bff !important;
        box-shadow: 0 0 0 3px rgba(46,91,255,0.30) !important;
    }
    .stApp input::placeholder, .stApp textarea::placeholder { color: #6e6e73 !important; opacity: 1; }
    .stApp div[data-baseweb="select"] span,
    .stApp div[data-baseweb="select"] svg { color: #f5f5f7 !important; fill: #f5f5f7 !important; }
    .stApp [data-testid="stNumberInput"] button {
        background-color: #2c2c30 !important; color: #f5f5f7 !important; border-color: #3a3a3f !important;
    }
    .stApp [data-testid="stNumberInput"] button svg { fill: #f5f5f7 !important; color: #f5f5f7 !important; }

    /* Dropdown list that opens when a selectbox is clicked */
    div[data-baseweb="popover"] ul,
    div[data-baseweb="popover"] li,
    div[data-baseweb="popover"] div[role="option"] {
        background-color: #1c1c1e !important; color: #f5f5f7 !important;
    }
    div[data-baseweb="popover"] li:hover { background-color: #2c2c30 !important; }

    /* Checkbox and slider */
    .stApp [data-testid="stCheckbox"] span[role="checkbox"],
    .stApp [data-baseweb="checkbox"] > span:first-child { border-color: #6f93ff !important; }
    [data-testid="stSliderThumbValue"] { color: #7a9bff !important; font-weight: 600; }
    [data-testid="stTickBarMin"], [data-testid="stTickBarMax"] { color: #86868b !important; }
    div[data-baseweb="slider"] div[role="slider"] { background-color: #2e5bff !important; }

    /* ---------- MAIN BUTTONS: royal-blue pills ---------- */
    div.stButton > button {
        background-color: #2e5bff; color: #ffffff; border: none;
        border-radius: 980px; padding: 0.75rem 2rem; font-weight: 600; width: 100%;
        box-shadow: none; transition: background-color 0.15s ease;
    }
    div.stButton > button:hover { background-color: #4a73ff; color: #ffffff; transform: none; box-shadow: none; }
    div.stButton > button p { color: #ffffff !important; font-weight: 600; }

    /* Hero buttons: one filled pill and one outlined pill (like Learn more / Pre-order) */
    .st-key-hero_a div.stButton > button { padding: 0.8rem 1.4rem; font-size: 1.05rem; }
    .st-key-hero_b div.stButton > button {
        background-color: transparent; border: 1px solid #2e5bff; padding: 0.8rem 1.4rem;
    }
    .st-key-hero_b div.stButton > button p { color: #7a9bff !important; font-size: 1.05rem; }
    .st-key-hero_b div.stButton > button:hover { background-color: rgba(46,91,255,0.15); }

    /* ---------- METRIC CARDS ---------- */
    [data-testid="stMetric"] {
        background: #111113; padding: 18px; border-radius: 16px;
        border: 1px solid #2c2c30; border-top: 3px solid #2e5bff;
    }
    [data-testid="stMetricLabel"] * { color: #86868b !important; font-size: 0.82rem !important; }
    [data-testid="stMetricValue"] * { color: #f5f5f7 !important; font-weight: 700; letter-spacing: -0.02em; }

    /* ---------- ALERT BOXES ---------- */
    [data-testid="stAlert"] {
        background-color: #1c1c1e !important; border: 1px solid #3a3a3f; border-radius: 12px;
    }
    [data-testid="stAlert"] * { color: #f5f5f7 !important; }

    /* ---------- TABLES ---------- */
    .stApp table { background: #111113; border-collapse: collapse; width: 100%; }
    .stApp th { background: #1c1c1e !important; color: #f5f5f7 !important; font-weight: 600; border-color: #2c2c30 !important; }
    .stApp td { color: #c7c7cc !important; background: #111113 !important; border-color: #2c2c30 !important; }
    .stApp tbody tr:nth-child(even) td { background: #161618 !important; }
    /* Only the cost breakdown tables highlight their last row (TOTAL) */
    [class*="st-key-breakdown"] tbody tr:last-child td {
        background: #15286b !important; color: #ffffff !important; font-weight: 700;
    }

    /* ---------- FORMS AND EXPANDERS ---------- */
    [data-testid="stForm"] { background: #111113; border: 1px solid #2c2c30; border-radius: 18px; }
    [data-testid="stFormSubmitButton"] > button {
        background-color: #2e5bff; color: #ffffff; border: none; border-radius: 980px;
        padding: 0.7rem 2rem; font-weight: 600; width: 100%; box-shadow: none;
    }
    [data-testid="stFormSubmitButton"] > button:hover { background-color: #4a73ff; color: #ffffff; }
    [data-testid="stFormSubmitButton"] > button p { color: #ffffff !important; }

    [data-testid="stExpander"] {
        background: #111113; border: 1px solid #2c2c30 !important; border-radius: 14px; margin-bottom: 10px;
    }
    [data-testid="stExpander"] summary, [data-testid="stExpander"] summary * {
        color: #f5f5f7 !important; font-weight: 600;
    }

    /* ---------- PROFILE AVATAR ---------- */
    .avatar {
        width: 88px; height: 88px; border-radius: 50%; margin: 4px auto 8px auto;
        background: linear-gradient(135deg, #3a3a3f, #2e5bff); color: #ffffff;
        border: 2px solid #d2d2d7;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.9rem; font-weight: 700; letter-spacing: -0.02em;
        box-shadow: 0 6px 22px rgba(46,91,255,0.40);
    }
    .profile-name { text-align: center; color: #f5f5f7; font-weight: 700; font-size: 1.4rem; letter-spacing: -0.02em; }
    .profile-sub { text-align: center; color: #86868b; font-size: 0.88rem; margin-bottom: 12px; }

    /* ---------- HOME PAGE ---------- */
    .home-heading {
        text-align: center; color: #f5f5f7; font-weight: 700; letter-spacing: -0.03em;
        font-size: clamp(1.7rem, 5vw, 2.6rem); line-height: 1.1; margin: 64px 0 8px 0;
    }
    .home-sub { text-align: center; color: #86868b; font-size: 1.1rem; margin-bottom: 26px; }

    /* Sample estimate card under the hero (like the MacBook picture in the Apple page) */
    .showcase {
        max-width: 760px; margin: 34px auto 6px auto; padding: 26px;
        background: linear-gradient(180deg, #19191c 0%, #0c0c0e 100%);
        border: 1px solid #2c2c30; border-radius: 24px;
        box-shadow: 0 30px 90px rgba(46,91,255,0.28);
    }
    .sc-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 14px; flex-wrap: wrap; margin-bottom: 8px; }
    .sc-title { color: #f5f5f7; font-weight: 600; font-size: 1.05rem; }
    .sc-sub { color: #86868b; font-size: 0.85rem; margin-top: 4px; }
    .sc-total { color: #ffffff; font-weight: 700; letter-spacing: -0.03em; font-size: clamp(1.8rem, 5.5vw, 2.8rem); line-height: 1.05; }
    .sc-right { text-align: right; }
    .sc-row { display: flex; align-items: center; gap: 12px; margin-top: 14px; }
    .sc-label { width: 92px; color: #c7c7cc; font-size: 0.86rem; flex: 0 0 auto; }
    .sc-bar { flex: 1 1 auto; height: 10px; background: #222226; border-radius: 99px; overflow: hidden; }
    .sc-fill { height: 100%; border-radius: 99px; background: linear-gradient(90deg, #2e5bff, #7a9bff); }
    .sc-amt { width: 112px; text-align: right; color: #f5f5f7; font-size: 0.86rem; flex: 0 0 auto; font-variant-numeric: tabular-nums; }

    /* Feature tiles */
    .tile-big {
        font-size: clamp(1.7rem, 4vw, 2.2rem); font-weight: 700; letter-spacing: -0.03em; line-height: 1.1;
        background: linear-gradient(90deg, #f5f5f7, #7a9bff); -webkit-background-clip: text;
        background-clip: text; -webkit-text-fill-color: transparent; margin: 6px 0 10px 0;
    }
    .tile-title { color: #f5f5f7; font-weight: 600; font-size: 1.15rem; margin-bottom: 6px; }
    .tile-text { color: #a1a1a6; font-size: 0.98rem; line-height: 1.5; margin-bottom: 8px; min-height: 3.2em; }
    [class*="st-key-tile_"] div.stButton > button {
        background: transparent; width: auto; padding: 0.2rem 0; border-radius: 0; box-shadow: none;
    }
    [class*="st-key-tile_"] div.stButton > button p { color: #2997ff !important; font-weight: 500; font-size: 1rem; }
    [class*="st-key-tile_"] div.stButton > button:hover { background: transparent; }
    [class*="st-key-tile_"] div.stButton > button:hover p { text-decoration: underline; }

    /* How it works */
    .steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
    .step { background: #111113; border: 1px solid #2c2c30; border-radius: 18px; padding: 24px; }
    .step-num {
        width: 34px; height: 34px; border-radius: 50%; background: #2e5bff; color: #ffffff;
        display: flex; align-items: center; justify-content: center; font-weight: 700; margin-bottom: 14px;
    }
    .step-title { color: #f5f5f7; font-weight: 600; font-size: 1.1rem; margin-bottom: 6px; }
    .step-text { color: #a1a1a6; font-size: 0.95rem; line-height: 1.5; }

    /* Event types */
    .events { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
    .event { background: #111113; border: 1px solid #2c2c30; border-radius: 18px; padding: 20px; }
    .event-name { color: #f5f5f7; font-weight: 600; font-size: 1.05rem; margin-bottom: 6px; }
    .event-text { color: #a1a1a6; font-size: 0.9rem; line-height: 1.45; }

    /* Closing call to action */
    .cta-title {
        text-align: center; color: #f5f5f7; font-weight: 700; letter-spacing: -0.03em;
        font-size: clamp(1.8rem, 5vw, 2.8rem); line-height: 1.1; margin: 70px 0 8px 0;
    }
    .cta-sub { text-align: center; color: #86868b; font-size: 1.1rem; margin-bottom: 22px; }
    .home-foot { text-align: center; color: #6e6e73; font-size: 0.8rem; margin-top: 46px; }

    /* ---------- SITE FOOTER (Home page) ---------- */
    /* Full-width footer band: it breaks out of the centred page column and uses the whole screen width.
       The side padding keeps the content at most 1600px wide on very large screens. */
    .st-key-sitefooter {
        width: 100vw !important; max-width: 100vw !important;
        margin-top: 70px; margin-left: calc(50% - 50vw) !important; margin-right: calc(50% - 50vw) !important;
        padding: 44px max(32px, calc((100vw - 1600px) / 2)) 12px max(32px, calc((100vw - 1600px) / 2));
        box-sizing: border-box; background: #070709; border-top: 1px solid #2c2c30;
    }
    .ft-brand {
        font-family: Georgia, "Times New Roman", serif; font-size: 2rem; font-weight: 700; letter-spacing: -0.03em;
        background: linear-gradient(115deg, #f5f7ff 0%, #b8c8ff 45%, #7898ff 100%);
        -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
    }
    .ft-tag { color: #86868b; font-size: 0.9rem; line-height: 1.5; margin: 8px 0 16px 0; }
    .ft-head {
        color: #f5f5f7; font-weight: 700; font-size: 0.85rem; letter-spacing: 0.08em;
        text-transform: uppercase; margin-bottom: 8px;
    }
    .ft-social a {
        display: inline-flex; align-items: center; justify-content: center;
        width: 38px; height: 38px; border-radius: 50%; margin: 0 8px 8px 0;
        background: #2c2c30; font-weight: 700; font-size: 0.82rem;
        text-decoration: none; transition: background-color 0.15s ease;
    }
    .stApp .ft-social a, .stApp .ft-social a:visited { color: #f5f5f7 !important; }
    .ft-social a:hover { background: #2e5bff; }
    .ft-contact { color: #a1a1a6; font-size: 0.9rem; line-height: 1.7; margin-top: 6px; overflow-wrap: anywhere; }
    .stApp .ft-contact a, .stApp .ft-contact a:visited { color: #a1a1a6 !important; text-decoration: none; }
    .stApp .ft-contact a:hover { color: #ffffff !important; text-decoration: underline; }
    .ft-copy { text-align: center; color: #6e6e73; font-size: 0.8rem; margin: 34px 0 6px 0; }

    /* Footer buttons look like plain text links, not blue pills */
    .st-key-sitefooter div.stButton > button {
        background: transparent; width: auto; min-height: 0; padding: 0.22rem 0;
        border-radius: 0; justify-content: flex-start; text-align: left;
    }
    .st-key-sitefooter div.stButton > button p {
        color: #a1a1a6 !important; font-weight: 400; font-size: 0.95rem;
    }
    .st-key-sitefooter div.stButton > button:hover { background: transparent; }
    .st-key-sitefooter div.stButton > button:hover p { color: #ffffff !important; text-decoration: underline; }

    /* About, FAQ and Contact pages */
    .about-lead { color: #c7c7cc; font-size: 1.05rem; line-height: 1.65; margin-bottom: 6px; }
    .stat-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin: 18px 0 8px 0; }
    .stat { background: #111113; border: 1px solid #2c2c30; border-radius: 18px; padding: 18px; text-align: center; }
    .stat-num {
        font-size: 1.9rem; font-weight: 700; letter-spacing: -0.03em; line-height: 1.1;
        background: linear-gradient(90deg, #f5f5f7, #7a9bff); -webkit-background-clip: text;
        background-clip: text; -webkit-text-fill-color: transparent;
    }
    .stat-label { color: #86868b; font-size: 0.85rem; margin-top: 4px; }
    .contact-line { color: #f5f5f7; font-size: 1.05rem; font-weight: 600; margin: 4px 0 2px 0; overflow-wrap: anywhere; }
    .contact-note { color: #86868b; font-size: 0.88rem; margin-bottom: 10px; }

    @media (max-width: 800px) {
        .stat-row { grid-template-columns: repeat(2, 1fr); }
        .steps { grid-template-columns: 1fr; }
        .events { grid-template-columns: repeat(2, 1fr); }
    }

    /* ---------- SMALL SCREENS ---------- */
    /* Centred button rows (hero buttons and the closing button), they wrap on small screens */
    .st-key-herobtns { flex-direction: row !important; flex-wrap: wrap; justify-content: center; align-items: center; gap: 12px !important; }
    .st-key-ctabtn { align-items: center; }
    .st-key-herobtns [data-testid="stElementContainer"], .st-key-herobtns .element-container,
    .st-key-ctabtn [data-testid="stElementContainer"], .st-key-ctabtn .element-container { width: auto !important; flex: 0 0 auto; }
    .st-key-herobtns div.stButton > button, .st-key-ctabtn div.stButton > button { width: auto; min-width: 150px; }

    /* Wide tables scroll sideways instead of breaking the page on phones */
    .stApp [data-testid="stTable"] { overflow-x: auto; }

    /* ---------- PHONE LAYOUT ---------- */
    @media (max-width: 640px) {
        .block-container { padding-top: 9rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }
        .promo { font-size: 0.78rem; padding: 10px 12px; }

        /* Top bar: hide the Eventora logo and shrink links so the mobile navigation still fits */
        .st-key-topnav [data-testid="stHorizontalBlock"] {
            display: flex !important; flex-flow: row nowrap !important;
            justify-content: stretch !important; align-items: center !important;
            gap: 0 !important; min-height: 52px; padding: 0 4px !important; width: 100% !important;
        }
        .st-key-topnav [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {
            flex: 0 0 42px !important; width: 42px !important;
        }
        .st-key-topnav [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:not(:first-child):not(:last-child) {
            flex: 1 1 0% !important; width: 0 !important;
        }
        .st-key-topnav [data-testid="stColumn"]:first-child { display: none !important; }
        .st-key-topnav [data-testid="stColumn"] > div,
        .st-key-topnav [data-testid="stColumn"] [data-testid="stVerticalBlock"] { min-height: 52px; }
        .st-key-topnav div.stButton { height: 52px; }
        .st-key-topnav div.stButton > button { height: 52px; min-height: 52px; padding: 0 0.15rem; }
        .st-key-topnav div.stButton > button p { font-size: 0.74rem; }
        .st-key-nav_Profile div.stButton > button p { font-size: 1rem; }

        .st-key-sitefooter { padding-left: 18px; padding-right: 18px; }

        /* Hero and buttons */
        .hero { padding-top: 8px; }
        .st-key-herobtns div.stButton > button, .st-key-ctabtn div.stButton > button { padding: 0.75rem 1.3rem; min-width: 150px; }
        .st-key-hero_a div.stButton > button p, .st-key-hero_b div.stButton > button p { font-size: 0.98rem; }
        .home-heading { margin-top: 48px; }
        .cta-title { margin-top: 52px; }

        /* Sample estimate card */
        .showcase { padding: 18px; border-radius: 20px; }
        .sc-right { text-align: left; }
        .sc-label { width: 66px; font-size: 0.78rem; }
        .sc-amt { width: 92px; font-size: 0.74rem; }
        .sc-row { gap: 8px; }
        .tile-text { min-height: 0; }

        /* Expander titles (saved estimates, edit expense) wrap instead of overlapping */
        [data-testid="stExpander"] summary { gap: 8px; align-items: flex-start; }
        [data-testid="stExpander"] summary p { white-space: normal !important; overflow-wrap: anywhere; line-height: 1.35; font-size: 0.95rem; }

        /* Metric cards: smaller numbers that wrap, never cut off or overlap */
        [data-testid="stMetricValue"], [data-testid="stMetricValue"] * {
            font-size: 1.45rem !important; white-space: normal !important; overflow: visible !important;
            text-overflow: clip !important; overflow-wrap: anywhere;
        }
        [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * { white-space: normal !important; }

        /* Tables: smaller text and tighter cells */
        .stApp th, .stApp td { font-size: 0.8rem; padding: 0.4rem 0.5rem !important; }

        /* Buttons with long names wrap onto two lines */
        div.stButton > button p, [data-testid="stFormSubmitButton"] > button p { white-space: normal; line-height: 1.25; }

        /* Cards, alerts and captions never push past the screen edge */
        [data-testid="stAlert"] *, [data-testid="stCaptionContainer"] p, .stApp li { overflow-wrap: anywhere; }
        [data-testid="stVerticalBlockBorderWrapper"] { padding: 0.2rem; }
    }
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
    "special_requests": "",
    "expenses": [],
    "next_expense_id": 1,
    "expense_message": None,
    "scroll_top": False,
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

## Fixed black bar at the top: Eventora logo, six menu links, a Profile icon, and a promo strip underneath
def top_nav():
    current = st.session_state["page"]
    saved_count = len(st.session_state["history"])

    ## Compact Eventora wordmark embedded in the app so no separate asset is required.
    eventora_logo = "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"

    with st.container(key="topnav"):
        ## 1 logo + 6 menu links + 1 profile icon, all spread evenly across the bar
        cols = st.columns([1.65, 1, 1, 1, 1, 1, 1, 0.55])

        with cols[0]:
            if eventora_logo.startswith("PASTE_"):
                ## Fallback text logo, shown only until the real base64 logo is pasted in
                st.markdown('<div class="brand"><b style="color:#f5f5f7;font-size:1.4rem">Eventora</b></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="brand"><img src="data:image/png;base64,{eventora_logo}" alt="Eventora" /></div>', unsafe_allow_html=True)

        for column, page_name in zip(cols[1:7], nav_pages):
            with column:
                label = page_name
                if page_name == "Saved" and saved_count > 0:
                    label = f"Saved ({saved_count})"
                st.button(
                    label, key=f"nav_{page_name}", on_click=go_to, args=(page_name,),
                    type="primary" if current == page_name else "secondary",
                )

        with cols[7]:
            st.button(
                "👤", key="nav_Profile", help="Profile", on_click=go_to, args=("Profile",),
                type="primary" if current == "Profile" else "secondary",
            )

        ## Promo strip (like the offer line under the Apple menu)
        st.markdown(
            '<div class="promo">Instant estimates with 18% GST included. '
            'Get up to <b>20% discount</b> based on your booking budget.</div>',
            unsafe_allow_html=True,
        )


## ---------------------------------------------------------------
## 4B. HOME PAGE (Apple-style landing page)
## ---------------------------------------------------------------

## Home page: hero, sample estimate, feature tiles, how it works, event types, closing call to action and footer
def home_page():

    ## Big centred hero with two pill buttons (like Learn more / Pre-order)
    st.markdown("""
    <div class="hero">
        <h1>Eventora</h1>
        <p class="hero-sub">Event Budget Calculator</p>
        <p class="hero-note">Know the cost before you book.</p>
        <p class="hero-description">Instant estimates for weddings, parties, corporate events and conferences.</p>
    </div>
    """, unsafe_allow_html=True)

    with st.container(key="herobtns"):
        st.button("Calculate budget", key="hero_a", on_click=go_to, args=("Calculator",))
        st.button("View price list", key="hero_b", on_click=go_to, args=("Price List",))

    ## Sample estimate card: a real example worked out from the price lists above
    sample_guests = 200
    sample_days = 2
    sample_rows = [
        ("Venue", venue_rates["Banquet Hall"] * sample_days),
        ("Catering", catering_rates["Veg"] * sample_guests * sample_days),
        ("Decor", decor_rates["Floral"] * sample_days),
        ("DJ & Sound", addon_rates["DJ & Sound System"] * sample_days),
    ]
    sample_subtotal = sum(cost for label, cost in sample_rows)
    sample_discount_percent = get_discount_percent(sample_subtotal)
    sample_total = sample_subtotal * (100 - sample_discount_percent) / 100 * (1 + GST_RATE)
    biggest_cost = max(cost for label, cost in sample_rows)

    bars_html = ""
    for label, cost in sample_rows:
        width = round(cost / biggest_cost * 100)
        bars_html += (
            f'<div class="sc-row"><div class="sc-label">{label}</div>'
            f'<div class="sc-bar"><div class="sc-fill" style="width:{width}%"></div></div>'
            f'<div class="sc-amt">{format_money(cost)}</div></div>'
        )

    st.markdown(
        '<div class="showcase"><div class="sc-head"><div>'
        f'<div class="sc-title">Wedding · {sample_guests} guests · {sample_days} days</div>'
        '<div class="sc-sub">Banquet Hall, Veg menu, Floral decor and DJ. A sample estimate.</div></div>'
        f'<div class="sc-right"><div class="sc-total">{format_money(sample_total)}</div>'
        f'<div class="sc-sub">After {sample_discount_percent}% discount and 18% GST</div></div></div>'
        + bars_html + '</div>',
        unsafe_allow_html=True,
    )

    ## Feature tiles: four cards, each with a link to the matching page
    st.markdown(
        '<div class="home-heading">Everything you need to plan the budget.</div>'
        '<div class="home-sub">From the first estimate to the last payment.</div>',
        unsafe_allow_html=True,
    )

    tile_row1 = st.columns(2)
    with tile_row1[0]:
        with st.container(border=True):
            st.markdown(
                '<div class="tile-big">GST included</div>'
                '<div class="tile-title">Instant estimate</div>'
                '<div class="tile-text">Venue, catering, decoration and add-ons are added up in a second, with discount and 18% GST.</div>',
                unsafe_allow_html=True,
            )
            st.button("Open calculator ›", key="tile_calc", on_click=go_to, args=("Calculator",))
    with tile_row1[1]:
        with st.container(border=True):
            st.markdown(
                '<div class="tile-big">Up to 20% off</div>'
                '<div class="tile-title">Tiered discounts</div>'
                '<div class="tile-text">Get 20% off on bookings of ₹5 lakh or more, 10% off from ₹3 lakh, and 5% off below ₹3 lakh.</div>',
                unsafe_allow_html=True,
            )
            st.button("View discount rules ›", key="tile_discounts", on_click=go_to, args=("Discounts",))

    tile_row2 = st.columns(2)
    with tile_row2[0]:
        with st.container(border=True):
            st.markdown(
                '<div class="tile-big">Extra Expenses</div>'
                '<div class="tile-title">Extra Expenses Tracker</div>'
                '<div class="tile-text">Record additional work, changes, and costs requested after the original booking.</div>',
                unsafe_allow_html=True,
            )
            st.button("Track extra expenses ›", key="tile_expenses", on_click=go_to, args=("Extra Expenses",))
    with tile_row2[1]:
        with st.container(border=True):
            st.markdown(
                '<div class="tile-big">Every option</div>'
                '<div class="tile-title">Save and compare</div>'
                '<div class="tile-text">Save each estimate with a name, then open them side by side to pick the best plan.</div>',
                unsafe_allow_html=True,
            )
            st.button("View saved estimates ›", key="tile_saved", on_click=go_to, args=("Saved",))

    ## How it works: three steps in order
    st.markdown(
        '<div class="home-heading">Three steps. That is all.</div>'
        '<div class="home-sub">No forms to print and no calls to make.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="steps">'
        '<div class="step"><div class="step-num">1</div><div class="step-title">Add your details</div>'
        '<div class="step-text">Add your event details and receive a discount of 5%, 10% or 20%, based on the booking subtotal.</div></div>'
        '<div class="step"><div class="step-num">2</div><div class="step-title">Describe your event</div>'
        '<div class="step-text">Choose the event, guests, days, venue, menu, decor and add-ons, then press Calculate Budget.</div></div>'
        '<div class="step"><div class="step-num">3</div><div class="step-title">Track every rupee</div>'
        '<div class="step-text">Save the estimate and log each payment on the Expenses page as the event comes together.</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    ## Event types the calculator is made for
    st.markdown(
        '<div class="home-heading">Made for every kind of event.</div>'
        '<div class="home-sub">Pick one and the calculator adds a tip for it.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="events">'
        '<div class="event"><div class="event-name">Wedding</div><div class="event-text">Extra days for mehendi, sangeet and the wedding itself.</div></div>'
        '<div class="event"><div class="event-name">Birthday Party</div><div class="event-text">A simple theme and return gifts go a long way.</div></div>'
        '<div class="event"><div class="event-name">Corporate Event</div><div class="event-text">Good sound and a proper stage matter most.</div></div>'
        '<div class="event"><div class="event-name">Conference</div><div class="event-text">Seating, stage and sound set-up for every session.</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    ## Closing call to action
    st.markdown(
        '<div class="cta-title">Ready to plan your event?</div>'
        '<div class="cta-sub">Get your estimate in under a minute.</div>',
        unsafe_allow_html=True,
    )
    with st.container(key="ctabtn"):
        st.button("Calculate budget", key="cta_calc", on_click=go_to, args=("Calculator",))

    ## Site footer (links, contact and social icons)
    site_footer()


## Footer shown at the bottom of the Home page (every link opens a page of this app)
def site_footer():
    with st.container(key="sitefooter"):
        brand, c1, c2, c3, c4, social = st.columns([1.5, 1, 1, 1, 1, 1.3])

        with brand:
            st.markdown(
                '<div class="ft-brand">Eventora</div>'
                '<div class="ft-tag">Event budgets made simple. Instant estimates with GST and discounts included.</div>',
                unsafe_allow_html=True,
            )

        with c1:
            st.markdown('<div class="ft-head">Explore</div>', unsafe_allow_html=True)
            st.button("Home", key="ft_home", on_click=go_to, args=("Home",))
            st.button("Calculator", key="ft_calc", on_click=go_to, args=("Calculator",))
            st.button("Price List", key="ft_price", on_click=go_to, args=("Price List",))
            st.button("Discounts", key="ft_disc", on_click=go_to, args=("Discounts",))

        with c2:
            st.markdown('<div class="ft-head">Planning</div>', unsafe_allow_html=True)
            st.button("Extra Expenses", key="ft_exp", on_click=go_to, args=("Extra Expenses",))
            st.button("Saved Estimates", key="ft_saved", on_click=go_to, args=("Saved",))
            st.button("My Profile", key="ft_profile", on_click=go_to, args=("Profile",))

        with c3:
            st.markdown('<div class="ft-head">Events</div>', unsafe_allow_html=True)
            for etype in event_types:
                st.button(etype, key=f"ft_ev_{etype}", on_click=go_to_event, args=(etype,))

        with c4:
            st.markdown('<div class="ft-head">Company</div>', unsafe_allow_html=True)
            st.button("About Us", key="ft_about", on_click=go_to, args=("About",))
            st.button("FAQ", key="ft_faq", on_click=go_to, args=("FAQ",))
            st.button("Contact Us", key="ft_contact", on_click=go_to, args=("Contact",))

        with social:
            st.markdown('<div class="ft-head">Follow us</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="ft-social">'
                '<a href="https://www.linkedin.com" target="_blank" title="LinkedIn">in</a>'
                '<a href="https://www.instagram.com" target="_blank" title="Instagram">IG</a>'
                '<a href="https://x.com" target="_blank" title="X">X</a>'
                '<a href="https://www.youtube.com" target="_blank" title="YouTube">YT</a>'
                '<a href="https://www.facebook.com" target="_blank" title="Facebook">f</a>'
                '</div>'
                '<div class="ft-contact">'
                f'<a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a><br>{CONTACT_PHONE}</div>',
                unsafe_allow_html=True,
            )

        st.markdown(
            '<div class="ft-copy">© 2026 Eventora. All rights reserved.</div>',
            unsafe_allow_html=True,
        )


## ---------------------------------------------------------------
## 4C. ABOUT, FAQ AND CONTACT PAGES (opened from the footer)
## ---------------------------------------------------------------

## About page: what Eventora is, a few facts taken from the price lists, and what makes it different
def about_page():
    page_header("About Eventora", "Event budgets made simple.")

    st.markdown(
        '<div class="about-lead">Eventora is an event budget calculator for weddings, birthday parties, '
        'corporate events and conferences. Choose the venue, menu, decoration and add-ons, and you get one clear '
        'estimate with the discount and 18% GST already worked out, so you know the cost before you book.</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="stat-row">'
        f'<div class="stat"><div class="stat-num">{len(event_types)}</div><div class="stat-label">Event types</div></div>'
        f'<div class="stat"><div class="stat-num">{len(venue_rates)}</div><div class="stat-label">Venue options</div></div>'
        f'<div class="stat"><div class="stat-num">{DISCOUNT_TIERS[0][1]}%</div><div class="stat-label">Top booking discount</div></div>'
        f'<div class="stat"><div class="stat-num">{int(GST_RATE * 100)}%</div><div class="stat-label">GST shown upfront</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="home-heading" style="margin-top:44px">What you get</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="steps">'
        '<div class="step"><div class="step-num">1</div><div class="step-title">Clear pricing</div>'
        '<div class="step-text">Every venue, menu, theme and add-on has a fixed price on the Price List page.</div></div>'
        '<div class="step"><div class="step-num">2</div><div class="step-title">Fair discounts</div>'
        '<div class="step-text">The discount (5%, 10% or 20%) depends only on the size of your booking.</div></div>'
        '<div class="step"><div class="step-num">3</div><div class="step-title">Full tracking</div>'
        '<div class="step-text">Save and compare estimates, record extra expenses and download an invoice.</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    with st.container(key="ctabtn"):
        st.button("Calculate budget", key="about_calc", on_click=go_to, args=("Calculator",))


## FAQ page: answers match the rules used by the calculator
def faq_page():
    page_header("Frequently Asked Questions", "Quick answers about estimates, discounts, saving and invoices.")

    top_tier_amount, top_tier_percent = DISCOUNT_TIERS[0]
    mid_tier_amount, mid_tier_percent = DISCOUNT_TIERS[1]

    faqs = [
        ("How is my estimate calculated?",
         "Venue rent, catering, decoration and add-ons are added to give the subtotal. The booking discount is "
         "deducted from the subtotal, and then 18% GST is added on the remaining amount."),
        ("How are venue, catering and decoration charged?",
         "Venue rent and decoration are charged per day. Catering is charged per guest per day. DJ, photography and "
         "stage add-ons are charged per day, and return gifts are charged per guest."),
        ("What discount will I get?",
         f"{top_tier_percent}% off when the subtotal is {format_money(top_tier_amount).replace('.00', '')} or more, "
         f"{mid_tier_percent}% off from {format_money(mid_tier_amount).replace('.00', '')}, and "
         f"{BASE_DISCOUNT_PERCENT}% off below that. The subtotal is counted before discount and GST."),
        ("Is GST included in the prices?",
         "The Price List shows prices before discount and 18% GST. The final estimate on the Calculator page "
         "includes the GST."),
        ("Does my client type change the discount?",
         "No. The discount depends only on the booking subtotal, not on whether you are a regular, returning or "
         "corporate client."),
        ("Can I save and compare estimates?",
         "Yes. Give an estimate a name and save it, then open the Saved page to review them. Saved estimates are "
         "kept only for your current visit, so download the invoice of anything you want to keep."),
        ("How do I get an invoice?",
         "Open the Saved page, pick an estimate and press Buy Now. A PDF invoice is prepared for download. "
         "No online payment is taken in this version."),
        ("What if the client asks for extra work after booking?",
         "Add it on the Extra Expenses page. Each extra cost is listed and added to the original total to show "
         "the revised total."),
    ]
    for question, answer in faqs:
        with st.expander(question):
            st.write(answer)

    st.markdown('<div class="cta-sub" style="margin-top:30px">Did not find your answer?</div>', unsafe_allow_html=True)
    with st.container(key="ctabtn"):
        st.button("Contact us", key="faq_contact", on_click=go_to, args=("Contact",))


## Contact page: email, phone and quick links
def contact_page():
    page_header("Contact Us", "Questions about an estimate or a booking? We are happy to help.")

    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            section_title("Email")
            st.markdown(
                f'<div class="contact-line">{CONTACT_EMAIL}</div>'
                '<div class="contact-note">Write to us and we will reply with the details.</div>',
                unsafe_allow_html=True,
            )
            st.link_button("Send an email", f"mailto:{CONTACT_EMAIL}")
    with right:
        with st.container(border=True):
            section_title("Phone")
            st.markdown(
                f'<div class="contact-line">{CONTACT_PHONE}</div>'
                '<div class="contact-note">Call us to talk through your event plan.</div>',
                unsafe_allow_html=True,
            )
            st.link_button("Call us", f"tel:{CONTACT_PHONE.replace(' ', '')}")

    with st.container(border=True):
        section_title("Quick links")
        st.write("Most answers are only a click away.")
        q1, q2, q3 = st.columns(3)
        with q1:
            st.button("Read the FAQ", key="contact_faq", on_click=go_to, args=("FAQ",), use_container_width=True)
        with q2:
            st.button("Open calculator", key="contact_calc", on_click=go_to, args=("Calculator",), use_container_width=True)
        with q3:
            st.button("View price list", key="contact_price", on_click=go_to, args=("Price List",), use_container_width=True)


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
    chart_colors = ["#2e5bff", "#7a9bff", "#a1a1a6", "#5e5ce6"]
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

    ## Discount note
    st.caption(f"A {estimate['total_discount_percent']}% discount was applied based on the subtotal before GST.")

    ## Next step: go and track the real payments
    st.caption("Next step: open the Expenses page to track every payment against this estimate.")


## Calculator page: event inputs, Calculate button and estimate display
def calculator_page():

    page_header("Budget Calculator", "Tell us about your event and get an instant estimate.")

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

    ## Card 3: add-on checkboxes and special requests
    with st.container(border=True):
        section_title("Add-on Services")

        want_dj = st.checkbox("DJ & Sound System (+₹25,000/day)", key="want_dj")
        want_photo = st.checkbox("Photography & Videography (+₹40,000/day)", key="want_photo")
        want_stage = st.checkbox("Stage & Lighting (+₹30,000/day)", key="want_stage")
        want_gifts = st.checkbox("Return Gifts (+₹150/guest)", key="want_gifts")

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

                ## Choose a fixed discount tier using the subtotal before discount and GST.
                subtotal = venue_cost + catering_cost + decor_cost + addon_cost
                bulk_discount_percent = 0
                client_discount_percent = 0
                total_discount_percent = get_discount_percent(subtotal)

                ## GST is charged on the amount after the tiered discount.
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
                    "client_phone": st.session_state.get("phone", "").strip(),
                    "client_email": st.session_state.get("email", "").strip(),
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

## Price list page: venues, catering, decoration and add-ons
def price_list_page():
    page_header("Price List", "All prices are before discount and 18% GST.")

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

    st.caption("Discounts are based on the booking subtotal before discount and 18% GST. Visit the Discounts page for the full policy.")


## ---------------------------------------------------------------
## 7. DISCOUNTS PAGE
## ---------------------------------------------------------------

def discounts_page():
    page_header("Discount Policy", "Your booking discount is determined by the subtotal before discount and GST.")

    with st.container(border=True):
        section_title("Discount Tiers")
        st.table({
            "Booking subtotal (before discount and GST)": [
                "₹5,00,000 and above",
                "₹3,00,000 and above, but below ₹5,00,000",
                "Below ₹3,00,000",
            ],
            "Fixed discount": ["20%", "10%", "5%"],
        })

    st.markdown("""
    ### How the discount works
    - The discount tier is selected automatically from the booking subtotal.
    - The discount is deducted before the 18% GST is calculated.
    - The discount is fixed for the applicable tier; client type does not add another discount.
    - A subtotal of exactly ₹5,00,000 qualifies for 20%; exactly ₹3,00,000 qualifies for 10%.
    """)
    st.info("Example: a ₹5,20,000 subtotal qualifies for a 20% discount. GST is then calculated on the remaining ₹4,16,000.")


## ---------------------------------------------------------------
## 8. EXTRA EXPENSES PAGE
## ---------------------------------------------------------------

## Track additional costs requested after the original event booking

def expenses_page():
    page_header(
        "Extra Expenses Tracker",
        "Record extra work or changes requested after the original booking, and see the revised event total."
    )

    ## Show and manage extra expenses even if a booking estimate has not been calculated yet.
    ## If there is no current estimate, extras can still be entered and reviewed; the original total is shown as zero.
    if "budget" not in st.session_state:
        original_total = 0.0
        st.info(
            "No original booking total is available in this session yet. "
            "You can still add and review extra expenses below; calculate a booking on the Calculator page "
            "when you want the revised total to include the original booking amount."
        )
        st.button("Go to Calculator", key="go_calc", on_click=go_to, args=("Calculator",))
    else:
        original_total = float(st.session_state["budget"].get("total", 0))
    extra_categories = [
        "Additional decoration",
        "Extra catering",
        "Additional equipment",
        "Extended hours / extra day",
        "Change request",
        "Other extra work",
    ]

    st.markdown(
        "Record only costs that were **not included in the original booking**. "
        "These are added on top of the original booking total."
    )

    ## Add one client-requested extra
    with st.form("expense_form", clear_on_submit=True):
        what_for = st.text_input(
            "Extra work or change requested",
            placeholder="e.g. add a flower backdrop requested after booking"
        )
        f1, f2 = st.columns(2)
        with f1:
            category = st.selectbox("Extra expense category", extra_categories)
        with f2:
            amount = st.number_input("Extra cost (₹)", min_value=0, value=0, step=500)
        add_clicked = st.form_submit_button("Add Extra Expense")

    if add_clicked:
        if what_for.strip() == "":
            st.error("Please describe the extra work or change requested.")
        elif amount <= 0:
            st.error("Extra cost must be more than ₹0.")
        else:
            clean_what = what_for.strip()
            clean_what = clean_what[0].upper() + clean_what[1:]
            st.session_state["expenses"].append({
                "id": st.session_state["next_expense_id"],
                "what": clean_what,
                "category": category,
                "amount": float(amount),
            })
            st.session_state["next_expense_id"] += 1
            st.success("Extra expense added to the booking!")

    ## Show any message from the last edit or delete
    message = st.session_state.get("expense_message")
    if message is not None:
        if message[0] == "error":
            st.error(message[1])
        else:
            st.success(message[1])
        st.session_state["expense_message"] = None

    expenses = st.session_state["expenses"]
    extra_total = sum(float(e.get("amount", 0)) for e in expenses)
    revised_total = original_total + extra_total

    ## Summary cards always show the original booking, extras, and revised total
    m1, m2, m3 = st.columns(3)
    m1.metric("Original Booking Total", format_money(original_total))
    m2.metric("Extra Expenses", format_money(extra_total))
    m3.metric("Revised Total", format_money(revised_total))

    if len(expenses) == 0:
        st.info("No extra expenses added yet. If the client requests additional work after booking, add it above.")
        return

    section_title("Additional Work and Costs")
    st.table({
        "No.": list(range(1, len(expenses) + 1)),
        "Extra Work / Change": [e["what"] for e in expenses],
        "Category": [e.get("category", "Other extra work") for e in expenses],
        "Extra Cost": [format_money(float(e["amount"])) for e in expenses],
    })

    ## Edit or remove an extra entry
    with st.expander("✏️ Edit or Remove an Extra Expense"):
        expense_ids = [e["id"] for e in expenses]
        expense_labels = {
            e["id"]: f"{position}. {e['what']} · {format_money(float(e['amount']))}"
            for position, e in enumerate(expenses, start=1)
        }
        if st.session_state.get("manage_id") not in expense_ids:
            st.session_state["manage_id"] = expense_ids[0]

        selected_id = st.selectbox(
            "Choose the extra expense", expense_ids,
            format_func=lambda i: expense_labels[i], key="manage_id",
        )
        selected = next(e for e in expenses if e["id"] == selected_id)
        edit_categories = list(extra_categories)
        old_category = selected.get("category", "Other extra work")
        if old_category not in edit_categories:
            edit_categories.append(old_category)

        with st.form("edit_expense_form"):
            st.text_input(
                "Extra work or change requested", value=selected["what"],
                key=f"edit_what_{selected_id}",
            )
            g1, g2 = st.columns(2)
            with g1:
                st.selectbox(
                    "Extra expense category", edit_categories,
                    index=edit_categories.index(old_category),
                    key=f"edit_cat_{selected_id}",
                )
            with g2:
                st.number_input(
                    "Extra cost (₹)", min_value=0, value=int(float(selected["amount"])), step=500,
                    key=f"edit_amt_{selected_id}",
                )
            st.form_submit_button(
                "Update Extra Expense", on_click=update_expense, args=(selected_id,)
            )

        st.button(
            "Delete This Extra Expense", key="delete_expense",
            on_click=delete_expense, args=(selected_id,),
        )

    st.caption("Revised total = original booking total + extra expenses recorded here. Confirm separately whether any additional tax applies to extra work.")

    ## Controls to remove the most recent entry or clear the extras list
    b1, b2 = st.columns(2)
    with b1:
        if st.button("Remove Last Extra Expense"):
            st.session_state["expenses"].pop()
            st.rerun()
    with b2:
        if st.button("Clear All Extra Expenses"):
            st.session_state["expenses"] = []
            st.rerun()


## ---------------------------------------------------------------
## 9. INVOICE GENERATION
## ---------------------------------------------------------------

def create_invoice_pdf(item):
    """Create a branded PDF invoice using Python's standard library only."""
    from datetime import datetime

    def money(key):
        try:
            return format_money(float(item.get(key, 0) or 0)).replace("₹", "INR ")
        except (TypeError, ValueError):
            return "INR 0.00"

    invoice_date = datetime.now().strftime("%d %B %Y")
    booking_id = str(item.get("booking_id") or "Not assigned")
    invoice_number = f"EV-{booking_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    client = str(item.get("client_name") or item.get("name_text") or "Client")

    def pdf_text(value):
        value = str(value).replace("₹", "INR ").replace("—", "-").replace("–", "-").replace("·", "-")
        value = value.encode("cp1252", errors="replace").decode("cp1252")
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    commands = []

    def draw_text(x, y, value, size=10, font="F1", color=(0.16, 0.18, 0.24)):
        commands.append(
            f"{color[0]} {color[1]} {color[2]} rg BT /{font} {size} Tf "
            f"{x} {y} Td ({pdf_text(value)}) Tj ET"
        )

    def line(x1, y1, x2, y2):
        commands.append(f"0.82 0.85 0.91 RG 0.7 w {x1} {y1} m {x2} {y2} l S")

    commands.append("0.08 0.16 0.40 rg 0 760 595 82 re f")
    draw_text(42, 805, "EVENTORA", 27, "F2", (1, 1, 1))
    draw_text(44, 784, "EVENT BUDGET AND EVENT MANAGEMENT", 9, "F1", (0.82, 0.87, 1))
    draw_text(440, 805, "INVOICE", 16, "F2", (1, 1, 1))
    draw_text(42, 735, f"Invoice No.: {invoice_number}", 9, "F2")
    draw_text(365, 735, f"Invoice Date: {invoice_date}", 9)
    draw_text(42, 716, f"Booking ID: {booking_id}", 9)
    draw_text(365, 716, "Payment Status: PENDING", 9, "F2", (0.65, 0.32, 0.08))
    line(42, 700, 553, 700)

    draw_text(42, 678, "BILL TO", 11, "F2", (0.08, 0.16, 0.40))
    draw_text(42, 659, client, 10, "F2")
    y = 642
    for value in [
        item.get("client_city", ""),
        f"Phone: {item.get('client_phone')}" if item.get("client_phone") else "",
        f"Email: {item.get('client_email')}" if item.get("client_email") else "",
    ]:
        if value:
            draw_text(42, y, value, 9)
            y -= 15

    draw_text(42, 590, "EVENT DETAILS", 11, "F2", (0.08, 0.16, 0.40))
    event_lines = [
        f"Event: {item.get('event_type', 'Event')}",
        f"Time: {item.get('event_time', 'Not specified')}",
        f"Guests: {item.get('guests', '-')}",
        f"Duration: {item.get('days', '-')} day(s)",
        f"Venue: {item.get('venue', '-')}",
        f"Catering: {item.get('catering', '-')}",
        f"Decoration: {item.get('decor', '-')}",
        f"Add-ons: {item.get('addons_text', 'None')}",
    ]
    y = 570
    for value in event_lines:
        draw_text(42, y, value, 9)
        y -= 15

    table_top = y - 5
    commands.append(f"0.08 0.16 0.40 rg 42 {table_top-22} 511 22 re f")
    draw_text(52, table_top-15, "DESCRIPTION", 9, "F2", (1, 1, 1))
    draw_text(440, table_top-15, "AMOUNT (INR)", 9, "F2", (1, 1, 1))
    rows = [
        ("Venue", money("venue_cost")),
        ("Catering", money("catering_cost")),
        ("Decoration", money("decor_cost")),
        ("Add-on Services", money("addon_cost")),
        ("Subtotal", money("subtotal")),
        (f"Discount ({item.get('total_discount_percent', 0)}%)", "- " + money("discount_amount")),
        ("GST (18%)", money("gst")),
        ("TOTAL PAYABLE", money("total")),
    ]
    row_y = table_top - 42
    for idx, (label, amount) in enumerate(rows):
        if idx == len(rows) - 1:
            commands.append(f"0.90 0.93 1 rg 42 {row_y-7} 511 23 re f")
        bold = "F2" if idx == len(rows) - 1 else "F1"
        draw_text(52, row_y, label, 9, bold)
        draw_text(420, row_y, amount, 9, bold)
        line(42, row_y-7, 553, row_y-7)
        row_y -= 23

    draw_text(42, max(55, row_y-12), "Generated from the saved Eventora estimate.", 8, "F1", (0.40, 0.42, 0.47))
    draw_text(42, max(40, row_y-27), "Payment has not been processed. Payment status: Pending.", 8, "F1", (0.40, 0.42, 0.47))
    draw_text(42, 25, "Thank you for choosing Eventora.", 9, "F2", (0.08, 0.16, 0.40))

    stream = "\n".join(commands).encode("cp1252", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode())
        pdf.extend(obj + b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects)+1}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(
        f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode()
    )
    return bytes(pdf), invoice_number


## ---------------------------------------------------------------
## 10. SAVED ESTIMATES PAGE
## ---------------------------------------------------------------

def saved_page():
    """Display saved estimates, allow selection for purchase, and download an invoice."""
    page_header("Saved Estimates", "Choose a saved estimate to review, purchase, and generate its invoice.")
    history = st.session_state.get("history", [])

    if not history:
        st.info("You haven't saved any estimates yet. Open Calculator, calculate a budget, and select Save Estimate.")
        st.button("Go to Calculator", key="saved_go_calculator", on_click=go_to, args=("Calculator",))
        return

    st.caption(f"{len(history)} saved estimate{'s' if len(history) != 1 else ''}")

    # Select a specific saved estimate. The selection is independent of the last calculator result.
    labels = []
    for index, item in enumerate(history):
        estimate_name = item.get("name", f"Estimate {index + 1}")
        booking = item.get("booking_id", "No booking ID")
        amount = format_money(float(item.get("total", 0) or 0))
        labels.append(f"{estimate_name} · {booking} · {amount}")

    selected_label = st.selectbox("Select the estimate you want to buy", labels, key="purchase_estimate_choice")
    selected_index = labels.index(selected_label)
    selected_item = history[selected_index]

    with st.expander(f"{selected_item.get('name', 'Selected estimate')} · {format_money(float(selected_item.get('total', 0) or 0))}", expanded=True):
        st.caption(f"Saved on: {selected_item.get('saved_on', 'Date not available')}")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Budget", format_money(float(selected_item.get("total", 0) or 0)))
        m2.metric("Guests", str(selected_item.get("guests", "—")))
        m3.metric("Discount Saved", format_money(float(selected_item.get("discount_amount", 0) or 0)))

        details = [
            f"- **Client:** {selected_item.get('client_name') or selected_item.get('name_text', '—')}",
            f"- **Booking ID:** {selected_item.get('booking_id', '—')}",
            f"- **Event:** {selected_item.get('event_type', '—')} ({selected_item.get('event_time', '—')})",
            f"- **Venue:** {selected_item.get('venue', '—')}",
            f"- **Catering:** {selected_item.get('catering', '—')}",
            f"- **Decoration:** {selected_item.get('decor', '—')}",
            f"- **Add-ons:** {selected_item.get('addons_text', 'None')}",
        ]
        st.markdown("\n".join(details))
        st.table({
            "Item": ["Venue", "Catering", "Decoration", "Add-ons", "Subtotal",
                     f"Discount ({selected_item.get('total_discount_percent', 0)}%)", "GST (18%)", "TOTAL"],
            "Amount": [
                format_money(float(selected_item.get("venue_cost", 0) or 0)),
                format_money(float(selected_item.get("catering_cost", 0) or 0)),
                format_money(float(selected_item.get("decor_cost", 0) or 0)),
                format_money(float(selected_item.get("addon_cost", 0) or 0)),
                format_money(float(selected_item.get("subtotal", 0) or 0)),
                "-" + format_money(float(selected_item.get("discount_amount", 0) or 0)),
                format_money(float(selected_item.get("gst", 0) or 0)),
                format_money(float(selected_item.get("total", 0) or 0)),
            ],
        })

    st.markdown("### Purchase this estimate")
    st.caption("Select Buy Now to prepare an invoice for this exact saved estimate. No online payment is processed in this version.")
    if st.button("Buy Now", key="buy_selected_estimate", type="primary", use_container_width=True):
        st.session_state["invoice_estimate_index"] = selected_index
        st.session_state["invoice_generated_at"] = datetime.now().strftime("%Y%m%d%H%M%S")

    invoice_index = st.session_state.get("invoice_estimate_index")
    if invoice_index is not None:
        if invoice_index < len(history):
            invoice_item = history[invoice_index]
            pdf_bytes, invoice_number = create_invoice_pdf(invoice_item)
            safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(invoice_item.get("name", "Eventora_Invoice")))
            st.success(f"Invoice {invoice_number} is ready. Payment status: Pending.")
            st.download_button(
                label="Download Invoice (PDF)",
                data=pdf_bytes,
                file_name=f"Eventora_Invoice_{safe_name}.pdf",
                mime="application/pdf",
                key=f"download_invoice_{invoice_index}_{st.session_state.get('invoice_generated_at', '')}",
                use_container_width=True,
            )
        else:
            st.session_state.pop("invoice_estimate_index", None)

    st.divider()
    st.caption("You can still manage your saved estimates below.")
    for index, item in enumerate(history):
        with st.expander(f"Manage: {item.get('name', f'Estimate {index + 1}')}"):
            st.button(
                "Delete this estimate", key=f"delete_saved_{index}",
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
            help="Discount is based on the booking subtotal: 5%, 10% or 20%. Client type does not change the discount tier.",
        )
    st.caption("Your details are saved automatically and used on the Calculator page.")


## ---------------------------------------------------------------
## 10. DRAW THE TOP BAR AND SHOW THE SELECTED PAGE
## ---------------------------------------------------------------

## Top menu bar: always visible, the open page is underlined in royal blue
top_nav()

## Show the page that is selected
current_page = st.session_state["page"]
if current_page == "Home":
    home_page()
elif current_page == "Calculator":
    calculator_page()
elif current_page == "Price List":
    price_list_page()
elif current_page == "Discounts":
    discounts_page()
elif current_page == "Extra Expenses":
    expenses_page()
elif current_page == "Saved":
    saved_page()
elif current_page == "About":
    about_page()
elif current_page == "FAQ":
    faq_page()
elif current_page == "Contact":
    contact_page()
else:
    profile_page()

## After a page change (for example a footer link), scroll back to the top so the new page starts from its heading
if st.session_state["scroll_top"]:
    st.session_state["scroll_top"] = False
    components.html(
        "<script>"
        "const doc = window.parent.document;"
        "const box = doc.querySelector('[data-testid=\"stMain\"]') || doc.querySelector('section.main');"
        "if (box) { box.scrollTo(0, 0); }"
        "window.parent.scrollTo(0, 0);"
        "</script>",
        height=0,
    )

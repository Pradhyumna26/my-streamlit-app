## Event Budget Calculator (business idea: Event Management)
## Run with: streamlit run app.py
## Needs Python 3.10 or newer (match-case is used) and a recent Streamlit: pip install --upgrade streamlit
## The app has a TOP menu bar (Apple-style black bar) with 6 pages:
##   Home, Calculator, Price List, Expenses, Saved and Profile
## The footer on the Home page also opens three extra pages: About, FAQ and Contact


## Import the libraries: html (safe text for the avatar), datetime (save time), pandas (chart data), streamlit (the app)
import html
import base64
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

    /* Uploaded photo for the DJ & Sound System card */
    .addon-photo {
        width: 100%;
        height: 112px;
        overflow: hidden;
        border-radius: 12px;
        margin-bottom: 10px;
        border: 1px solid #26314f;
        background: #080b18;
    }
    .addon-photo img {
        display: block;
        width: 100%;
        height: 100%;
        object-fit: cover;
        object-position: center;
    }

    /* ---------- ADD-ON SERVICES: FOUR-CARD GRID ---------- */
    .addon-icon {
        width: 48px; height: 48px; border-radius: 14px;
        display: flex; align-items: center; justify-content: center;
        background: rgba(46, 91, 255, 0.12);
        border: 1px solid #26314f; color: #7a9bff;
        margin-bottom: 10px;
    }
    .addon-icon svg {
        width: 25px; height: 25px; fill: none; stroke: currentColor;
        stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round;
    }
    .st-key-addons [data-testid="stHorizontalBlock"] {
        gap: 16px !important; align-items: stretch !important;
    }
    .st-key-addons [data-testid="stVerticalBlockBorderWrapper"] {
        height: 100%; min-height: 150px;
        background: linear-gradient(180deg, #151518 0%, #0d0d10 100%);
        border: 1px solid #303039 !important;
        border-radius: 16px;
        padding: 14px !important;
        transition: border-color 0.18s ease, background 0.18s ease;
    }
    .st-key-addons [data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: #496fff !important;
    }
    .st-key-addons [data-testid="stCheckbox"] { margin-top: 4px; }
    .st-key-addons [data-testid="stCaptionContainer"] p {
        color: #7a9bff !important; font-size: 0.88rem; font-weight: 600;
        margin-top: 2px;
    }
    @media (max-width: 640px) {
        .st-key-addons [data-testid="stHorizontalBlock"] { gap: 10px !important; }
        .st-key-addons [data-testid="stVerticalBlockBorderWrapper"] {
            min-height: 145px; padding: 10px !important;
        }
    }

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


## Simple line icons for the add-on services (drawn in code, so no image files are needed)
# Uploaded DJ-controller image, embedded so the app remains a single-file project.
DJ_CONTROLLER_IMAGE = 'data:image/jpeg;base64,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'


addon_icons = {
    "dj": '<path d="M7 3h10a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/>'
          '<circle cx="12" cy="14.5" r="3.5"/><circle cx="12" cy="7.5" r="1"/>',
    "photo": '<path d="M5 7h14a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2z"/>'
             '<path d="M8 7l1.5-3h5L16 7"/><circle cx="12" cy="13.5" r="3.5"/>',
    "stage": '<path d="M8 3h8l2 6H6z"/><path d="M7 13l-3 7M12 13v7M17 13l3 7"/>',
    "gift": '<rect x="4" y="10" width="16" height="11" rx="1"/><rect x="3" y="7" width="18" height="3" rx="1"/>'
            '<path d="M12 7v14"/><path d="M12 7c-2-3-5-3-5-1s3 1 5 1zM12 7c2-3 5-3 5-1s-3 1-5 1z"/>',
}


## One add-on row: icon tile on the left, checkbox on the right. Returns True when it is ticked.
def addon_row(icon_name, label, key):
    icon_col, box_col = st.columns([1, 12], vertical_alignment="center")
    with icon_col:
        st.markdown(
            f'<div class="addon-icon"><svg viewBox="0 0 24 24">{addon_icons[icon_name]}</svg></div>',
            unsafe_allow_html=True,
        )
    with box_col:
        return st.checkbox(label, key=key)


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

    ## Card 3: add-on services displayed in a 2 x 2 card grid
    with st.container(border=True):
        section_title("Add-on Services")

        with st.container(key="addons"):
            ## First row: DJ and Photography
            col1, col2 = st.columns(2, gap="medium")

            with col1:
                with st.container(border=True):
                    st.markdown(
                        f'<div class="addon-photo"><img src="{DJ_CONTROLLER_IMAGE}" alt="DJ controller and sound mixing equipment"></div>',
                        unsafe_allow_html=True,
                    )
                    want_dj = st.checkbox("DJ & Sound System", key="want_dj")
                    st.caption("+₹25,000 / day")

            with col2:
                with st.container(border=True):
                    st.markdown(
                        f'<div class="addon-icon"><svg viewBox="0 0 24 24">{addon_icons["photo"]}</svg></div>',
                        unsafe_allow_html=True,
                    )
                    want_photo = st.checkbox("Photography & Videography", key="want_photo")
                    st.caption("+₹40,000 / day")

            ## Second row: Stage and Return Gifts
            col3, col4 = st.columns(2, gap="medium")

            with col3:
                with st.container(border=True):
                    st.markdown(
                        f'<div class="addon-icon"><svg viewBox="0 0 24 24">{addon_icons["stage"]}</svg></div>',
                        unsafe_allow_html=True,
                    )
                    want_stage = st.checkbox("Stage & Lighting", key="want_stage")
                    st.caption("+₹30,000 / day")

            with col4:
                with st.container(border=True):
                    st.markdown(
                        f'<div class="addon-icon"><svg viewBox="0 0 24 24">{addon_icons["gift"]}</svg></div>',
                        unsafe_allow_html=True,
                    )
                    want_gifts = st.checkbox("Return Gifts", key="want_gifts")
                    st.caption("+₹150 / guest")

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
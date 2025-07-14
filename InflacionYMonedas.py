import streamlit as st
import pandas as pd
from datetime import datetime

# --- Load data ---
@st.cache_data
def load_data():
    df = pd.read_csv('IPC_MoM_extended_month_forward_added_currency.csv')
    return df

df = load_data()

# --- Redenominations ---
redenominations = [
    (datetime(1970, 1, 1), 2, 'Peso Ley 18.188'),
    (datetime(1983, 6, 1), 4, 'Peso Argentino'),
    (datetime(1985, 6, 15), 3, 'Austral'),
    (datetime(1992, 1, 1), 4, 'Peso'),
]

def get_currency(date):
    for change_date, _, currency in reversed(redenominations):
        if date >= change_date:
            return currency
    return 'Peso Moneda Nacional'

def to_current_peso(amount, date):
    for change_date, zeroes, _ in redenominations:
        if date < change_date:
            amount /= 10 ** zeroes
    return amount

def from_current_peso(amount, date):
    for change_date, zeroes, _ in reversed(redenominations):
        if date < change_date:
            amount *= 10 ** zeroes
    return amount

def parse_date(date_str):
    for fmt in ('%d/%m/%Y', '%m/%d/%Y'):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None

def get_cumulative_inflation(df, start_date, end_date):
    # Find the rows for the dates
    df['ParsedDate'] = df['Date'].apply(parse_date)
    df = df.dropna(subset=['ParsedDate'])
    df = df.sort_values('ParsedDate')
    mask = (df['ParsedDate'] >= start_date) & (df['ParsedDate'] <= end_date)
    inflation_factors = (1 + df.loc[mask, 'CPI_MoM'].astype(float)).cumprod()
    if inflation_factors.empty:
        return 1.0
    return inflation_factors.iloc[-1]

# --- Streamlit UI ---
st.title("Argentina Inflation Calculator (with Currency Changes)")

direction = st.radio(
    "Choose conversion direction:",
    ("Past → Present (adjust for inflation)", "Present → Past (deflate for inflation)")
)

amount = st.number_input("Enter the amount:", min_value=0.0, value=100.0)
date_str = st.text_input("Enter the date (dd/mm/yyyy or mm/dd/yyyy):", "01/01/1980")

date = parse_date(date_str)
today = df['Date'].iloc[-1]
today_date = parse_date(today)

if date is None:
    st.error("Invalid date format. Please use dd/mm/yyyy or mm/dd/yyyy.")
else:
    if direction == "Past → Present (adjust for inflation)":
        # Convert to current Peso
        currency = get_currency(date)
        amount_in_pesos = to_current_peso(amount, date)
        # Apply inflation
        inflation_factor = get_cumulative_inflation(df, date, today_date)
        adjusted_amount = amount_in_pesos * inflation_factor
        st.write(f"Original amount: {amount} ({currency}) on {date.strftime('%d/%m/%Y')}")
        st.write(f"Converted to current Peso: {amount_in_pesos:.8f}")
        st.write(f"Inflation-adjusted value (current Peso): {adjusted_amount:.2f}")
        st.write(f"Inflation period: {date.strftime('%d/%m/%Y')} to {today_date.strftime('%d/%m/%Y')}")
    else:
        # Convert from current Peso to past currency
        currency = get_currency(date)
        inflation_factor = get_cumulative_inflation(df, date, today_date)
        amount_in_pesos = amount / inflation_factor
        amount_in_past = from_current_peso(amount_in_pesos, date)
        st.write(f"Current amount: {amount} (Peso) on {today_date.strftime('%d/%m/%Y')}")
        st.write(f"Deflated to {amount_in_pesos:.8f} current Peso on {date.strftime('%d/%m/%Y')}")
        st.write(f"Equivalent in {currency} on {date.strftime('%d/%m/%Y')}: {amount_in_past:.2f}")
        st.write(f"Inflation period: {date.strftime('%d/%m/%Y')} to {today_date.strftime('%d/%m/%Y')}")

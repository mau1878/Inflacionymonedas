import streamlit as st
import pandas as pd
from datetime import datetime

# --- Currency conversion info ---
currency_steps = [
    ('Peso Moneda Nacional', datetime(1881, 11, 5), 0),
    ('Peso Ley 18.188', datetime(1970, 1, 1), 2),
    ('Peso Argentino', datetime(1983, 6, 1), 4),
    ('Austral', datetime(1985, 6, 15), 3),
    ('Peso', datetime(1992, 1, 1), 4),
]

def get_currency_and_factor(date):
    factor = 1
    current = 'Peso Moneda Nacional'
    for i in range(1, len(currency_steps)):
        if date >= currency_steps[i][1]:
            factor *= 10 ** currency_steps[i][2]
            current = currency_steps[i][0]
    return current, factor

def convert_to_current_peso(amount, date):
    # List of redenominations: (date, zeroes removed)
    redenominations = [
        (datetime(1970, 1, 1), 2),   # Peso Moneda Nacional → Peso Ley 18.188
        (datetime(1983, 6, 1), 4),   # Peso Ley 18.188 → Peso Argentino
        (datetime(1985, 6, 15), 3),  # Peso Argentino → Austral
        (datetime(1992, 1, 1), 4),   # Austral → Peso
    ]
    for change_date, zeroes in redenominations:
        if date < change_date:
            amount /= 10 ** zeroes
    return amount

# --- Load data ---
@st.cache_data
def load_data():
    df = pd.read_csv('IPC_MoM_extended_month_forward_added_currency.csv')
    return df

df = load_data()

# --- Streamlit UI ---
st.title("Argentina Inflation Calculator (with Currency Changes)")

amount = st.number_input("Enter the amount:", min_value=0.0, value=100.0)
date_str = st.text_input("Enter the start date (dd/mm/yyyy or mm/dd/yyyy):", "01/01/1980")

# Parse date
date = None
for fmt in ('%d/%m/%Y', '%m/%d/%Y'):
    try:
        date = datetime.strptime(date_str, fmt)
        break
    except ValueError:
        continue

if date is None:
    st.error("Invalid date format. Please use dd/mm/yyyy or mm/dd/yyyy.")
else:
    # Find the row in the CSV matching the date
    df['ParsedDate'] = df['Date'].apply(
        lambda x: next((datetime.strptime(x, fmt) for fmt in ('%d/%m/%Y', '%m/%d/%Y') if not pd.isna(x) and len(x.split('/'))==3 and all(part.isdigit() for part in x.split('/')) and len(x.split('/')[2])==4 and datetime.strptime(x, fmt)), None)
        if isinstance(x, str) else None
    )
    df = df.dropna(subset=['ParsedDate'])
    df = df.sort_values('ParsedDate')
    # Find the index of the start date
    start_idx = df[df['ParsedDate'] >= date].index.min()
    if pd.isna(start_idx):
        st.error("Date not found in data.")
    else:
        # Calculate cumulative inflation from start date to last available
        inflation_factors = (1 + df.loc[start_idx:, 'CPI_MoM'].astype(float)).cumprod()
        final_factor = inflation_factors.iloc[-1]
        # Currency conversion
        currency, factor = get_currency_and_factor(date)
        amount_in_pesos = convert_to_current_peso(amount, date)
        adjusted_amount = amount_in_pesos * final_factor
        st.write(f"Original amount: {amount} ({currency}) on {date.strftime('%d/%m/%Y')}")
        st.write(f"Converted to current Peso: {amount_in_pesos:.8f}")
        st.write(f"Inflation-adjusted value (current Peso): {adjusted_amount:.2f}")
        st.write(f"Inflation period: {date.strftime('%d/%m/%Y')} to {df['ParsedDate'].iloc[-1].strftime('%d/%m/%Y')}")

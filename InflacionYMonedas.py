import streamlit as st
import pandas as pd
from datetime import datetime

# --- Redenominaciones ---
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
    df['ParsedDate'] = df['Date'].apply(parse_date)
    df = df.dropna(subset=['ParsedDate'])
    df = df.sort_values('ParsedDate')
    mask = (df['ParsedDate'] >= start_date) & (df['ParsedDate'] <= end_date)
    inflation_factors = (1 + df.loc[mask, 'CPI_MoM'].astype(float)).cumprod()
    if inflation_factors.empty:
        return 1.0
    return inflation_factors.iloc[-1]

def format_arg_amount(amount, decimals=2):
    return f"{amount:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- Cargar datos ---
@st.cache_data
def load_data():
    df = pd.read_csv('IPC_MoM_extended_month_forward_added_currency.csv')
    return df

df = load_data()
df['ParsedDate'] = df['Date'].apply(parse_date)
min_date = df['ParsedDate'].min()
max_date = df['ParsedDate'].max()

# --- Interfaz de usuario ---
st.title("Calculadora de Inflación Argentina (con Cambios de Moneda)")

st.markdown("""
Esta calculadora permite convertir valores históricos a valores actuales (y viceversa) teniendo en cuenta la inflación y los cambios de moneda ocurridos en la historia argentina.

**Cambios de moneda en Argentina:**
- **Peso Moneda Nacional** (hasta 1970)
- **Peso Ley 18.188** (desde 1970, se quitaron 2 ceros)
- **Peso Argentino** (desde 1983, se quitaron 4 ceros)
- **Austral** (desde 1985, se quitaron 3 ceros)
- **Peso** (desde 1992, se quitaron 4 ceros)

Por ejemplo, $10.000.000 de Pesos Moneda Nacional equivalen a 1 Peso actual.

---
""")

st.warning(
    "⚠️ El IPC utilizado es mensual y los cálculos son aproximados, especialmente para períodos muy largos o con alta inflación acumulada. "
    "Los resultados deben interpretarse como una referencia orientativa."
)

direction = st.radio(
    "¿Qué desea calcular?",
    ("Pasado → Presente (ajustar por inflación)", "Presente → Pasado (deflactar por inflación)")
)

amount = st.number_input("Ingrese el monto:", min_value=0.0, value=100.0, step=1.0, format="%.2f")
date_str = st.text_input(
    f"Ingrese la fecha (dd/mm/aaaa o mm/dd/aaaa) entre {min_date.strftime('%d/%m/%Y')} y {max_date.strftime('%d/%m/%Y')}:",
    "01/01/1980"
)

date = parse_date(date_str)
today = df['Date'].iloc[-1]
today_date = parse_date(today)

if date is None:
    st.error("Formato de fecha inválido. Use dd/mm/aaaa o mm/dd/aaaa.")
elif date < min_date or date > max_date:
    st.error(
        f"La fecha ingresada está fuera del rango de datos disponibles ({min_date.strftime('%d/%m/%Y')} a {max_date.strftime('%d/%m/%Y')})."
    )
else:
    if direction == "Pasado → Presente (ajustar por inflación)":
        currency = get_currency(date)
        amount_in_pesos = to_current_peso(amount, date)
        inflation_factor = get_cumulative_inflation(df, date, today_date)
        adjusted_amount = amount_in_pesos * inflation_factor
        adjusted_amount_no_redenom = amount * inflation_factor  # Solo inflación, sin quita de ceros

        st.markdown(f"""
**Monto original:**  
{format_arg_amount(amount)} ({currency}) al {date.strftime('%d/%m/%Y')}  
_Es el valor nominal en la moneda vigente en esa fecha._

**Equivalente en pesos actuales (solo por cambios de moneda):**  
{format_arg_amount(amount_in_pesos, 8)} (Peso)  
_Este valor **no** está ajustado por inflación, solo refleja la conversión por quita de ceros y cambios de moneda._

**Monto ajustado solo por inflación (sin cambios de moneda):**  
{format_arg_amount(adjusted_amount_no_redenom)} ({currency})  
_Es el valor que tendría hoy ese monto si nunca se hubieran quitado ceros ni cambiado de moneda, solo ajustando por inflación._

**Monto ajustado por inflación y cambios de moneda:**  
{format_arg_amount(adjusted_amount)} (Peso)  
_Es el valor que tendría hoy ese monto, ajustado por la inflación acumulada **y** considerando los cambios de moneda y la quita de ceros._

**Período de inflación considerado:**  
{date.strftime('%d/%m/%Y')} a {today_date.strftime('%d/%m/%Y')}
""")
    else:
        currency = get_currency(date)
        inflation_factor = get_cumulative_inflation(df, date, today_date)
        amount_in_pesos = amount / inflation_factor
        amount_in_past = from_current_peso(amount_in_pesos, date)
        amount_in_past_no_redenom = amount_in_pesos  # Solo inflación, sin quita de ceros

        st.markdown(f"""
**Monto actual:**  
{format_arg_amount(amount)} (Peso) al {today_date.strftime('%d/%m/%Y')}  
_Es el valor nominal en la moneda vigente hoy._

**Equivalente deflactado a la fecha seleccionada (solo por inflación):**  
{format_arg_amount(amount_in_past_no_redenom, 8)} (Peso) al {date.strftime('%d/%m/%Y')}  
_El monto actual ajustado hacia atrás por la inflación acumulada, sin considerar cambios de moneda._

**Equivalente en la moneda histórica (con cambios de moneda):**  
{format_arg_amount(amount_in_past)} ({currency}) al {date.strftime('%d/%m/%Y')}  
_El valor que tendría ese monto en la moneda vigente en la fecha seleccionada, considerando los cambios de moneda y la quita de ceros._

**Período de inflación considerado:**  
{date.strftime('%d/%m/%Y')} a {today_date.strftime('%d/%m/%Y')}
""")

st.info("""
**Referencias sobre los cambios de moneda en Argentina:**
- 1970: Peso Moneda Nacional → Peso Ley 18.188 (se quitaron 2 ceros)
- 1983: Peso Ley 18.188 → Peso Argentino (se quitaron 4 ceros)
- 1985: Peso Argentino → Austral (se quitaron 3 ceros)
- 1992: Austral → Peso (se quitaron 4 ceros)

**Fuente de datos:** IPC mensual de Argentina (1943-2025).

---

_Creado por MTaurus (X: [@mtaurus_ok](https://x.com/mtaurus_ok))_
""")

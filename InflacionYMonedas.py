import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from num2words import num2words

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

def add_months(dt, months):
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, [31,
        29 if year%4==0 and not year%100==0 or year%400==0 else 28,
        31,30,31,30,31,31,30,31,30,31][month-1])
    return datetime(year, month, day)

def get_cumulative_inflation(df, start_date, end_date):
    df['ParsedDate'] = pd.to_datetime(df['Date'], errors='coerce', dayfirst=True)
    df = df.dropna(subset=['ParsedDate'])
    df = df.sort_values('ParsedDate')
    first_inflation_date = add_months(start_date, 1).replace(day=1)
    mask = (df['ParsedDate'] >= first_inflation_date) & (df['ParsedDate'] <= end_date)
    inflation_factors = (1 + df.loc[mask, 'CPI_MoM'].astype(float)).cumprod()
    return inflation_factors.iloc[-1] if not inflation_factors.empty else 1.0

def format_arg_amount(amount, decimals=2):
    # For very small values (< 1e-6 and not zero), return both normal and scientific notation
    if abs(amount) < 1e-6 and amount != 0:
        high_precision_decimals = 12  # High precision for decimal format
        scientific_decimals = 8  # Precision for scientific notation
        # Normal format with high precision
        formatted_normal = f"{amount:,.{high_precision_decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
        # Scientific notation
        formatted_scientific = f"{amount:.{scientific_decimals}e}".replace("e", "×10^")
        return formatted_normal, formatted_scientific
    # For other values, use standard Argentine format
    formatted_normal = f"{amount:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted_normal, None

def amount_to_words(amount, currency, decimals=2):
    entero = int(round(amount))
    decimales = int(round((amount - entero) * (10 ** decimals)))
    if decimales > 0:
        return f"{num2words(entero, lang='es').capitalize()} {currency} con {num2words(decimales, lang='es')} centavos"
    return f"{num2words(entero, lang='es').capitalize()} {currency}"

# --- Cargar datos ---
@st.cache_data
def load_data():
    df = pd.read_csv('IPC_MoM_extended_month_forward_added_currency.csv')
    return df

# Initialize session state
if 'direction' not in st.session_state:
    st.session_state.direction = "Pasado → Presente (ajustar por inflación)"

# --- Interfaz de usuario ---
st.title("Calculadora de Inflación Argentina (con Cambios de Moneda)")

st.markdown("""
Esta calculadora te permite saber cuánto valdría hoy un monto del pasado, o cuánto valdría en el pasado un monto actual, teniendo en cuenta la inflación y los cambios de moneda que hubo en la Argentina.

**¿Por qué es importante esto?**  
A lo largo de la historia argentina, la moneda cambió varias veces y se le quitaron ceros para simplificar los billetes. Además, la inflación hace que el valor real del dinero cambie con el tiempo.

**Cambios de moneda en Argentina:**
- **Peso Moneda Nacional** (hasta 1970)
- **Peso Ley 18.188** (desde 1970, se quitaron 2 ceros)
- **Peso Argentino** (desde 1983, se quitaron 4 ceros)
- **Austral** (desde 1985, se quitaron 3 ceros)
- **Peso** (desde 1992, se quitaron 4 ceros)

Por ejemplo, $10.000.000 de Pesos Moneda Nacional (antes de 1970) equivalen a 1 Peso actual.

---
""")

st.warning(
    "⚠️ El IPC utilizado es mensual y los cálculos son aproximados, especialmente para períodos muy largos o con alta inflación acumulada. "
    "Los resultados deben tomarse como una referencia orientativa, no como un valor exacto.\n\n"
    "IMPORTANTE: En el archivo de datos, la columna 'Date' indica el primer día del mes siguiente al período de inflación mensual. "
    "Por ejemplo, el valor junto a 01/02/1945 corresponde a la inflación de enero de 1945.\n\n"
    "NOTA: Para valores muy pequeños (menores a 0.000001), se muestran tanto el formato decimal con 12 decimales como la notación científica con 8 decimales para mayor precisión.\n\n"
    "NOTA: El monto ingresado se muestra formateado con separadores de miles debajo del campo de entrada para facilitar la lectura."
)

# Load data
df = load_data()
df['ParsedDate'] = pd.to_datetime(df['Date'], errors='coerce', dayfirst=True)
min_date = df['ParsedDate'].min().date()
max_date = df['ParsedDate'].max().date()

# Radio button for mode selection
st.session_state.direction = st.radio(
    "¿Qué querés calcular?",
    (
        "Pasado → Presente (ajustar por inflación)",
        "Presente → Pasado (deflactar por inflación)"
    ),
    key="direction_radio"
)

# Debug: Display current direction
st.write(f"Modo actual: {st.session_state.direction}")

# Input form to handle amount and date
with st.form("calculation_form"):
    if st.session_state.direction == "Pasado → Presente (ajustar por inflación)":
        st.subheader("¿Cuánto valdría hoy un monto del pasado?")
        amount = st.number_input(
            "Ingresá el monto que tenías en el pasado:",
            min_value=0.0, value=100.0, step=1.0, format="%.2f",
            key="amount_past"
        )
        # Display formatted amount in real-time
        amount_normal, amount_scientific = format_arg_amount(amount)
        amount_display = f"Monto formateado: {amount_normal}"
        if amount_scientific:
            amount_display += f" ({amount_scientific})"
        st.write(amount_display)
        selected_date = st.date_input(
            f"¿De qué fecha es ese monto? (seleccioná una fecha entre {min_date.strftime('%d/%m/%Y')} y {max_date.strftime('%d/%m/%Y')}):",
            value=date(1980, 1, 1),
            min_value=min_date,
            max_value=max_date,
            key="date_past"
        )
    else:
        st.subheader("¿Cuánto valdría en el pasado un monto actual?")
        amount = st.number_input(
            "Ingresá el monto que tenés hoy:",
            min_value=0.0, value=100.0, step=1.0, format="%.2f",
            key="amount_present"
        )
        # Display formatted amount in real-time
        amount_normal, amount_scientific = format_arg_amount(amount)
        amount_display = f"Monto formateado: {amount_normal}"
        if amount_scientific:
            amount_display += f" ({amount_scientific})"
        st.write(amount_display)
        selected_date = st.date_input(
            f"¿A qué fecha querés llevar ese monto? (seleccioná una fecha entre {min_date.strftime('%d/%m/%Y')} y {max_date.strftime('%d/%m/%Y')}):",
            value=date(1980, 1, 1),
            min_value=min_date,
            max_value=max_date,
            key="date_present"
        )
    
    submitted = st.form_submit_button("Calcular")

if submitted:
    # Convert selected_date (datetime.date) to datetime.datetime
    date = datetime.combine(selected_date, datetime.min.time())
    today = df['ParsedDate'].iloc[-1].to_pydatetime()

    if date < datetime.combine(min_date, datetime.min.time()) or date > datetime.combine(max_date, datetime.min.time()):
        st.error(
            f"La fecha seleccionada está fuera del rango de datos disponibles ({min_date.strftime('%d/%m/%Y')} a {max_date.strftime('%d/%m/%Y')})."
        )
    else:
        if st.session_state.direction == "Pasado → Presente (ajustar por inflación)":
            currency = get_currency(date)
            amount_in_pesos = to_current_peso(amount, date)
            inflation_factor = get_cumulative_inflation(df, date, today)
            adjusted_amount = amount_in_pesos * inflation_factor
            adjusted_amount_no_redenom = amount * inflation_factor

            # Format amounts
            amount_normal, amount_scientific = format_arg_amount(amount)
            amount_in_pesos_normal, amount_in_pesos_scientific = format_arg_amount(amount_in_pesos, 8)
            adjusted_amount_no_redenom_normal, adjusted_amount_no_redenom_scientific = format_arg_amount(adjusted_amount_no_redenom)
            adjusted_amount_normal, adjusted_amount_scientific = format_arg_amount(adjusted_amount)
            example_amount_normal, example_amount_scientific = format_arg_amount(
                to_current_peso(100, datetime(1980, 1, 1)) * get_cumulative_inflation(df, datetime(1980, 1, 1), today)
            )

            # Build output string
            amount_display = f"{amount_normal} ({currency})"
            if amount_scientific:
                amount_display += f"\n({amount_scientific})"
            amount_in_pesos_display = f"{amount_in_pesos_normal} (Peso)"
            if amount_in_pesos_scientific:
                amount_in_pesos_display += f"\n({amount_in_pesos_scientific})"
            adjusted_amount_no_redenom_display = f"{adjusted_amount_no_redenom_normal} ({currency})"
            if adjusted_amount_no_redenom_scientific:
                adjusted_amount_no_redenom_display += f"\n({adjusted_amount_no_redenom_scientific})"
            adjusted_amount_display = f"{adjusted_amount_normal} (Peso)"
            if adjusted_amount_scientific:
                adjusted_amount_display += f"\n({adjusted_amount_scientific})"
            example_amount_display = f"{example_amount_normal} (Peso)"
            if example_amount_scientific:
                example_amount_display += f"\n({example_amount_scientific})"

            st.markdown(f"""
**Monto original:**  
{amount_display} al {date.strftime('%d/%m/%Y')}  
_{amount_to_words(amount, currency)}_

**Equivalente en pesos actuales (solo por cambios de moneda):**  
{amount_in_pesos_display}  
_{amount_to_words(amount_in_pesos, 'pesos', 8)}_  
Este valor muestra cuántos pesos actuales obtendrías si solo se aplicaran los cambios de moneda y la quita de ceros, **sin** tener en cuenta la inflación.  
Por ejemplo, si en 1991 tenías 100.000 Australes, hoy serían 10 Pesos actuales, porque en 1992 se quitaron 4 ceros y se cambió de Austral a Peso.

**Monto ajustado solo por inflación (sin cambios de moneda):**  
{adjusted_amount_no_redenom_display}  
_{amount_to_words(adjusted_amount_no_redenom, currency)}_  
Este valor muestra cuánto dinero necesitarías hoy, en la **misma moneda antigua**, para tener el mismo poder de compra que tenías en esa fecha.  
Por ejemplo, si en 1980 tenías 100 Pesos Ley, hoy necesitarías {format_arg_amount(100 * get_cumulative_inflation(df, datetime(1980, 1, 1), today))[0]} Pesos Ley para comprar lo mismo.

**Monto ajustado por inflación y cambios de moneda:**  
{adjusted_amount_display}  
_{amount_to_words(adjusted_amount, 'pesos')}_  
Este es el valor más realista: muestra cuántos pesos actuales necesitarías hoy para tener el mismo poder de compra que ese monto en la fecha elegida, considerando tanto la inflación como todos los cambios de moneda.  
Por ejemplo, si en 1980 tenías 100 Pesos Ley, hoy necesitarías {example_amount_display} Pesos actuales para comprar lo mismo.

**Período de inflación considerado:**  
{date.strftime('%d/%m/%Y')} a {today.strftime('%d/%m/%Y')}
""")
        else:
            currency = get_currency(date)
            inflation_factor = get_cumulative_inflation(df, date, today)
            amount_in_pesos = amount / inflation_factor
            amount_in_past = from_current_peso(amount_in_pesos, date)
            amount_in_past_no_redenom = amount_in_pesos

            # Format amounts
            amount_normal, amount_scientific = format_arg_amount(amount)
            amount_in_past_no_redenom_normal, amount_in_past_no_redenom_scientific = format_arg_amount(amount_in_past_no_redenom, 8)
            amount_in_past_normal, amount_in_past_scientific = format_arg_amount(amount_in_past)
            example_amount_1980_normal, example_amount_1980_scientific = format_arg_amount(
                10000 / get_cumulative_inflation(df, datetime(1980, 1, 1), today), 8
            )
            example_amount_1991_normal, example_amount_1991_scientific = format_arg_amount(
                from_current_peso(10000 / get_cumulative_inflation(df, datetime(1991, 1, 1), today), datetime(1991, 1, 1))
            )

            # Build output string
            amount_display = f"{amount_normal} (Peso)"
            if amount_scientific:
                amount_display += f"\n({amount_scientific})"
            amount_in_past_no_redenom_display = f"{amount_in_past_no_redenom_normal} (Peso)"
            if amount_in_past_no_redenom_scientific:
                amount_in_past_no_redenom_display += f"\n({amount_in_past_no_redenom_scientific})"
            amount_in_past_display = f"{amount_in_past_normal} ({currency})"
            if amount_in_past_scientific:
                amount_in_past_display += f"\n({amount_in_past_scientific})"
            example_amount_1980_display = f"{example_amount_1980_normal} (Peso)"
            if example_amount_1980_scientific:
                example_amount_1980_display += f"\n({example_amount_1980_scientific})"
            example_amount_1991_display = f"{example_amount_1991_normal} (Austral)"
            if example_amount_1991_scientific:
                example_amount_1991_display += f"\n({example_amount_1991_scientific})"

            st.markdown(f"""
**Monto actual:**  
{amount_display} al {today.strftime('%d/%m/%Y')}  
_{amount_to_words(amount, 'pesos')}_

**Equivalente deflactado a la fecha seleccionada (solo por inflación):**  
{amount_in_past_no_redenom_display} al {date.strftime('%d/%m/%Y')}  
_{amount_to_words(amount_in_past_no_redenom, 'pesos', 8)}_  
Este valor muestra cuántos pesos actuales equivaldrían, en poder de compra, a la fecha elegida, **sin** tener en cuenta los cambios de moneda.  
Por ejemplo, si hoy tenés 10.000 Pesos y querés saber cuánto valdrían en 1980, serían {example_amount_1980_display} Pesos actuales de ese año, solo ajustando por inflación.

**Equivalente en la moneda histórica (con cambios de moneda):**  
{amount_in_past_display} al {date.strftime('%d/%m/%Y')}  
_{amount_to_words(amount_in_past, currency)}_  
Este valor muestra cuántos billetes de la moneda antigua necesitarías en esa fecha para tener el mismo poder de compra que el monto actual, considerando tanto la inflación como todos los cambios de moneda y la quita de ceros.  
Por ejemplo, si hoy tenés 10.000 Pesos y querés saber cuántos Australes equivaldrían en 1991, serían {example_amount_1991_display} Australes.

**Período de inflación considerado:**  
{date.strftime('%d/%m/%Y')} a {today.strftime('%d/%m/%Y')}
""")

st.info("""
**¿Qué son los cambios de moneda?**  
A lo largo de la historia, la Argentina cambió varias veces de moneda y le quitó ceros para simplificar los billetes. Por ejemplo, $10.000.000 de Pesos Moneda Nacional (antes de 1970) equivalen a 1 Peso actual.

**Fuentes y referencias:**
- [inflacionverdadera.com/argentina](https://www.inflacionverdadera.com/argentina/)
- Para los meses en los que aún no se conoce el IPC oficial, se utilizan proyecciones del REM (Relevamiento de Expectativas de Mercado) publicado por el BCRA.

**Fuente de datos:** IPC mensual de Argentina (1943-2025).

---

_Creado por MTaurus (X: [@mtaurus_ok](https://x.com/mtaurus_ok))_
""")

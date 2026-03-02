import yfinance as yf
import pandas as pd
import os
import json
import requests
import traceback

# ==============================
# CONFIGURACIÓN
# ==============================

SYMBOL = "^GSPC"
LEVELS = [5, 10, 15, 20]  # niveles de alerta en %
STATE_FILE = "sp500_state.json"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# ==============================
# TELEGRAM
# ==============================

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram no configurado")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print("Error enviando mensaje Telegram:", e)


# ==============================
# DATA LOADER ROBUSTO
# ==============================

def get_data_yf(symbol, interval="1d", period="max"):
    try:
        df = yf.download(
            tickers=symbol,
            interval=interval,
            period=period,
            progress=False,
            auto_adjust=False
        )

        if df is None or df.empty:
            print(f"⚠️ yfinance: No hay datos para {symbol}")
            return None

        # 🔥 Aplanar MultiIndex si existe
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Normalizar nombres columnas
        df = df.rename(columns=str.title)

        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']

        # Intentar mapear columnas si faltan
        if not all(col in df.columns for col in required_cols):
            column_mapping = {}
            for col in required_cols:
                matching_cols = [c for c in df.columns if col.lower() in c.lower()]
                if matching_cols:
                    column_mapping[matching_cols[0]] = col

            if column_mapping:
                df = df.rename(columns=column_mapping)
                print(f"DEBUG: Columnas renombradas: {column_mapping}")

        available_cols = [col for col in required_cols if col in df.columns]
        df = df[available_cols]

        if 'Close' not in df.columns:
            print("❌ No existe columna Close")
            return None

        df = df.sort_index()

        # Manejo timezone
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")

        df.index = df.index.tz_convert("America/Santiago")

        df = df.dropna(subset=["Close"])

        return df

    except Exception as e:
        print(f"❌ Error yfinance ({symbol}): {e}")
        traceback.print_exc()
        return None


# ==============================
# ESTADO PERSISTENTE
# ==============================

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"triggered": []}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


# ==============================
# MAIN
# ==============================

def main():

    df = get_data_yf(SYMBOL, interval="1d", period="max")

    if df is None or len(df) < 300:
        print("Datos insuficientes")
        return

    historical_max = df["Close"].max()

    # Rolling máximo 12 meses (252 días bursátiles)
    rolling_max = df["Close"].rolling(window=252, min_periods=1).max()

    current_price = df["Close"].iloc[-2]  # vela cerrada
    current_max_12m = rolling_max.iloc[-2]

    drawdown = (current_max_12m - current_price) / current_max_12m * 100

    print("====================================")
    print(f"Precio actual: {current_price:.2f}")
    print(f"Máximo 12M: {current_max_12m:.2f}")
    print(f"Máximo histórico: {historical_max:.2f}")
    print(f"Drawdown 12M: {drawdown:.2f}%")
    print("====================================")

    # Mensaje informativo diario
    info_message = (
        f"📊 S&P 500\n"
        f"Precio: {current_price:.2f}\n"
        f"Máx 12M: {current_max_12m:.2f}\n"
        f"Máx histórico: {historical_max:.2f}\n"
        f"Drawdown: {drawdown:.2f}%"
    )

    send_telegram(info_message)

    # ==============================
    # ALERTAS ESCALONADAS
    # ==============================

    state = load_state()
    triggered = state["triggered"]

    alert_message = None

    for level in LEVELS:
        if drawdown >= level and level not in triggered:
            alert_message = (
                f"🚨 ALERTA S&P 500\n"
                f"Caída: {drawdown:.2f}%\n"
                f"Superó nivel −{level}%\n"
                f"Precio: {current_price:.2f}"
            )
            triggered.append(level)
            break

    # Reset si vuelve cerca de máximos
    if drawdown < 1:
        triggered = []

    save_state({"triggered": triggered})

    if alert_message:
        send_telegram(alert_message)
        print("✅ Alerta enviada")


# ==============================

if __name__ == "__main__":
    main()

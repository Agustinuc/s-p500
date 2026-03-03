import yfinance as yf
import pandas as pd
import os
import json
import requests
import traceback

# ==============================
# CONFIGURACIÓN
# ==============================

SYMBOLS = {
    "^GSPC": "S&P 500",
    "^IPSA": "IPSA Chile"
}

LEVELS = [5, 10, 15, 20]
STATE_FILE = "market_state.json"

TELEGRAM_BOT_TOKEN = "8756159949:AAE-Nd2pI0mASrFH-6kbOSW_kRVGPtW7sJU"
TELEGRAM_CHAT_ID = "-5178095003"


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
# DATA LOADER
# ==============================

def get_data_yf(symbol):
    try:
        df = yf.download(
            tickers=symbol,
            interval="1d",
            period="max",
            progress=False,
            auto_adjust=False
        )

        if df is None or df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.rename(columns=str.title)

        if 'Close' not in df.columns:
            return None

        df = df.sort_index()

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
# ESTADO
# ==============================

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


# ==============================
# MAIN
# ==============================

def main():

    state = load_state()

    for symbol, name in SYMBOLS.items():

        print(f"\n===== Analizando {name} =====")

        df = get_data_yf(symbol)

        if df is None or len(df) < 300:
            print("Datos insuficientes")
            continue

        rolling_max = df["Close"].rolling(window=252, min_periods=1).max()

        current_price = df["Close"].iloc[-2]
        current_max_12m = rolling_max.iloc[-2]

        drawdown = (current_max_12m - current_price) / current_max_12m * 100

        print(f"Precio actual: {current_price:.2f}")
        print(f"Drawdown 12M: {drawdown:.2f}%")

        # Estado por índice
        if symbol not in state:
            state[symbol] = {"triggered": []}

        triggered = state[symbol]["triggered"]
        alert_message = None

        for level in LEVELS:
            if drawdown >= level and level not in triggered:
                alert_message = (
                    f"🚨 CORRECCIÓN {name}\n"
                    f"Caída: {drawdown:.2f}%\n"
                    f"Superó nivel −{level}%\n"
                    f"Precio actual: {current_price:.2f}"
                )
                triggered.append(level)
                break

        # Reset si vuelve cerca de máximos
        if drawdown < 1:
            triggered = []

        state[symbol]["triggered"] = triggered

        if alert_message:
            send_telegram(alert_message)
            print("✅ Alerta enviada")
        else:
            print("Sin nuevas alertas.")

    save_state(state)


# ==============================

if __name__ == "__main__":
    main()

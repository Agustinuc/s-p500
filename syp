import yfinance as yf
import os
import json
import requests

# ==============================
# CONFIG
# ==============================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

STATE_FILE = "sp500_state.json"
LEVELS = [5, 10, 15, 20]


# ==============================
# TELEGRAM
# ==============================

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram no configurado")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    requests.post(url, json=payload)


# ==============================
# MAIN
# ==============================

def main():

    # Descargar 2 años de datos del S&P 500
    df = yf.download("^GSPC", period="2y", progress=False)

    if df is None or len(df) < 260:
        print("Datos insuficientes")
        return

    df = df.sort_index()

    # Máximo rolling 12 meses (252 días)
    rolling_max = df["Close"].rolling(window=252, min_periods=1).max()

    current_price = df["Close"].iloc[-2]
    current_max = rolling_max.iloc[-2]

    drawdown = (current_max - current_price) / current_max * 100

    print(f"Precio actual: {current_price:.2f}")
    print(f"Máximo 12M: {current_max:.2f}")
    print(f"Drawdown: {drawdown:.2f}%")

    # Cargar estado previo
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
    else:
        state = {"triggered": []}

    triggered = state["triggered"]
    message = None

    # Detectar nuevos niveles
    for level in LEVELS:
        if drawdown >= level and level not in triggered:
            message = (
                f"ALERTA S&P 500\n"
                f"Caída: {drawdown:.2f}%\n"
                f"Superó nivel −{level}%\n"
                f"Precio actual: {current_price:.2f}"
            )
            triggered.append(level)
            break

    # Reset si vuelve a nuevo máximo (menos de 1% de caída)
    if drawdown < 1:
        triggered = []

    # Guardar estado
    with open(STATE_FILE, "w") as f:
        json.dump({"triggered": triggered}, f)

    # Enviar alerta
    if message:
        send_telegram(message)
        print("Alerta enviada")


if __name__ == "__main__":
    main()

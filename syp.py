import yfinance as yf
import os
import json
import requests

# ==============================
# CONFIG (USA VARIABLES DE ENTORNO EN PRODUCCIÓN)
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

    df = yf.download("^GSPC", period="max", progress=False)

    if df is None or len(df) < 300:
        print("Datos insuficientes")
        return

    df = df.sort_index()

    # Máximo histórico absoluto
    historical_max = float(df["Close"].max())
    current_price = float(df["Close"].iloc[-2])
    current_max_12m = float(rolling_max.iloc[-2])

    # Máximo rolling 12 meses (252 días)
    rolling_max = df["Close"].rolling(window=252, min_periods=1).max()

    drawdown = (current_max_12m - current_price) / current_max_12m * 100

    print(f"Precio actual: {current_price:.2f}")
    print(f"Máximo 12M: {current_max_12m:.2f}")
    print(f"Máximo histórico: {historical_max:.2f}")
    print(f"Drawdown: {drawdown:.2f}%")

    # 🔎 MENSAJE INFORMATIVO SIEMPRE
    info_message = (
        f"📊 Estado S&P 500\n"
        f"Precio actual: {current_price:.2f}\n"
        f"Máximo 12M: {current_max_12m:.2f}\n"
        f"Máximo histórico: {historical_max:.2f}\n"
        f"Drawdown 12M: {drawdown:.2f}%"
    )

    send_telegram(info_message)

    # ==============================
    # ALERTAS POR NIVELES
    # ==============================

    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
    else:
        state = {"triggered": []}

    triggered = state["triggered"]
    alert_message = None

    for level in LEVELS:
        if drawdown >= level and level not in triggered:
            alert_message = (
                f"🚨 ALERTA S&P 500\n"
                f"Caída: {drawdown:.2f}%\n"
                f"Superó nivel −{level}%\n"
                f"Precio actual: {current_price:.2f}"
            )
            triggered.append(level)
            break

    # Reset si vuelve cerca del máximo
    if drawdown < 1:
        triggered = []

    with open(STATE_FILE, "w") as f:
        json.dump({"triggered": triggered}, f)

    if alert_message:
        send_telegram(alert_message)
        print("Alerta enviada")


if __name__ == "__main__":
    main()

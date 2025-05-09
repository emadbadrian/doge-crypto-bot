import ccxt
import pandas as pd
import ta
import time
import logging
from telegram import Bot

# ======================= تنظیمات =========================
TELEGRAM_BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
TELEGRAM_CHAT_ID = 'YOUR_TELEGRAM_CHAT_ID'
SYMBOL = 'DOGE/USDT'
TIMEFRAME = '5m'
CANDLE_LIMIT = 100
INTERVAL = 300  # هر 300 ثانیه = 5 دقیقه یکبار تحلیل انجام بشه

# ======================= ربات تلگرام ======================
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# ======================= Binance API =====================
exchange = ccxt.binance()

# ======================= تابع تحلیل ======================
def analyze():
    try:
        ohlcv = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=CANDLE_LIMIT)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # محاسبه اندیکاتورها با ta
        df['RSI'] = ta.momentum.RSIIndicator(df['close']).rsi()
        macd = ta.trend.MACD(df['close'])
        df['MACD'] = macd.macd()
        df['MACD_signal'] = macd.macd_signal()
        df['MA20'] = df['close'].rolling(window=20).mean()
        df['MA50'] = df['close'].rolling(window=50).mean()

        latest = df.iloc[-1]

        signal = "📈 تحلیل دوج کوین (DOGE/USDT):\n"
        signal += f"قیمت فعلی: {latest['close']:.4f} دلار\n"
        signal += f"RSI: {latest['RSI']:.2f} => {'خرید' if latest['RSI'] < 30 else 'فروش' if latest['RSI'] > 70 else 'نرمال'}\n"
        signal += f"MACD: {latest['MACD']:.4f}, سیگنال: {latest['MACD_signal']:.4f} => {'صعودی' if latest['MACD'] > latest['MACD_signal'] else 'نزولی'}\n"
        signal += f"MA20: {latest['MA20']:.4f}, MA50: {latest['MA50']:.4f} => {'روند صعودی' if latest['MA20'] > latest['MA50'] else 'روند نزولی'}"

        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=signal)
        logging.info("✅ پیام ارسال شد")

    except Exception as e:
        logging.error(f"❌ خطا در تحلیل: {e}")

# ======================= اجرای مداوم =====================
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    while True:
        analyze()
        time.sleep(INTERVAL)


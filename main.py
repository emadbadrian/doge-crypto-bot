import requests
import pandas as pd
import asyncio
import logging
from telegram import Bot
from telegram.constants import ParseMode
import time

# ======================= تنظیمات =========================
TELEGRAM_BOT_TOKEN = '7795930019:AAF7HXcw1iPyYc175yvNz4csvQjZz8tt9jI'
TELEGRAM_CHAT_ID = 34776308
SYMBOL = 'dogecoin'
CURRENCY = 'usd'
INTERVAL = 240  # هر 4 دقیقه یک‌بار تحلیل انجام بشه

bot = Bot(token=TELEGRAM_BOT_TOKEN)

# ======================= تابع دریافت داده (Binance) ======================
def fetch_doge_data():
    url = 'https://api.binance.com/api/v3/klines'
    params = {
        'symbol': 'DOGEUSDT',
        'interval': '1m',
        'limit': 180
    }

    for _ in range(3):  # تا ۳ بار تلاش کنه
        try:
            response = requests.get(url, params=params)
            data = response.json()
            if isinstance(data, list) and len(data) >= 50:
                prices = [[int(item[0]), float(item[4])] for item in data]
                df = pd.DataFrame(prices, columns=['timestamp', 'price'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                return df
            else:
                raise ValueError("داده کافی برای تحلیل دریافت نشد.")
        except Exception as e:
            logging.warning(f"⏳ تلاش مجدد برای دریافت داده از Binance... {e}")
            time.sleep(10)

    raise ValueError("قیمت‌ها در پاسخ Binance پیدا نشد!")

# ======================= تابع تحلیل و ارسال پیام ======================
async def analyze_and_send():
    try:
        df = fetch_doge_data()
        df['MA5'] = df['price'].rolling(window=5).mean()
        df['MA10'] = df['price'].rolling(window=10).mean()
        df['EMA20'] = df['price'].ewm(span=20, adjust=False).mean()
        df['EMA50'] = df['price'].ewm(span=50, adjust=False).mean()

        df['change'] = df['price'].pct_change()
        df['RSI'] = 100 - (100 / (1 + df['change'].rolling(14).apply(lambda x: (x[x>0].sum() / abs(x[x<0].sum())) if abs(x[x<0].sum()) > 0 else 0)))

        df['MACD'] = df['price'].ewm(span=12, adjust=False).mean() - df['price'].ewm(span=26, adjust=False).mean()
        df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

        df['upper_band'] = df['price'].rolling(window=20).mean() + 2 * df['price'].rolling(window=20).std()
        df['lower_band'] = df['price'].rolling(window=20).mean() - 2 * df['price'].rolling(window=20).std()

        latest = df.iloc[-1]

        rsi_signal = 'خرید' if latest['RSI'] < 35 else 'فروش' if latest['RSI'] > 65 else 'نرمال'
        trend_signal = 'صعودی' if latest['MA5'] > latest['MA10'] else 'نزولی'
        macd_signal = 'خرید' if latest['MACD'] > latest['MACD_signal'] else 'فروش'
        bb_signal = 'خرید' if latest['price'] < latest['lower_band'] else 'فروش' if latest['price'] > latest['upper_band'] else 'نرمال'

        # تصمیم نهایی
        if rsi_signal == 'خرید' and trend_signal == 'صعودی' and macd_signal == 'خرید' and bb_signal == 'خرید':
            final_decision = '\n✅ <b>سیگنال خرید قوی</b>'
        elif rsi_signal == 'فروش' and trend_signal == 'نزولی' and macd_signal == 'فروش' and bb_signal == 'فروش':
            final_decision = '\n⚠️ <b>سیگنال فروش قوی</b>'
        else:
            final_decision = '\nℹ️ <b>وضعیت خنثی</b>'

        signal = "📈 <b>تحلیل دوج کوین (Binance)</b>\n"
        signal += f"قیمت فعلی: <b>{latest['price']:.4f}</b> دلار\n"
        signal += f"RSI: <b>{latest['RSI']:.2f}</b> => {rsi_signal}\n"
        signal += f"MA5: {latest['MA5']:.4f}, MA10: {latest['MA10']:.4f} => روند {trend_signal}\n"
        signal += f"MACD: {latest['MACD']:.4f}, Signal: {latest['MACD_signal']:.4f} => {macd_signal}\n"
        signal += f"Bollinger: محدوده [{latest['lower_band']:.4f} - {latest['upper_band']:.4f}] => {bb_signal}"
        signal += final_decision

        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=signal, parse_mode=ParseMode.HTML)
        logging.info("✅ پیام ارسال شد")

    except Exception as e:
        logging.error(f"❌ خطا در تحلیل: {e}")

# ======================= اجرای مداوم ======================
async def main_loop():
    while True:
        await analyze_and_send()
        await asyncio.sleep(INTERVAL)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main_loop())


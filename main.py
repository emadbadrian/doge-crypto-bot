import requests
import pandas as pd
import asyncio
import logging
from telegram import Bot
from telegram.constants import ParseMode

# ======================= تنظیمات =========================
TELEGRAM_BOT_TOKEN = '7795930019:AAF7HXcw1iPyYc175yvNz4csvQjZz8tt9jI'
TELEGRAM_CHAT_ID = '34776308'
SYMBOL = 'dogecoin'
CURRENCY = 'usd'
INTERVAL = 300  # هر 300 ثانیه = 5 دقیقه یکبار تحلیل انجام بشه

bot = Bot(token=TELEGRAM_BOT_TOKEN)

# ======================= تابع دریافت داده ======================
def fetch_doge_data():
    url = f'https://api.coingecko.com/api/v3/coins/{SYMBOL}/market_chart?vs_currency={CURRENCY}&days=1&interval=daily'
    response = requests.get(url)
    data = response.json()

    if 'prices' not in data:
        raise ValueError("قیمت‌ها در پاسخ API پیدا نشد!")

    prices = data['prices'][-100:]  # آخرین 100 کندل
    df = pd.DataFrame(prices, columns=['timestamp', 'price'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# ======================= تابع تحلیل و ارسال پیام ======================
async def analyze_and_send():
    try:
        df = fetch_doge_data()
        df['MA20'] = df['price'].rolling(window=20).mean()
        df['MA50'] = df['price'].rolling(window=50).mean()
        df['change'] = df['price'].pct_change()
        df['RSI'] = 100 - (100 / (1 + df['change'].rolling(14).apply(lambda x: (x[x>0].sum() / abs(x[x<0].sum())) if abs(x[x<0].sum()) > 0 else 0)))

        latest = df.iloc[-1]

        signal = "📈 <b>تحلیل دوج کوین (CoinGecko)</b>\n"
        signal += f"قیمت فعلی: <b>{latest['price']:.4f}</b> دلار\n"
        signal += f"RSI: <b>{latest['RSI']:.2f}</b> => {'خرید' if latest['RSI'] < 30 else 'فروش' if latest['RSI'] > 70 else 'نرمال'}\n"
        signal += f"MA20: {latest['MA20']:.4f}, MA50: {latest['MA50']:.4f} => {'روند صعودی' if latest['MA20'] > latest['MA50'] else 'روند نزولی'}"

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

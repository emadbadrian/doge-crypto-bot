import requests
import pandas as pd
import asyncio
import logging
from telegram import Bot
from telegram.constants import ParseMode

# ======================= تنظیمات =========================
TELEGRAM_BOT_TOKEN = '7795930019:AAF7HXcw1iPyYc175yvNz4csvQjZz8tt9jI'
TELEGRAM_CHAT_ID = 34776308
SYMBOL = 'dogecoin'
CURRENCY = 'usd'
INTERVAL = 300  # هر 300 ثانیه = 5 دقیقه یکبار تحلیل انجام بشه

bot = Bot(token=TELEGRAM_BOT_TOKEN)

# ======================= تابع دریافت داده ======================
def fetch_doge_data():
    url = f'https://api.coingecko.com/api/v3/coins/{SYMBOL}/market_chart?vs_currency={CURRENCY}&days=1&interval=minutely'
    response = requests.get(url)

    try:
        data = response.json()
    except Exception as e:
        logging.error(f"❌ خطا در خواندن JSON: {e}")
        raise

    logging.info(f"📦 پاسخ API: {data}")

    if 'prices' not in data or not data['prices']:
        raise ValueError("قیمت‌ها در پاسخ API پیدا نشد!")

    prices = data['prices'][-100:]  # آخرین 100 کندل
    df = pd.DataFrame(prices, columns=['timestamp', 'price'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# ======================= تابع تحلیل و ارسال پیام ======================
async def analyze_and_send():
    try:
        df = fetch_doge_data()
        df['MA5'] = df['price'].rolling(window=5).mean()
        df['MA10'] = df['price'].rolling(window=10).mean()
        df['change'] = df['price'].pct_change()
        df['RSI'] = 100 - (100 / (1 + df['change'].rolling(14).apply(lambda x: (x[x>0].sum() / abs(x[x<0].sum())) if abs(x[x<0].sum()) > 0 else 0)))

        latest = df.iloc[-1]

        rsi_signal = 'خرید' if latest['RSI'] < 30 else 'فروش' if latest['RSI'] > 70 else 'نرمال'
        trend_signal = 'روند صعودی' if latest['MA5'] > latest['MA10'] else 'روند نزولی'
        final_decision = ''

        if rsi_signal == 'خرید' and trend_signal == 'روند صعودی':
            final_decision = '\n✅ <b>سیگنال خرید قوی!</b>'
        elif rsi_signal == 'فروش' and trend_signal == 'روند نزولی':
            final_decision = '\n⚠️ <b>احتمال ریزش، سیگنال فروش</b>'
        else:
            final_decision = '\nℹ️ <b>وضعیت خنثی، بهتر است صبر کنید</b>'

        signal = "📈 <b>تحلیل سریع دوج کوین (CoinGecko)</b>\n"
        signal += f"قیمت فعلی: <b>{latest['price']:.4f}</b> دلار\n"
        signal += f"RSI: <b>{latest['RSI']:.2f}</b> => {rsi_signal}\n"
        signal += f"MA5: {latest['MA5']:.4f}, MA10: {latest['MA10']:.4f} => {trend_signal}"
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

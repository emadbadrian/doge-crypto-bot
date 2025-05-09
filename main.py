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

# ======================= تابع دریافت داده از CoinMarketCap ======================
def fetch_doge_data():
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/historical'
    headers = {
        'X-CMC_PRO_API_KEY': '7fa3b3bb-7d34-49e6-9c95-be070c350e35'
    }
    params = {
        'symbol': 'DOGE',
        'convert': 'USD',
        'interval': '1m',
        'count': 180
    }

    for _ in range(3):
        try:
            response = requests.get(url, headers=headers, params=params)
            data = response.json()
            quotes = data.get('data', {}).get('quotes', [])
            if isinstance(quotes, list) and len(quotes) >= 100:
                prices = [[int(pd.to_datetime(q['timestamp']).timestamp() * 1000), float(q['quote']['USD']['price'])] for q in quotes]
                df = pd.DataFrame(prices, columns=['timestamp', 'price'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                return df
            else:
                raise ValueError("داده کافی برای تحلیل دریافت نشد.")
        except Exception as e:
            logging.warning(f"⏳ تلاش مجدد برای دریافت داده از CoinMarketCap... {e}")
            time.sleep(10)

    raise ValueError("قیمت‌ها در پاسخ CoinMarketCap پیدا نشد!")

# ======================= تابع تحلیل و ارسال پیام ======================
async def analyze_and_send():
    try:
        df = fetch_doge_data()
        df['MA5'] = df['price'].rolling(window=5).mean()
        df['MA10'] = df['price'].rolling(window=10).mean()
        df['EMA20'] = df['price'].ewm(span=20, adjust=False).mean()
        df['EMA50'] = df['price'].ewm(span=50, adjust=False).mean()
        df['EMA100'] = df['price'].ewm(span=100, adjust=False).mean()
        df['EMA200'] = df['price'].ewm(span=200, adjust=False).mean()

        df['change'] = df['price'].pct_change()
        df['RSI'] = 100 - (100 / (1 + df['change'].rolling(14).apply(lambda x: (x[x>0].sum() / abs(x[x<0].sum())) if abs(x[x<0].sum()) > 0 else 0)))

        df['MACD'] = df['price'].ewm(span=12, adjust=False).mean() - df['price'].ewm(span=26, adjust=False).mean()
        df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

        df['upper_band'] = df['price'].rolling(window=20).mean() + 2 * df['price'].rolling(window=20).std()
        df['lower_band'] = df['price'].rolling(window=20).mean() - 2 * df['price'].rolling(window=20).std()

        df['ATR'] = df['price'].rolling(window=14).std() * 2
        df['ADX'] = df['change'].abs().rolling(window=14).mean() * 100

        latest = df.iloc[-1]

        rsi_signal = 'خرید' if latest['RSI'] < 35 else 'فروش' if latest['RSI'] > 65 else 'نرمال'
        trend_signal = 'صعودی' if latest['MA5'] > latest['MA10'] else 'نزولی'
        macd_signal = 'خرید' if latest['MACD'] > latest['MACD_signal'] else 'فروش'
        bb_signal = 'خرید' if latest['price'] < latest['lower_band'] else 'فروش' if latest['price'] > latest['upper_band'] else 'نرمال'
        atr_signal = 'نوسان بالا' if latest['ATR'] > df['ATR'].mean() else 'نوسان کم'
        adx_signal = 'قدرت بالا' if latest['ADX'] > 25 else 'ضعیف'

        long_trend_signal = 'صعودی' if latest['EMA50'] > latest['EMA100'] and latest['EMA100'] > latest['EMA200'] else 'نزولی'

        signal = ""
        total_signals = 0
        chart_link = f"https://www.tradingview.com/symbols/DOGEUSD/"

        if rsi_signal == 'خرید': total_signals += 1
        if trend_signal == 'صعودی': total_signals += 1
        if macd_signal == 'خرید': total_signals += 1
        if bb_signal == 'خرید': total_signals += 1
        if latest['ADX'] > 25: total_signals += 1

        # سیگنال کوتاه‌مدت
        if total_signals >= 4:
            signal += f"✅ <b>سیگنال خرید قوی - کوتاه‌مدت</b>\n"
            signal += f"🎯 پتانسیل سود ۱–۳٪ در ۵ تا ۳۰ دقیقه\n"
            signal += f"📊 اندیکاتورهای موافق: {total_signals} / 5\n"
            signal += f"📉 سطح اطمینان: {'بالا' if total_signals == 5 else 'متوسط'}\n"
            signal += f"🔗 <a href='{chart_link}'>نمایش نمودار لحظه‌ای</a>"
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=signal, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            logging.info("✅ پیام کوتاه‌مدت ارسال شد")

        # سیگنال بلندمدت
        total_long_signals = 0
        if rsi_signal == 'خرید': total_long_signals += 1
        if macd_signal == 'خرید': total_long_signals += 1
        if long_trend_signal == 'صعودی': total_long_signals += 1

        if total_long_signals >= 2:
            signal = f"✅ <b>سیگنال خرید احتمالی - بلندمدت</b>\n"
            signal += f"🎯 پتانسیل سود ۳–۱۰٪ طی ۳ تا ۲۴ ساعت\n"
            signal += f"📊 اندیکاتورهای موافق: {total_long_signals} / 3\n"
            signal += f"📉 سطح اطمینان: {'بالا' if total_long_signals == 3 else 'متوسط'}\n"
            signal += f"🔗 <a href='{chart_link}'>نمایش نمودار لحظه‌ای</a>"
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=signal, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            logging.info("✅ پیام بلندمدت ارسال شد")

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

import logging
import requests
import pandas as pd
import time
from ta import add_all_ta_features
from ta.utils import dropna
from telegram import Bot

# ---------- تنظیمات ----------
TOKEN = '7795930019:AAF7HXcw1iPyYc175yvNz4csvQjZz8tt9jI'
CHAT_ID = '34776308'
CMC_API_KEY = '7fa3b3bb-7d34-49e6-9c95-be070c350e35'
SYMBOL = 'DOGE'
INTERVAL = '5m'
LIMIT = 100
SLEEP_INTERVAL = 300  # هر ۵ دقیقه چک کن

# ---------- لاگ ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- گرفتن داده ----------
def fetch_data():
    url = f'https://pro-api.coinmarketcap.com/v1/cryptocurrency/ohlcv/historical'
    params = {
        'symbol': SYMBOL,
        'interval': INTERVAL,
        'count': LIMIT
    }
    headers = {'X-CMC_PRO_API_KEY': CMC_API_KEY}
    response = requests.get(url, params=params, headers=headers)
    data = response.json()

    try:
        quotes = data['data']['quotes']
        df = pd.DataFrame([{
            'time': q['timestamp'],
            'open': float(q['quote']['USD']['open']),
            'high': float(q['quote']['USD']['high']),
            'low': float(q['quote']['USD']['low']),
            'close': float(q['quote']['USD']['close']),
            'volume': float(q['quote']['USD']['volume'])
        } for q in quotes])
        return df
    except Exception as e:
        logger.error(f'❌ خطا در تحلیل: {e}')
        return None

# ---------- تحلیل ----------
def analyze(df):
    df = dropna(df)
    df = add_all_ta_features(df, open="open", high="high", low="low", close="close", volume="volume")

    latest = df.iloc[-1]
    signals = []

    if latest['trend_macd'] > 0 and latest['momentum_rsi'] < 30:
        signals.append('🟢 سیگنال کوتاه‌مدت: مناسب برای سود سریع (۳٪ تا ۳۰ دقیقه)')

    if latest['trend_macd_diff'] > 0 and latest['trend_adx'] > 25 and latest['trend_ema_fast'] > latest['trend_ema_slow']:
        signals.append('🔵 سیگنال بلندمدت: مناسب برای سود بیشتر (۳٪ تا ۶ ساعت)')

    return signals

# ---------- ارسال پیام ----------
def send_message(text):
    try:
        Bot(token=TOKEN).send_message(chat_id=CHAT_ID, text=text)
    except Exception as e:
        logger.error(f'❌ خطا در ارسال پیام: {e}')

# ---------- اجرای ربات ----------
if __name__ == '__main__':
    while True:
        logger.info("📊 در حال تحلیل...")
        df = fetch_data()
        if df is not None:
            signals = analyze(df)
            if signals:
                for s in signals:
                    send_message(s)
            else:
                logger.info("🚫 سیگنالی یافت نشد.")
        time.sleep(SLEEP_INTERVAL)

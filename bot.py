import warnings
import os
import logging
import pandas as pd
import numpy as np
import ccxt
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Игнорируем предупреждения
warnings.filterwarnings("ignore")

# Токен берем из переменных окружения (на Render мы его добавим позже)
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Инициализация Gate.io
exchange = ccxt.gateio({
    'enableRateLimit': True,
    'headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    },
})

def fetch_data(symbol, timeframe, limit=50):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        return pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    except Exception:
        return pd.DataFrame()

def calculate_indicators(df):
    try:
        close = df['close']
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        atr = (df['high'] - df['low']).rolling(window=14).mean()
        return rsi.iloc[-1], atr.iloc[-1]
    except:
        return 50.0, 0.0

def generate_report():
    df_sol = fetch_data('SOL/USDT', '1h')
    df_btc = fetch_data('BTC/USDT', '1h')
    
    if df_sol.empty: 
        return "⚠️ Ошибка: Сервер не дает данные."

    price = float(df_sol['close'].iloc[-1])
    rsi, atr = calculate_indicators(df_sol)
    btc_price = float(df_btc['close'].iloc[-1]) if not df_btc.empty else 0.0
    
    report = f"🤖 Советник 'Ловец Теней' (v3.3 PRO-LITE)\n\n"
    report += f"📊 Текущий маркет (Gate.io):\n• Рыночная цена SOL: ${price:.2f}\n"
    report += f"• Спот BTC: ${btc_price:.1f}\n\n"
    report += "⚡ ВАРИАНТ А: ТАКТИКА «СКАЛЬПИНГ»\n"
    report += f"• 🔵 Тейк-Профит: ${price * 1.02:.2f}\n• 🔴 Стоп-Лосс: ${price * 0.992:.2f}\n\n"
    report += "🎯 ВАРИАНТ Б: ТАКТИКА «СНАЙПЕР»\n"
    report += f"• 🟢 Вход: ${price * 0.98:.2f}\n• 🔵 Тейк: ${price * 1.03:.2f}\n\n"
    report += f"🔍 Срез Smart-метрик:\n• Индекс RSI: {rsi:.1f}\n• ATR: {atr:.2f}"
    return report

async def start(update, context):
    kb = [['📊 Найти Сигнал SOL']]
    await update.message.reply_text("Бот 'Ловец Теней' активен!", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def handle_message(update, context):
    if update.message.text == '📊 Найти Сигнал SOL':
        await update.message.reply_text(generate_report())

def main():
    if not TOKEN: 
        print("Ошибка: TOKEN не найден!")
        return
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.run_polling()

if __name__ == '__main__':
    main()

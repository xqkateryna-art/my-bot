import os
import ccxt
import pandas as pd
import numpy as np
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters

TOKEN = os.getenv("TELEGRAM_TOKEN")
exchange = ccxt.gateio({'enableRateLimit': True})

def get_indicators(symbol):
    ohlcv = exchange.fetch_ohlcv(symbol, '1h', limit=50)
    df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'close', 'v'])
    
    # Фильтр шума (EMA 9)
    df['ema'] = df['close'].ewm(span=9).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # ATR (Волатильность)
    high_low = df['h'] - df['l']
    atr = high_low.rolling(window=14).mean()
    
    # Уровни (Поддержка/Сопротивление)
    support = df['l'].rolling(window=20).min().iloc[-1]
    resistance = df['h'].rolling(window=20).max().iloc[-1]
    
    return df['close'].iloc[-1], rsi.iloc[-1], atr.iloc[-1], support, resistance, df['ema'].iloc[-1]

def generate_report():
    sol_price, rsi, atr, sup, res, ema = get_indicators('SOL/USDT')
    btc_price, _, _, _, _, _ = get_indicators('BTC/USDT')
    
    # Корреляция простая (направление)
    corr_status = "Высокая" if rsi > 50 else "Нейтральная"
    
    report = f"🤖 Ловец Теней v3.3 PRO\n\n"
    report += f"📊 Маркет:\n• SOL: ${sol_price:.2f} (EMA: {ema:.2f})\n• BTC: ${btc_price:.1f}\n"
    report += f"• Поддержка: ${sup:.2f} | Сопр: ${res:.2f}\n\n"
    
    # Фильтр шума/логика
    scalp_entry = sol_price * 0.99 if sol_price > ema else sol_price * 0.98
    
    report += "⚡ ТАКТИКА «СКАЛЬПИНГ»\n"
    report += f"• Вход: ${scalp_entry:.2f}\n• Тейк: ${sol_price*1.02:.2f}\n• Стоп: ${sol_price*0.99:.2f}\n\n"
    
    report += "🎯 ТАКТИКА «СНАЙПЕР»\n"
    report += f"• Вход: ${sup * 1.005:.2f}\n• Тейк: ${res * 0.99:.2f}\n• Стоп: ${sup * 0.98:.2f}\n\n"
    
    report += f"🔍 Метрики:\n• RSI: {rsi:.1f}\n• ATR: {atr:.2f}\n• Статус корреляции: {corr_status}"
    return report

async def start(update, context):
    kb = [['📊 Получить полный отчет']]
    await update.message.reply_text("Бот готов к анализу!", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def handle_message(update, context):
    if update.message.text == '📊 Получить полный отчет':
        await update.message.reply_text(generate_report())

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle_message))
app.run_polling()

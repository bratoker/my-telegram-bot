import logging
import random
import requests
import datetime
import json
import os
from deep_translator import GoogleTranslator
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, ConversationHandler, PreCheckoutQueryHandler
)

# ===================== НАСТРОЙКИ =====================
BOT_TOKEN    = "8792525541:AAF9ZRfZDZdC5nnini_S0SHxUfVTesYKBp4"
GROQ_API_KEY = "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"
OWNER_ID     = 5911024601  # Только владелец может добавлять ключи

# ===================== ХРАНИЛИЩЕ КЛЮЧЕЙ =====================
KEYS_FILE = "keys.json"

def load_keys():
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, "r") as f:
            return json.load(f)
    return {"keys": [], "users": {}}

def save_keys(data):
    with open(KEYS_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ===================== СОСТОЯНИЯ =====================
WAITING_KOSTI_GUESS    = 1
WAITING_SUYEFA_CHOICE  = 2
WAITING_CALC_EXPR      = 3
WAITING_TRANSLATE_TEXT = 4
WAITING_MINES_COUNT    = 5
WAITING_AI_CHAT        = 6
WAITING_SLOTS_BET      = 7

# ===================== ДАННЫЕ =====================
FACTS = [
    "Мозг человека потребляет около 20% всей энергии тела.",
    "Осьминоги имеют три сердца и голубую кровь.",
    "На Земле больше деревьев, чем звёзд в Млечном Пути.",
    "Молния нагревается до 30 000 Кельвин — в 5 раз горячее поверхности Солнца.",
    "Пчёлы могут узнавать человеческие лица.",
    "Акулы старше деревьев — появились около 450 млн лет назад.",
    "Мёд никогда не портится — в гробницах находили 3000-летний мёд.",
    "Слоны — единственные животные, которые не могут прыгать.",
    "ДНК человека на 98.7% совпадает с ДНК шимпанзе.",
    "95% океанов до сих пор не исследованы.",
    "Бабочки пробуют еду ногами — там вкусовые рецепторы.",
    "Свет от Солнца достигает Земли за 8 минут 20 секунд.",
    "Дельфины спят с одним открытым глазом.",
    "Бананы слабо радиоактивны из-за калия-40.",
    "Горячая вода замерзает быстрее холодной — эффект Мпембы.",
    "Муравьи никогда не спят и не имеют лёгких.",
    "На Луне следы астронавтов сохранятся миллионы лет.",
    "У акул нет костей — скелет полностью хрящевой.",
    "Лягушки пьют воду через кожу, а не через рот.",
    "Золото никогда не ржавеет.",
    "В теле человека бактерий больше, чем клеток самого тела.",
    "Гавайи удаляются от Японии на 10 см каждый год.",
    "Улитки могут спать до 3 лет подряд.",
    "Вороны помнят лица обидчиков годами.",
    "Цветок Раффлезия достигает 1 метра в диаметре.",
    "Рыбы-клоун все рождаются самцами.",
    "Две одинаковые снежинки найти практически невозможно.",
    "Пицца изобретена в Неаполе в конце 18 века.",
    "Лев слышит добычу на расстоянии до 9 км.",
    "Нейтронная звезда: чайная ложка вещества весит миллиарды тонн.",
]
FACT_EMOJIS = ["🧠","🐙","🌍","⚡","🐝","🦈","🍯","🐘","🧬","🌊","🦋","🔭","🐬","🍌","🧊","🐜","🌙","🦴","🐸","🧪","🦠","🌋","🎭","🦜","🌺","🐠","❄️","🍕","🦁","🧲"]

RU_HOLIDAYS = {
    (1,1):"🎉 Новый год",
    (1,7):"🎄 Рождество (православное)",
    (2,23):"🎖️ День защитника Отечества",
    (3,8):"💐 Международный женский день",
    (5,1):"🌸 Праздник Весны и Труда",
    (5,9):"🎗️ День Победы",
    (6,12):"🇷🇺 День России",
    (11,4):"🤝 День народного единства",
    (12,31):"🥂 Канун Нового года",
}
BY_HOLIDAYS = {
    (1,1):"🎉 Новы год",
    (1,7):"🎄 Каляды (Рождество)",
    (3,8):"💐 Міжнародны жаночы дзень",
    (3,15):"🇧🇾 Дзень Канстытуцыі",
    (5,1):"🌸 Свята Працы",
    (5,9):"🎗️ Дзень Перамогі",
    (7,3):"🇧🇾 Дзень Незалежнасці",
    (11,7):"🏴 Дзень Кастрычніцкай рэвалюцыі",
    (12,25):"🎄 Каляды (каталіцкія)",
}
BOT_MOODS = [
    "😊 Я сегодня в отличном настроении! Готов помочь тебе!",
    "🌟 Чувствую себя потрясающе! Заряжен энергией и позитивом!",
    "🎉 Настроение — супер! Радуюсь каждому сообщению!",
    "☀️ Всё замечательно! Солнце светит в моей цифровой душе!",
    "🚀 Энтузиазм зашкаливает! Готов горы свернуть вместе с тобой!",
    "🦋 Лёгкость и радость переполняют меня сегодня!",
    "💪 Полон сил и оптимизма! Нет задачи, с которой не справимся!",
]

# ===================== СЛОТ-МАШИНА =====================
SLOT_SYMBOLS = ["🍒","🍋","🍊","🍇","💎","7️⃣","🔔","⭐"]
SLOT_PAYOUTS = {
    "💎": 50,
    "7️⃣": 20,
    "🔔": 15,
    "⭐": 10,
    "🍇": 8,
    "🍊": 6,
    "🍋": 4,
    "🍒": 3,
}

def spin_slots():
    return [random.choice(SLOT_SYMBOLS) for _ in range(3)]

def calc_payout(reels, bet):
    s1, s2, s3 = reels
    if s1 == s2 == s3:
        mult = SLOT_PAYOUTS.get(s1, 3)
        return bet * mult, f"🎰 ДЖЕКПОТ! Все три совпали! x{mult}"
    elif s1 == s2 or s2 == s3 or s1 == s3:
        return bet * 2, "✨ Два совпали! x2"
    else:
        return 0, "😔 Не повезло..."

async def slots_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "slots_coins" not in context.user_data:
        context.user_data["slots_coins"] = 100
    coins = context.user_data["slots_coins"]
    kb = [["10 монет", "25 монет"], ["50 монет", "Всё ва-банк!"]]
    await update.message.reply_text(
        f"🎰 *Слот-машина!*\n\n"
        f"💰 Твой баланс: *{coins} монет*\n\n"
        f"*Выигрыши (все три одинаковых):*\n"
        f"💎 — x50 | 7️⃣ — x20 | 🔔 — x15\n"
        f"⭐ — x10 | 🍇 — x8 | 🍊 — x6\n"
        f"🍋 — x4 | 🍒 — x3\n"
        f"Два одинаковых — x2\n\n"
        f"Выбери ставку или /stop для выхода:",
        reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True),
        parse_mode="Markdown"
    )
    return WAITING_SLOTS_BET

async def slots_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    coins = context.user_data.get("slots_coins", 100)
    mapping = {"10 монет": 10, "25 монет": 25, "50 монет": 50, "Всё ва-банк!": coins}
    bet = mapping.get(text)
    if bet is None:
        try:
            bet = int(text)
        except ValueError:
            await update.message.reply_text("⚠️ Выбери ставку из меню или /stop для выхода!")
            return WAITING_SLOTS_BET

    if bet <= 0 or bet > coins:
        await update.message.reply_text(
            f"⚠️ Недостаточно монет! У тебя *{coins}* монет.",
            parse_mode="Markdown"
        )
        return WAITING_SLOTS_BET

    reels = spin_slots()
    payout, msg = calc_payout(reels, bet)
    context.user_data["slots_coins"] = coins - bet + payout
    new_balance = context.user_data["slots_coins"]
    result_line = " | ".join(reels)

    extra = ""
    if new_balance <= 0:
        context.user_data["slots_coins"] = 100
        new_balance = 100
        extra = "\n\n💸 *Монеты закончились!* Даю 100 новых монет 🎁"

    kb = [["10 монет", "25 монет"], ["50 монет", "Всё ва-банк!"]]
    await update.message.reply_text(
        f"🎰 *[ {result_line} ]*\n\n"
        f"{msg}\n"
        f"Ставка: *{bet}* монет | {'Выигрыш' if payout > 0 else 'Потеря'}: *{payout if payout > 0 else bet}* монет\n\n"
        f"💰 Баланс: *{new_balance} монет*{extra}\n\n"
        f"Крути снова или /stop для выхода:",
        reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True),
        parse_mode="Markdown"
    )
    return WAITING_SLOTS_BET

# ===================== КЛЮЧИ HAPP =====================
async def addkey_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ У тебя нет прав для этой команды!")
        return

    if not context.args:
        await update.message.reply_text(
            "📝 *Использование:*\n`/addkey ВАШ_КЛЮЧ`\n\nПример:\n`/addkey vless://abc123...`",
            parse_mode="Markdown"
        )
        return

    key = " ".join(context.args)
    data = load_keys()
    data["keys"].append(key)
    save_keys(data)
    await update.message.reply_text(
        f"✅ *Ключ успешно добавлен!*\n\n"
        f"🔑 Ключ: `{key[:50]}...`\n"
        f"📦 Всего ключей в базе: *{len(data['keys'])}*",
        parse_mode="Markdown"
    )

async def listkeys_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ У тебя нет прав!")
        return

    data = load_keys()
    keys = data.get("keys", [])

    if not keys:
        await update.message.reply_text("📦 Ключей пока нет.\nДобавь через /addkey")
        return

    text = f"📦 *Ключей в базе: {len(keys)}*\n\n"
    for i, k in enumerate(keys, 1):
        short = k[:50] + "..." if len(k) > 50 else k
        text += f"{i}. `{short}`\n"

    await update.message.reply_text(text, parse_mode="Markdown")

async def clearkeys_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ У тебя нет прав!")
        return

    data = load_keys()
    count = len(data.get("keys", []))
    data["keys"] = []
    save_keys(data)
    await update.message.reply_text(f"🗑️ Удалено *{count}* ключей!", parse_mode="Markdown")

async def happ_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = load_keys()
    users = data.get("users", {})
    user_info = users.get(str(user_id), {})
    expires = user_info.get("expires")

    # Проверяем есть ли активный ключ
    if expires:
        exp_date = datetime.datetime.fromisoformat(expires)
        if exp_date > datetime.datetime.now():
            hours_left = int((exp_date - datetime.datetime.now()).total_seconds() / 3600)
            days_left = hours_left // 24
            key = user_info.get("key", "ключ не найден")
            await update.message.reply_text(
                f"🔑 *Твой активный ключ Happ:*\n\n"
                f"`{key}`\n\n"
                f"⏳ Действует ещё: *{hours_left} ч.* ({days_left} дн.)\n"
                f"📅 До: {exp_date.strftime('%d.%m.%Y %H:%M')}\n\n"
                f"Чтобы продлить доступ — купи снова после истечения срока!",
                parse_mode="Markdown"
            )
            return

    # Проверяем наличие ключей в базе
    keys = data.get("keys", [])
    if not keys:
        await update.message.reply_text(
            "😔 К сожалению, ключей сейчас нет.\n\n"
            "Ключи обновляются каждый день — заходи позже! 🔄"
        )
        return

    # Показываем кнопку покупки
    kb = [[InlineKeyboardButton("⭐ Купить доступ — 10 звёзд (2 дня)", callback_data="buy_happ")]]
    await update.message.reply_text(
        "🔑 *Ключи Happ (VPN)*\n\n"
        f"📦 Доступно ключей: *{len(keys)}*\n\n"
        "💫 *Цена: 10 звёзд = 2 дня доступа*\n\n"
        "После оплаты ты получишь рабочий ключ для приложения *Happ*.\n"
        "Вставь ключ в приложение и пользуйся VPN!\n\n"
        "Нажми кнопку ниже чтобы купить:",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

async def buy_happ_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_keys()
    if not data.get("keys"):
        await query.edit_message_text("😔 Ключей нет. Зайди позже!")
        return

    await context.bot.send_invoice(
        chat_id=query.from_user.id,
        title="🔑 Ключ Happ на 2 дня",
        description="VPN ключ для приложения Happ. Доступ на 2 дня после оплаты.",
        payload="happ_key_2days",
        currency="XTR",
        prices=[LabeledPrice("Ключ Happ (2 дня)", 10)],
    )

async def precheckout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    if query.invoice_payload == "happ_key_2days":
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="Ошибка оплаты. Попробуй снова!")

async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    payment = update.message.successful_payment

    if payment.invoice_payload == "happ_key_2days":
        data = load_keys()
        keys = data.get("keys", [])

        if not keys:
            await update.message.reply_text(
                "😔 Ключи закончились! Обратись к администратору — деньги будут возвращены."
            )
            return

        # Выдаём случайный ключ
        key = random.choice(keys)
        expires = (datetime.datetime.now() + datetime.timedelta(days=2)).isoformat()

        if "users" not in data:
            data["users"] = {}

        data["users"][str(user_id)] = {
            "key": key,
            "expires": expires,
            "purchased_at": datetime.datetime.now().isoformat()
        }
        save_keys(data)

        expire_date = datetime.datetime.now() + datetime.timedelta(days=2)

        await update.message.reply_text(
            f"✅ *Оплата прошла успешно!*\n\n"
            f"🔑 *Твой ключ Happ:*\n`{key}`\n\n"
            f"⏳ Действует *2 дня*\n"
            f"📅 До: {expire_date.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"📱 *Как использовать:*\n"
            f"1. Открой приложение *Happ*\n"
            f"2. Вставь ключ\n"
            f"3. Подключайся!\n\n"
            f"Посмотреть ключ снова: /happ",
            parse_mode="Markdown"
        )

        # Уведомление владельцу о покупке
        try:
            await context.bot.send_message(
                OWNER_ID,
                f"💰 *Новая оплата!*\n\n"
                f"👤 Пользователь: {update.effective_user.full_name}\n"
                f"🆔 ID: `{user_id}`\n"
                f"⭐ Звёзд: {payment.total_amount}\n"
                f"🔑 Ключ: `{key[:60]}...`\n"
                f"📅 До: {expire_date.strftime('%d.%m.%Y %H:%M')}",
                parse_mode="Markdown"
            )
        except Exception:
            pass

# ===================== УНИВЕРСАЛЬНАЯ ОТМЕНА =====================
async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⛔ *Остановлено!*\n\n/start — главное меню",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⛔ *Остановлено!*\n\n/start — главное меню",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# ===================== /start =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    name = update.effective_user.first_name or "Друг"
    text = (
        f"👋 Привет, *{name}*! Я твой многофункциональный бот!\n\n"
        "📚 *Информация:*\n"
        "  /fact — интересный факт\n"
        "  /currency — курс валют (USD, EUR, BYN)\n"
        "  /crypto — 📈 Курс крипты (BTC, ETH, TON)\n"
        "  /time — дата и точное время\n"
        "  /mood — настроение бота\n"
        "  /holidays — праздники сегодня\n\n"
        "🎮 *Игры:*\n"
        "  /kosti — 🎲 Угадай число\n"
        "  /Cyefa — ✂️ Камень, ножницы, бумага\n"
        "  /mines — 💣 Сапёр (18 ячеек)\n"
        "  /slots — 🎰 Слот-машина\n\n"
        "🛠️ *Инструменты:*\n"
        "  /kalck — 🧮 Калькулятор\n"
        "  /launge — 🌍 Переводчик RU ↔ EN\n\n"
        "🔑 *VPN:*\n"
        "  /happ — Ключи Happ (10 ⭐ = 2 дня)\n\n"
        "🤖 *ИИ-ассистент:*\n"
        "  /ai — Поговори со мной как с другом!\n\n"
        "❗ */stop — остановить любую команду*\n\n"
        "Выбери команду и поехали! 🚀"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())

# ===================== ИНФОРМАЦИЯ =====================
async def fact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = random.randint(0, len(FACTS)-1)
    await update.message.reply_text(
        f"💡 *Интересный факт:*\n\n{FACT_EMOJIS[idx]} {FACTS[idx]}",
        parse_mode="Markdown"
    )

async def currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Получаю актуальный курс валют...")
    try:
        data = requests.get("https://api.exchangerate-api.com/v4/latest/RUB", timeout=10).json()
        r = data.get("rates", {})
        text = (
            "💱 *Курс валют к рублю (RUB):*\n\n"
            f"🇺🇸 1 USD = `{1/r['USD']:.2f}` ₽\n"
            f"🇪🇺 1 EUR = `{1/r['EUR']:.2f}` ₽\n"
            f"🇧🇾 1 BYN = `{1/r['BYN']:.2f}` ₽\n\n"
            f"🕐 Обновлено: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
    except Exception:
        text = "❌ Не удалось получить курс валют. Попробуй позже."
    await update.message.reply_text(text, parse_mode="Markdown")

async def crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Получаю курс криптовалют...")
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": "bitcoin,ethereum,the-open-network", "vs_currencies": "usd,rub"}
        data = requests.get(url, params=params, timeout=10).json()
        btc = data["bitcoin"]
        eth = data["ethereum"]
        ton = data["the-open-network"]
        text = (
            "📈 *Курс криптовалют:*\n\n"
            f"₿ *Bitcoin (BTC)*\n"
            f"  💵 `${btc['usd']:,.0f}` | 💰 `{btc['rub']:,.0f} ₽`\n\n"
            f"Ξ *Ethereum (ETH)*\n"
            f"  💵 `${eth['usd']:,.0f}` | 💰 `{eth['rub']:,.0f} ₽`\n\n"
            f"💎 *Toncoin (TON)*\n"
            f"  💵 `${ton['usd']:,.2f}` | 💰 `{ton['rub']:,.2f} ₽`\n\n"
            f"🕐 Обновлено: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
    except Exception:
        text = "❌ Не удалось получить курс крипты. Попробуй позже."
    await update.message.reply_text(text, parse_mode="Markdown")

async def time_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now()
    days = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]
    months = ["января","февраля","марта","апреля","мая","июня","июля","августа","сентября","октября","ноября","декабря"]
    await update.message.reply_text(
        f"🕐 *Текущее время и дата:*\n\n"
        f"📅 {days[now.weekday()]}, {now.day} {months[now.month-1]} {now.year} г.\n"
        f"⏰ {now.strftime('%H:%M:%S')}\n"
        f"📆 Неделя №{now.isocalendar()[1]} в году",
        parse_mode="Markdown"
    )

async def mood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🤖 *Настроение бота:*\n\n{random.choice(BOT_MOODS)}",
        parse_mode="Markdown"
    )

async def holidays(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now()
    key = (now.month, now.day)
    await update.message.reply_text(
        f"🗓️ *Праздники сегодня* ({now.strftime('%d.%m.%Y')}):\n\n"
        f"🇷🇺 *Россия:* {RU_HOLIDAYS.get(key, 'праздников нет')}\n"
        f"🇧🇾 *Беларусь:* {BY_HOLIDAYS.get(key, 'праздников нет')}",
        parse_mode="Markdown"
    )

# ===================== КОСТИ =====================
async def kosti_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["kosti_number"] = random.randint(1, 10)
    context.user_data["kosti_attempts"] = 0
    await update.message.reply_text(
        "🎲 *Игра: Угадай число!*\n\n"
        "Я загадал число от *1 до 10*.\n"
        "Напиши своё число! 🤔\n\n"
        "/stop — выйти из игры",
        parse_mode="Markdown"
    )
    return WAITING_KOSTI_GUESS

async def kosti_guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        guess = int(update.message.text.strip())
        if not 1 <= guess <= 10:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ Введи целое число от 1 до 10!")
        return WAITING_KOSTI_GUESS

    context.user_data["kosti_attempts"] += 1
    a = context.user_data["kosti_attempts"]
    secret = context.user_data["kosti_number"]

    if guess == secret:
        word = "попытку" if a == 1 else ("попытки" if a < 5 else "попыток")
        await update.message.reply_text(
            f"🎉 *Верно! Ты угадал за {a} {word}!*\n"
            f"Я загадал *{secret}*. Молодец! 🏆\n\n"
            f"Сыграть ещё? /kosti",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    hint = "больше" if secret > guess else "меньше"
    await update.message.reply_text(
        f"❌ Неверно! Моё число *{hint}*, чем {guess}.\n"
        f"Попробуй ещё или /stop для выхода:",
        parse_mode="Markdown"
    )
    return WAITING_KOSTI_GUESS

# ===================== КНБ =====================
async def suyefa_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [["🪨 Камень", "✂️ Ножницы", "📄 Бумага"]]
    await update.message.reply_text(
        "✂️ *Камень, Ножницы, Бумага!*\n\n"
        "🪨 Камень бьёт Ножницы\n"
        "✂️ Ножницы бьют Бумагу\n"
        "📄 Бумага бьёт Камень\n\n"
        "Выбери или /stop для выхода:",
        reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True),
        parse_mode="Markdown"
    )
    return WAITING_SUYEFA_CHOICE

async def suyefa_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mapping = {
        "🪨 камень": "камень", "камень": "камень",
        "✂️ ножницы": "ножницы", "ножницы": "ножницы",
        "📄 бумага": "бумага", "бумага": "бумага"
    }
    user_choice = mapping.get(update.message.text.strip().lower())
    if not user_choice:
        await update.message.reply_text("⚠️ Выбери: Камень, Ножницы или Бумага!")
        return WAITING_SUYEFA_CHOICE

    bot_choice = random.choice(["камень", "ножницы", "бумага"])
    emojis = {"камень": "🪨", "ножницы": "✂️", "бумага": "📄"}
    wins = {"камень": "ножницы", "ножницы": "бумага", "бумага": "камень"}

    if user_choice == bot_choice:
        result = "🤝 *Ничья!*"
    elif wins[user_choice] == bot_choice:
        result = "🎉 *Ты победил!*"
    else:
        result = "😈 *Бот победил!*"

    await update.message.reply_text(
        f"Ты: {emojis[user_choice]} *{user_choice.capitalize()}*\n"
        f"Бот: {emojis[bot_choice]} *{bot_choice.capitalize()}*\n\n"
        f"{result}\n\n"
        f"Сыграть ещё? /Cyefa | Выход: /stop",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# ===================== САПЁР =====================
def build_mines_keyboard(board, revealed, game_over=False):
    keyboard = []
    for row in range(6):
        kb_row = []
        for col in range(3):
            idx = row * 3 + col
            if revealed[idx]:
                label = "💣" if board[idx] == "MINE" else "✅"
            elif game_over and board[idx] == "MINE":
                label = "💣"
            else:
                label = "⬜"
            kb_row.append(InlineKeyboardButton(label, callback_data=f"mines_{idx}"))
        keyboard.append(kb_row)
    return InlineKeyboardMarkup(keyboard)

async def mines_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [["3 мины 😊", "5 мин 😐"], ["7 мин 😰", "10 мин 💀"]]
    await update.message.reply_text(
        "💣 *Игра: Сапёр!*\n\n"
        "Поле *18 ячеек*. Под некоторыми спрятаны мины 💣\n\n"
        "  ✅ — безопасно, продолжаешь\n"
        "  💣 — мина, игра окончена!\n\n"
        "Открой все безопасные ячейки — *победа!* 🏆\n\n"
        "Выбери сложность или /stop для выхода:",
        reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True),
        parse_mode="Markdown"
    )
    return WAITING_MINES_COUNT

async def mines_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mapping = {"3 мины 😊": 3, "5 мин 😐": 5, "7 мин 😰": 7, "10 мин 💀": 10}
    count = mapping.get(update.message.text.strip())
    if count is None:
        await update.message.reply_text(
            "⚠️ Выбери сложность из меню или /stop для выхода!",
            reply_markup=ReplyKeyboardRemove()
        )
        return WAITING_MINES_COUNT

    board = ["SAFE"] * 18
    for pos in random.sample(range(18), count):
        board[pos] = "MINE"

    context.user_data["mines_board"]     = board
    context.user_data["mines_revealed"]  = [False] * 18
    context.user_data["mines_count"]     = count
    context.user_data["mines_safe_left"] = 18 - count

    markup = build_mines_keyboard(board, [False] * 18)
    await update.message.reply_text(
        f"💣 *Сапёр* | Мин: {count} | Безопасных: {18 - count}\n\n"
        f"Нажимай на ячейки — удачи! 🍀\n"
        f"/stop — выйти из игры",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def mines_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not query.data.startswith("mines_"):
        return

    idx      = int(query.data.split("_")[1])
    board    = context.user_data.get("mines_board")
    revealed = context.user_data.get("mines_revealed")

    if not board or not revealed:
        await query.edit_message_text("⚠️ Игра не найдена. Начни новую: /mines")
        return

    if revealed[idx]:
        await query.answer("Ячейка уже открыта!", show_alert=False)
        return

    revealed[idx] = True
    context.user_data["mines_revealed"] = revealed

    if board[idx] == "MINE":
        markup = build_mines_keyboard(board, revealed, game_over=True)
        await query.edit_message_text(
            "💥 *БУМ! Ты наступил на мину!*\n\n"
            "Игра окончена 😢\n"
            "Начать снова: /mines",
            reply_markup=markup,
            parse_mode="Markdown"
        )
    else:
        context.user_data["mines_safe_left"] -= 1
        safe_left  = context.user_data["mines_safe_left"]
        mine_count = context.user_data["mines_count"]
        markup = build_mines_keyboard(board, revealed)

        if safe_left == 0:
            await query.edit_message_text(
                "🏆 *ПОБЕДА! Все безопасные ячейки открыты!*\n\n"
                "Молодец, сапёр! 💪\n"
                "Ещё раз: /mines",
                reply_markup=markup,
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                f"💣 *Сапёр* | Мин: {mine_count} | Осталось открыть: {safe_left}\n\n"
                f"✅ Безопасно! Продолжай!\n"
                f"/stop — выйти",
                reply_markup=markup,
                parse_mode="Markdown"
            )

# ===================== ПЕРЕВОДЧИК =====================
async def launge_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌍 *Переводчик RU ↔ EN*\n\n"
        "Отправь слово или предложение — переведу автоматически!\n"
        "Кириллица → Английский\n"
        "Латиница → Русский\n\n"
        "/stop — остановить переводчик",
        parse_mode="Markdown"
    )
    return WAITING_TRANSLATE_TEXT

async def launge_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        ru_chars = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
        if ru_chars > 0:
            translated = GoogleTranslator(source='ru', target='en').translate(text)
            direction = "🇷🇺 → 🇬🇧"
        else:
            translated = GoogleTranslator(source='en', target='ru').translate(text)
            direction = "🇬🇧 → 🇷🇺"
        await update.message.reply_text(
            f"🌍 *Перевод {direction}:*\n\n"
            f"📝 Оригинал: `{text}`\n"
            f"✅ Перевод: *{translated}*\n\n"
            "Отправь ещё или /stop для остановки.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Ошибка перевода. Попробуй снова.\n`{e}`",
            parse_mode="Markdown"
        )
    return WAITING_TRANSLATE_TEXT

# ===================== КАЛЬКУЛЯТОР =====================
async def kalck_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧮 *Калькулятор*\n\n"
        "Отправь пример: `12 + 34`, `100 * 5 - 3`, `256 % 7`\n\n"
        "/stop — выйти",
        parse_mode="Markdown"
    )
    return WAITING_CALC_EXPR

async def kalck_compute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    expr = update.message.text.strip()

    if not any(c.isdigit() for c in expr):
        await update.message.reply_text(
            "⚠️ Введи математический пример, например: `12 + 34`",
            parse_mode="Markdown"
        )
        return WAITING_CALC_EXPR

    if not all(c in "0123456789+-*/%., ()" for c in expr):
        await update.message.reply_text(
            "⚠️ Недопустимые символы! Используй только цифры и `+ - * / %`",
            parse_mode="Markdown"
        )
        return WAITING_CALC_EXPR

    try:
        result = eval(expr, {"__builtins__": {}}, {})
        if isinstance(result, float):
            result = round(result, 10)
        await update.message.reply_text(
            f"🧮 `{expr}` = *{result}*\n\nВведи ещё или /stop",
            parse_mode="Markdown"
        )
    except ZeroDivisionError:
        await update.message.reply_text("❌ Деление на ноль!")
    except Exception:
        await update.message.reply_text("❌ Не могу вычислить. Проверь пример.")
    return WAITING_CALC_EXPR

# ===================== ИИ АССИСТЕНТ =====================
AI_SYSTEM = """Ты дружелюбный русскоязычный бот-собеседник по имени Дружок. Общаешься как близкий друг — тепло, с юмором, живо.

Правила:
- Всегда отвечай на русском языке
- Будь живым и искренним, иногда шути, используй разговорный стиль
- ОБЯЗАТЕЛЬНО помни весь диалог и ссылайся на сказанное ранее
- Проявляй реальный интерес к собеседнику, задавай вопросы в тему
- Не говори как робот — говори как человек
- Если спрашивают кто ты — скажи что ты ИИ-друг по имени Дружок, но с характером
- Хорошо разбираешься в: играх, кино, музыке, спорте, технологиях, жизни
- Умеешь поддержать, пошутить, поспорить, дать совет
- Эмодзи используй умеренно — только по делу
- Отвечай кратко как в живом чате, но содержательно"""

async def ai_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ai_history"] = []
    name = update.effective_user.first_name or "друг"
    await update.message.reply_text(
        f"🤖 Привет, {name}! Я Дружок — твой ИИ-собеседник.\n\n"
        "Можем говорить о чём угодно: жизнь, игры, кино, советы 😄\n\n"
        "Пиши что хочешь! /stop — выйти"
    )
    return WAITING_AI_CHAT

async def ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    history = context.user_data.get("ai_history", [])
    history.append({"role": "user", "content": user_text})
    if len(history) > 30:
        history = history[-30:]

    await update.message.chat.send_action("typing")

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "system", "content": AI_SYSTEM}] + history,
                "max_tokens": 800,
            },
            timeout=30,
        )
        data = resp.json()
        if "choices" in data:
            ai_reply = data["choices"][0]["message"]["content"]
        else:
            ai_reply = "❌ Ошибка: " + data.get("error", {}).get("message", "Неизвестная ошибка")
    except requests.exceptions.Timeout:
        ai_reply = "⏳ Долго думаю... Попробуй ещё раз!"
    except Exception as e:
        ai_reply = f"❌ Ошибка: {str(e)}"

    history.append({"role": "assistant", "content": ai_reply})
    context.user_data["ai_history"] = history
    await update.message.reply_text(ai_reply)
    return WAITING_AI_CHAT

# ===================== ЗАПУСК =====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Простые команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("fact", fact))
    app.add_handler(CommandHandler("currency", currency))
    app.add_handler(CommandHandler("crypto", crypto))
    app.add_handler(CommandHandler("time", time_cmd))
    app.add_handler(CommandHandler("mood", mood))
    app.add_handler(CommandHandler("holidays", holidays))

    # Ключи Happ
    app.add_handler(CommandHandler("happ", happ_cmd))
    app.add_handler(CommandHandler("addkey", addkey_cmd))
    app.add_handler(CommandHandler("listkeys", listkeys_cmd))
    app.add_handler(CommandHandler("clearkeys", clearkeys_cmd))
    app.add_handler(CallbackQueryHandler(buy_happ_callback, pattern="^buy_happ$"))
    app.add_handler(PreCheckoutQueryHandler(precheckout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))

    FALLBACKS = [
        CommandHandler("stop", stop_cmd),
        CommandHandler("start", cancel),
    ]

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("kosti", kosti_start)],
        states={WAITING_KOSTI_GUESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, kosti_guess)]},
        fallbacks=FALLBACKS,
    ))
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("Cyefa", suyefa_start)],
        states={WAITING_SUYEFA_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, suyefa_choice)]},
        fallbacks=FALLBACKS,
    ))
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("mines", mines_start)],
        states={WAITING_MINES_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, mines_count)]},
        fallbacks=FALLBACKS,
    ))
    app.add_handler(CallbackQueryHandler(mines_callback, pattern=r"^mines_\d+$"))
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("slots", slots_start)],
        states={WAITING_SLOTS_BET: [MessageHandler(filters.TEXT & ~filters.COMMAND, slots_bet)]},
        fallbacks=FALLBACKS,
    ))
    # ПЕРЕВОДЧИК — обязательно выше калькулятора!
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("launge", launge_start)],
        states={WAITING_TRANSLATE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, launge_translate)]},
        fallbacks=FALLBACKS,
    ))
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("kalck", kalck_start)],
        states={WAITING_CALC_EXPR: [MessageHandler(filters.TEXT & ~filters.COMMAND, kalck_compute)]},
        fallbacks=FALLBACKS,
    ))
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("ai", ai_start)],
        states={WAITING_AI_CHAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ai_chat)]},
        fallbacks=FALLBACKS,
    ))

    print("✅ Бот запущен! Нажми Ctrl+C для остановки.")
    app.run_polling()

if __name__ == "__main__":
    main()

# bot.py
import telebot
import mysql.connector
from datetime import datetime
import config 

# Инициализация бота
bot = telebot.TeleBot(config.BOT_TOKEN)

# Подключение к базе данных
def get_db_connection():
    return mysql.connector.connect(
        host=config.DB_HOST,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME
    )

# Команда /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = telebot.types.KeyboardButton("🔐 Мой статус")
    #btn2 = telebot.types.KeyboardButton("📅 Сколько осталось")
    btn3 = telebot.types.KeyboardButton("❓ Помощь")
    keyboard.add(btn1)
    keyboard.add(btn3)

    bot.reply_to(
        message,
        f"👋 Привет, {message.from_user.first_name}!\n"
        "Я — бот для управления электронной подписью.\n"
        "Выбери действие в меню.",
        reply_markup=keyboard
    )

# Команда /help
@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = (
        "📌 <b>Справка по боту</b>\n\n"
        "Доступные команды:\n"
        "🔸 /start — главное меню\n"
        "🔸 /status — статус вашего сертификата\n"
        "🔸 /upcoming — сколько дней осталось\n"
        "🔸 /help — это сообщение\n\n"
        "📬 <b> Тех. поддержка</b>\n"
        "📱 Телефон: <code>+7 (495) 123-45-67</code>\n"
        "📧 Email: <code>ep-support@company.local</code>\n"
        "👤 Telegram: <a href='https://t.me/@deeanahhh'>@deeanahhh</a>"
    )
    bot.send_message(message.chat.id, help_text, parse_mode='HTML')

# Команда /status
@bot.message_handler(commands=['status'])
def send_status(message):
    user_id = str(message.from_user.id)
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT e.full_name, e.position, c.serial_number, c.valid_to, c.status, c.certificate_type
            FROM certificates c
            JOIN employees e ON c.employee_id = e.id
            WHERE e.telegram_id = %s
            ORDER BY c.valid_to DESC
        """, (user_id,))
        results = cursor.fetchall()
        conn.close()

        if results:
            response = "🔐 <b>Статус электронных подписей</b>\n\n"
            for idx, result in enumerate(results, start=1):
                days_left = (result['valid_to'].date() - datetime.now().date()).days
                status_text = "🟢 Активен" if days_left > 0 else "🔴 Просрочен"
                expiring = " ⚠️ Срок истекает!" if 0 < days_left <= 7 else ""

                response += (
                    f"<u>Сертификат {idx}</u>\n"
                    f"👤 <b>ФИО:</b> {result['full_name']}\n"
                    f"💼 <b>Должность:</b> {result['position']}\n"
                    f"🔢 <b>Серийный номер:</b> <code>{result['serial_number']}</code>\n"
                    f"📆 <b>Действует до:</b> {result['valid_to'].strftime('%d.%m.%Y')}\n"
                    f"⏳ <b>Осталось дней:</b> {days_left}\n"
                    f"🔖 <b>Тип:</b> {result['certificate_type']}\n"
                    f"✅ <b>Статус:</b> {status_text}{expiring}\n\n"
                )

            bot.send_message(message.chat.id, response, parse_mode='HTML', disable_web_page_preview=True)
        else:
            bot.send_message(
                message.chat.id,
                "❌ Ваши сертификаты не найдены в системе.\n"
                "Возможно, ваш Telegram ID не привязан к учётной записи.\n"
                "Обратитесь к администратору."
            )
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка базы данных: {str(e)}")


# Обработка кнопок
@bot.message_handler(func=lambda message: message.text == "🔐 Мой статус")
def button_status(message):
    send_status(message)

# @bot.message_handler(func=lambda message: message.text == "📅 Сколько осталось")
# def button_upcoming(message):
#     send_upcoming(message)

@bot.message_handler(func=lambda message: message.text == "❓ Помощь")
def button_help(message):
    send_help(message)

# Обработка неизвестных сообщений
@bot.message_handler(func=lambda message: True)
def echo_message(message):
    bot.send_message(
        message.chat.id,
        "Я не понял команду. Используйте меню или введите /help."
    )

# Запуск бота
if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()
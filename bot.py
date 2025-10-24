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


# Команда /start — главная проверка и вход
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Проверяем, есть ли пользователь в таблице employees по telegram_id
        cursor.execute("""
            SELECT e.full_name 
            FROM employees e 
            WHERE e.telegram_id = %s 
        """, (user_id,))
        employee = cursor.fetchone()

        if not employee:
            # Пользователь не найден
            conn.close()
            bot.reply_to(
                message,
                f"👋 Здравствуйте, {message.from_user.first_name}!\n\n"
                "Ваш Telegram-аккаунт <b>не привязан</b> к нашей базе данных.\n\n"
                "Чтобы получить доступ:\n"
                "Обратитесь к администратору\n"
                "📬 <b>Контакты:</b>\n"
                "📞 <code>+7 (495) 123-45-67</code>\n"
                "📧 <code>ep-support@company.local</code>",
                parse_mode='HTML'
            )
            return

        full_name = employee[0]
        conn.close()

        # Пользователь найден — строим меню
        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn_status = telebot.types.KeyboardButton("🔐 Мой статус")
        btn_help = telebot.types.KeyboardButton("❓ Помощь")
        keyboard.add(btn_status, btn_help)

        # Отправляем приветствие с меню
        bot.reply_to(
            message,
            f"👋 Привет, <b>{message.from_user.first_name}</b>!\n"
            f"Вы вошли как <b>{full_name}</b>.\n"
            "Выберите действие в меню ниже.",
            reply_markup=keyboard,
            parse_mode='HTML'
        )

    except Exception as e:
        bot.reply_to(
            message,
            "⚠️ Произошла ошибка при подключении к системе.\n"
            "Попробуйте позже или обратитесь к администратору."
        )
        print(f"[ERROR] Ошибка в /start: {e}")


# Команда /help
@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = (
        "📌 <b>Справка по боту</b>\n\n"
        "Доступные команды:\n"
        "🔸 /start — главное меню\n"
        "🔸 /status — статус вашего сертификата\n"
        "🔸 /help — это сообщение\n\n"
        "📬 <b>Контакты:</b>\n"
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
                "Возможно, ваш аккаунт не имеет привязанных сертификатов.\n"
                "Обратитесь к администратору."
            )
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка базы данных: {str(e)}")


# Команда /admin_panel (и кнопка)
@bot.message_handler(commands=['admin_panel'])
def admin_panel_command(message):
    show_admin_panel(message)

@bot.message_handler(func=lambda message: message.text == "⚙️ Админ-панель")
def admin_panel_button(message):
    show_admin_panel(message)

def show_admin_panel(message):
    user_id = str(message.from_user.id)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM users WHERE telegram_id = %s", (user_id,))
        result = cursor.fetchone()
        conn.close()

        if result and result[0] == 'admin':
            web_panel_url = "http://127.0.0.1:5000"
            login = config.PANEL_LOGIN  
            password = config.PANEL_PASSWORD

            admin_message = (
                "🛡️ <b>Доступ к админ-панели</b>\n\n"
                f"🌐 <b>Ссылка:</b> <a href='{web_panel_url}'>Перейти к панели управления</a>\n"
                f"🔑 <b>Логин:</b> <tg-spoiler>{login}</tg-spoiler>\n"
                f"🔒 <b>Пароль:</b> <tg-spoiler>{password}</tg-spoiler>\n\n"
                "⚠️ Не передавайте эти данные третьим лицам!"
            )
            bot.send_message(message.chat.id, admin_message, parse_mode='HTML')
        else:
            bot.send_message(
                message.chat.id,
                "🚫 У вас нет прав доступа к админ-панели.\n"
                "Эта функция доступна только администраторам."
            )
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка при проверке доступа: {str(e)}")


# Обработка кнопок
@bot.message_handler(func=lambda message: message.text == "🔐 Мой статус")
def button_status(message):
    send_status(message)

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
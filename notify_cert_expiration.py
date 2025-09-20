# notify_cert_expiration.py
import mysql.connector
import requests
from datetime import datetime

# --- Настройки ---
TOKEN = "8430513965:AAFdKtwhFztn1UC2zUbhF4G3mMQMRyT1CIo"  
CHANNEL_ID = "-1002749201183"  

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '29242233',
    'database': 'digital_signatures'
}

# --- Функция с логированием времени ---
def log_info(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")



def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        'chat_id': CHANNEL_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            log_info("Сообщение отправлено в Telegram")
        else:
            log_info(f"Ошибка отправки: {response.text}")
    except Exception as e:
        log_info(f"Ошибка при отправке сообщения: {e}")

def check_expiring_certs():
# --- SQL-запрос: сертификаты, заканчивающиеся через 7 дней ---
    QUERY = """
    SELECT 
        e.full_name,
        e.email,
        c.serial_number,
        c.valid_to,
        c.thumbprint_sha256
    FROM certificates c
    JOIN employees e ON c.employee_id = e.id
    WHERE c.status = 'active'
    AND c.valid_to BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 7 DAY);
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(QUERY)
        results = cursor.fetchall()

        if results:
            message = "🔔 <b>Уведомление об истечении срока ЭП</b>\n"
            message += "Сертификаты, заканчивающиеся через 7 дней:\n\n"
            for row in results:
                full_name, email, serial, valid_to, thumbprint = row
                message += f"👤 <b>{full_name}</b>\n"
                message += f"📧 {email}\n"
                message += f"🔢 Серийный: <code>{serial}</code>\n"
                message += f"📅 Окончание: {valid_to}\n"
                message += f"🔍 SHA-256: <code>{thumbprint}</code>\n"
                message += "────────────────────\n"
            send_telegram_message(message)
        else:
            log_info("Нет сертификатов, заканчивающихся через 7 дней.")

        cursor.close()
        conn.close()

    except Exception as e:
        error_msg = f"Ошибка проверки базы: {str(e)}"
        log_info(error_msg)
        send_telegram_message(error_msg)

if __name__ == "__main__":
    check_expiring_certs()
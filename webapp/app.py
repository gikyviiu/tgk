# app.py
from flask import Flask, render_template, request, redirect, session, url_for, flash # type: ignore
import mysql.connector
from config import Config
from datetime import datetime, date
import requests
import hashlib

app = Flask(__name__)
app.secret_key = 'ybw45qb'  
app.config.from_object(Config)

def get_db_connection():
    return mysql.connector.connect(
        host=app.config['DB_HOST'],
        user=app.config['DB_USER'],
        password=app.config['DB_PASSWORD'],
        database=app.config['DB_NAME']
    )







@app.before_request
def require_login():
    allowed_routes = ['login']
    if 'username' not in session and request.endpoint not in allowed_routes:
        return redirect(url_for('login'))
    



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        conn.close()

        if user:
            # Проверяем хэш SHA256
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            if password_hash == user['password_hash']:
                session['username'] = user['username']
                session['role'] = user['role']
                session['full_name'] = user['full_name']
                flash("Вы вошли в систему", "success")
                return redirect(url_for('index'))
        
        flash("Неверный логин или пароль", "danger")

    return render_template('login.html')



@app.route('/logout')
def logout():
    session.clear()
    flash("👋 Вы вышли из системы", "info")
    return redirect(url_for('login'))







# Главная страница — список сертификатов

@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Получаем параметры фильтрации
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '')  # active, expired, warning
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    # Базовый SQL-запрос
    query = """
        SELECT c.*, e.full_name, e.position, e.department, e.email
        FROM certificates c
        JOIN employees e ON c.employee_id = e.id
        WHERE 1=1
    """
    params = []

    # Поиск по ФИО
    if search:
        query += " AND (e.full_name LIKE %s OR e.email LIKE %s)"
        params.extend([f'%{search}%', f'%{search}%'])

    # Фильтрация по дате
    if date_from:
        query += " AND c.valid_to >= %s"
        params.append(date_from + " 00:00:00")
    if date_to:
        query += " AND c.valid_to <= %s"
        params.append(date_to + " 23:59:59")

    # Выполняем запрос
    cursor.execute(query, params)
    certs = cursor.fetchall()
    conn.close()

    # Добавляем статус для отображения
    today = date.today()
    filtered_certs = []
    for cert in certs:
        days_left = (cert['valid_to'].date() - today).days
        cert['days_left'] = days_left
        if days_left < 0:
            cert['status_class'] = 'expired'
            cert['status_label'] = 'Просрочен'
        elif days_left <= 7:
            cert['status_class'] = 'warning'
            cert['status_label'] = 'Скоро истекает'
        else:
            cert['status_class'] = 'active'
            cert['status_label'] = 'Активен'

        # Фильтрация по статусу
        if status_filter == 'active' and cert['status_class'] != 'active':
            continue
        if status_filter == 'expired' and cert['status_class'] != 'expired':
            continue
        if status_filter == 'warning' and cert['status_class'] != 'warning':
            continue

        filtered_certs.append(cert)

    return render_template('index.html', certificates=filtered_certs, 
                          search=search, status_filter=status_filter,
                          date_from=date_from, date_to=date_to)


# Просмотр деталей
@app.route('/view/<int:cert_id>')
def view(cert_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT c.*, e.full_name, e.position, e.department, e.email
        FROM certificates c
        JOIN employees e ON c.employee_id = e.id
        WHERE c.id = %s
    """, (cert_id,))
    cert = cursor.fetchone()
    conn.close()

    if not cert:
        flash("Сертификат не найден", "danger")
        return redirect(url_for('index'))

    # Вычисляем разницу в днях в Python
    current_time = datetime.now()
    if cert['valid_to']:
        days_left = (cert['valid_to'] - current_time).days
    else:
        days_left = None

    return render_template('view.html', cert=cert, current_time=current_time, days_left=days_left)

# Добавить сертификат
@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        data = request.form
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO certificates (
                    employee_id, serial_number, issuer, subject, valid_from, valid_to,
                    thumbprint_sha1, thumbprint_sha256, public_key, key_usage,
                    certificate_type, storage_location, pin_code_hint, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data['employee_id'], data['serial_number'], data['issuer'], data['subject'],
                data['valid_from'], data['valid_to'], data['thumbprint_sha1'],
                data['thumbprint_sha256'], data['public_key'], data['key_usage'],
                data['certificate_type'], data['storage_location'], data['pin_code_hint'],
                data['notes']
            ))
            conn.commit()
            flash("Сертификат добавлен!", "success")
        except Exception as e:
            flash(f"Ошибка: {str(e)}", "danger")
        finally:
            conn.close()
        return redirect(url_for('index'))

    # Получаем список сотрудников
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, full_name FROM employees ORDER BY full_name")
    employees = cursor.fetchall()
    conn.close()
    return render_template('add.html', employees=employees)

# Редактировать
@app.route('/edit/<int:cert_id>', methods=['GET', 'POST'])
def edit(cert_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        data = request.form
        try:
            cursor.execute("""
                UPDATE certificates SET
                    employee_id=%s, serial_number=%s, issuer=%s, subject=%s,
                    valid_from=%s, valid_to=%s, thumbprint_sha1=%s, thumbprint_sha256=%s,
                    public_key=%s, key_usage=%s, certificate_type=%s,
                    storage_location=%s, pin_code_hint=%s, notes=%s
                WHERE id=%s
            """, (
                data['employee_id'], data['serial_number'], data['issuer'], data['subject'],
                data['valid_from'], data['valid_to'], data['thumbprint_sha1'],
                data['thumbprint_sha256'], data['public_key'], data['key_usage'],
                data['certificate_type'], data['storage_location'], data['pin_code_hint'],
                data['notes'], cert_id
            ))
            conn.commit()
            flash("Сертификат обновлён!", "success")
        except Exception as e:
            flash(f"Ошибка: {str(e)}", "danger")
        return redirect(url_for('index'))

    cursor.execute("SELECT * FROM certificates WHERE id = %s", (cert_id,))
    cert = cursor.fetchone()
    cursor.execute("SELECT id, full_name FROM employees ORDER BY full_name")
    employees = cursor.fetchall()
    conn.close()
    return render_template('edit.html', cert=cert, employees=employees)

# Удалить
@app.route('/delete/<int:cert_id>')
def delete(cert_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM certificates WHERE id = %s", (cert_id,))
        conn.commit()
        flash("Сертификат удалён", "info")
    except Exception as e:
        flash(f"Ошибка удаления: {str(e)}", "danger")
    finally:
        conn.close()
    return redirect(url_for('index'))

# Запуск приложения
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
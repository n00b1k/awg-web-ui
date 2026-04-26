import sqlite3
import bcrypt
from flask_login import UserMixin
from contextlib import contextmanager
import os
from datetime import datetime, timedelta

DB_PATH = '/etc/amnezia/users.db'
login_attempts = {}

class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_db() as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        admin_user = os.getenv('ADMIN_USERNAME', 'admin')
        admin_password = os.getenv('ADMIN_PASSWORD', '')
        admin_password_hash = os.getenv('ADMIN_PASSWORD_HASH', '')
        
        user = db.execute('SELECT * FROM users WHERE username = ?', (admin_user,)).fetchone()
        
        if not user:
            if admin_password_hash:
                # Используем готовый хеш
                password_hash = admin_password_hash
                print(f"Using provided password hash for user: {admin_user}")
            elif admin_password:
                # Генерируем хеш из пароля
                password_hash = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                print(f"Generated password hash for user: {admin_user}")
            else:
                # Генерируем случайный пароль
                import secrets
                import string
                random_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
                password_hash = bcrypt.hashpw(random_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                print(f"WARNING: No password provided! Generated random password for user {admin_user}: {random_password}")
                print(f"Please save this password: {random_password}")
            
            db.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                      (admin_user, password_hash))
            print(f"Created admin user: {admin_user}")

def check_login_attempts(username):
    if username in login_attempts:
        attempts, last_attempt = login_attempts[username]
        if attempts >= 5 and datetime.now() - last_attempt < timedelta(minutes=15):
            remaining = int(15 - (datetime.now() - last_attempt).seconds / 60)
            return False, f"Too many failed attempts. Please try again in {remaining} minutes"
    return True, None

def record_login_attempt(username, success):
    """Запись попытки входа"""
    if success:
        # Успешный вход - очищаем историю попыток
        if username in login_attempts:
            del login_attempts[username]
    else:
        # Неудачная попытка
        if username in login_attempts:
            attempts, last_attempt = login_attempts[username]
            login_attempts[username] = (attempts + 1, datetime.now())
        else:
            login_attempts[username] = (1, datetime.now())

def verify_password(username, password):
    """Проверка пароля пользователя с защитой от брутфорса"""
    # Проверяем количество попыток входа
    allowed, message = check_login_attempts(username)
    if not allowed:
        return None, message
    
    with get_db() as db:
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            # Успешный вход
            record_login_attempt(username, True)
            return User(user['id'], user['username'], user['password_hash']), None
        else:
            # Неудачная попытка
            record_login_attempt(username, False)
            return None, "Invalid username or password"

def get_user(user_id):
    """Получение пользователя по ID"""
    with get_db() as db:
        user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if user:
            return User(user['id'], user['username'], user['password_hash'])
    return None

def login_required_with_message(f):
    """Декоратор для проверки авторизации с редиректом на страницу входа"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please login to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
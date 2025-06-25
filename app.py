import sqlite3
from flask import Flask, request, render_template_string, redirect, url_for, session

# Уязвимое хранение секретного ключа прямо в коде
SECRET_KEY = "insecure_secret_key"

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Инициализация базы данных при первом запуске
def init_db():
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        text TEXT
    )
    ''')
    # Создаём тестового пользователя
    c.execute("INSERT OR IGNORE INTO users (username, password) VALUES ('admin', 'admin')")
    conn.commit()
    conn.close()

init_db()

# Главная страница
@app.route('/')
def index():
    return '''
    <h2>Добро пожаловать!</h2>
    <a href="/register">Регистрация</a> | <a href="/login">Вход</a> | <a href="/profile">Профиль</a> | <a href="/comments">Комментарии</a>
    '''

# Регистрация
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # SQL-инъекция: прямое подставление данных пользователя в запрос
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('db.sqlite3')
        c = conn.cursor()
        c.execute(f"INSERT INTO users (username, password) VALUES ('{username}', '{password}')")
        conn.commit()
        conn.close()
        return redirect(url_for('login'))
    return '''
    <h3>Регистрация</h3>
    <form method="post">
      Логин: <input name="username"><br>
      Пароль: <input name="password" type="password"><br>
      <button type="submit">Зарегистрироваться</button>
    </form>
    '''

# Вход
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # SQL-инъекция: нет экранирования пользовательских данных
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('db.sqlite3')
        c = conn.cursor()
        c.execute(f"SELECT * FROM users WHERE username='{username}' AND password='{password}'")
        user = c.fetchone()
        conn.close()
        if user:
            session['username'] = username
            return redirect(url_for('profile', username=username))
        else:
            return "Ошибка входа"
    return '''
    <h3>Вход</h3>
    <form method="post">
      Логин: <input name="username"><br>
      Пароль: <input name="password" type="password"><br>
      <button type="submit">Войти</button>
    </form>
    '''

# Просмотр профиля любого пользователя (IDOR)
@app.route('/profile')
def profile():
    username = request.args.get('username', None)
    if not username:
        # Если пользователь авторизован, показать свой профиль
        if 'username' in session:
            username = session['username']
        else:
            return redirect(url_for('login'))
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    c.execute(f"SELECT id, username FROM users WHERE username='{username}'")
    user = c.fetchone()
    conn.close()
    if user:
        return f"<h3>Профиль пользователя {user[1]}</h3><p>ID: {user[0]}</p>"
    else:
        return "Пользователь не найден"

# Оставить XSS-комментарий (нет экранирования)
@app.route('/comments', methods=['GET', 'POST'])
def comments():
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    if request.method == 'POST':
        text = request.form['text']
        user = session.get('username', 'Гость')
        # XSS: нет экранирования, любой HTML сохраняется
        c.execute(f"INSERT INTO comments (user, text) VALUES ('{user}', '{text}')")
        conn.commit()
    c.execute("SELECT user, text FROM comments ORDER BY id DESC")
    comments = c.fetchall()
    conn.close()
    comment_html = "<br>".join([f"<b>{u}:</b> {t}" for u, t in comments])
    # Простой шаблон, не фильтрует XSS
    return f'''
    <h3>Комментарии</h3>
    <form method="post">
      <textarea name="text" rows="3" cols="40"></textarea><br>
      <button type="submit">Добавить</button>
    </form>
    <div>{comment_html}</div>
    '''

# CSRF-уязвимость: смена пароля без проверки токена
@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'username' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        new_password = request.form['password']
        conn = sqlite3.connect('db.sqlite3')
        c = conn.cursor()
        c.execute(f"UPDATE users SET password='{new_password}' WHERE username='{session['username']}'")
        conn.commit()
        conn.close()
        return "Пароль изменён"
    return '''
    <h3>Смена пароля</h3>
    <form method="post">
      Новый пароль: <input name="password" type="password"><br>
      <button type="submit">Сменить</button>
    </form>
    '''

# Выход
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, threaded=False)

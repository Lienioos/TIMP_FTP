from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
from werkzeug.utils import secure_filename
from ftplib import FTP
import os
import tempfile
import configparser
import datetime
import json
import hashlib
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'key'

# Пути к файлам
CONFIG_FILE = 'ftp_config.ini'
USERS_FILE = 'users.json'
LOGS_FILE = 'logs.json'

# Инициализация JSON файлов для хранения данных
def init_json_db():
    # Создаем файл пользователей, если его нет
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump([], f)
    
    # Создаем файл логов, если его нет
    if not os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, 'w') as f:
            json.dump([], f)

# Функции для работы с пользователями
def get_users():
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def get_user_by_username(username):
    users = get_users()
    for user in users:
        if user['username'] == username:
            return user
    return None

def get_user_by_id(user_id):
    users = get_users()
    for user in users:
        if user['id'] == user_id:
            return user
    return None

def add_user(username, password, email=None):
    users = get_users()
    # Проверка на существующее имя пользователя
    if get_user_by_username(username):
        return False, "Пользователь с таким именем уже существует"
    
    # Проверка на существующий email
    if email:
        for user in users:
            if user.get('email') == email:
                return False, "Email уже используется"
    
    # Создаем нового пользователя
    new_id = 1
    if users:
        new_id = max(user['id'] for user in users) + 1
    
    new_user = {
        'id': new_id,
        'username': username,
        'password': hash_password(password),
        'email': email,
        'created_at': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    users.append(new_user)
    save_users(users)
    return True, new_user['id']

# Функции для работы с логами
def get_logs():
    with open(LOGS_FILE, 'r') as f:
        return json.load(f)

def save_logs(logs):
    with open(LOGS_FILE, 'w') as f:
        json.dump(logs, f, indent=4)

def log_action(user_id, action, details=None):
    logs = get_logs()
    
    new_id = 1
    if logs:
        new_id = max(log['id'] for log in logs) + 1
    
    new_log = {
        'id': new_id,
        'user_id': user_id,
        'action': action,
        'details': details,
        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    logs.append(new_log)
    save_logs(logs)

def get_user_logs(user_id):
    logs = get_logs()
    return [log for log in logs if log['user_id'] == user_id]

# Хеширование пароля
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Декоратор для проверки авторизации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему для доступа к этой странице', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Загрузка конфигурации FTP
def load_config():
    config = configparser.ConfigParser()
    
    # If file doesn't exist or is invalid, create it with default values
    if not os.path.exists(CONFIG_FILE):
        config['FTP'] = {
            'host': '1.1.1.1',
            'port': '21',
            'username': 'lienioos',
            'password': '123123',
            'directory': '/'
        }
        with open(CONFIG_FILE, 'w') as f:
            config.write(f)
    else:
        config.read(CONFIG_FILE)

    return config

# Функции для работы с FTP
def connect_ftp():
    config = load_config()
    ftp = FTP()
    try:
        ftp.connect(config['FTP']['host'], int(config['FTP']['port']))
        ftp.login(config['FTP']['username'], config['FTP']['password'])
        if 'directory' in config['FTP'] and config['FTP']['directory'] != '/':
            ftp.cwd(config['FTP']['directory'])
        return ftp
    except Exception as e:
        print(f"Ошибка подключения по FTP : {e}")
        return None

def list_ftp_files(ftp, path='.'):
    files = []
    dirs = []
    
    try:
        if path != '.':
            ftp.cwd(path)
        
        entries = []
        ftp.dir(entries.append)
        
        for entry in entries:
            parts = entry.split()
            # Проверяем, является ли элемент директорией
            if entry.startswith('d'):
                dirs.append(parts[-1])
            else:
                file_info = {
                    'name': parts[-1],
                    'size': parts[4],
                    'date': ' '.join(parts[5:8])
                }
                files.append(file_info)
                
        if path != '.':
            ftp.cwd('..')
            
        return {'files': files, 'dirs': dirs, 'current_path': path}
    except Exception as e:
        print(f"Error listing files: {e}")
        return {'files': [], 'dirs': [], 'current_path': path, 'error': str(e)}

# Маршруты для авторизации
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        
        if not username or not password:
            flash('Все поля обязательны для заполнения', 'error')
            return redirect(url_for('register'))
        
        success, message = add_user(username, password, email)
        if success:
            flash('Регистрация успешна!', 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'error')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = get_user_by_username(username)
        if user and user['password'] == hash_password(password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            log_action(user['id'], 'login', 'Успешный вход в систему')
            flash(f'Добро пожаловать, {username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    if 'user_id' in session:
        log_action(session['user_id'], 'logout', 'Выход из системы')
        session.pop('user_id', None)
        session.pop('username', None)
    
    flash('Вы вышли из системы', 'success')
    return redirect(url_for('login'))

@app.route('/user/logs')
@login_required
def user_logs():
    user_id = session['user_id']
    logs = get_user_logs(user_id)
    return render_template('logs.html', logs=logs)

# Оригинальные маршруты с добавлением авторизации и логирования
@app.route('/')
@login_required
def index():
    ftp = connect_ftp()
    if ftp:
        try:
            file_list = list_ftp_files(ftp)
            ftp.quit()  
            log_action(session['user_id'], 'browse', 'Просмотр корневой директории')
            return render_template('index.html', **file_list)
        except Exception as e:
            flash(f'Ошибка при работе с FTP: {e}', 'error')
            return redirect(url_for('settings'))
    else:
        flash('Не удалось подключиться к FTP-серверу.', 'error')
        return redirect(url_for('settings'))

@app.route('/browse/<path:directory>')
@login_required
def browse(directory):
    ftp = connect_ftp()
    if ftp:
        try:
            file_list = list_ftp_files(ftp, directory)
            ftp.quit()
            log_action(session['user_id'], 'browse', f'Просмотр директории: {directory}')
            return render_template('index.html', **file_list)
        except Exception as e:
            flash(f'Ошибка при просмотре директории: {e}', 'error')
            return redirect(url_for('index'))
    else:
        flash('Не удалось подключиться к FTP-серверу', 'error')
        return redirect(url_for('index'))

@app.route('/download/<path:filepath>')
@login_required
def download(filepath):
    ftp = connect_ftp()
    if ftp:
        try:
            # Создаем временный файл для загрузки
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            filename = os.path.basename(filepath)
            
            # Скачиваем файл с FTP-сервера
            with open(temp_file.name, 'wb') as f:
                ftp.retrbinary(f'RETR {filepath}', f.write)
            
            ftp.quit()
            
            log_action(session['user_id'], 'download', f'Скачивание файла: {filepath}')
            # Отправляем файл пользователю
            return send_file(temp_file.name, as_attachment=True, download_name=filename)
        except Exception as e:
            flash(f'Ошибка при скачивании файла: {e}', 'error')
            return redirect(url_for('index'))
    else:
        flash('Не удалось подключиться к FTP-серверу', 'error')
        return redirect(url_for('index'))

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    if 'file' not in request.files:
        flash('Файл не выбран', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    current_dir = request.form.get('current_path', '.')
    
    if file.filename == '':
        flash('Файл не выбран', 'error')
        return redirect(url_for('index'))
    
    filename = secure_filename(file.filename)
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    file.save(temp_file.name)
    
    ftp = connect_ftp()
    if ftp:
        try:
            if current_dir != '.':
                ftp.cwd(current_dir)
                
            with open(temp_file.name, 'rb') as f:
                ftp.storbinary(f'STOR {filename}', f)
                
            flash(f'Файл {filename} успешно загружен', 'success')
            log_action(session['user_id'], 'upload', f'Загрузка файла: {current_dir}/{filename}')
            ftp.quit()
        except Exception as e:
            flash(f'Ошибка при загрузке файла: {e}', 'error')
    else:
        flash('Не удалось подключиться к FTP-серверу', 'error')
    
    
    if current_dir != '.':
        return redirect(url_for('browse', directory=current_dir))
    else:
        return redirect(url_for('index'))

@app.route('/create_directory', methods=['POST'])
@login_required
def create_directory():
    directory_name = request.form.get('directory_name')
    current_dir = request.form.get('current_path', '.')
    
    if not directory_name:
        flash('Имя директории не указано', 'error')
        return redirect(url_for('index'))
    
    ftp = connect_ftp()
    if ftp:
        try:
            if current_dir != '.':
                ftp.cwd(current_dir)
                
            ftp.mkd(directory_name)
            flash(f'Директория {directory_name} успешно создана', 'success')
            log_action(session['user_id'], 'create_directory', f'Создание директории: {current_dir}/{directory_name}')
            ftp.quit()
        except Exception as e:
            flash(f'Ошибка при создании директории: {e}', 'error')
    else:
        flash('Не удалось подключиться к FTP-серверу', 'error')
    
    if current_dir != '.':
        return redirect(url_for('browse', directory=current_dir))
    else:
        return redirect(url_for('index'))

@app.route('/delete/<path:filepath>')
@login_required
def delete_file(filepath):
    ftp = connect_ftp()
    if ftp:
        try:
            directory = os.path.dirname(filepath)
            filename = os.path.basename(filepath)
            
            if directory:
                ftp.cwd(directory)
                
            ftp.delete(filename)
            flash(f'Файл {filename} успешно удален', 'success')
            log_action(session['user_id'], 'delete', f'Удаление файла: {filepath}')
            ftp.quit()
            
            if directory:
                return redirect(url_for('browse', directory=directory))
            else:
                return redirect(url_for('index'))
        except Exception as e:
            flash(f'Ошибка при удалении файла: {e}', 'error')
            return redirect(url_for('index'))
    else:
        flash('Не удалось подключиться к FTP-серверу', 'error')
        return redirect(url_for('index'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        config = configparser.ConfigParser()
        config['FTP'] = {
            'host': request.form.get('host'),
            'port': request.form.get('port'),
            'username': request.form.get('username'),
            'password': request.form.get('password'),
            'directory': request.form.get('directory', '/')
        }
        
        with open(CONFIG_FILE, 'w') as f:
            config.write(f)
        
        log_action(session['user_id'], 'settings_update', 'Обновление настроек FTP')    
        flash('Настройки успешно сохранены', 'success')
        return redirect(url_for('index'))
    else:
        config = load_config()
        return render_template('settings.html', config=config['FTP'])

if __name__ == '__main__':
    # Убедимся, что директория для шаблонов существует
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # Инициализация JSON базы данных
    init_json_db()
    
    app.run(debug=1)
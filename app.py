from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
import sqlite3
import time
import re
import os  # ФИКС ДЛЯ ХОСТИНГА
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# ФИКС ДЛЯ ХОСТИНГА
app.secret_key = os.environ.get('SECRET_KEY', 'mog_secret_key_123')
app.permanent_session_lifetime = 86400 * 30

def get_db():
    conn = sqlite3.connect('mogclicker.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            balance REAL DEFAULT 0,
            click_power INTEGER DEFAULT 1,
            auto_income REAL DEFAULT 0,
            color TEXT DEFAULT '#ffffff',
            badge TEXT DEFAULT '',
            badge_color TEXT DEFAULT '#ffffff',
            theme TEXT DEFAULT 'dark',
            lang TEXT DEFAULT 'ru',
            zoom INTEGER DEFAULT 100,
            font_family TEXT DEFAULT 'Montserrat',
            is_banned INTEGER DEFAULT 0,
            ban_reason TEXT DEFAULT '',
            ban_msg TEXT DEFAULT '',
            ban_until REAL DEFAULT 0,
            ban_duration TEXT DEFAULT '',
            mute_until REAL DEFAULT 0
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            receiver TEXT,
            amount REAL,
            timestamp REAL
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            text TEXT,
            timestamp REAL,
            reply_user TEXT DEFAULT '',
            reply_text TEXT DEFAULT ''
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY,
            reward REAL,
            uses_left INTEGER
        )''')
        conn.commit()

init_db()

HTML_CODE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>MOGCLICKER</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Comic+Neue:wght@700&family=Montserrat:wght@400;700&family=Play:wght@400;700&family=Russo+One&display=swap" rel="stylesheet">
    
    <style>
        * { -webkit-tap-highlight-color: transparent; box-sizing: border-box; transition: background 0.3s, color 0.3s, border-color 0.3s; }
        
        :root { --bg: #121212; --panel: #1e1e1e; --text: #ffffff; --neon: #00ffcc; --gold: #ffd700; --border: #333; }
        body.theme-light { --bg: #f0f0f0; --panel: #ffffff; --text: #121212; --neon: #0077ff; --border: #ccc; }
        body.theme-neon { --bg: #0a001a; --panel: #1a0033; --text: #ffffff; --neon: #ff00ff; --border: #ff00ff; }
        body.theme-cyber { --bg: #000000; --panel: #111111; --text: #ffff00; --neon: #ff003c; --border: #ff003c; }
        body.theme-ocean { --bg: #001220; --panel: #003366; --text: #e0f7fa; --neon: #00e5ff; --border: #00e5ff; }
        body.theme-retro { --bg: #1a1a1a; --panel: #2a2a2a; --text: #00ff00; --neon: #00ff00; --border: #00ff00; }

        body { background: var(--bg); color: var(--text); font-family: '{{ user.font_family if user else "Montserrat" }}', sans-serif; margin: 0; padding: 10px; user-select: none; text-align: center; overflow-x: hidden; min-height: 100vh; display: flex; flex-direction: column; align-items: center; }
        
        .bubbles { position: fixed; top: 0; left: 0; width: 100%; height: 100%; overflow: hidden; z-index: -1; pointer-events: none; }
        .bubble { position: absolute; border-radius: 50%; background: rgba(255, 255, 255, 0.05); animation: floatBubble 15s infinite linear; }
        @keyframes floatBubble { 0% { transform: translateY(100vh) scale(0); opacity: 0; } 50% { opacity: 0.5; } 100% { transform: translateY(-100px) scale(1.5); opacity: 0; } }

        h1 { color: var(--neon); text-shadow: 0 0 10px var(--neon); margin: 10px 0; font-size: 32px; }
        
        .nav { display: flex; justify-content: center; gap: 5px; margin-bottom: 15px; flex-wrap: wrap; width: 100%; max-width: 400px; }
        .nav button { background: var(--panel); border: 1px solid var(--border); color: var(--text); padding: 8px 12px; border-radius: 8px; cursor: pointer; font-weight: bold; transition: 0.2s; }
        .nav button.active { border-color: var(--neon); color: var(--neon); box-shadow: 0 0 10px var(--neon); }
        
        .view { display: none; background: var(--panel); padding: 20px; border-radius: 20px; border: 1px solid var(--border); min-height: 400px; width: 100%; max-width: 400px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); opacity: 0; transform: translateY(15px); transition: opacity 0.3s ease, transform 0.3s ease; }
        .view.active { display: block; opacity: 1; transform: translateY(0); }

        #auth-wrapper { display: flex; justify-content: center; align-items: center; min-height: 100vh; width: 100%; }
        .glass-card { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(15px); -webkit-backdrop-filter: blur(15px); border: 1px solid rgba(255, 255, 255, 0.1); padding: 30px 20px; border-radius: 25px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37); width: 100%; max-width: 400px; }
        
        input[type="text"], input[type="password"], input[type="number"] { width: 100%; padding: 15px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.2); color: var(--text); border-radius: 15px; margin-bottom: 15px; outline: none; font-size: 16px; transition: 0.3s; }
        input[type="text"]:focus, input[type="password"]:focus { border-color: var(--neon); box-shadow: 0 0 15px var(--neon); background: rgba(0,0,0,0.5); }
        
        .btn-main { background: var(--neon); color: #000; padding: 15px; border: none; border-radius: 15px; cursor: pointer; font-weight: bold; font-size: 16px; width: 100%; margin-bottom: 15px; transition: 0.3s; box-shadow: 0 0 15px transparent; }
        .btn-main:hover { filter: brightness(1.2); box-shadow: 0 0 15px var(--neon); transform: translateY(-2px); }
        .btn-main:active { transform: translateY(1px); }
        .btn-danger { background: #ff4444; color: white; }
        .btn-gold { background: var(--gold); box-shadow: 0 0 15px transparent; }
        .btn-gold:hover { box-shadow: 0 0 15px var(--gold); }

        #score { font-size: 45px; color: var(--gold); font-weight: bold; text-shadow: 0 0 15px rgba(255,215,0,0.4); margin: 15px 0; transition: transform 0.1s; }
        #coin { width: 200px; height: 200px; background: radial-gradient(circle, var(--gold), #b8860b); border-radius: 50%; margin: 20px auto; font-size: 80px; line-height: 200px; cursor: pointer; box-shadow: 0 0 40px var(--gold); display: block; transition: transform 0.1s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
        #coin:active { transform: scale(0.85); box-shadow: 0 0 20px var(--gold); }
        
        .shop-item { display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.2); padding: 15px; margin-bottom: 10px; border-radius: 15px; border: 1px solid var(--border); transition: 0.3s; }
        .shop-item:hover { border-color: var(--neon); transform: translateX(5px); }
        .shop-item button { background: var(--neon); color: #000; border: none; padding: 10px 15px; border-radius: 10px; cursor: pointer; font-weight: bold; transition: 0.2s; }
        
        .top-player { display: flex; justify-content: space-between; padding: 12px; border-bottom: 1px solid var(--border); align-items: center; transition: 0.2s; }
        .top-player:hover { background: rgba(255,255,255,0.05); }
        
        .floating { position: fixed; color: var(--gold); font-weight: bold; font-size: 30px; pointer-events: none; animation: floatUp 0.8s cubic-bezier(0.25, 1, 0.5, 1) forwards; text-shadow: 0 0 10px #000; z-index: 999; }
        @keyframes floatUp { 0% { opacity: 1; transform: translateY(0) scale(1); } 100% { opacity: 0; transform: translateY(-120px) scale(1.5); } }
        
        .badge { padding: 4px 10px; border-radius: 8px; font-size: 12px; margin-left: 5px; font-weight: bold; display: inline-block; text-shadow: none; }
        .hammer { margin-left: 5px; font-size: 14px; cursor: pointer; filter: drop-shadow(0 0 5px #ff0000); transition: 0.2s; }
        .hammer:hover { transform: scale(1.3); }
        
        .rainbow-text { background: linear-gradient(90deg, #ff0000, #ff7f00, #ffff00, #00ff00, #0000ff, #4b0082, #8f00ff, #ff0000); background-size: 200% auto; -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: bold; animation: rainbowAnim 3s linear infinite; }
        @keyframes rainbowAnim { to { background-position: 200% center; } }

        #toast-container { position: fixed; top: 20px; left: 50%; transform: translateX(-50%); z-index: 1000; display: flex; flex-direction: column; gap: 10px; width: 80%; max-width: 300px; }
        .toast { background: var(--panel); color: var(--text); padding: 15px; border-radius: 10px; border-left: 5px solid var(--neon); box-shadow: 0 5px 15px rgba(0,0,0,0.5); animation: slideDown 0.3s forwards, fadeOut 0.3s 2.7s forwards; font-weight: bold; text-align: left; }
        .toast.error { border-left-color: #ff4444; }
        @keyframes slideDown { from { transform: translateY(-20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        @keyframes fadeOut { to { opacity: 0; transform: translateY(-20px); } }
        
        .setting-item { display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.2); padding: 15px; margin-bottom: 10px; border-radius: 10px; border: 1px solid var(--border); cursor: pointer; transition: 0.2s; }
        .setting-item:hover { border-color: var(--neon); }
        input[type="range"] { width: 100%; accent-color: var(--neon); height: 20px; margin-top: 10px; }
        
        .auth-switch { color: var(--neon); cursor: pointer; text-decoration: none; margin-top: 15px; display: block; font-size: 14px; transition: 0.2s; }
        .auth-switch:hover { text-shadow: 0 0 10px var(--neon); }
        
        .modal { display: flex; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 9999; justify-content: center; align-items: center; backdrop-filter: blur(5px); opacity: 0; visibility: hidden; transition: opacity 0.3s ease, visibility 0.3s ease; }
        .modal.active { opacity: 1; visibility: visible; }
        .modal-content { background: #1a1a1a; border: 2px solid var(--neon); padding: 25px; border-radius: 15px; max-width: 90%; width: 350px; text-align: left; box-shadow: 0 0 30px rgba(0,255,204,0.2); position: relative; transform: scale(0.8); transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275); max-height: 80vh; overflow-y: auto; }
        .modal.active .modal-content { transform: scale(1); }
        .modal-title { color: var(--neon); font-size: 22px; font-weight: bold; text-align: center; margin-bottom: 20px; text-shadow: 0 0 10px var(--neon); }
        .close-btn { position: absolute; top: 10px; right: 15px; font-size: 24px; cursor: pointer; color: #ff4444; transition: 0.2s; }
        .close-btn:hover { transform: scale(1.2); text-shadow: 0 0 10px #ff4444; }
        
        .custom-option { padding: 15px; border-bottom: 1px solid var(--border); cursor: pointer; transition: 0.2s; border-radius: 8px; margin-bottom: 5px; font-size: 16px; }
        .custom-option:hover { background: rgba(255,255,255,0.1); color: var(--neon); padding-left: 20px; }
        .custom-option:last-child { border-bottom: none; }

        .info-label { color: #0077ff; font-weight: bold; margin-bottom: 5px; font-size: 14px;}
        .info-value { color: #ffffff; margin-bottom: 15px; font-family: monospace; font-size: 15px; background: rgba(255,255,255,0.1); padding: 8px 10px; border-radius: 5px; }
        
        #chat-container { width: 100%; max-width: 400px; background: var(--panel); border: 2px solid var(--border); border-radius: 20px; display: flex; flex-direction: column; margin-top: 20px; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); overflow: hidden; position: relative;}
        #chat-messages { height: 300px; overflow-y: auto; padding: 15px; text-align: left; font-size: 14px; display: flex; flex-direction: column; gap: 10px; }
        
        .chat-msg { word-wrap: break-word; background: rgba(0,0,0,0.2); padding: 10px; border-radius: 10px; border-left: 3px solid var(--neon); line-height: 1.4; position: relative; user-select: none; touch-action: pan-y; transition: transform 0.2s;}
        
        .chat-reply-preview { font-size: 11px; color: #888; border-left: 2px solid #555; padding-left: 5px; margin-bottom: 5px; display: none; }
        
        #chat-input-area { display: flex; padding: 10px; gap: 10px; background: rgba(0,0,0,0.4); border-top: 1px solid var(--border); flex-direction: column;}
        
        #chat-reply-bar { display: none; background: rgba(255,255,255,0.1); padding: 8px; border-radius: 8px; margin-bottom: 5px; font-size: 12px; text-align: left; border-left: 3px solid var(--gold); position: relative;}
        .close-reply { position: absolute; right: 5px; top: 5px; cursor: pointer; color: #ff4444; font-weight: bold;}
        
        .chat-input-row { display: flex; gap: 10px; width: 100%; }
        #chat-input { flex: 1; margin: 0; padding: 12px; border-radius: 20px; }
        #chat-send { width: 50px; margin: 0; padding: 0; border-radius: 50%; display: flex; justify-content: center; align-items: center; }
        
        #chat-mute-status { display: none; padding: 15px; background: rgba(255,0,0,0.2); color: #ff4444; font-weight: bold; text-align: center; border-radius: 10px; }
        
        .ban-fullscreen { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #0a0000; z-index: 10000; display: flex; justify-content: center; align-items: center; flex-direction: column; }
        .ban-fullscreen .modal-content { border-color: #ff4444; width: 90%; max-width: 400px; transform: scale(1); }
    </style>
</head>
<body class="theme-{{ user.theme if user else 'dark' }}" style="zoom: {{ user.zoom if user else 100 }}%; font-family: '{{ user.font_family if user else 'Montserrat' }}', sans-serif;">
    
    <div class="bubbles" id="bubbles"></div>
    <div id="toast-container"></div>

    {% if user and user.is_banned %}
        <div class="ban-fullscreen">
            <div class="modal-content" style="border-color: #ff4444;">
                <div class="modal-title" style="color: #ff4444; text-shadow: 0 0 10px #ff0000;">!ВЫ ЗАБАНЕНЫ!</div>
                <div class="info-label">!ПРИЧИНА:</div>
                <div class="info-value" style="color: #ff4444;">{{ user.ban_reason }}</div>
                <div class="info-label" style="color: #888;">!СООБЩЕНИЕ К БАНУ:</div>
                <div class="info-value" style="color: #aaa; font-size: 13px;">{{ user.ban_msg }}</div>
                <div class="info-label">!ВАШ НИК:</div>
                <div class="info-value">{{ user.username }}</div>
                <div class="info-label">!ЗАБАНЕН НА:</div>
                <div class="info-value">{{ user.ban_duration }}</div>
                <div class="info-label">!ОСТАЛОСЬ ВРЕМЕНИ:</div>
                <div class="info-value" id="ban-timer" style="color: #ff4444; font-weight: bold; font-size: 18px;"></div>
                <a href="/logout" class="btn-main btn-danger" style="display: block; text-decoration: none; margin-top: 20px;">Выйти с аккаунта</a>
            </div>
        </div>
        <script>
            let remaining = {{ remaining_seconds }};
            function updateTimer() {
                if(remaining <= 0) { window.location.reload(); return; }
                let d = Math.floor(remaining / 86400); let h = Math.floor((remaining % 86400) / 3600);
                let m = Math.floor((remaining % 3600) / 60); let s = remaining % 60;
                let text = ""; if(d > 0) text += d + "д "; if(h > 0) text += h + "ч ";
                text += m + "м " + s + "с";
                document.getElementById('ban-timer').innerText = text;
                remaining--; setTimeout(updateTimer, 1000);
            }
            updateTimer();
        </script>

    {% elif not user %}
        <div id="auth-wrapper">
            <div class="glass-card">
                <h1>MOGCLICKER</h1>
                <div id="login-box">
                    <h3>Вход</h3>
                    <input type="text" id="l-username" placeholder="Логин (только англ.)">
                    <input type="password" id="l-password" placeholder="Пароль">
                    <button class="btn-main" onclick="doAuth('login')">Войти</button>
                    <a class="auth-switch" onclick="toggleAuth('reg')">Нет аккаунта? Зарегистрироваться</a>
                </div>
                <div id="reg-box" style="display: none;">
                    <h3>Регистрация</h3>
                    <input type="text" id="r-username" placeholder="Логин (только англ.)">
                    <input type="password" id="r-password" placeholder="Пароль">
                    <button class="btn-main btn-gold" onclick="doAuth('register')">Создать аккаунт</button>
                    <a class="auth-switch" onclick="toggleAuth('login')">Уже есть аккаунт? Войти</a>
                </div>
            </div>
        </div>
    
    {% else %}
        <h1>MOGCLICKER</h1>
        <div style="font-size: 16px; margin-bottom: 15px; display: flex; justify-content: center; align-items: center; gap: 5px; flex-wrap: wrap;">
            <span>Привет</span>, 
            <span class="{% if user.color == 'rainbow' %}rainbow-text{% endif %}" style="color: {{ user.color if user.color != 'rainbow' else '' }}; font-weight: bold;">{{ user.username }}</span>
            {% if user.badge %}
                <span class="badge {% if user.badge_color == 'rainbow' %}rainbow-text{% endif %}" style="{% if user.badge_color != 'rainbow' %}background: {{ user.badge_color }}; color: #000;{% endif %}">{{ user.badge }}</span>
            {% endif %}
            | <a href="/logout" style="color: #ff4444; text-decoration: none; font-weight: bold;">Выйти</a>
        </div>

        <div class="nav">
            <button onclick="switchTab('game')" id="tab-game" class="active">Игра</button>
            <button onclick="switchTab('shop')" id="tab-shop">Магазин</button>
            <button onclick="switchTab('transfer')" id="tab-transfer">Переводы</button>
            <button onclick="switchTab('top')" id="tab-top">Топ</button>
            <button onclick="switchTab('settings')" id="tab-settings">Настройки</button>
        </div>

        <div id="view-game" class="view active">
            <div id="score">{{ user.balance|int }} ₽</div>
            <div id="coin" onclick="clickCoin(event)">₽</div>
            <div id="stats">
                Сила клика: <span id="ui-click-power">{{ user.click_power }}</span> | 
                Доход: <span id="ui-auto-income">{{ user.auto_income }}</span>/сек
            </div>
        </div>

        <div id="view-shop" class="view">
            <h3>Улучшения</h3>
            <div class="shop-item">
                <div>Мультиклик (x2)</div>
                <button onclick="buyUpgrade('multi')">{{ multi_price }} ₽</button>
            </div>
            <div class="shop-item">
                <div>Автокликер (+1/сек)</div>
                <button onclick="buyUpgrade('auto')">{{ auto_price }} ₽</button>
            </div>
            <h3>Кастомизация</h3>
            <div class="shop-item">
                <div>Радужный ник</div>
                <button onclick="buyCustom('color', 'rainbow', 5000)">5,000 ₽</button>
            </div>
            <div class="shop-item">
                <div>Бейдж "MOG"</div>
                <button onclick="buyCustom('badge', 'MOG', 1000)">1,000 ₽</button>
            </div>
        </div>

        <div id="view-transfer" class="view">
            <h3>Переводы</h3>
            <input type="text" id="tr-nick" placeholder="Ник получателя" style="margin-bottom: 10px;">
            <input type="number" id="tr-amount" placeholder="Сумма" style="margin-bottom: 10px;">
            <button class="btn-main" onclick="doTransfer()" style="margin-bottom: 20px;">Перевести</button>
            
            <div style="display:flex; gap:5px; margin-bottom: 10px;">
                <button class="nav-btn active" style="flex:1; padding:8px; border-radius:5px; background:var(--neon); color:#000; border:none; font-weight:bold;" onclick="loadTransfers('day', this)">День</button>
                <button class="nav-btn" style="flex:1; padding:8px; border-radius:5px; background:var(--panel); color:var(--text); border:1px solid var(--border);" onclick="loadTransfers('month', this)">Месяц</button>
                <button class="nav-btn" style="flex:1; padding:8px; border-radius:5px; background:var(--panel); color:var(--text); border:1px solid var(--border);" onclick="loadTransfers('all', this)">Всегда</button>
            </div>
            <h4 style="text-align:left; margin-bottom:5px;">Топ переводчиков:</h4>
            <div id="transfer-top-list" style="text-align:left; font-size:14px; margin-bottom:20px; max-height:150px; overflow-y:auto;"></div>
            
            <h4 style="text-align:left; margin-bottom:5px;">Ваши переводы:</h4>
            <div id="my-transfer-list" style="text-align:left; font-size:14px; max-height:150px; overflow-y:auto;"></div>
        </div>

        <div id="view-top" class="view">
            <h3>Топ игроков</h3>
            <div id="top-list">Загрузка...</div>
        </div>

        <div id="view-settings" class="view">
            <h3>Настройки</h3>
            <div class="setting-item" onclick="openModal('lang-modal')">
                <span>Язык</span><span id="display-lang">Русский</span>
            </div>
            <div class="setting-item" onclick="openModal('theme-modal')">
                <span>Тема</span><span id="display-theme">Тёмная</span>
            </div>
            <div class="setting-item" onclick="openModal('font-modal')">
                <span>Шрифт</span><span id="display-font">{{ user.font_family }}</span>
            </div>
            <div class="setting-item" style="flex-direction: column; align-items: flex-start;">
                <div style="display:flex; justify-content:space-between; width:100%;">
                    <span>Масштаб UI</span><span id="zoom-val">{{ user.zoom }}%</span>
                </div>
                <input type="range" id="set-zoom" min="50" max="150" step="10" value="{{ user.zoom }}" oninput="updateZoom(this.value)">
            </div>
            
            <h4 style="text-align:left; margin-top:20px;">Промокод</h4>
            <div style="display:flex; gap:10px;">
                <input type="text" id="promo-input" placeholder="Введите код..." style="margin-bottom:0;">
                <button class="btn-main" onclick="redeemPromo()" style="width:100px; margin-bottom:0;">Ввод</button>
            </div>

            <div class="setting-item" style="background: rgba(255,0,0,0.1); border-color: #ff4444; flex-direction: column; margin-top:20px;">
                <p style="font-size: 12px; margin-bottom: 10px;">Опасная зона!</p>
                <button class="btn-main btn-danger" onclick="resetProgress()" style="width:100%;">Сбросить прогресс</button>
            </div>
        </div>

        <div id="chat-container">
            <div id="chat-messages"></div>
            
            <div id="chat-mute-status">
                Вы заглушены на <span id="mute-timer">0с</span>
            </div>

            <div id="chat-input-area">
                <div id="chat-reply-bar">
                    <span id="reply-text-preview" style="color:var(--gold); font-weight:bold;"></span><br>
                    <span id="reply-message-preview" style="color:#aaa; font-size:11px;"></span>
                    <span class="close-reply" onclick="cancelReply()">×</span>
                </div>
                <div class="chat-input-row">
                    <input type="text" id="chat-input" placeholder="Сообщение в чат..." onkeypress="handleChatEnter(event)">
                    <button id="chat-send" class="btn-main" onclick="sendChat()" style="padding:0;">➤</button>
                </div>
            </div>
        </div>
    {% endif %}

    <!-- МОДАЛКИ НАСТРОЕК -->
    <div class="modal" id="lang-modal">
        <div class="modal-content">
            <span class="close-btn" onclick="closeModal('lang-modal')">×</span>
            <div class="modal-title">Язык</div>
            <div class="custom-option" onclick="changeSetting('lang', 'ru'); closeModal('lang-modal')">Русский</div>
            <div class="custom-option" onclick="changeSetting('lang', 'en'); closeModal('lang-modal')">English</div>
            <div class="custom-option" onclick="changeSetting('lang', 'ua'); closeModal('lang-modal')">Українська</div>
        </div>
    </div>
    
    <div class="modal" id="theme-modal">
        <div class="modal-content">
            <span class="close-btn" onclick="closeModal('theme-modal')">×</span>
            <div class="modal-title">Тема</div>
            <div class="custom-option" onclick="changeSetting('theme', 'dark'); closeModal('theme-modal')">Тёмная</div>
            <div class="custom-option" onclick="changeSetting('theme', 'light'); closeModal('theme-modal')">Светлая</div>
            <div class="custom-option" onclick="changeSetting('theme', 'neon'); closeModal('theme-modal')">Неон</div>
            <div class="custom-option" onclick="changeSetting('theme', 'cyber'); closeModal('theme-modal')">Киберпанк</div>
            <div class="custom-option" onclick="changeSetting('theme', 'ocean'); closeModal('theme-modal')">Океан</div>
            <div class="custom-option" onclick="changeSetting('theme', 'retro'); closeModal('theme-modal')">Ретро</div>
        </div>
    </div>

    <div class="modal" id="font-modal">
        <div class="modal-content">
            <span class="close-btn" onclick="closeModal('font-modal')">×</span>
            <div class="modal-title">Шрифт</div>
            <div class="custom-option" onclick="changeSetting('font_family', 'Montserrat'); closeModal('font-modal')" style="font-family: 'Montserrat';">Montserrat (Стандарт)</div>
            <div class="custom-option" onclick="changeSetting('font_family', 'Play'); closeModal('font-modal')" style="font-family: 'Play';">Play (Техно)</div>
            <div class="custom-option" onclick="changeSetting('font_family', 'Russo One'); closeModal('font-modal')" style="font-family: 'Russo One';">Russo One (Жирный)</div>
            <div class="custom-option" onclick="changeSetting('font_family', 'Comic Neue'); closeModal('font-modal')" style="font-family: 'Comic Neue';">Comic Neue</div>
        </div>
    </div>

    <!-- МОДАЛКА ПРОСМОТРА БАНА -->
    <div class="modal" id="other-ban-modal">
        <div class="modal-content" style="border-color: #ff4444;">
            <span class="close-btn" onclick="closeOtherBan()">×</span>
            <div class="modal-title" style="color:#ff4444; text-shadow: 0 0 10px #ff0000;">ЗАБАНЕН</div>
            <div class="info-label">НИК НАРУШИТЕЛЯ:</div><div class="info-value" id="other-ban-nick"></div>
            <div class="info-label">ПРИЧИНА:</div><div class="info-value" id="other-ban-reason" style="color: #ff4444;"></div>
            <div class="info-label" style="color: #888;">СООБЩЕНИЕ:</div><div class="info-value" id="other-ban-msg" style="color: #aaa; font-size: 13px;"></div>
            <div class="info-label">ЗАБАНЕН НА:</div><div class="info-value" id="other-ban-duration"></div>
            <div class="info-label">ОСТАЛОСЬ:</div><div class="info-value" id="other-ban-until" style="color: #ff4444; font-weight:bold;"></div>
        </div>
    </div>

    <script>
        const isLoggedIn = {{ 'true' if user and not user.is_banned else 'false' }};
        const THEMES = { dark: "Тёмная", light: "Светлая", neon: "Неон", cyber: "Киберпанк", ocean: "Океан", retro: "Ретро" };
        
        let currentLang = "{{ user.lang if user else 'ru' }}";
        let currentTheme = "{{ user.theme if user else 'dark' }}";
        let currentZoom = parseInt("{{ user.zoom if user else 100 }}");
        let balance = parseFloat("{{ user.balance if user else 0 }}");
        let clickPower = parseInt("{{ user.click_power if user else 1 }}");
        let autoIncome = parseFloat("{{ user.auto_income if user else 0 }}");
        let muteUntil = parseFloat("{{ user.mute_until if user else 0 }}");

        function openModal(id) { document.getElementById(id).classList.add('active'); }
        function closeModal(id) { document.getElementById(id).classList.remove('active'); }

        function playSound(type) {
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            if(audioCtx.state === 'suspended') audioCtx.resume();
            const osc = audioCtx.createOscillator(); const gain = audioCtx.createGain();
            if(type === 'click') { osc.type = 'sine'; osc.frequency.setValueAtTime(800, audioCtx.currentTime); osc.frequency.exponentialRampToValueAtTime(1200, audioCtx.currentTime + 0.05); gain.gain.setValueAtTime(0.1, audioCtx.currentTime); }
            else if(type === 'error') { osc.type = 'sawtooth'; osc.frequency.setValueAtTime(150, audioCtx.currentTime); gain.gain.setValueAtTime(0.1, audioCtx.currentTime); }
            else if(type === 'success') { osc.type = 'triangle'; osc.frequency.setValueAtTime(400, audioCtx.currentTime); osc.frequency.exponentialRampToValueAtTime(800, audioCtx.currentTime + 0.1); gain.gain.setValueAtTime(0.1, audioCtx.currentTime); }
            gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.2);
            osc.connect(gain); gain.connect(audioCtx.destination); osc.start(); osc.stop(audioCtx.currentTime + 0.2);
        }

        function showToast(text, type = 'success') {
            playSound(type); const container = document.getElementById('toast-container'); const toast = document.createElement('div');
            toast.className = `toast ${type}`; toast.innerText = text; container.appendChild(toast); setTimeout(() => toast.remove(), 3000);
        }

        function doAuth(action) {
            let u = action === 'login' ? document.getElementById('l-username').value : document.getElementById('r-username').value;
            let p = action === 'login' ? document.getElementById('l-password').value : document.getElementById('r-password').value;
            
            if(/[а-яА-ЯёЁ]/.test(u) || /[а-яА-ЯёЁ]/.test(p)) {
                return showToast("Только английские буквы!", 'error');
            }

            fetch('/' + action, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username: u, password: p}) })
            .then(res => res.json().then(data => ({status: res.status, data}))).then(res => {
                if(res.status === 200 && res.data.success) window.location.reload();
                else if (res.status === 403 && res.data.banned) window.location.reload(); 
                else showToast(action === 'login' ? "Неверный логин или пароль!" : (res.data.error === 'Cyrillic' ? "Только английские буквы!" : "Логин занят!"), 'error');
            });
        }

        function toggleAuth(box) {
            document.getElementById('login-box').style.display = box === 'login' ? 'block' : 'none';
            document.getElementById('reg-box').style.display = box === 'reg' ? 'block' : 'none';
        }

        function switchTab(tab) {
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            document.querySelectorAll('.nav button').forEach(b => b.classList.remove('active'));
            document.getElementById('view-' + tab).classList.add('active');
            document.getElementById('tab-' + tab).classList.add('active');
            if(tab === 'top') loadTop();
            if(tab === 'transfer') loadTransfers('day', document.querySelector('#view-transfer .nav-btn'));
        }

        setInterval(() => {
            if(!isLoggedIn) return;
            fetch('/api/user').then(r => { if(r.status === 403) { window.location.reload(); return; } return r.json(); }).then(data => {
                if(data && data.success) {
                    if(data.balance !== balance) { balance = data.balance; document.getElementById('score').innerText = Math.floor(balance) + ' ₽'; }
                    clickPower = data.click_power; autoIncome = data.auto_income; muteUntil = data.mute_until;
                    document.getElementById('ui-click-power').innerText = clickPower; document.getElementById('ui-auto-income').innerText = autoIncome;
                    checkMuteStatus();
                }
            }).catch(()=>{});
        }, 2000);

        setInterval(() => {
            if(!isLoggedIn || autoIncome <= 0) return;
            balance += autoIncome;
            document.getElementById('score').innerText = Math.floor(balance) + ' ₽';
            fetch('/api/click', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({amount: autoIncome}) });
        }, 1000);

        function clickCoin(e) {
            if(!isLoggedIn) return;
            balance += clickPower;
            const scoreEl = document.getElementById('score');
            scoreEl.innerText = Math.floor(balance) + ' ₽'; scoreEl.style.transform = "scale(1.1)";
            setTimeout(() => scoreEl.style.transform = "scale(1)", 100); playSound('click');
            
            const el = document.createElement('div'); el.className = 'floating'; el.innerText = '+' + clickPower + ' ₽';
            el.style.left = (e.clientX - 20) + 'px'; el.style.top = (e.clientY - 40) + 'px';
            document.body.appendChild(el); setTimeout(() => el.remove(), 800);
            
            fetch('/api/click', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({amount: clickPower}) })
            .then(res => { if(res.status === 403) { showToast("АБЬЮЗ! АККАУНТ УДАЛЕН!", 'error'); setTimeout(() => window.location.href = '/logout', 2000); } });
        }

        function buyUpgrade(type) {
            fetch('/api/buy', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({type: type}) })
            .then(res => res.json()).then(data => { if(data.success) { showToast("Успешно!", 'success'); setTimeout(() => location.reload(), 800); } else showToast("Мало денег!", 'error'); });
        }

        function buyCustom(type, value, price) {
            fetch('/api/buy_custom', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({type, value, price}) })
            .then(res => res.json()).then(data => { if(data.success) { showToast("Успешно!", 'success'); setTimeout(() => location.reload(), 800); } else showToast("Мало денег!", 'error'); });
        }

        function loadTop() {
            fetch('/api/top').then(res => res.json()).then(data => {
                let html = ''; data.forEach((p, i) => {
                    let badgeClass = p.badge_color === 'rainbow' ? 'rainbow-text' : '';
                    let badgeStyle = p.badge_color !== 'rainbow' ? `background:${p.badge_color}; color:#000;` : '';
                    let badgeHtml = p.badge ? `<span class="badge ${badgeClass}" style="${badgeStyle}">${p.badge}</span>` : '';
                    let hammerHtml = p.is_banned ? `<span class="hammer" onclick="showOtherBan('${p.username}')">🔨</span>` : '';
                    let nameClass = p.color === 'rainbow' ? 'rainbow-text' : '';
                    let nameStyle = p.color !== 'rainbow' ? `style="color:${p.color}; font-weight:bold;"` : '';
                    html += `<div class="top-player"><span>#${i+1} <span class="${nameClass}" ${nameStyle}>${p.username}</span> ${badgeHtml}${hammerHtml}</span> <span>${Math.floor(p.balance)} ₽</span></div>`;
                });
                document.getElementById('top-list').innerHTML = html;
            });
        }

        let topBanInterval = null;
        function showOtherBan(username) {
            fetch('/api/ban_info/' + username).then(res => res.json()).then(data => {
                if(data.success) {
                    document.getElementById('other-ban-nick').innerText = data.username;
                    document.getElementById('other-ban-reason').innerText = data.ban_reason;
                    document.getElementById('other-ban-msg').innerText = data.ban_msg;
                    document.getElementById('other-ban-duration').innerText = data.ban_duration;
                    
                    let remaining = data.remaining;
                    if(topBanInterval) clearInterval(topBanInterval);
                    
                    function updateTopTimer() {
                        if(remaining <= 0) { document.getElementById('other-ban-until').innerText = "Истек"; clearInterval(topBanInterval); return; }
                        let d = Math.floor(remaining / 86400); let h = Math.floor((remaining % 86400) / 3600);
                        let m = Math.floor((remaining % 3600) / 60); let s = remaining % 60;
                        let text = ""; if(d > 0) text += d + "д "; if(h > 0) text += h + "ч ";
                        text += m + "м " + s + "с";
                        document.getElementById('other-ban-until').innerText = text;
                        remaining--;
                    }
                    updateTopTimer();
                    topBanInterval = setInterval(updateTopTimer, 1000);

                    openModal('other-ban-modal');
                }
            });
        }
        function closeOtherBan() { closeModal('other-ban-modal'); if(topBanInterval) clearInterval(topBanInterval); }

        function changeSetting(key, value) {
            if(key === 'theme') { currentTheme = value; document.body.className = 'theme-' + value; document.getElementById('display-theme').innerText = THEMES[value]; }
            if(key === 'lang') { currentLang = value; document.getElementById('display-lang').innerText = value === 'ru' ? 'Русский' : value === 'en' ? 'English' : 'Українська'; }
            if(key === 'font_family') { 
                document.body.style.fontFamily = "'" + value + "', sans-serif"; 
                document.getElementById('display-font').innerText = value; 
            }
            fetch('/api/settings', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({key: key, value: value}) })
            .then(() => showToast("Сохранено!", 'success'));
        }

        function updateZoom(val) {
            document.getElementById('zoom-val').innerText = val + '%'; document.body.style.zoom = val + "%";
            clearTimeout(window.zoomTimer);
            window.zoomTimer = setTimeout(() => { fetch('/api/settings', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({key: 'zoom', value: val}) }); }, 500);
        }

        function resetProgress() { if(confirm("Точно сбросить?")) fetch('/api/reset', { method: 'POST' }).then(() => location.reload()); }

        function doTransfer() {
            let nick = document.getElementById('tr-nick').value; let amount = parseFloat(document.getElementById('tr-amount').value);
            if(!nick || !amount || amount <= 0) return showToast("Заполни поля!", "error");
            
            fetch('/api/transfer', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({receiver: nick, amount: amount}) })
            .then(res => res.json()).then(data => {
                if(data.success) { showToast("Перевод успешен!", 'success'); document.getElementById('tr-nick').value = ''; document.getElementById('tr-amount').value = ''; balance -= amount; document.getElementById('score').innerText = Math.floor(balance) + ' ₽'; loadTransfers('day', document.querySelector('#view-transfer .nav-btn')); } 
                else showToast(data.error, 'error');
            });
        }

        function loadTransfers(period, btn) {
            document.querySelectorAll('#view-transfer .nav-btn').forEach(b => { b.style.background = 'var(--panel)'; b.style.color = 'var(--text)'; b.style.border = '1px solid var(--border)'; });
            btn.style.background = 'var(--neon)'; btn.style.color = '#000'; btn.style.border = 'none';

            fetch('/api/transfers/top?period=' + period).then(res => res.json()).then(data => {
                let html = '';
                data.forEach((t, i) => { html += `<div style="padding:5px 0; border-bottom:1px solid var(--border);">#${i+1} <b>${t.sender}</b> перевел <b>${t.total}</b> ₽</div>`; });
                document.getElementById('transfer-top-list').innerHTML = html || '<div style="color:#888;">Нет переводов</div>';
            });

            fetch('/api/transfers/my').then(res => res.json()).then(data => {
                let html = '';
                data.forEach(t => {
                    let date = new Date(t.timestamp * 1000).toLocaleString();
                    html += `<div style="padding:5px 0; border-bottom:1px solid var(--border);">Вы -> <b>${t.receiver}</b> (${t.amount} ₽) <br><span style="font-size:10px; color:#888;">${date}</span></div>`;
                });
                document.getElementById('my-transfer-list').innerHTML = html || '<div style="color:#888;">Вы еще не переводили</div>';
            });
        }

        function redeemPromo() {
            let code = document.getElementById('promo-input').value;
            if(!code) return;
            fetch('/api/promo/redeem', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({code: code}) })
            .then(res => res.json()).then(data => {
                if(data.success) { showToast("Промокод активирован! +" + data.reward + " ₽", 'success'); document.getElementById('promo-input').value = ''; balance += data.reward; document.getElementById('score').innerText = Math.floor(balance) + ' ₽'; }
                else showToast(data.error, 'error');
            });
        }

        let currentReplyUser = "";
        let currentReplyText = "";

        function loadChat() {
            if(!isLoggedIn) return;
            fetch('/api/chat/get').then(res => res.json()).then(data => {
                let container = document.getElementById('chat-messages');
                let isScrolledToBottom = container.scrollHeight - container.clientHeight <= container.scrollTop + 50;
                let html = '';
                
                data.forEach(m => {
                    let time = new Date(m.timestamp * 1000).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                    let nameClass = m.color === 'rainbow' ? 'rainbow-text' : '';
                    let nameStyle = m.color !== 'rainbow' ? `color:${m.color}; font-weight:bold;` : '';
                    let badgeClass = m.badge_color === 'rainbow' ? 'rainbow-text' : '';
                    let badgeStyle = m.badge_color !== 'rainbow' ? `background:${m.badge_color}; color:#000;` : '';
                    let badgeHtml = m.badge ? `<span class="badge ${badgeClass}" style="${badgeStyle}">${m.badge}</span>` : '';

                    let replyHtml = '';
                    if(m.reply_user) {
                        replyHtml = `<div class="chat-reply-preview" style="display:block; border-left-color:var(--neon); margin-bottom:8px;">
                                        <b>${m.reply_user}</b><br>${m.reply_text}
                                     </div>`;
                    }

                    html += `<div class="chat-msg" onmousedown="startSwipe(event, '${m.username}', '${m.text.replace(/'/g, "\\'")}')" ontouchstart="startSwipe(event, '${m.username}', '${m.text.replace(/'/g, "\\'")}')">
                                ${replyHtml}
                                <span class="${nameClass}" style="${nameStyle}">${m.username}</span>
                                ${badgeHtml}
                                <span style="font-size:10px; color:#888; float:right;">${time}</span>
                                <br>${m.text}
                             </div>`;
                });
                container.innerHTML = html;
                if(isScrolledToBottom) container.scrollTop = container.scrollHeight;
            });
        }

        let startX = 0;
        function startSwipe(e, user, text) {
            startX = e.touches ? e.touches[0].clientX : e.clientX;
            let element = e.currentTarget;
            let endHandler = function(endEvent) {
                let endX = endEvent.changedTouches ? endEvent.changedTouches[0].clientX : endEvent.clientX;
                if (startX - endX > 50) {
                    setReply(user, text);
                }
                element.style.transform = "translateX(0)";
                element.removeEventListener('touchend', endHandler);
                element.removeEventListener('mouseup', endHandler);
            };
            element.addEventListener('touchend', endHandler);
            element.addEventListener('mouseup', endHandler);
        }

        function setReply(user, text) {
            currentReplyUser = user;
            currentReplyText = text;
            document.getElementById('reply-text-preview').innerText = "Ответ: " + user;
            document.getElementById('reply-message-preview').innerText = text;
            document.getElementById('chat-reply-bar').style.display = 'block';
            document.getElementById('chat-input').focus();
        }

        function cancelReply() {
            currentReplyUser = "";
            currentReplyText = "";
            document.getElementById('chat-reply-bar').style.display = 'none';
        }

        function sendChat() {
            let inp = document.getElementById('chat-input');
            if(!inp.value.trim()) return;
            fetch('/api/chat/send', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text: inp.value, reply_user: currentReplyUser, reply_text: currentReplyText}) })
            .then(res => res.json()).then(data => {
                if(data.success) { inp.value = ''; cancelReply(); loadChat(); }
                else showToast(data.error, 'error');
            });
        }

        function handleChatEnter(e) { if(e.key === 'Enter') sendChat(); }

        function checkMuteStatus() {
            let now = Math.floor(Date.now() / 1000);
            let muteTimeLeft = muteUntil - now;
            
            let inputArea = document.getElementById('chat-input-area');
            let muteStatus = document.getElementById('chat-mute-status');
            
            if(muteTimeLeft > 0) {
                inputArea.style.display = 'none';
                muteStatus.style.display = 'block';
                
                let m = Math.floor(muteTimeLeft / 60);
                let s = muteTimeLeft % 60;
                document.getElementById('mute-timer').innerText = (m > 0 ? m + "м " : "") + s + "с";
            } else {
                inputArea.style.display = 'flex';
                muteStatus.style.display = 'none';
            }
        }
        setInterval(checkMuteStatus, 1000);

        window.onload = () => {
            if(isLoggedIn) { setInterval(loadChat, 3000); loadChat(); checkMuteStatus(); }
        };
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    user = None; remaining_seconds = 0
    if 'user_id' in session:
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user: session.pop('user_id', None)
        elif user['is_banned']:
            if time.time() >= user['ban_until']:
                with get_db() as conn:
                    conn.execute('UPDATE users SET is_banned=0, ban_reason="", ban_msg="", ban_until=0, ban_duration="" WHERE id = ?', (user['id'],))
                    conn.commit()
                user = dict(user); user['is_banned'] = 0
            else: remaining_seconds = int(user['ban_until'] - time.time())
            
    multi_price = 50 * (2 ** (user['click_power'] - 1)) if user and not user['is_banned'] else 50
    auto_price = 200 * (3 ** user['auto_income']) if user and not user['is_banned'] else 200
    return render_template_string(HTML_CODE, user=user, multi_price=int(multi_price), auto_price=int(auto_price), remaining_seconds=remaining_seconds)

@app.route('/api/user')
def api_user():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    with get_db() as conn:
        user = conn.execute('SELECT balance, click_power, auto_income, is_banned, mute_until FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user: return jsonify({'error': 'No user'}), 401
        if user['is_banned']: return jsonify({'error': 'Banned'}), 403
        return jsonify({'success': True, 'balance': user['balance'], 'click_power': user['click_power'], 'auto_income': user['auto_income'], 'mute_until': user['mute_until']})

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    u, p = data['username'], data['password']
    if re.search('[а-яА-ЯёЁ]', u) or re.search('[а-яА-ЯёЁ]', p):
        return jsonify({'error': 'Cyrillic'}), 400
    with get_db() as conn:
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (u, generate_password_hash(p)))
            conn.commit(); user = conn.execute('SELECT * FROM users WHERE username = ?', (u,)).fetchone()
            session.permanent = True; session['user_id'] = user['id']; return jsonify({'success': True}), 200
        except sqlite3.IntegrityError: return jsonify({'error': 'Taken'}), 400

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    with get_db() as conn:
        user = conn.execute('SELECT * FROM users WHERE username = ?', (data['username'],)).fetchone()
        if user and check_password_hash(user['password'], data['password']):
            if user['is_banned']:
                if time.time() >= user['ban_until']:
                    conn.execute('UPDATE users SET is_banned=0, ban_reason="", ban_msg="", ban_until=0, ban_duration="" WHERE id = ?', (user['id'],))
                    conn.commit()
                else: return jsonify({'banned': True}), 403
            session.permanent = True; session['user_id'] = user['id']; return jsonify({'success': True}), 200
    return jsonify({'error': 'Bad auth'}), 401

@app.route('/logout')
def logout():
    session.pop('user_id', None); return redirect(url_for('index'))

@app.route('/api/click', methods=['POST'])
def api_click():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    with get_db() as conn:
        user = conn.execute('SELECT is_banned FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user: return jsonify({'error': 'No user'}), 401
        if user['is_banned']:
            conn.execute('DELETE FROM users WHERE id = ?', (session['user_id'],)); conn.commit()
            session.pop('user_id', None); return jsonify({'error': 'banned_deleted'}), 403
        conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (request.json.get('amount', 1), session['user_id']))
        conn.commit()
    return jsonify({'success': True})

@app.route('/api/buy', methods=['POST'])
def api_buy():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    type = request.json.get('type')
    with get_db() as conn:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if type == 'multi':
            price = 50 * (2 ** (user['click_power'] - 1))
            if user['balance'] >= price:
                conn.execute('UPDATE users SET balance = balance - ?, click_power = click_power * 2 WHERE id = ?', (price, user['id'])); conn.commit(); return jsonify({'success': True})
        elif type == 'auto':
            price = 200 * (3 ** user['auto_income'])
            if user['balance'] >= price:
                conn.execute('UPDATE users SET balance = balance - ?, auto_income = auto_income + 1 WHERE id = ?', (price, user['id'])); conn.commit(); return jsonify({'success': True})
    return jsonify({'error': 'No money'}), 400

@app.route('/api/buy_custom', methods=['POST'])
def api_buy_custom():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    data = request.json
    with get_db() as conn:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if user['balance'] >= data['price']:
            if data['type'] == 'color': conn.execute('UPDATE users SET balance = balance - ?, color = ? WHERE id = ?', (data['price'], data['value'], user['id']))
            elif data['type'] == 'badge': conn.execute('UPDATE users SET balance = balance - ?, badge = ?, badge_color = ? WHERE id = ?', (data['price'], data['value'], '#00ffcc', user['id']))
            conn.commit(); return jsonify({'success': True})
    return jsonify({'error': 'No money'}), 400

@app.route('/api/top')
def api_top():
    with get_db() as conn:
        users = conn.execute('SELECT username, balance, color, badge, badge_color, is_banned FROM users ORDER BY balance DESC LIMIT 10').fetchall()
        return jsonify([dict(u) for u in users])

@app.route('/api/ban_info/<username>')
def api_ban_info(username):
    with get_db() as conn:
        user = conn.execute('SELECT username, ban_reason, ban_msg, ban_until, ban_duration FROM users WHERE username = ? AND is_banned = 1', (username,)).fetchone()
        if user: return jsonify({'success': True, **dict(user), 'remaining': max(0, int(user['ban_until'] - time.time()))})
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/settings', methods=['POST'])
def api_settings():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    with get_db() as conn:
        conn.execute(f'UPDATE users SET {request.json["key"]} = ? WHERE id = ?', (request.json['value'], session['user_id'])); conn.commit()
    return jsonify({'success': True})

@app.route('/api/reset', methods=['POST'])
def api_reset():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    with get_db() as conn:
        conn.execute('UPDATE users SET balance=0, click_power=1, auto_income=0, color="#ffffff", badge="", badge_color="#ffffff" WHERE id = ?', (session['user_id'],)); conn.commit()
    return jsonify({'success': True})

@app.route('/api/transfer', methods=['POST'])
def api_transfer():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    data = request.json; amount = data['amount']; receiver = data['receiver']
    if amount <= 0: return jsonify({'error': 'Неверная сумма'}), 400
    with get_db() as conn:
        sender = conn.execute('SELECT username, balance FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        target = conn.execute('SELECT username FROM users WHERE username = ?', (receiver,)).fetchone()
        if not target: return jsonify({'error': 'Игрок не найден'}), 404
        if sender['username'] == receiver: return jsonify({'error': 'Себе нельзя'}), 400
        if sender['balance'] < amount: return jsonify({'error': 'Мало денег'}), 400
        
        conn.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (amount, session['user_id']))
        conn.execute('UPDATE users SET balance = balance + ? WHERE username = ?', (amount, receiver))
        conn.execute('INSERT INTO transfers (sender, receiver, amount, timestamp) VALUES (?, ?, ?, ?)', (sender['username'], receiver, amount, time.time()))
        conn.commit()
    return jsonify({'success': True})

@app.route('/api/transfers/top')
def api_transfers_top():
    period = request.args.get('period', 'all'); now = time.time()
    start = now - 86400 if period == 'day' else (now - 2592000 if period == 'month' else 0)
    with get_db() as conn:
        rows = conn.execute('SELECT sender, SUM(amount) as total FROM transfers WHERE timestamp >= ? GROUP BY sender ORDER BY total DESC LIMIT 10', (start,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/transfers/my')
def api_transfers_my():
    if 'user_id' not in session: return jsonify([])
    with get_db() as conn:
        user = conn.execute('SELECT username FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        rows = conn.execute('SELECT receiver, amount, timestamp FROM transfers WHERE sender = ? ORDER BY timestamp DESC LIMIT 20', (user['username'],)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/chat/get')
def api_chat_get():
    with get_db() as conn:
        msgs = conn.execute('''
            SELECT c.*, u.color, u.badge, u.badge_color 
            FROM chat_messages c 
            JOIN users u ON c.username = u.username 
            ORDER BY c.timestamp DESC LIMIT 50
        ''').fetchall()
    return jsonify([dict(m) for m in reversed(msgs)])

@app.route('/api/chat/send', methods=['POST'])
def api_chat_send():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    data = request.json; text = data.get('text', '').strip()
    reply_user = data.get('reply_user', '')
    reply_text = data.get('reply_text', '')

    if not text: return jsonify({'error': 'Пустое'}), 400
    with get_db() as conn:
        user = conn.execute('SELECT username, mute_until FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if user['mute_until'] > time.time(): return jsonify({'error': 'Вы заглушены!'}), 403
        
        conn.execute('INSERT INTO chat_messages (username, text, timestamp, reply_user, reply_text) VALUES (?, ?, ?, ?, ?)', 
                     (user['username'], text[:100], time.time(), reply_user, reply_text[:50]))
        conn.commit()
    return jsonify({'success': True})

@app.route('/api/promo/redeem', methods=['POST'])
def api_promo_redeem():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    code = request.json.get('code', '').strip()
    with get_db() as conn:
        promo = conn.execute('SELECT * FROM promocodes WHERE code = ?', (code,)).fetchone()
        if not promo or promo['uses_left'] <= 0: return jsonify({'error': 'Недействительный код'}), 400
        conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (promo['reward'], session['user_id']))
        conn.execute('UPDATE promocodes SET uses_left = uses_left - 1 WHERE code = ?', (code,))
        conn.commit()
        return jsonify({'success': True, 'reward': promo['reward']})

# ФИКС ДЛЯ ХОСТИНГА (порт 8080)
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, use_reloader=False)

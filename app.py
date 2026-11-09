from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
import time
import re
import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'mog_secret_key_123')
app.permanent_session_lifetime = 86400 * 30

db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print("⚠️ ВНИМАНИЕ! DATABASE_URL НЕ НАЙДЕНА! БАЗА БУДЕТ СЛЕТАТЬ!")
    db_url = 'sqlite:///mogclicker.db'
else:
    print("✅ ПОДКЛЮЧЕНИЕ К POSTGRESQL УСПЕШНО!")

if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
if "postgresql://" in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if "sslmode" not in db_url: db_url += "?sslmode=disable"

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- МОДЕЛИ ---
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    mog_coins = db.Column(db.Float, default=0.0)
    click_power = db.Column(db.Integer, default=1)
    auto_income = db.Column(db.Float, default=0.0)
    color = db.Column(db.String(50), default='#ffffff')
    badge = db.Column(db.String(50), default='')
    badge_color = db.Column(db.String(50), default='#ffffff')
    badge_expire = db.Column(db.Float, default=0.0)
    theme = db.Column(db.String(50), default='dark')
    lang = db.Column(db.String(10), default='ru')
    zoom = db.Column(db.Integer, default=100)
    font_family = db.Column(db.String(50), default='Montserrat')
    is_banned = db.Column(db.Integer, default=0)
    ban_reason = db.Column(db.String(200), default='')
    ban_msg = db.Column(db.String(200), default='')
    ban_until = db.Column(db.Float, default=0.0)
    ban_duration = db.Column(db.String(50), default='')
    mute_until = db.Column(db.Float, default=0.0)
    clan_id = db.Column(db.Integer, db.ForeignKey('clans.id'), nullable=True)
    clan_role = db.Column(db.String(20), default='')

class Clan(db.Model):
    __tablename__ = 'clans'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    leader = db.Column(db.String(80), nullable=False)
    is_open = db.Column(db.Boolean, default=True)

class Transfer(db.Model):
    __tablename__ = 'transfers'
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(80))
    receiver = db.Column(db.String(80))
    amount = db.Column(db.Float)
    timestamp = db.Column(db.Float)

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80))
    text = db.Column(db.String(200))
    timestamp = db.Column(db.Float)
    reply_user = db.Column(db.String(80), default='')
    reply_text = db.Column(db.String(100), default='')

class Promocode(db.Model):
    __tablename__ = 'promocodes'
    code = db.Column(db.String(50), primary_key=True)
    type = db.Column(db.String(20))
    value = db.Column(db.String(50))
    uses_left = db.Column(db.Integer)

with app.app_context():
    db.create_all()

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
        * { -webkit-tap-highlight-color: transparent; box-sizing: border-box; }
        :root { --bg: #121212; --panel: #1e1e1e; --text: #ffffff; --neon: #00ffcc; --gold: #ffd700; --border: #333; }
        body.theme-light { --bg: #f0f0f0; --panel: #ffffff; --text: #121212; --neon: #0077ff; --border: #ccc; }
        body.theme-neon { --bg: #0a001a; --panel: #1a0033; --text: #ffffff; --neon: #ff00ff; --border: #ff00ff; }
        body.theme-cyber { --bg: #000000; --panel: #111111; --text: #ffff00; --neon: #ff003c; --border: #ff003c; }
        body.theme-ocean { --bg: #001220; --panel: #003366; --text: #e0f7fa; --neon: #00e5ff; --border: #00e5ff; }
        body.theme-retro { --bg: #1a1a1a; --panel: #2a2a2a; --text: #00ff00; --neon: #00ff00; --border: #00ff00; }
        body { background: var(--bg); color: var(--text); font-family: '{{ user.font_family if user else "Montserrat" }}', sans-serif; margin: 0; padding: 10px; user-select: none; text-align: center; overflow-x: hidden; min-height: 100vh; display: flex; flex-direction: column; align-items: center; transition: background 0.3s, color 0.3s; }
        
        .view { display: none; background: var(--panel); padding: 20px; border-radius: 20px; border: 1px solid var(--border); min-height: 400px; width: 100%; max-width: 400px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); opacity: 0; transform: translateY(20px) scale(0.98); transition: opacity 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275), transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
        .view.active { display: block; opacity: 1; transform: translateY(0) scale(1); }

        #auth-wrapper { display: flex; justify-content: center; align-items: center; min-height: 100vh; width: 100%; }
        .glass-card { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(15px); -webkit-backdrop-filter: blur(15px); border: 1px solid rgba(255, 255, 255, 0.1); padding: 30px 20px; border-radius: 25px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37); width: 100%; max-width: 400px; }
        
        .auth-tabs { display: flex; gap: 10px; margin-bottom: 20px; }
        .auth-tab { flex: 1; padding: 10px; background: var(--border); color: var(--text); border: none; border-radius: 10px; cursor: pointer; transition: 0.3s; font-weight: bold; }
        .auth-tab.active { background: var(--neon); color: #000; box-shadow: 0 0 10px var(--neon); }
        .auth-form { display: none; }
        .auth-form.active { display: block; animation: fadeIn 0.3s; }

        input[type="text"], input[type="password"], input[type="number"] { width: 100%; padding: 15px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.2); color: var(--text); border-radius: 15px; margin-bottom: 15px; outline: none; font-size: 16px; transition: 0.3s; }
        input:focus { border-color: var(--neon); box-shadow: 0 0 15px var(--neon); background: rgba(0,0,0,0.5); }
        
        .btn-main { background: var(--neon); color: #000; padding: 15px; border: none; border-radius: 15px; cursor: pointer; font-weight: bold; font-size: 16px; width: 100%; margin-bottom: 15px; transition: 0.3s; box-shadow: 0 0 15px transparent; }
        .btn-main:hover { filter: brightness(1.2); box-shadow: 0 0 15px var(--neon); transform: translateY(-2px); }
        .btn-main:active { transform: translateY(1px); }
        .btn-danger { background: #ff4444; color: white; }
        .btn-gold { background: var(--gold); box-shadow: 0 0 15px transparent; }
        .btn-gold:hover { box-shadow: 0 0 15px var(--gold); }
        .btn-disabled { background: #444 !important; color: #888 !important; cursor: not-allowed !important; box-shadow: none !important; transform: none !important; }

        .nav-btn { background: var(--panel); border: 1px solid var(--border); color: var(--text); padding: 8px 12px; border-radius: 8px; cursor: pointer; font-weight: bold; transition: 0.2s; font-size: 14px; }
        .nav-btn.active { border-color: var(--neon); color: var(--neon); box-shadow: 0 0 10px var(--neon); }

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
        
        /* ИСПРАВЛЕННЫЙ БЕЙДЖИК (ТАБЛЕТКА) */
        .badge { 
            padding: 4px 10px; border-radius: 12px; font-size: 12px; margin-left: 5px; font-weight: bold; 
            display: inline-block; text-shadow: none; cursor: help; transition: 0.2s; 
            background: rgba(255,255,255,0.1); border: 1px solid var(--border); 
        }
        .badge:hover { transform: scale(1.1); border-color: var(--neon); }
        .hammer { margin-left: 5px; font-size: 14px; cursor: pointer; filter: drop-shadow(0 0 5px #ff0000); transition: 0.2s; }
        .hammer:hover { transform: scale(1.3); }
        
        .rainbow-text { background: linear-gradient(90deg, #ff0000, #ff7f00, #ffff00, #00ff00, #0000ff, #4b0082, #8f00ff, #ff0000); background-size: 200% auto; -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: bold; animation: rainbowAnim 3s linear infinite; }
        @keyframes rainbowAnim { to { background-position: 200% center; } }

        #toast-container { position: fixed; top: 20px; left: 50%; transform: translateX(-50%); z-index: 1000; display: flex; flex-direction: column; gap: 10px; width: 80%; max-width: 300px; }
        .toast { background: var(--panel); color: var(--text); padding: 15px; border-radius: 10px; border-left: 5px solid var(--neon); box-shadow: 0 5px 15px rgba(0,0,0,0.5); animation: slideDown 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards, fadeOut 0.3s 2.7s forwards; font-weight: bold; text-align: left; }
        .toast.error { border-left-color: #ff4444; }
        @keyframes slideDown { from { transform: translateY(-30px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        @keyframes fadeOut { to { opacity: 0; transform: translateY(-20px); } }
        
        .setting-item { display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.2); padding: 15px; margin-bottom: 10px; border-radius: 10px; border: 1px solid var(--border); cursor: pointer; transition: 0.2s; }
        .setting-item:hover { border-color: var(--neon); }
        input[type="range"] { width: 100%; accent-color: var(--neon); height: 20px; margin-top: 10px; }
        
        .modal { display: flex; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 9999; justify-content: center; align-items: center; backdrop-filter: blur(5px); opacity: 0; visibility: hidden; transition: opacity 0.3s ease, visibility 0.3s ease; }
        .modal.active { opacity: 1; visibility: visible; }
        .modal-content { background: #1a1a1a; border: 2px solid var(--neon); padding: 25px; border-radius: 15px; max-width: 90%; width: 350px; text-align: left; box-shadow: 0 0 30px rgba(0,255,204,0.2); position: relative; transform: scale(0.7) translateY(50px); transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); max-height: 80vh; overflow-y: auto; }
        .modal.active .modal-content { transform: scale(1) translateY(0); }
        .modal-title { color: var(--neon); font-size: 22px; font-weight: bold; text-align: center; margin-bottom: 20px; text-shadow: 0 0 10px var(--neon); }
        .close-btn { position: absolute; top: 10px; right: 15px; font-size: 24px; cursor: pointer; color: #ff4444; transition: 0.2s; }
        .close-btn:hover { transform: scale(1.2) rotate(90deg); text-shadow: 0 0 10px #ff4444; }
        
        .custom-option { padding: 15px; border-bottom: 1px solid var(--border); cursor: pointer; transition: 0.2s; border-radius: 8px; margin-bottom: 5px; font-size: 16px; }
        .custom-option:hover { background: rgba(255,255,255,0.1); color: var(--neon); padding-left: 20px; }

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
        
        .clan-card { background: rgba(0,0,0,0.3); border: 1px solid var(--border); border-radius: 10px; padding: 15px; margin-bottom: 10px; }
        .clan-card h4 { margin: 0 0 10px 0; color: var(--gold); }
        .member-list { margin-top: 10px; max-height: 200px; overflow-y: auto; text-align: left; }
        .member-item { display: flex; justify-content: space-between; padding: 8px; border-bottom: 1px solid var(--border); font-size: 14px; }
    </style>
</head>
<body class="theme-{{ user.theme if user else 'dark' }}" style="zoom: {{ user.zoom if user else 100 }}%; font-family: '{{ user.font_family if user else 'Montserrat' }}', sans-serif;">
    <div id="toast-container"></div>

    {% if user and user.is_banned %}
        <div class="modal active" style="display:flex;">
            <div class="modal-content" style="border-color: #ff4444;">
                <div class="modal-title" style="color: #ff4444;">!ВЫ ЗАБАНЕНЫ!</div>
                <div class="info-label">ПРИЧИНА:</div><div class="info-value" style="color: #ff4444;">{{ user.ban_reason }}</div>
                <div class="info-label">СООБЩЕНИЕ:</div><div class="info-value" style="color: #aaa; font-size: 13px;">{{ user.ban_msg }}</div>
                <div class="info-label">ЗАБАНЕН НА:</div><div class="info-value">{{ user.ban_duration }}</div>
                <div class="info-label">ОСТАЛОСЬ:</div><div class="info-value" id="ban-timer" style="color: #ff4444; font-weight: bold; font-size: 18px;"></div>
                <a href="/logout" class="btn-main btn-danger" style="display: block; text-decoration: none; margin-top: 20px;">Выйти</a>
            </div>
        </div>
        <script>
            let remaining = {{ remaining_seconds }};
            function updateTimer() {
                if(remaining <= 0) { window.location.reload(); return; }
                let d = Math.floor(remaining / 86400); let h = Math.floor((remaining % 86400) / 3600);
                let m = Math.floor((remaining % 3600) / 60); let s = remaining % 60;
                let text = ""; if(d > 0) text += d + "д "; if(h > 0) text += h + "ч ";
                text += m + "м " + s + "с"; document.getElementById('ban-timer').innerText = text;
                remaining--; setTimeout(updateTimer, 1000);
            }
            updateTimer();
        </script>

    {% elif not user %}
        <div id="auth-wrapper">
            <div class="glass-card">
                <h1 style="color: var(--neon); text-shadow: 0 0 10px var(--neon);">MOGCLICKER</h1>
                <div class="auth-tabs">
                    <button class="auth-tab active" onclick="switchAuth('login')">Вход</button>
                    <button class="auth-tab" onclick="switchAuth('reg')">Регистрация</button>
                </div>
                <div id="form-login" class="auth-form active">
                    <input type="text" id="l-username" placeholder="Логин">
                    <input type="password" id="l-password" placeholder="Пароль">
                    <button class="btn-main" onclick="doAuth('login')">Войти</button>
                </div>
                <div id="form-reg" class="auth-form">
                    <input type="text" id="r-username" placeholder="Логин (только англ.)">
                    <input type="password" id="r-password" placeholder="Пароль">
                    <button class="btn-main btn-gold" onclick="doAuth('register')">Создать аккаунт</button>
                </div>
            </div>
        </div>
    
    {% else %}
        <h1>MOGCLICKER</h1>
        <div style="font-size: 16px; margin-bottom: 15px; display: flex; justify-content: center; align-items: center; gap: 5px; flex-wrap: wrap;">
            <span>Привет</span>, 
            <span id="current-username" class="{% if user.color == 'rainbow' %}rainbow-text{% endif %}" style="color: {{ user.color if user.color != 'rainbow' else '' }}; font-weight: bold;">{{ user.username }}</span>
            {% if user.badge %}
                <span class="badge {% if user.badge_color == 'rainbow' %}rainbow-text{% endif %}" id="current-badge" style="{% if user.badge_color != 'rainbow' %}background: {{ user.badge_color }}; color: #000; border-color: {{ user.badge_color }};{% endif %}" onclick="showToast('Этот бейдж коллекционный!', 'success')">{{ user.badge }}</span>
            {% endif %}
            | <span style="color: var(--neon);">{{ user.mog_coins|int }} 💎</span>
            | <a href="/logout" style="color: #ff4444; text-decoration: none; font-weight: bold;">Выйти</a>
        </div>

        <div class="nav" style="display: flex; justify-content: center; gap: 5px; margin-bottom: 15px; flex-wrap: wrap; width: 100%; max-width: 400px;">
            <button onclick="switchTab('game')" id="tab-game" class="nav-btn active">Игра</button>
            <button onclick="switchTab('shop')" id="tab-shop" class="nav-btn">Магазин</button>
            <button onclick="switchTab('transfer')" id="tab-transfer" class="nav-btn">Переводы</button>
            <button onclick="switchTab('clan')" id="tab-clan" class="nav-btn">Союзы</button>
            <button onclick="switchTab('top')" id="tab-top" class="nav-btn">Топ</button>
            <button onclick="switchTab('settings')" id="tab-settings" class="nav-btn">Настройки</button>
        </div>

        <div id="view-game" class="view active">
            <div id="score">{{ user.balance|int }} ₽</div>
            <div id="coin" onclick="clickCoin(event)">₽</div>
            <div>Сила: <span id="ui-click-power">{{ user.click_power }}</span> | Доход: <span id="ui-auto-income">{{ user.auto_income }}</span>/с</div>
        </div>

        <div id="view-shop" class="view">
            <h3>Улучшения</h3>
            <div class="shop-item"><div>Мультиклик (x2)</div><button onclick="buyUpgrade('multi')">{{ multi_price }} ₽</button></div>
            <div class="shop-item"><div>Автокликер (+1/с)</div><button onclick="buyUpgrade('auto')">{{ auto_price }} ₽</button></div>
            
            <h3>Кастомизация</h3>
            <div class="shop-item"><div>Бейдж "MOG" <br><small style="color: #888; font-size: 10px;">(14 дней)</small></div><button onclick="buyCustom('badge', 'MOG', 5000)">5,000 ₽</button></div>

            <h3>Донат-валюта (💎)</h3>
            <div class="shop-item" style="opacity: 0.7;"><div>100 💎<br><small style="color: #ff4444;">(Скоро)</small></div><button class="btn-disabled">Купить</button></div>
        </div>

        <div id="view-transfer" class="view">
            <h3>Переводы</h3>
            <input type="text" id="tr-nick" placeholder="Ник получателя">
            <input type="number" id="tr-amount" placeholder="Сумма">
            <button class="btn-main" onclick="doTransfer()">Перевести</button>
            <div style="display:flex; gap:5px; margin-bottom: 10px;">
                <button class="nav-btn active" onclick="loadTransfers('day', this)">День</button>
                <button class="nav-btn" onclick="loadTransfers('month', this)">Месяц</button>
                <button class="nav-btn" onclick="loadTransfers('all', this)">Всегда</button>
            </div>
            <h4 style="text-align:left;">Топ переводчиков:</h4><div id="transfer-top-list" style="text-align:left; font-size:14px; margin-bottom:20px; max-height:150px; overflow-y:auto;"></div>
            <h4 style="text-align:left;">Ваши переводы:</h4><div id="my-transfer-list" style="text-align:left; font-size:14px; max-height:150px; overflow-y:auto;"></div>
        </div>

        <div id="view-clan" class="view">
            <h3>Союзы (Кланы)</h3>
            <div id="clan-content">
                {% if user.clan_id %}
                    <div id="my-clan-info">
                        <div class="clan-card"><h4 id="c-name">Название</h4><p>Ваша роль: <span id="c-role" style="color:var(--gold); font-weight:bold;"></span></p><button class="btn-main btn-danger" onclick="leaveClan()">Покинуть союз</button></div>
                        <h4>Участники:</h4><div id="clan-members" class="member-list"></div>
                        <div id="clan-admin-controls" style="display:none; margin-top: 15px;">
                            <h4>Управление (Лидер):</h4>
                            <input type="text" id="clan-target" placeholder="Ник участника">
                            <button class="btn-main" onclick="clanAction('promote')">Назначить Админом</button>
                            <button class="btn-main" onclick="clanAction('transfer')">Передать Лидерство</button>
                            <button class="btn-main btn-danger" onclick="clanAction('kick')">Кикнуть</button>
                            <button class="btn-main btn-danger" onclick="deleteClan()">Удалить Союз</button>
                        </div>
                    </div>
                {% else %}
                    <div id="no-clan-info">
                        <button class="btn-main" onclick="openModal('create-clan-modal')">Создать Союз</button>
                        <input type="text" id="search-clan" placeholder="Поиск союза...">
                        <button class="btn-main" onclick="searchClans()">Найти</button>
                        <div id="clan-search-results" style="text-align:left; margin-top:15px;"></div>
                    </div>
                {% endif %}
            </div>
        </div>

        <div id="view-top" class="view"><h3>Топ игроков</h3><div id="top-list">Загрузка...</div></div>

        <div id="view-settings" class="view">
            <h3>Настройки</h3>
            <div class="setting-item" onclick="openModal('lang-modal')"><span>Язык</span><span id="display-lang">Русский</span></div>
            <div class="setting-item" onclick="openModal('theme-modal')"><span>Тема</span><span id="display-theme">Тёмная</span></div>
            <div class="setting-item" onclick="openModal('font-modal')"><span>Шрифт</span><span id="display-font">{{ user.font_family }}</span></div>
            <div class="setting-item" style="flex-direction: column; align-items: flex-start;">
                <div style="display:flex; justify-content:space-between; width:100%;"><span>Масштаб UI</span><span id="zoom-val">{{ user.zoom }}%</span></div>
                <input type="range" id="set-zoom" min="50" max="150" step="10" value="{{ user.zoom }}" oninput="updateZoom(this.value)">
            </div>
            <h4 style="text-align:left; margin-top:20px;">Промокод</h4>
            <div style="display:flex; gap:10px;"><input type="text" id="promo-input" placeholder="Введите код..." style="margin-bottom:0;"><button class="btn-main" onclick="redeemPromo()" style="width:100px; margin-bottom:0;">Ввод</button></div>
            <div class="setting-item" style="background: rgba(255,0,0,0.1); border-color: #ff4444; flex-direction: column; margin-top:20px;">
                <p style="font-size: 12px; margin-bottom: 10px;">Опасная зона!</p><button class="btn-main btn-danger" onclick="resetProgress()" style="width:100%;">Сбросить прогресс</button>
            </div>
        </div>

        <div id="chat-container">
            <div id="chat-messages"></div>
            <div id="chat-mute-status" style="display:none;">Вы заглушены на <span id="mute-timer">0с</span></div>
            <div id="chat-input-area">
                <div id="chat-reply-bar"><span id="reply-text-preview" style="color:var(--gold); font-weight:bold;"></span><br><span id="reply-message-preview" style="color:#aaa; font-size:11px;"></span><span class="close-reply" onclick="cancelReply()">×</span></div>
                <div class="chat-input-row">
                    <input type="text" id="chat-input" placeholder="Сообщение в чат..." onkeypress="handleChatEnter(event)">
                    <button id="chat-send" class="btn-main" onclick="sendChat()" style="padding:0;">➤</button>
                </div>
            </div>
        </div>
    {% endif %}

    <div class="modal" id="create-clan-modal">
        <div class="modal-content">
            <span class="close-btn" onclick="closeModal('create-clan-modal')">×</span>
            <div class="modal-title">Создать Союз</div>
            <input type="text" id="new-clan-name" placeholder="Название союза">
            <div style="margin-bottom:15px; display:flex; align-items:center; gap:10px;">
                <input type="checkbox" id="new-clan-open" style="width:20px; height:20px; margin:0;" checked> 
                <label for="new-clan-open">Открытый для вступления</label>
            </div>
            <button class="btn-main" onclick="createClan()">Создать (1000 ₽)</button>
        </div>
    </div>
    <div class="modal" id="lang-modal"><div class="modal-content"><span class="close-btn" onclick="closeModal('lang-modal')">×</span><div class="modal-title">Язык</div><div class="custom-option" onclick="changeSetting('lang', 'ru')">Русский</div><div class="custom-option" onclick="changeSetting('lang', 'en')">English</div></div></div>
    <div class="modal" id="theme-modal"><div class="modal-content"><span class="close-btn" onclick="closeModal('theme-modal')">×</span><div class="modal-title">Тема</div><div class="custom-option" onclick="changeSetting('theme', 'dark')">Тёмная</div><div class="custom-option" onclick="changeSetting('theme', 'light')">Светлая</div><div class="custom-option" onclick="changeSetting('theme', 'neon')">Неон</div><div class="custom-option" onclick="changeSetting('theme', 'cyber')">Киберпанк</div><div class="custom-option" onclick="changeSetting('theme', 'ocean')">Океан</div><div class="custom-option" onclick="changeSetting('theme', 'retro')">Ретро</div></div></div>
    <div class="modal" id="font-modal"><div class="modal-content"><span class="close-btn" onclick="closeModal('font-modal')">×</span><div class="modal-title">Шрифт</div><div class="custom-option" onclick="changeSetting('font_family', 'Montserrat')" style="font-family:'Montserrat'">Montserrat</div><div class="custom-option" onclick="changeSetting('font_family', 'Play')" style="font-family:'Play'">Play</div><div class="custom-option" onclick="changeSetting('font_family', 'Russo One')" style="font-family:'Russo One'">Russo One</div><div class="custom-option" onclick="changeSetting('font_family', 'Comic Neue')" style="font-family:'Comic Neue'">Comic Neue</div></div></div>
    <div class="modal" id="other-ban-modal"><div class="modal-content" style="border-color: #ff4444;"><span class="close-btn" onclick="closeOtherBan()">×</span><div class="modal-title" style="color:#ff4444;">ЗАБАНЕН</div><div class="info-label">НИК:</div><div class="info-value" id="other-ban-nick"></div><div class="info-label">ПРИЧИНА:</div><div class="info-value" id="other-ban-reason" style="color:#ff4444;"></div><div class="info-label">ДО:</div><div class="info-value" id="other-ban-until" style="color:#ff4444; font-weight:bold;"></div></div></div>

    <script>
        const isLoggedIn = {{ 'true' if user and not user.is_banned else 'false' }};
        const currentUserClanId = {{ user.clan_id if user and user.clan_id else 'null' }};
        let currentLang = "{{ user.lang if user else 'ru' }}";
        let currentTheme = "{{ user.theme if user else 'dark' }}";
        let currentZoom = parseInt("{{ user.zoom if user else 100 }}");
        
        // Защита от NaN (пустых полей из БД)
        let balance = parseFloat("{{ user.balance|default(0, true) }}");
        let clickPower = parseInt("{{ user.click_power|default(1, true) }}");
        let autoIncome = parseFloat("{{ user.auto_income|default(0, true) }}");
        let muteUntil = parseFloat("{{ user.mute_until|default(0, true) }}");

        function openModal(id) { document.getElementById(id).classList.add('active'); }
        function closeModal(id) { document.getElementById(id).classList.remove('active'); }

        let audioCtx = null;
        function initAudio() { 
            try {
                if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)(); 
                if (audioCtx.state === 'suspended') audioCtx.resume(); 
            } catch(e) {}
        }
        document.body.addEventListener('click', initAudio, { once: true });
        document.body.addEventListener('touchstart', initAudio, { once: true });

        function playSound(type) {
            if (!audioCtx) return;
            try {
                const osc = audioCtx.createOscillator(); const gain = audioCtx.createGain();
                if(type === 'click') { osc.type = 'sine'; osc.frequency.setValueAtTime(800, audioCtx.currentTime); osc.frequency.exponentialRampToValueAtTime(1200, audioCtx.currentTime + 0.05); gain.gain.setValueAtTime(0.1, audioCtx.currentTime); }
                else if(type === 'error') { osc.type = 'sawtooth'; osc.frequency.setValueAtTime(150, audioCtx.currentTime); gain.gain.setValueAtTime(0.1, audioCtx.currentTime); }
                else if(type === 'success') { osc.type = 'triangle'; osc.frequency.setValueAtTime(400, audioCtx.currentTime); osc.frequency.exponentialRampToValueAtTime(800, audioCtx.currentTime + 0.1); gain.gain.setValueAtTime(0.1, audioCtx.currentTime); }
                gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.2);
                osc.connect(gain); gain.connect(audioCtx.destination); osc.start(); osc.stop(audioCtx.currentTime + 0.2);
            } catch(e) {}
        }

        function showToast(text, type = 'success') {
            playSound(type); const container = document.getElementById('toast-container'); const toast = document.createElement('div');
            toast.className = `toast ${type}`; toast.innerText = text; container.appendChild(toast); setTimeout(() => toast.remove(), 3000);
        }

        function switchAuth(tab) {
            document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.auth-form').forEach(f => f.classList.remove('active'));
            if(tab === 'login') { document.querySelectorAll('.auth-tab')[0].classList.add('active'); document.getElementById('form-login').classList.add('active'); } 
            else { document.querySelectorAll('.auth-tab')[1].classList.add('active'); document.getElementById('form-reg').classList.add('active'); }
        }

        function doAuth(action) {
            let u = action === 'login' ? document.getElementById('l-username').value : document.getElementById('r-username').value;
            let p = action === 'login' ? document.getElementById('l-password').value : document.getElementById('r-password').value;
            if(/[а-яА-ЯёЁ]/.test(u) || /[а-яА-ЯёЁ]/.test(p)) return showToast("Только английские буквы!", 'error');
            fetch('/' + action, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username: u, password: p}) })
            .then(res => res.json().then(data => ({status: res.status, data}))).then(res => {
                if(res.status === 200 && res.data.success) window.location.reload();
                else if (res.status === 403 && res.data.banned) window.location.reload(); 
                else showToast(action === 'login' ? "Неверный логин или пароль!" : "Логин занят!", 'error');
            });
        }

        function switchTab(tab) {
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            document.querySelectorAll('.nav-btn').forEach(b => { b.classList.remove('active'); });
            document.getElementById('view-' + tab).classList.add('active');
            let btn = document.getElementById('tab-' + tab);
            btn.classList.add('active');
            if(tab === 'top') loadTop();
            if(tab === 'transfer') loadTransfers('day', document.querySelector('#view-transfer .nav-btn'));
            if(tab === 'clan') loadClanInfo();
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
            initAudio(); balance += clickPower;
            const scoreEl = document.getElementById('score');
            scoreEl.innerText = Math.floor(balance) + ' ₽'; scoreEl.style.transform = "scale(1.1)";
            setTimeout(() => scoreEl.style.transform = "scale(1)", 100); playSound('click');
            const el = document.createElement('div'); el.className = 'floating'; el.innerText = '+' + clickPower + ' ₽';
            el.style.left = (e.clientX - 20) + 'px'; el.style.top = (e.clientY - 40) + 'px';
            document.body.appendChild(el); setTimeout(() => el.remove(), 800);
            fetch('/api/click', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({amount: clickPower}) })
            .then(res => { if(res.status === 403) { showToast("АБЬЮЗ!", 'error'); setTimeout(() => window.location.href = '/logout', 2000); } });
        }

        function buyUpgrade(type) {
            fetch('/api/buy', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({type: type}) })
            .then(res => res.json()).then(data => { 
                if(data.success) { showToast("Успешно!", 'success'); balance = data.new_balance; document.getElementById('score').innerText = Math.floor(balance) + ' ₽'; setTimeout(() => location.reload(), 1000); } 
                else showToast("Мало денег!", 'error'); 
            });
        }

        function buyCustom(type, value, price) {
            fetch('/api/buy_custom', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({type, value, price}) })
            .then(res => res.json()).then(data => { 
                if(data.success) { 
                    showToast("Успешно!", 'success'); 
                    balance = data.new_balance; 
                    document.getElementById('score').innerText = Math.floor(balance) + ' ₽'; 
                    if (type === 'badge') {
                        let badgeEl = document.getElementById('current-badge');
                        if(!badgeEl) {
                            let nameEl = document.getElementById('current-username');
                            let span = document.createElement('span');
                            span.id = 'current-badge';
                            span.className = 'badge';
                            span.innerText = value;
                            nameEl.parentNode.insertBefore(span, nameEl.nextSibling);
                        } else {
                            badgeEl.innerText = value;
                            badgeEl.className = 'badge';
                            badgeEl.style.display = 'inline-block';
                        }
                    }
                } 
                else showToast("Мало денег!", 'error'); 
            });
        }

        function createClan() {
            let name = document.getElementById('new-clan-name').value; let open = document.getElementById('new-clan-open').checked;
            if(!name) return showToast("Введи название", 'error');
            fetch('/api/clan/create', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name: name, is_open: open}) })
            .then(res => res.json()).then(data => { if(data.success) { showToast("Союз создан!", 'success'); setTimeout(() => location.reload(), 1000); } else showToast(data.error, 'error'); });
        }

        function searchClans() {
            let query = document.getElementById('search-clan').value;
            fetch('/api/clan/search?q=' + query).then(res => res.json()).then(data => {
                let html = ''; data.forEach(c => { html += `<div class="clan-card"><h4>${c.name}</h4><p>Лидер: ${c.leader}</p><button class="btn-main" onclick="joinClan(${c.id})">Вступить</button></div>`; });
                document.getElementById('clan-search-results').innerHTML = html || '<div>Ничего не найдено</div>';
            });
        }

        function joinClan(id) {
            fetch('/api/clan/join', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({clan_id: id}) })
            .then(res => res.json()).then(data => { if(data.success) { showToast("Вы вступили!", 'success'); setTimeout(() => location.reload(), 1000); } else showToast(data.error, 'error'); });
        }

        function loadClanInfo() {
            if(!currentUserClanId) return;
            fetch('/api/clan/info').then(res => res.json()).then(data => {
                if(data.success) {
                    document.getElementById('c-name').innerText = data.clan.name; document.getElementById('c-role').innerText = data.role;
                    if(data.role === 'Лидер') document.getElementById('clan-admin-controls').style.display = 'block';
                    let html = ''; data.members.forEach(m => { html += `<div class="member-item"><span>${m.username}</span><span style="color:var(--gold);">${m.role}</span></div>`; });
                    document.getElementById('clan-members').innerHTML = html;
                }
            });
        }

        function clanAction(action) {
            let target = document.getElementById('clan-target').value;
            if(!target) return showToast("Введи ник", 'error');
            fetch('/api/clan/action', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({action: action, target: target}) })
            .then(res => res.json()).then(data => { if(data.success) { showToast("Успешно!", 'success'); loadClanInfo(); } else showToast(data.error, 'error'); });
        }

        function leaveClan() { if(confirm("Покинуть союз?")) fetch('/api/clan/leave', { method: 'POST' }).then(res => res.json()).then(data => { if(data.success) location.reload(); else showToast(data.error, 'error'); }); }
        function deleteClan() { if(confirm("Удалить союз навсегда?")) fetch('/api/clan/delete', { method: 'POST' }).then(res => res.json()).then(data => { if(data.success) location.reload(); else showToast(data.error, 'error'); }); }

        function loadTop() {
            fetch('/api/top').then(res => res.json()).then(data => {
                let html = ''; data.forEach((p, i) => {
                    let badgeClass = p.badge_color === 'rainbow' ? 'rainbow-text' : '';
                    let badgeStyle = p.badge_color !== 'rainbow' ? `background:${p.badge_color}; color:#000; border-color:${p.badge_color};` : '';
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
                    document.getElementById('other-ban-nick').innerText = data.username; document.getElementById('other-ban-reason').innerText = data.ban_reason;
                    let remaining = data.remaining; let text = "";
                    if(remaining > 0) { let d = Math.floor(remaining / 86400); let h = Math.floor((remaining % 86400) / 3600); let m = Math.floor((remaining % 3600) / 60); if(d>0) text+=d+"д "; if(h>0) text+=h+"ч "; text+=m+"м"; } else text = "Истек";
                    document.getElementById('other-ban-until').innerText = text; openModal('other-ban-modal');
                }
            });
        }
        function closeOtherBan() { closeModal('other-ban-modal'); if(topBanInterval) clearInterval(topBanInterval); }

        function changeSetting(key, value) {
            if(key === 'theme') { document.body.className = 'theme-' + value; document.getElementById('display-theme').innerText = value; }
            if(key === 'lang') { document.getElementById('display-lang').innerText = value; }
            if(key === 'font_family') { document.body.style.fontFamily = "'" + value + "', sans-serif"; document.getElementById('display-font').innerText = value; }
            fetch('/api/settings', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({key: key, value: value}) }).then(() => { showToast("Сохранено!", 'success'); closeModal('lang-modal'); closeModal('theme-modal'); closeModal('font-modal'); });
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
            document.querySelectorAll('#view-transfer .nav-btn').forEach(b => { b.classList.remove('active'); });
            if(btn) btn.classList.add('active');
            fetch('/api/transfers/top?period=' + period).then(res => res.json()).then(data => {
                let html = ''; data.forEach((t, i) => { html += `<div style="padding:5px 0; border-bottom:1px solid var(--border);">#${i+1} <b>${t.sender}</b> перевел <b>${t.total}</b> ₽</div>`; });
                document.getElementById('transfer-top-list').innerHTML = html || '<div style="color:#888;">Нет переводов</div>';
            });
            fetch('/api/transfers/my').then(res => res.json()).then(data => {
                let html = ''; data.forEach(t => { let date = new Date(t.timestamp * 1000).toLocaleString(); html += `<div style="padding:5px 0; border-bottom:1px solid var(--border);">Вы -> <b>${t.receiver}</b> (${t.amount} ₽) <br><span style="font-size:10px; color:#888;">${date}</span></div>`; });
                document.getElementById('my-transfer-list').innerHTML = html || '<div style="color:#888;">Вы еще не переводили</div>';
            });
        }

        function redeemPromo() {
            let code = document.getElementById('promo-input').value;
            if(!code) return;
            fetch('/api/promo/redeem', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({code: code}) })
            .then(res => res.json()).then(data => { if(data.success) { showToast("Промокод активирован!", 'success'); document.getElementById('promo-input').value = ''; setTimeout(() => location.reload(), 1000); } else showToast(data.error, 'error'); });
        }

        let currentReplyUser = ""; let currentReplyText = "";
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
                    let badgeStyle = m.badge_color !== 'rainbow' ? `background:${m.badge_color}; color:#000; border-color:${m.badge_color};` : '';
                    let badgeHtml = m.badge ? `<span class="badge ${badgeClass}" style="${badgeStyle}">${m.badge}</span>` : '';
                    let replyHtml = '';
                    if(m.reply_user) { replyHtml = `<div class="chat-reply-preview" style="display:block; border-left-color:var(--neon); margin-bottom:8px;"><b>${m.reply_user}</b><br>${m.reply_text}</div>`; }
                    html += `<div class="chat-msg" onmousedown="startSwipe(event, '${m.username}', '${m.text.replace(/'/g, "\\'")}')" ontouchstart="startSwipe(event, '${m.username}', '${m.text.replace(/'/g, "\\'")}')">
                                ${replyHtml}<span class="${nameClass}" style="${nameStyle}">${m.username}</span> ${badgeHtml}
                                <span style="font-size:10px; color:#888; float:right;">${time}</span><br>${m.text}</div>`;
                });
                container.innerHTML = html; if(isScrolledToBottom) container.scrollTop = container.scrollHeight;
            });
        }

        let startX = 0;
        function startSwipe(e, user, text) {
            startX = e.touches ? e.touches[0].clientX : e.clientX;
            let element = e.currentTarget;
            let endHandler = function(endEvent) {
                let endX = endEvent.changedTouches ? endEvent.changedTouches[0].clientX : endEvent.clientX;
                if (startX - endX > 50) { setReply(user, text); }
                element.style.transform = "translateX(0)";
                element.removeEventListener('touchend', endHandler); element.removeEventListener('mouseup', endHandler);
            };
            element.addEventListener('touchend', endHandler); element.addEventListener('mouseup', endHandler);
        }

        function setReply(user, text) {
            currentReplyUser = user; currentReplyText = text;
            document.getElementById('reply-text-preview').innerText = "Ответ: " + user; document.getElementById('reply-message-preview').innerText = text;
            document.getElementById('chat-reply-bar').style.display = 'block'; document.getElementById('chat-input').focus();
        }
        function cancelReply() { currentReplyUser = ""; currentReplyText = ""; document.getElementById('chat-reply-bar').style.display = 'none'; }

        function sendChat() {
            let inp = document.getElementById('chat-input');
            if(!inp.value.trim()) return;
            fetch('/api/chat/send', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text: inp.value, reply_user: currentReplyUser, reply_text: currentReplyText}) })
            .then(res => res.json()).then(data => { if(data.success) { inp.value = ''; cancelReply(); loadChat(); } else showToast(data.error, 'error'); });
        }
        function handleChatEnter(e) { if(e.key === 'Enter') sendChat(); }

        function checkMuteStatus() {
            if (!isLoggedIn) return;
            let now = Math.floor(Date.now() / 1000); 
            let muteTimeLeft = muteUntil - now;
            let inputArea = document.getElementById('chat-input-area'); 
            let muteStatus = document.getElementById('chat-mute-status');
            
            if(muteTimeLeft > 1) { 
                inputArea.style.display = 'none'; 
                muteStatus.style.display = 'block'; 
                let m = Math.floor(muteTimeLeft / 60); 
                let s = muteTimeLeft % 60; 
                document.getElementById('mute-timer').innerText = (m > 0 ? m + "м " : "") + s + "с"; 
            }
            else { 
                inputArea.style.display = 'flex'; 
                muteStatus.style.display = 'none'; 
            }
        }
        setInterval(checkMuteStatus, 1000);
        window.onload = () => { if(isLoggedIn) { setInterval(loadChat, 3000); loadChat(); checkMuteStatus(); } };
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    user = None; remaining_seconds = 0
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if not user: session.pop('user_id', None)
        elif user.is_banned:
            if time.time() >= user.ban_until:
                user.is_banned = 0; user.ban_reason = ""; user.ban_msg = ""; user.ban_until = 0; user.ban_duration = ""; db.session.commit()
            else: remaining_seconds = int(user.ban_until - time.time())
        if user and user.badge_expire > 0 and time.time() > user.badge_expire:
            user.badge = ''; user.badge_expire = 0; db.session.commit()

    multi_price = 50 * (2 ** (user.click_power - 1)) if user and not user.is_banned else 50
    auto_price = 200 * (3 ** user.auto_income) if user and not user.is_banned else 200
    return render_template_string(HTML_CODE, user=user, multi_price=int(multi_price), auto_price=int(auto_price), remaining_seconds=remaining_seconds)

@app.route('/api/user')
def api_user():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    user = User.query.get(session['user_id'])
    if not user: return jsonify({'error': 'No user'}), 401
    if user.is_banned: return jsonify({'error': 'Banned'}), 403
    return jsonify({'success': True, 'balance': user.balance, 'click_power': user.click_power, 'auto_income': user.auto_income, 'mute_until': user.mute_until})

@app.route('/register', methods=['POST'])
def register():
    data = request.json; u, p = data['username'], data['password']
    if re.search('[а-яА-ЯёЁ]', u) or re.search('[а-яА-ЯёЁ]', p): return jsonify({'error': 'Cyrillic'}), 400
    if User.query.filter_by(username=u).first(): return jsonify({'error': 'Taken'}), 400
    user = User(username=u, password=generate_password_hash(p))
    db.session.add(user); db.session.commit()
    session.permanent = True; session['user_id'] = user.id
    return jsonify({'success': True}), 200

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if user and check_password_hash(user.password, data['password']):
        if user.is_banned:
            if time.time() >= user.ban_until:
                user.is_banned = 0; user.ban_reason = ""; user.ban_msg = ""; user.ban_until = 0; user.ban_duration = ""; db.session.commit()
            else: return jsonify({'banned': True}), 403
        session.permanent = True; session['user_id'] = user.id
        return jsonify({'success': True}), 200
    return jsonify({'error': 'Bad auth'}), 401

@app.route('/logout')
def logout():
    session.pop('user_id', None); return redirect(url_for('index'))

@app.route('/api/click', methods=['POST'])
def api_click():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    user = User.query.get(session['user_id'])
    if not user: return jsonify({'error': 'No user'}), 401
    if user.is_banned:
        db.session.delete(user); db.session.commit(); session.pop('user_id', None)
        return jsonify({'error': 'banned_deleted'}), 403
    user.balance += request.json.get('amount', 1)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/buy', methods=['POST'])
def api_buy():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    type = request.json.get('type'); user = User.query.get(session['user_id'])
    if type == 'multi':
        price = 50 * (2 ** (user.click_power - 1))
        if user.balance >= price:
            user.balance -= price; user.click_power *= 2; db.session.commit()
            return jsonify({'success': True, 'new_balance': user.balance})
    elif type == 'auto':
        price = 200 * (3 ** user.auto_income)
        if user.balance >= price:
            user.balance -= price; user.auto_income += 1; db.session.commit()
            return jsonify({'success': True, 'new_balance': user.balance})
    return jsonify({'error': 'No money'}), 400

@app.route('/api/buy_custom', methods=['POST'])
def api_buy_custom():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    data = request.json; user = User.query.get(session['user_id'])
    if user.balance >= data['price']:
        if data['type'] == 'badge':
            user.balance -= data['price']; user.badge = data['value']; user.badge_color = '#00ffcc'; user.badge_expire = time.time() + 14 * 86400
        db.session.commit()
        return jsonify({'success': True, 'new_balance': user.balance})
    return jsonify({'error': 'No money'}), 400

@app.route('/api/clan/create', methods=['POST'])
def clan_create():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    data = request.json; user = User.query.get(session['user_id'])
    if user.clan_id: return jsonify({'error': 'Вы уже в союзе'}), 400
    if user.balance < 1000: return jsonify({'error': 'Нужно 1000 ₽'}), 400
    if Clan.query.filter_by(name=data['name']).first(): return jsonify({'error': 'Название занято'}), 400
    clan = Clan(name=data['name'], leader=user.username, is_open=data['is_open'])
    user.balance -= 1000; user.clan_id = clan.id; user.clan_role = 'Лидер'
    db.session.add(clan); db.session.commit(); return jsonify({'success': True})

@app.route('/api/clan/search')
def clan_search():
    q = request.args.get('q', ''); clans = Clan.query.filter(Clan.name.ilike(f'%{q}%')).limit(10).all()
    return jsonify([{'id': c.id, 'name': c.name, 'leader': c.leader} for c in clans])

@app.route('/api/clan/join', methods=['POST'])
def clan_join():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    user = User.query.get(session['user_id'])
    if user.clan_id: return jsonify({'error': 'Вы уже в союзе'}), 400
    clan = Clan.query.get(request.json.get('clan_id'))
    if not clan or not clan.is_open: return jsonify({'error': 'Союз закрыт'}), 400
    user.clan_id = clan.id; user.clan_role = 'Участник'; db.session.commit(); return jsonify({'success': True})

@app.route('/api/clan/info')
def clan_info():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    user = User.query.get(session['user_id'])
    if not user.clan_id: return jsonify({'error': 'Нет клана'}), 400
    clan = Clan.query.get(user.clan_id); members = User.query.filter_by(clan_id=user.clan_id).all()
    return jsonify({'success': True, 'clan': {'name': clan.name}, 'role': user.clan_role, 'members': [{'username': m.username, 'role': m.clan_role} for m in members]})

@app.route('/api/clan/action', methods=['POST'])
def clan_action():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    user = User.query.get(session['user_id']); data = request.json; action = data['action']; target_name = data['target']
    if user.clan_role != 'Лидер': return jsonify({'error': 'Только лидер'}), 403
    target = User.query.filter_by(username=target_name, clan_id=user.clan_id).first()
    if not target: return jsonify({'error': 'Игрок не в вашем союзе'}), 404
    if target.username == user.username: return jsonify({'error': 'Это вы'}), 400
    if action == 'promote': target.clan_role = 'Админ'
    elif action == 'kick': target.clan_id = None; target.clan_role = ''
    elif action == 'transfer':
        target.clan_role = 'Лидер'; user.clan_role = 'Админ'; Clan.query.get(user.clan_id).leader = target.username
    db.session.commit(); return jsonify({'success': True})

@app.route('/api/clan/leave', methods=['POST'])
def clan_leave():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    user = User.query.get(session['user_id'])
    if user.clan_role == 'Лидер': return jsonify({'error': 'Лидер не может выйти'}), 400
    user.clan_id = None; user.clan_role = ''; db.session.commit(); return jsonify({'success': True})

@app.route('/api/clan/delete', methods=['POST'])
def clan_delete():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    user = User.query.get(session['user_id'])
    if user.clan_role != 'Лидер': return jsonify({'error': 'Только лидер'}), 403
    User.query.filter_by(clan_id=user.clan_id).update({'clan_id': None, 'clan_role': ''})
    Clan.query.filter_by(id=user.clan_id).delete(); db.session.commit(); return jsonify({'success': True})

@app.route('/api/top')
def api_top():
    users = User.query.order_by(User.balance.desc()).limit(10).all()
    return jsonify([{'username': u.username, 'balance': u.balance, 'color': u.color, 'badge': u.badge, 'badge_color': u.badge_color, 'is_banned': u.is_banned} for u in users])

@app.route('/api/ban_info/<username>')
def api_ban_info(username):
    user = User.query.filter_by(username=username, is_banned=1).first()
    if user: return jsonify({'success': True, 'username': user.username, 'ban_reason': user.ban_reason, 'ban_msg': user.ban_msg, 'remaining': max(0, int(user.ban_until - time.time()))})
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/settings', methods=['POST'])
def api_settings():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    data = request.json; user = User.query.get(session['user_id'])
    setattr(user, data['key'], data['value']); db.session.commit(); return jsonify({'success': True})

@app.route('/api/reset', methods=['POST'])
def api_reset():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    user = User.query.get(session['user_id'])
    user.balance = 0; user.click_power = 1; user.auto_income = 0; user.color = '#ffffff'; user.badge = ''; user.badge_color = '#ffffff'
    db.session.commit(); return jsonify({'success': True})

@app.route('/api/transfer', methods=['POST'])
def api_transfer():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    data = request.json; amount = data['amount']; receiver = data['receiver']
    if amount <= 0: return jsonify({'error': 'Неверная сумма'}), 400
    sender = User.query.get(session['user_id']); target = User.query.filter_by(username=receiver).first()
    if not target: return jsonify({'error': 'Игрок не найден'}), 404
    if sender.username == receiver: return jsonify({'error': 'Себе нельзя'}), 400
    if sender.balance < amount: return jsonify({'error': 'Мало денег'}), 400
    sender.balance -= amount; target.balance += amount
    db.session.add(Transfer(sender=sender.username, receiver=receiver, amount=amount, timestamp=time.time())); db.session.commit()
    return jsonify({'success': True})

@app.route('/api/transfers/top')
def api_transfers_top():
    period = request.args.get('period', 'all'); now = time.time()
    start = now - 86400 if period == 'day' else (now - 2592000 if period == 'month' else 0)
    from sqlalchemy import func
    rows = db.session.query(Transfer.sender, func.sum(Transfer.amount).label('total')).filter(Transfer.timestamp >= start).group_by(Transfer.sender).order_by(func.sum(Transfer.amount).desc()).limit(10).all()
    return jsonify([{'sender': r.sender, 'total': r.total} for r in rows])

@app.route('/api/transfers/my')
def api_transfers_my():
    if 'user_id' not in session: return jsonify([])
    user = User.query.get(session['user_id'])
    rows = Transfer.query.filter_by(sender=user.username).order_by(Transfer.timestamp.desc()).limit(20).all()
    return jsonify([{'receiver': r.receiver, 'amount': r.amount, 'timestamp': r.timestamp} for r in rows])

@app.route('/api/chat/get')
def api_chat_get():
    msgs = ChatMessage.query.order_by(ChatMessage.timestamp.desc()).limit(50).all()
    res = []
    for m in reversed(msgs):
        u = User.query.filter_by(username=m.username).first()
        res.append({'username': m.username, 'text': m.text, 'timestamp': m.timestamp, 'reply_user': m.reply_user, 'reply_text': m.reply_text, 'color': u.color if u else '#fff', 'badge': u.badge if u else '', 'badge_color': u.badge_color if u else '#fff'})
    return jsonify(res)

@app.route('/api/chat/send', methods=['POST'])
def api_chat_send():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    data = request.json; text = data.get('text', '').strip()
    if not text: return jsonify({'error': 'Пустое'}), 400
    user = User.query.get(session['user_id'])
    if user.mute_until > time.time(): return jsonify({'error': 'Вы заглушены!'}), 403
    msg = ChatMessage(username=user.username, text=text[:100], timestamp=time.time(), reply_user=data.get('reply_user', ''), reply_text=data.get('reply_text', '')[:50])
    db.session.add(msg); db.session.commit(); return jsonify({'success': True})

@app.route('/api/promo/redeem', methods=['POST'])
def api_promo_redeem():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    code = request.json.get('code', '').strip(); promo = Promocode.query.filter_by(code=code).first()
    if not promo or promo.uses_left <= 0: return jsonify({'error': 'Недействительный код'}), 400
    user = User.query.get(session['user_id'])
    if promo.type == 'money': user.balance += float(promo.value)
    elif promo.type == 'coins': user.mog_coins += float(promo.value)
    elif promo.type == 'badge': user.badge = promo.value; user.badge_expire = time.time() + 14 * 86400
    elif promo.type == 'color': user.color = promo.value
    promo.uses_left -= 1; db.session.commit(); return jsonify({'success': True})

ADMIN_SECRET_TOKEN = "MOG_SECRET_2026"

@app.route('/api/admin/command', methods=['POST'])
def api_admin_command():
    data = request.json
    if data.get('token') != ADMIN_SECRET_TOKEN: return jsonify({'error': 'Доступ запрещен'}), 403
    cmd_str = data.get('command', '').strip()
    if not cmd_str: return jsonify({'error': 'Пустая команда'})
    parts = cmd_str.split(); action = parts[0]
    try:
        if action == '/createuser' and len(parts) >= 3:
            if User.query.filter_by(username=parts[1]).first(): return jsonify({'error': 'Ник занят'})
            new_u = User(username=parts[1], password=generate_password_hash(parts[2]))
            db.session.add(new_u); db.session.commit(); return jsonify({'success': True, 'msg': f'Аккаунт {parts[1]} создан'})
        target = parts[1] if len(parts) > 1 else ""; user = User.query.filter_by(username=target).first()
        if not user: return jsonify({'error': f'Игрок {target} не найден'})
        if action == '/give' and len(parts) >= 3: user.balance += float(parts[2]); db.session.commit(); return jsonify({'success': True, 'msg': f'Выдано {parts[2]} ₽'})
        elif action == '/givecoins' and len(parts) >= 3: user.mog_coins += float(parts[2]); db.session.commit(); return jsonify({'success': True, 'msg': f'Выдано {parts[2]} MOG Coins'})
        elif action == '/givebadge' and len(parts) >= 3: user.badge = parts[2]; user.badge_expire = time.time() + 14 * 86400; db.session.commit(); return jsonify({'success': True, 'msg': f'Бейдж {parts[2]} выдан'})
        elif action == '/setcolor' and len(parts) >= 3: user.color = parts[2]; db.session.commit(); return jsonify({'success': True, 'msg': f'Цвет изменен'})
        elif action == '/setbadgecolor' and len(parts) >= 3: user.badge_color = parts[2]; db.session.commit(); return jsonify({'success': True, 'msg': f'Цвет бейджа изменен'})
        elif action == '/ban' and len(parts) >= 3:
            duration = parts[2]; reason = " ".join(parts[3:]) if len(parts) > 3 else "Без причины"; sec = 60
            if 'm' in duration: sec = int(duration.replace('m','')) * 60
            elif 'h' in duration: sec = int(duration.replace('h','')) * 3600
            elif 'd' in duration: sec = int(duration.replace('d','')) * 86400
            user.is_banned = 1; user.ban_reason = reason; user.ban_until = time.time() + sec; user.ban_duration = duration
            db.session.commit(); return jsonify({'success': True, 'msg': f'Игрок {target} забанен на {duration}'})
        elif action == '/mute' and len(parts) >= 3:
            duration = parts[2]; sec = 60
            if 'm' in duration: sec = int(duration.replace('m','')) * 60
            elif 'h' in duration: sec = int(duration.replace('h','')) * 3600
            user.mute_until = time.time() + sec; db.session.commit(); return jsonify({'success': True, 'msg': f'Игрок {target} заглушен на {duration}'})
        elif action == '/reset': user.balance = 0; user.click_power = 1; user.auto_income = 0; db.session.commit(); return jsonify({'success': True, 'msg': f'Прогресс сброшен'})
        elif action == '/promo' and len(parts) >= 5:
            p_code, p_type, p_val, p_uses = parts[1], parts[2], parts[3], int(parts[4])
            if Promocode.query.get(p_code): return jsonify({'error': 'Промокод уже есть'})
            db.session.add(Promocode(code=p_code, type=p_type, value=p_val, uses_left=p_uses)); db.session.commit(); return jsonify({'success': True, 'msg': f'Промокод {p_code} создан'})
        return jsonify({'error': 'Неизвестная команда'})
    except Exception as e:
        db.session.rollback(); return jsonify({'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, use_reloader=False)

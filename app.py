from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
import time
import re
import os
import random
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'mog_secret_key_123')
app.permanent_session_lifetime = 86400 * 30

db_url = os.environ.get('DATABASE_URL')
if not db_url:
    db_url = 'sqlite:///mogclicker.db'
else:
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    if "postgresql://" in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
        if "sslmode" not in db_url:
            db_url += "?sslmode=disable"

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
    created_at = db.Column(db.Float, default=time.time)
    can_write_red = db.Column(db.Boolean, default=False)
    skin = db.Column(db.String(50), default='')
    skin_mult = db.Column(db.Float, default=1.0)
    mod_rank = db.Column(db.Integer, default=0) # 0 - игрок, 1 - мл.мод, 2 - ст.мод, 3 - админ, 4 - ст.админ

class Inventory(db.Model):
    __tablename__ = 'inventory'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    item_type = db.Column(db.String(20)) 
    item_name = db.Column(db.String(50))
    item_mult = db.Column(db.Float, default=1.0)

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
    is_red = db.Column(db.Boolean, default=False)

class Promocode(db.Model):
    __tablename__ = 'promocodes'
    code = db.Column(db.String(50), primary_key=True)
    type = db.Column(db.String(20))
    value = db.Column(db.String(50))
    uses_left = db.Column(db.Integer)

with app.app_context():
    db.create_all()
    try:
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS can_write_red BOOLEAN DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS skin VARCHAR(50) DEFAULT '';"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS skin_mult FLOAT DEFAULT 1.0;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS mod_rank INTEGER DEFAULT 0;"))
            conn.execute(text("ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS is_red BOOLEAN DEFAULT FALSE;"))
            conn.commit()
    except Exception:
        pass

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
        * { -webkit-tap-highlight-color: transparent; box-sizing: border-box; transition: background 0.3s ease, color 0.3s ease, border-color 0.3s ease, transform 0.2s ease, box-shadow 0.2s ease; }
        
        :root { --bg: #121212; --panel: #1e1e1e; --text: #ffffff; --neon: #00ffcc; --gold: #ffd700; --border: #333; }
        body.theme-light { --bg: #f0f0f0; --panel: #ffffff; --text: #121212; --neon: #0077ff; --border: #ccc; }
        body.theme-neon { --bg: #0a001a; --panel: #1a0033; --text: #ffffff; --neon: #ff00ff; --border: #ff00ff; }
        body.theme-cyber { --bg: #000000; --panel: #111111; --text: #ffff00; --neon: #ff003c; --border: #ff003c; }
        body.theme-ocean { --bg: #001220; --panel: #003366; --text: #e0f7fa; --neon: #00e5ff; --border: #00e5ff; }
        body.theme-retro { --bg: #1a1a1a; --panel: #2a2a2a; --text: #00ff00; --neon: #00ff00; --border: #00ff00; }
        
        body { background: var(--bg); color: var(--text); font-family: '{{ user.font_family if user else "Montserrat" }}', sans-serif; margin: 0; padding: 10px; user-select: none; text-align: center; overflow-x: hidden; min-height: 100vh; display: flex; flex-direction: column; align-items: center; }
        
        .view { display: none; background: var(--panel); padding: 20px; border-radius: 20px; border: 1px solid var(--border); min-height: 400px; width: 100%; max-width: 400px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); opacity: 0; transform: translateY(20px) scale(0.98); }
        .view.active { display: block; opacity: 1; transform: translateY(0) scale(1); animation: slideIn 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards; }
        @keyframes slideIn { from { opacity: 0; transform: translateY(20px) scale(0.98); } to { opacity: 1; transform: translateY(0) scale(1); } }

        #auth-wrapper { display: flex; justify-content: center; align-items: center; min-height: 100vh; width: 100%; }
        .glass-card { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(15px); -webkit-backdrop-filter: blur(15px); border: 1px solid rgba(255, 255, 255, 0.1); padding: 30px 20px; border-radius: 25px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37); width: 100%; max-width: 400px; }
        
        .auth-tabs { display: flex; gap: 10px; margin-bottom: 20px; }
        .auth-tab { flex: 1; padding: 10px; background: var(--border); color: var(--text); border: none; border-radius: 10px; cursor: pointer; font-weight: bold; }
        .auth-tab.active { background: var(--neon); color: #000; box-shadow: 0 0 10px var(--neon); transform: translateY(-2px); }
        .auth-form { display: none; }
        .auth-form.active { display: block; animation: fadeIn 0.3s ease; }

        input[type="text"], input[type="password"], input[type="number"], select { width: 100%; padding: 15px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.2); color: var(--text); border-radius: 15px; margin-bottom: 15px; outline: none; font-size: 16px; }
        input:focus, select:focus { border-color: var(--neon); box-shadow: 0 0 15px var(--neon); background: rgba(0,0,0,0.5); }
        
        .btn-main { background: var(--neon); color: #000; padding: 15px; border: none; border-radius: 15px; cursor: pointer; font-weight: bold; font-size: 16px; width: 100%; margin-bottom: 15px; box-shadow: 0 0 15px transparent; }
        .btn-main:hover { filter: brightness(1.2); box-shadow: 0 0 15px var(--neon); transform: translateY(-2px); }
        .btn-main:active { transform: translateY(1px); }
        .btn-danger { background: #ff4444; color: white; }
        .btn-gold { background: var(--gold); }
        .btn-gold:hover { box-shadow: 0 0 15px var(--gold); }
        .btn-disabled { background: #444 !important; color: #888 !important; cursor: not-allowed !important; box-shadow: none !important; transform: none !important; }

        .nav-btn { background: var(--panel); border: 1px solid var(--border); color: var(--text); padding: 8px 12px; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 14px; }
        .nav-btn:hover { border-color: var(--neon); color: var(--neon); }
        .nav-btn.active { border-color: var(--neon); color: var(--neon); box-shadow: 0 0 10px var(--neon); }

        #score { font-size: 45px; color: var(--gold); font-weight: bold; text-shadow: 0 0 15px rgba(255,215,0,0.4); margin: 15px 0; }
        #coin { width: 200px; height: 200px; background: radial-gradient(circle, var(--gold), #b8860b); border-radius: 50%; margin: 20px auto; font-size: 80px; line-height: 200px; cursor: pointer; box-shadow: 0 0 40px var(--gold); display: block; }
        #coin:hover { transform: scale(1.05); }
        #coin:active { transform: scale(0.85); box-shadow: 0 0 20px var(--gold); }
        
        .stats-box { background: rgba(0,0,0,0.3); padding: 10px; border-radius: 10px; border: 1px solid var(--border); margin-bottom: 15px; font-size: 14px; display: flex; justify-content: space-around;}
        
        .shop-item { display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.2); padding: 15px; margin-bottom: 10px; border-radius: 15px; border: 1px solid var(--border); }
        .shop-item:hover { border-color: var(--neon); transform: translateX(5px); box-shadow: 0 0 10px rgba(0,255,204,0.1); }
        .shop-item button { background: var(--neon); color: #000; border: none; padding: 10px 15px; border-radius: 10px; cursor: pointer; font-weight: bold; }
        
        .top-player { display: flex; justify-content: space-between; padding: 12px; border-bottom: 1px solid var(--border); align-items: center; cursor: pointer; border-radius: 10px; }
        .top-player:hover { background: rgba(255,255,255,0.05); border-left: 3px solid var(--neon); padding-left: 15px; }
        
        .floating { position: fixed; color: var(--gold); font-weight: bold; font-size: 30px; pointer-events: none; animation: floatUp 0.8s cubic-bezier(0.25, 1, 0.5, 1) forwards; text-shadow: 0 0 10px #000; z-index: 999; }
        @keyframes floatUp { 0% { opacity: 1; transform: translateY(0) scale(1); } 100% { opacity: 0; transform: translateY(-120px) scale(1.5); } }
        
        .badge { padding: 4px 10px; border-radius: 12px; font-size: 12px; margin-left: 5px; font-weight: bold; display: inline-block; cursor: help; background: rgba(255,255,255,0.1); border: 1px solid var(--border); }
        .badge:hover { transform: scale(1.1); border-color: var(--neon); }
        
        .mod-badge { padding: 2px 6px; border-radius: 5px; font-size: 14px; margin-left: 5px; cursor: pointer; background: rgba(0, 255, 204, 0.2); border: 1px solid var(--neon); display: inline-block; }
        .mod-badge:hover { transform: scale(1.1); box-shadow: 0 0 5px var(--neon); }
        
        .rainbow-text { background: linear-gradient(90deg, #ff0000, #ff7f00, #ffff00, #00ff00, #0000ff, #4b0082, #8f00ff, #ff0000); background-size: 200% auto; -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: bold; animation: rainbowAnim 3s linear infinite; }
        @keyframes rainbowAnim { to { background-position: 200% center; } }

        #toast-container { position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); z-index: 1000; display: flex; flex-direction: column-reverse; gap: 10px; width: 80%; max-width: 300px; pointer-events: none;}
        .toast { background: var(--panel); color: var(--text); padding: 15px; border-radius: 10px; border-left: 5px solid var(--neon); box-shadow: 0 5px 15px rgba(0,0,0,0.5); animation: slideUp 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards, fadeOut 0.3s 2.7s forwards; font-weight: bold; text-align: left; }
        .toast.error { border-left-color: #ff4444; }
        @keyframes slideUp { from { transform: translateY(30px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        @keyframes fadeOut { to { opacity: 0; transform: translateY(-20px); } }
        
        .setting-item { display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.2); padding: 15px; margin-bottom: 10px; border-radius: 10px; border: 1px solid var(--border); cursor: pointer; }
        .setting-item:hover { border-color: var(--neon); transform: translateY(-2px); }
        input[type="range"] { width: 100%; accent-color: var(--neon); height: 20px; margin-top: 10px; }
        
        .modal { display: flex; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 9999; justify-content: center; align-items: center; backdrop-filter: blur(5px); opacity: 0; visibility: hidden; }
        .modal.active { opacity: 1; visibility: visible; }
        .modal-content { background: #1a1a1a; border: 2px solid var(--neon); padding: 25px; border-radius: 15px; max-width: 90%; width: 350px; text-align: left; box-shadow: 0 0 30px rgba(0,255,204,0.2); position: relative; transform: scale(0.8); max-height: 80vh; overflow-y: auto; }
        .modal.active .modal-content { transform: scale(1); animation: modalPop 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
        @keyframes modalPop { 0% { transform: scale(0.8); } 100% { transform: scale(1); } }
        .modal-title { color: var(--neon); font-size: 22px; font-weight: bold; text-align: center; margin-bottom: 20px; text-shadow: 0 0 10px var(--neon); }
        .close-btn { position: absolute; top: 10px; right: 15px; font-size: 24px; cursor: pointer; color: #ff4444; }
        .close-btn:hover { transform: scale(1.2) rotate(90deg); }
        
        .custom-option { padding: 15px; border-bottom: 1px solid var(--border); cursor: pointer; border-radius: 8px; margin-bottom: 5px; font-size: 16px; }
        .custom-option:hover { background: rgba(255,255,255,0.1); color: var(--neon); padding-left: 20px; }

        .info-label { color: #0077ff; font-weight: bold; margin-bottom: 5px; font-size: 14px;}
        .info-value { color: #ffffff; margin-bottom: 15px; font-family: monospace; font-size: 15px; background: rgba(255,255,255,0.1); padding: 8px 10px; border-radius: 5px; }
        
        #chat-container { width: 100%; max-width: 400px; background: var(--panel); border: 2px solid var(--border); border-radius: 20px; display: flex; flex-direction: column; margin-top: 20px; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); overflow: hidden; position: relative;}
        #chat-messages { height: 300px; overflow-y: auto; padding: 15px; text-align: left; font-size: 14px; display: flex; flex-direction: column; gap: 10px; }
        .chat-msg { word-wrap: break-word; background: rgba(0,0,0,0.2); padding: 10px; border-radius: 10px; border-left: 3px solid var(--neon); line-height: 1.4; position: relative; user-select: none; touch-action: pan-y; }
        .chat-msg.red-text-msg { color: #ff4444; border-left-color: #ff4444; }
        .chat-reply-preview { font-size: 11px; color: #888; border-left: 2px solid #555; padding-left: 5px; margin-bottom: 5px; display: none; }
        #chat-input-area { display: flex; padding: 10px; gap: 10px; background: rgba(0,0,0,0.4); border-top: 1px solid var(--border); flex-direction: column;}
        #chat-reply-bar { display: none; background: rgba(255,255,255,0.1); padding: 8px; border-radius: 8px; margin-bottom: 5px; font-size: 12px; text-align: left; border-left: 3px solid var(--gold); position: relative;}
        .close-reply { position: absolute; right: 5px; top: 5px; cursor: pointer; color: #ff4444; font-weight: bold;}
        
        .chat-input-row { display: flex; gap: 8px; width: 100%; align-items: center; }
        #chat-input { flex: 1; min-width: 0; margin: 0; padding: 12px; border-radius: 20px; }
        #chat-send { flex-shrink: 0; width: 48px; height: 48px; margin: 0; padding: 0; border-radius: 50%; display: flex; justify-content: center; align-items: center; font-size: 20px; }
        
        /* КАЗИНО */
        .casino-box { background: rgba(0,0,0,0.4); border: 2px solid var(--gold); border-radius: 15px; padding: 20px; margin-bottom: 20px;}
        .casino-buttons { display: flex; gap: 10px; margin-top: 15px;}
        .casino-buttons button { flex: 1; font-size: 16px; padding: 12px; }
        #casino-result { font-size: 20px; font-weight: bold; margin-top: 15px; text-align: center; height: 30px;}
        
        /* МОНЕТКА 3D */
        .coin-wrapper { width: 120px; height: 120px; margin: 20px auto; perspective: 1000px; display: none; }
        .coin { width: 100%; height: 100%; position: relative; transform-style: preserve-3d; transition: transform 1.5s ease-out; }
        .coin-face { position: absolute; width: 100%; height: 100%; backface-visibility: hidden; border-radius: 50%; background: radial-gradient(circle, #ffd700, #b8860b); display: flex; justify-content: center; align-items: center; font-size: 60px; border: 4px solid #8b6508; box-shadow: inset 0 0 20px rgba(0,0,0,0.5); }
        .coin-back { transform: rotateY(180deg); background: radial-gradient(circle, #d4af37, #8b6508); }
        
        /* КОЛЕСО */
        .wheel-container { width: 220px; height: 220px; margin: 20px auto; position: relative; display: none; }
        .wheel { width: 100%; height: 100%; border-radius: 50%; border: 5px solid var(--gold); position: relative; background: conic-gradient(#ff4444 0deg 60deg, #444 60deg 120deg, #00ffcc 120deg 180deg, #444 180deg 240deg, #ffd700 240deg 300deg, #444 300deg 360deg); transition: transform 3s cubic-bezier(0.1, 0.7, 0.1, 1); }
        .wheel-pointer { position: absolute; top: -15px; left: 50%; transform: translateX(-50%); font-size: 30px; z-index: 10; filter: drop-shadow(0 0 5px #000); }
        .wheel-label { position: absolute; left: 50%; top: 50%; margin-left: -15px; margin-top: -10px; font-size: 14px; font-weight: bold; color: #fff; text-shadow: 1px 1px 2px #000; }

        /* ИНВЕНТАРЬ */
        .inventory-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .inv-item { background: rgba(0,0,0,0.3); border: 1px solid var(--border); border-radius: 10px; padding: 15px; text-align: center; }
        .inv-item h4 { margin: 0 0 5px 0; font-size: 16px; color: var(--gold); }
        .inv-item p { margin: 0 0 10px 0; font-size: 12px; color: #aaa; }
        .inv-item button { padding: 8px; font-size: 12px; width: 100%;}
        
        /* МОД ПАНЕЛЬ */
        .mod-action-box { background: rgba(255, 68, 68, 0.1); border: 1px solid #ff4444; border-radius: 10px; padding: 15px; margin-bottom: 15px; }
    </style>
</head>
<body class="theme-{{ user.theme if user else 'dark' }}" style="zoom: {{ user.zoom if user else 100 }}%; font-family: '{{ user.font_family if user else 'Montserrat' }}', sans-serif;">
    <div id="toast-container"></div>

    {% if user and user.is_banned %}
        <div class="modal active" style="display:flex;">
            <div class="modal-content" style="border-color: #ff4444;">
                <div class="modal-title" style="color: #ff4444;">!ВЫ ЗАБАНЕНЫ!</div>
                <div class="info-label">ПРИЧИНА:</div><div class="info-value" style="color: #ff4444;">{{ user.ban_reason }}</div>
                <div class="info-label">ЗАБАНЕН НА:</div><div class="info-value">{{ user.ban_duration }}</div>
                <a href="/logout" class="btn-main btn-danger" style="display: block; text-decoration: none; margin-top: 20px;">Выйти</a>
            </div>
        </div>
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
            {% if user.mod_rank > 0 %}
                <span class="mod-badge" onclick="showModInfo('{{ user.username }}', {{ user.mod_rank }})">🛡️</span>
            {% endif %}
            {% if user.badge %}
                <span class="badge {% if user.badge_color == 'rainbow' %}rainbow-text{% endif %}" id="current-badge" style="{% if user.badge_color != 'rainbow' %}background: {{ user.badge_color }}; color: #000; border-color: {{ user.badge_color }};{% endif %}">{{ user.badge }}</span>
            {% endif %}
            | <span style="color: var(--neon);">{{ user.mog_coins|int }} 💎</span>
            | <a href="/logout" style="color: #ff4444; text-decoration: none; font-weight: bold;">Выйти</a>
        </div>

        <div class="nav" style="display: flex; justify-content: center; gap: 5px; margin-bottom: 15px; flex-wrap: wrap; width: 100%; max-width: 400px;">
            <button onclick="switchTab('game')" id="tab-game" class="nav-btn active">Игра</button>
            <button onclick="switchTab('casino')" id="tab-casino" class="nav-btn">Казино</button>
            <button onclick="switchTab('shop')" id="tab-shop" class="nav-btn">Магазин</button>
            <button onclick="switchTab('inventory')" id="tab-inventory" class="nav-btn">Инвентарь</button>
            <button onclick="switchTab('transfer')" id="tab-transfer" class="nav-btn">Переводы</button>
            <button onclick="switchTab('top')" id="tab-top" class="nav-btn">Топ</button>
            <button onclick="switchTab('settings')" id="tab-settings" class="nav-btn">Настройки</button>
            {% if user.mod_rank > 0 %}
            <button onclick="switchTab('mod')" id="tab-mod" class="nav-btn" style="border-color: var(--neon); color: var(--neon);">Модерация</button>
            {% endif %}
        </div>

        <div id="view-game" class="view active">
            <div id="score">{{ user.balance|int }} ₽</div>
            <div id="coin" onclick="clickCoin(event)">₽</div>
            
            <div class="stats-box">
                <div>Мультиклик: <span style="color:var(--neon); font-weight:bold;" id="ui-click-power">{{ user.click_power }}</span></div>
                <div>Автокликер: <span style="color:var(--neon); font-weight:bold;" id="ui-auto-income">{{ user.auto_income }}</span>/с</div>
            </div>
            <div>Скин: <span style="color:var(--gold); font-weight:bold;">{{ user.skin if user.skin else 'Нет' }} (x{{ user.skin_mult }})</span></div>
        </div>

        <div id="view-casino" class="view">
            <h3>Казино</h3>
            
            <div style="display:flex; gap:5px; margin-bottom: 15px;">
                <button class="nav-btn active" onclick="switchCasinoMode('coin')" id="mode-coin" style="flex:1;">Монетка</button>
                <button class="nav-btn" onclick="switchCasinoMode('wheel')" id="mode-wheel" style="flex:1;">Колесо</button>
            </div>

            <div id="casino-coin-mode" class="casino-box">
                <p>Введи ставку и выбери сторону. Угадаешь — забираешь x2!</p>
                <input type="number" id="casino-bet" placeholder="Сумма ставки">
                
                <div class="coin-wrapper" id="coin-anim">
                    <div class="coin" id="coin-element">
                        <div class="coin-face front">🦅</div>
                        <div class="coin-face back">🪙</div>
                    </div>
                </div>

                <div class="casino-buttons">
                    <button class="btn-main btn-gold" onclick="playCasino('heads')">Орёл 🦅</button>
                    <button class="btn-main btn-gold" onclick="playCasino('tails')">Решка 🪙</button>
                </div>
            </div>

            <div id="casino-wheel-mode" class="casino-box" style="display:none;">
                <p>Введи ставку и крути колесо!</p>
                <input type="number" id="wheel-bet" placeholder="Сумма ставки">
                
                <div class="wheel-container" id="wheel-anim">
                    <div class="wheel-pointer">🔻</div>
                    <div class="wheel" id="wheel-element">
                        <div class="wheel-label" style="transform: rotate(30deg) translateY(-80px);">x0</div>
                        <div class="wheel-label" style="transform: rotate(90deg) translateY(-80px);">x0.5</div>
                        <div class="wheel-label" style="transform: rotate(150deg) translateY(-80px);">x1</div>
                        <div class="wheel-label" style="transform: rotate(210deg) translateY(-80px);">x2</div>
                        <div class="wheel-label" style="transform: rotate(270deg) translateY(-80px);">x5</div>
                        <div class="wheel-label" style="transform: rotate(330deg) translateY(-80px);">x0</div>
                    </div>
                </div>

                <button class="btn-main" onclick="playWheel()" style="margin-top:20px;">Крутить 🎡</button>
            </div>

            <div id="casino-result"></div>
        </div>

        <div id="view-shop" class="view">
            <h3>Улучшения</h3>
            <div class="shop-item"><div>Мультиклик (x2)</div><button id="btn-multi" onclick="buyUpgrade('multi')">{{ multi_price }} ₽</button></div>
            <div class="shop-item"><div>Автокликер (+1/с)</div><button id="btn-auto" onclick="buyUpgrade('auto')">{{ auto_price }} ₽</button></div>
            
            <h3>Скины (Множители)</h3>
            {% if 'Iron' in inv_names %}
                <div class="shop-item"><div>Iron Skin (x1.5)</div><button class="btn-disabled" disabled>Куплено</button></div>
            {% else %}
                <div class="shop-item"><div>Iron Skin (x1.5)</div><button onclick="buyItem('skin', 'Iron', 10000, 1.5, this)">10,000 ₽</button></div>
            {% endif %}
            
            {% if 'Gold' in inv_names %}
                <div class="shop-item"><div>Gold Skin (x2)</div><button class="btn-disabled" disabled>Куплено</button></div>
            {% else %}
                <div class="shop-item"><div>Gold Skin (x2)</div><button onclick="buyItem('skin', 'Gold', 50000, 2.0, this)">50,000 ₽</button></div>
            {% endif %}
            
            {% if 'Diamond' in inv_names %}
                <div class="shop-item"><div>Diamond Skin (x5)</div><button class="btn-disabled" disabled>Куплено</button></div>
            {% else %}
                <div class="shop-item"><div>Diamond Skin (x5)</div><button onclick="buyItem('skin', 'Diamond', 500000, 5.0, this)">500,000 ₽</button></div>
            {% endif %}

            <h3>Бейджи</h3>
            {% if 'MOG' in inv_names %}
                <div class="shop-item"><div>Бейдж "MOG"</div><button class="btn-disabled" disabled>Куплено</button></div>
            {% else %}
                <div class="shop-item"><div>Бейдж "MOG" (14 дней)</div><button onclick="buyItem('badge', 'MOG', 5000, 0, this)">5,000 ₽</button></div>
            {% endif %}

            <h3>Донат-валюта (💎)</h3>
            <div class="shop-item" style="opacity: 0.7;"><div>100 💎<br><small style="color: #ff4444;">(Скоро)</small></div><button class="btn-disabled">Купить</button></div>
        </div>

        <div id="view-inventory" class="view">
            <h3>Инвентарь</h3>
            <h4 style="text-align:left; margin-bottom:5px;">Скины</h4>
            <div id="inv-skins" class="inventory-grid" style="margin-bottom:20px;"></div>
            <h4 style="text-align:left; margin-bottom:5px;">Бейджи</h4>
            <div id="inv-badges" class="inventory-grid"></div>
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

        <div id="view-top" class="view"><h3>Топ игроков</h3><div id="top-list">Загрузка...</div></div>

        <div id="view-mod" class="view">
            <h3 style="color: #ff4444;">Панель Модератора</h3>
            <p>Ваш ранг: <span style="color: var(--neon); font-weight: bold;">
                {% if user.mod_rank == 1 %}Младший Модератор{% elif user.mod_rank == 2 %}Старший Модератор{% elif user.mod_rank == 3 %}Администратор{% elif user.mod_rank == 4 %}Старший Администратор{% endif %}
            </span></p>
            
            <div class="mod-action-box">
                <h4 style="margin-top:0;">Выдать наказание</h4>
                <input type="text" id="mod-target" placeholder="Ник нарушителя">
                <input type="number" id="mod-duration" placeholder="Время в минутах">
                <input type="text" id="mod-reason" placeholder="Причина">
                
                <button class="btn-main btn-danger" onclick="doModAction('mute')">Замутить (Мут)</button>
                {% if user.mod_rank >= 3 %}
                    <button class="btn-main" style="background: #000; color: #ff0000; border: 1px solid #ff0000;" onclick="doModAction('ban')">Забанить (Бан)</button>
                {% endif %}
            </div>
        </div>

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
            <div style="display:flex; gap:10px;"><input type="text" id="promo-input" placeholder="Введите код..."><button class="btn-main" onclick="redeemPromo()" style="width:100px; margin-bottom:0;">Ввод</button></div>
            <div class="setting-item" style="background: rgba(255,0,0,0.1); border-color: #ff4444; flex-direction: column; margin-top:20px;">
                <p style="font-size: 12px; margin-bottom: 10px;">Опасная зона!</p><button class="btn-main btn-danger" onclick="resetProgress()" style="width:100%;">Сбросить прогресс</button>
            </div>
        </div>

        <div id="chat-container">
            <div id="chat-messages"></div>
            <div id="chat-mute-status" style="display:none;">Вы заглушены</div>
            <div id="chat-input-area">
                <div id="chat-reply-bar"><span id="reply-text-preview" style="color:var(--gold); font-weight:bold;"></span><br><span id="reply-message-preview" style="color:#aaa; font-size:11px;"></span><span class="close-reply" onclick="cancelReply()">×</span></div>
                <div class="chat-input-row">
                    <input type="text" id="chat-input" placeholder="Сообщение в чат..." onkeypress="handleChatEnter(event)">
                    {% if user.can_write_red %}
                    <label style="display:flex; align-items:center; justify-content:center; cursor:pointer; font-size:16px; width:30px; flex-shrink:0;" title="Красный текст">
                        <input type="checkbox" id="red-text-toggle" style="width:15px; height:15px; margin:0;">
                    </label>
                    {% endif %}
                    <button id="chat-send" class="btn-main" onclick="sendChat()">➤</button>
                </div>
            </div>
        </div>
    {% endif %}

    <!-- МОДАЛКИ -->
    <div class="modal" id="profile-modal">
        <div class="modal-content">
            <span class="close-btn" onclick="closeModal('profile-modal')">×</span>
            <div class="modal-title">Профиль игрока</div>
            <div class="info-label">НИК:</div><div class="info-value" id="p-nick"></div>
            <div class="info-label">БАЛАНС:</div><div class="info-value" id="p-balance" style="color: var(--gold); font-weight: bold;"></div>
            <div class="info-label">ДОНАТ-ВАЛЮТА:</div><div class="info-value" id="p-coins" style="color: var(--neon); font-weight: bold;"></div>
            <div class="info-label">МУЛЬТИКЛИК ЛВЛ:</div><div class="info-value" id="p-multi"></div>
            <div class="info-label">АВТОКЛИКЕР ЛВЛ:</div><div class="info-value" id="p-auto"></div>
            <div class="info-label">ДАТА РЕГИСТРАЦИИ:</div><div class="info-value" id="p-date"></div>
        </div>
    </div>

    <div class="modal" id="mod-info-modal">
        <div class="modal-content" style="border-color: var(--gold);">
            <span class="close-btn" onclick="closeModal('mod-info-modal')">×</span>
            <div class="modal-title" style="color: var(--gold);">Статус игрока</div>
            <div style="text-align:center; font-size: 50px; margin: 20px 0;">🛡️</div>
            <div class="info-label">НИК:</div><div class="info-value" id="m-nick"></div>
            <div class="info-label">ДОЛЖНОСТЬ:</div><div class="info-value" id="m-rank" style="color: var(--neon); font-weight: bold;"></div>
        </div>
    </div>

    <div class="modal" id="lang-modal"><div class="modal-content"><span class="close-btn" onclick="closeModal('lang-modal')">×</span><div class="modal-title">Язык</div><div class="custom-option" onclick="changeSetting('lang', 'ru')">Русский</div><div class="custom-option" onclick="changeSetting('lang', 'en')">English</div></div></div>
    <div class="modal" id="theme-modal"><div class="modal-content"><span class="close-btn" onclick="closeModal('theme-modal')">×</span><div class="modal-title">Тема</div><div class="custom-option" onclick="changeSetting('theme', 'dark')">Тёмная</div><div class="custom-option" onclick="changeSetting('theme', 'light')">Светлая</div><div class="custom-option" onclick="changeSetting('theme', 'neon')">Неон</div><div class="custom-option" onclick="changeSetting('theme', 'cyber')">Киберпанк</div><div class="custom-option" onclick="changeSetting('theme', 'ocean')">Океан</div><div class="custom-option" onclick="changeSetting('theme', 'retro')">Ретро</div></div></div>
    <div class="modal" id="font-modal"><div class="modal-content"><span class="close-btn" onclick="closeModal('font-modal')">×</span><div class="modal-title">Шрифт</div><div class="custom-option" onclick="changeSetting('font_family', 'Montserrat')" style="font-family:'Montserrat'">Montserrat</div><div class="custom-option" onclick="changeSetting('font_family', 'Play')" style="font-family:'Play'">Play</div><div class="custom-option" onclick="changeSetting('font_family', 'Russo One')" style="font-family:'Russo One'">Russo One</div><div class="custom-option" onclick="changeSetting('font_family', 'Comic Neue')" style="font-family:'Comic Neue'">Comic Neue</div></div></div>
    <div class="modal" id="other-ban-modal"><div class="modal-content" style="border-color: #ff4444;"><span class="close-btn" onclick="closeOtherBan()">×</span><div class="modal-title" style="color:#ff4444;">ЗАБАНЕН</div><div class="info-label">НИК:</div><div class="info-value" id="other-ban-nick"></div><div class="info-label">ПРИЧИНА:</div><div class="info-value" id="other-ban-reason" style="color:#ff4444;"></div><div class="info-label">ДО:</div><div class="info-value" id="other-ban-until" style="color:#ff4444; font-weight:bold;"></div></div></div>

    <script>
        let balance = parseFloat("{{ user.balance|default(0, true) }}");
        let clickPower = parseInt("{{ user.click_power|default(1, true) }}");
        let skinMult = parseFloat("{{ user.skin_mult|default(1, true) }}");
        let autoIncome = parseFloat("{{ user.auto_income|default(0, true) }}");
        let muteUntil = parseFloat("{{ user.mute_until|default(0, true) }}");
        
        let currentMultiPrice = parseInt("{{ multi_price }}");
        let currentAutoPrice = parseInt("{{ auto_price }}");

        let lastMessageTime = 0; // КД на чат

        function openModal(id) { document.getElementById(id).classList.add('active'); }
        function closeModal(id) { document.getElementById(id).classList.remove('active'); }

        let audioCtx = null;
        function initAudio() { try { if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)(); if (audioCtx.state === 'suspended') audioCtx.resume(); } catch(e) {} }
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
            playSound(type); 
            const container = document.getElementById('toast-container'); 
            
            // Ограничение в 3 уведомления
            if (container.children.length >= 3) {
                container.removeChild(container.firstElementChild);
            }
            
            const toast = document.createElement('div');
            toast.className = `toast ${type}`; toast.innerText = text; container.appendChild(toast); 
            setTimeout(() => toast.remove(), 3000);
        }

        function showModInfo(username, rank) {
            document.getElementById('m-nick').innerText = username;
            let rankName = '';
            if (rank === 1) rankName = 'Младший Модератор';
            else if (rank === 2) rankName = 'Старший Модератор';
            else if (rank === 3) rankName = 'Администратор';
            else if (rank === 4) rankName = 'Старший Администратор';
            document.getElementById('m-rank').innerText = rankName;
            openModal('mod-info-modal');
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
            if(tab === 'inventory') loadInventory();
        }

        function switchCasinoMode(mode) {
            document.getElementById('casino-coin-mode').style.display = mode === 'coin' ? 'block' : 'none';
            document.getElementById('casino-wheel-mode').style.display = mode === 'wheel' ? 'block' : 'none';
            document.getElementById('mode-coin').classList.toggle('active', mode === 'coin');
            document.getElementById('mode-wheel').classList.toggle('active', mode === 'wheel');
            document.getElementById('casino-result').innerText = '';
        }

        setInterval(() => {
            fetch('/api/user').then(r => { if(r.status === 403) { window.location.reload(); return; } return r.json(); }).then(data => {
                if(data && data.success) {
                    if(data.balance !== balance) { balance = data.balance; document.getElementById('score').innerText = Math.floor(balance) + ' ₽'; }
                    clickPower = data.click_power; autoIncome = data.auto_income; muteUntil = data.mute_until; skinMult = data.skin_mult;
                    document.getElementById('ui-click-power').innerText = clickPower; document.getElementById('ui-auto-income').innerText = autoIncome;
                    checkMuteStatus();
                }
            }).catch(()=>{});
        }, 2000);

        setInterval(() => {
            if(autoIncome <= 0) return;
            balance += autoIncome;
            document.getElementById('score').innerText = Math.floor(balance) + ' ₽';
            fetch('/api/click', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({amount: autoIncome}) });
        }, 1000);

        function clickCoin(e) {
            initAudio(); 
            let addAmount = clickPower * skinMult;
            balance += addAmount;
            const scoreEl = document.getElementById('score');
            scoreEl.innerText = Math.floor(balance) + ' ₽'; scoreEl.style.transform = "scale(1.1)";
            setTimeout(() => scoreEl.style.transform = "scale(1)", 100); playSound('click');
            const el = document.createElement('div'); el.className = 'floating'; el.innerText = '+' + addAmount + ' ₽';
            el.style.left = (e.clientX - 20) + 'px'; el.style.top = (e.clientY - 40) + 'px';
            document.body.appendChild(el); setTimeout(() => el.remove(), 800);
            fetch('/api/click', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({amount: clickPower}) })
            .then(res => { if(res.status === 403) { showToast("АБЬЮЗ!", 'error'); setTimeout(() => window.location.href = '/logout', 2000); } });
        }

        // --- КАЗИНО (МОНЕТКА) ---
        function playCasino(choice) {
            let bet = parseFloat(document.getElementById('casino-bet').value);
            if(!bet || bet <= 0) return showToast("Неверная ставка!", 'error');
            if(balance < bet) return showToast("Недостаточно денег!", 'error');
            
            let coinContainer = document.getElementById('coin-anim');
            let coinElement = document.getElementById('coin-element');
            let resEl = document.getElementById('casino-result');
            
            coinContainer.style.display = 'block';
            resEl.innerText = '';
            document.getElementById('casino-bet').disabled = true;
            
            // Крутим монетку
            coinElement.style.transition = 'none';
            coinElement.style.transform = 'rotateY(0deg)';
            
            setTimeout(() => { 
                coinElement.style.transition = 'transform 1.5s ease-out'; 
                coinElement.style.transform = 'rotateY(1800deg)'; 
            }, 50);

            setTimeout(() => {
                document.getElementById('casino-bet').disabled = false;
                
                fetch('/api/casino/bet', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({bet: bet, choice: choice, mode: 'coin'}) })
                .then(res => res.json()).then(data => {
                    if(data.success) {
                        balance = data.new_balance;
                        document.getElementById('score').innerText = Math.floor(balance) + ' ₽';
                        
                        // Поворачиваем монетку нужной стороной
                        if (data.result === 'heads') {
                            coinElement.style.transform = 'rotateY(1800deg)'; // Орел (лицо)
                        } else {
                            coinElement.style.transform = 'rotateY(1980deg)'; // Решка (оборот)
                        }

                        if(data.win) {
                            resEl.innerText = `ПОБЕДА! Выпало: ${data.result === 'heads' ? 'Орел' : 'Решка'} +${bet} ₽`;
                            resEl.style.color = 'var(--neon)';
                            playSound('success');
                        } else {
                            resEl.innerText = `ПРОИГРЫШ! Выпало: ${data.result === 'heads' ? 'Орел' : 'Решка'} -${bet} ₽`;
                            resEl.style.color = '#ff4444';
                            playSound('error');
                        }
                    } else showToast(data.error, 'error');
                });
            }, 1600);
        }

        // --- КАЗИНО (КОЛЕСО) ---
        function playWheel() {
            let bet = parseFloat(document.getElementById('wheel-bet').value);
            if(!bet || bet <= 0) return showToast("Неверная ставка!", 'error');
            if(balance < bet) return showToast("Недостаточно денег!", 'error');

            document.getElementById('wheel-anim').style.display = 'block';
            let resEl = document.getElementById('casino-result');
            resEl.innerText = '';
            document.getElementById('wheel-bet').disabled = true;
            
            let wheel = document.getElementById('wheel-element');
            
            fetch('/api/casino/bet', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({bet: bet, mode: 'wheel'}) })
            .then(res => res.json()).then(data => {
                if(data.success) {
                    let mult = data.mult;
                    let targetAngle = 0;
                    
                    if (mult === 0) targetAngle = 30;
                    else if (mult === 0.5) targetAngle = 90;
                    else if (mult === 1) targetAngle = 150;
                    else if (mult === 2) targetAngle = 210;
                    else if (mult === 5) targetAngle = 270;
                    
                    let spinDegrees = 1440 + (360 - targetAngle);
                    wheel.style.transform = `rotate(${spinDegrees}deg)`;

                    setTimeout(() => {
                        document.getElementById('wheel-bet').disabled = false;
                        balance = data.new_balance;
                        document.getElementById('score').innerText = Math.floor(balance) + ' ₽';
                        
                        if(data.mult > 1) {
                            resEl.innerText = `ВЫИГРЫШ x${data.mult}! +${bet * data.mult} ₽`;
                            resEl.style.color = 'var(--neon)';
                            playSound('success');
                        } else if(data.mult === 0) {
                            resEl.innerText = `x0. ПРОИГРЫШ! -${bet} ₽`;
                            resEl.style.color = '#ff4444';
                            playSound('error');
                        } else if(data.mult === 1) {
                            resEl.innerText = `x1. ВОЗВРАТ.`;
                            resEl.style.color = '#fff';
                            playSound('success');
                        } else {
                            resEl.innerText = `x${data.mult}. ПРОИГРЫШ! -${bet - (bet * data.mult)} ₽`;
                            resEl.style.color = '#ff4444';
                            playSound('error');
                        }
                        
                        setTimeout(() => { 
                            wheel.style.transition = 'none'; 
                            wheel.style.transform = 'rotate(0deg)'; 
                            setTimeout(() => wheel.style.transition = 'transform 3s cubic-bezier(0.1, 0.7, 0.1, 1)', 50);
                        }, 2000);
                    }, 3000); 
                } else showToast(data.error, 'error');
            });
        }

        // --- МАГАЗИН ---
        function buyUpgrade(type) {
            fetch('/api/buy', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({type: type}) })
            .then(res => res.json()).then(data => { 
                if(data.success) { 
                    showToast("Успешно!", 'success'); 
                    balance = data.new_balance; 
                    document.getElementById('score').innerText = Math.floor(balance) + ' ₽'; 
                    
                    if(type === 'multi') {
                        clickPower = data.new_power; currentMultiPrice = data.new_price;
                        document.getElementById('ui-click-power').innerText = clickPower;
                        document.getElementById('btn-multi').innerText = currentMultiPrice + ' ₽';
                    } else if(type === 'auto') {
                        autoIncome = data.new_income; currentAutoPrice = data.new_price;
                        document.getElementById('ui-auto-income').innerText = autoIncome;
                        document.getElementById('btn-auto').innerText = currentAutoPrice + ' ₽';
                    }
                } 
                else showToast(data.error, 'error'); 
            });
        }

        function buyItem(type, name, price, mult, btn) {
            if(balance < price) return showToast("Мало денег!", 'error');
            
            fetch('/api/buy_custom', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({type: type, name: name, price: price, mult: mult}) })
            .then(res => res.json()).then(data => { 
                if(data.success) { 
                    showToast("Куплено! Загляни в инвентарь.", 'success'); 
                    balance = data.new_balance; 
                    document.getElementById('score').innerText = Math.floor(balance) + ' ₽'; 
                    btn.innerText = 'Куплено';
                    btn.classList.add('btn-disabled');
                    btn.disabled = true;
                } 
                else showToast(data.error, 'error'); 
            });
        }

        // --- ИНВЕНТАРЬ ---
        function loadInventory() {
            fetch('/api/inventory').then(res => res.json()).then(data => {
                let skinsHtml = '';
                let badgesHtml = '';
                
                data.items.forEach(item => {
                    let btn = item.is_equipped 
                        ? `<button class="btn-danger" onclick="unequipItem(${item.id})">Снять</button>` 
                        : `<button onclick="equipItem(${item.id})">Надеть</button>`;
                    
                    let html = `<div class="inv-item">
                                    <h4>${item.item_name}</h4>
                                    <p>${item.item_type === 'skin' ? 'x' + item.item_mult : 'Бейдж'}</p>
                                    ${btn}
                                </div>`;
                                
                    if(item.item_type === 'skin') skinsHtml += html;
                    else badgesHtml += html;
                });
                
                document.getElementById('inv-skins').innerHTML = skinsHtml || '<div style="grid-column:1/-1; color:#888;">Пусто</div>';
                document.getElementById('inv-badges').innerHTML = badgesHtml || '<div style="grid-column:1/-1; color:#888;">Пусто</div>';
            });
        }

        function equipItem(id) {
            fetch('/api/equip', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id: id}) })
            .then(res => res.json()).then(data => {
                if(data.success) { showToast("Экипировано!", 'success'); loadInventory(); }
            });
        }

        function unequipItem(id) {
            fetch('/api/unequip', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id: id}) })
            .then(res => res.json()).then(data => {
                if(data.success) { showToast("Снято!", 'success'); loadInventory(); }
            });
        }

        // --- МОДЕРАЦИЯ ---
        function doModAction(action) {
            let target = document.getElementById('mod-target').value;
            let dur = parseInt(document.getElementById('mod-duration').value);
            let reason = document.getElementById('mod-reason').value;
            
            if(!target || !dur || !reason) return showToast("Заполни все поля!", 'error');
            
            fetch('/api/mod/action', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({action: action, target: target, duration: dur, reason: reason}) })
            .then(res => res.json()).then(data => {
                if(data.success) {
                    showToast(data.msg, 'success');
                    document.getElementById('mod-target').value = '';
                    document.getElementById('mod-duration').value = '';
                    document.getElementById('mod-reason').value = '';
                } else {
                    showToast(data.error, 'error');
                }
            });
        }

        // --- ОСТАЛЬНОЕ ---
        function loadTop() {
            fetch('/api/top').then(res => res.json()).then(data => {
                let html = ''; data.forEach((p, i) => {
                    let badgeClass = p.badge_color === 'rainbow' ? 'rainbow-text' : '';
                    let badgeStyle = p.badge_color !== 'rainbow' ? `background:${p.badge_color}; color:#000; border-color:${p.badge_color};` : '';
                    let badgeHtml = p.badge ? `<span class="badge ${badgeClass}" style="${badgeStyle}">${p.badge}</span>` : '';
                    let hammerHtml = p.is_banned ? `<span class="hammer" onclick="event.stopPropagation(); showOtherBan('${p.username}')">🔨</span>` : '';
                    let modHtml = p.mod_rank > 0 ? `<span class="mod-badge" onclick="event.stopPropagation(); showModInfo('${p.username}', ${p.mod_rank})">🛡️</span>` : '';
                    let nameClass = p.color === 'rainbow' ? 'rainbow-text' : '';
                    let nameStyle = p.color !== 'rainbow' ? `style="color:${p.color}; font-weight:bold;"` : '';
                    html += `<div class="top-player" onclick="openProfile('${p.username}')">
                                <span>#${i+1} <span class="${nameClass}" ${nameStyle}>${p.username}</span> ${modHtml} ${badgeHtml}${hammerHtml}</span> 
                                <span>${Math.floor(p.balance)} ₽</span>
                             </div>`;
                });
                document.getElementById('top-list').innerHTML = html;
            });
        }

        function openProfile(username) {
            fetch('/api/profile/' + username).then(res => res.json()).then(data => {
                if(data.error) return showToast("Error", "error");
                let nameClass = data.color === 'rainbow' ? 'rainbow-text' : '';
                let nameStyle = data.color !== 'rainbow' ? `style="color:${data.color}; font-weight:bold;"` : '';
                let badgeClass = data.badge_color === 'rainbow' ? 'rainbow-text' : '';
                let badgeStyle = data.badge_color !== 'rainbow' ? `background:${data.badge_color}; color:#000; border-color:${data.badge_color};` : '';
                let badgeHtml = data.badge ? `<span class="badge ${badgeClass}" style="${badgeStyle}">${data.badge}</span>` : '';
                let modHtml = data.mod_rank > 0 ? `<span class="mod-badge" onclick="showModInfo('${data.username}', ${data.mod_rank})">🛡️</span>` : '';
                
                document.getElementById('p-nick').innerHTML = `<span class="${nameClass}" ${nameStyle}>${data.username}</span> ${modHtml} ${badgeHtml}`;
                document.getElementById('p-balance').innerText = Math.floor(data.balance) + ' ₽';
                document.getElementById('p-coins').innerText = Math.floor(data.mog_coins) + ' 💎';
                document.getElementById('p-multi').innerText = data.click_power;
                document.getElementById('p-auto').innerText = data.auto_income + '/с';
                document.getElementById('p-date').innerText = data.created_at;
                openModal('profile-modal');
            });
        }

        let topBanInterval = null;
        function showOtherBan(username) {
            fetch('/api/ban_info/' + username).then(res => res.json()).then(data => {
                if(data.success) {
                    document.getElementById('other-ban-nick').innerText = data.username; document.getElementById('other-ban-reason').innerText = data.ban_reason;
                    let remaining = data.remaining; let text = "";
                    if(remaining > 0) { let d = Math.floor(remaining / 86400); let h = Math.floor((remaining % 86400) / 3600); let m = Math.floor((remaining % 3600) / 60); if(d>0) text+=d+"d "; if(h>0) text+=h+"h "; text+=m+"m"; } else text = "Expired";
                    document.getElementById('other-ban-until').innerText = text; openModal('other-ban-modal');
                }
            });
        }
        function closeOtherBan() { closeModal('other-ban-modal'); if(topBanInterval) clearInterval(topBanInterval); }

        function changeSetting(key, value) {
            if(key === 'theme') { document.body.className = 'theme-' + value; document.getElementById('display-theme').innerText = value; }
            if(key === 'lang') { document.getElementById('display-lang').innerText = value === 'ru' ? 'Русский' : 'English'; }
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
                let html = ''; data.forEach((t, i) => { html += `<div style="padding:5px 0; border-bottom:1px solid var(--border);">#${i+1} <b>${t.sender}</b> -> <b>${t.total}</b> ₽</div>`; });
                document.getElementById('transfer-top-list').innerHTML = html || '<div style="color:#888;">-</div>';
            });
            fetch('/api/transfers/my').then(res => res.json()).then(data => {
                let html = ''; data.forEach(t => { let date = new Date(t.timestamp * 1000).toLocaleString(); html += `<div style="padding:5px 0; border-bottom:1px solid var(--border);">Вы -> <b>${t.receiver}</b> (${t.amount} ₽) <br><span style="font-size:10px; color:#888;">${date}</span></div>`; });
                document.getElementById('my-transfer-list').innerHTML = html || '<div style="color:#888;">-</div>';
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
                    
                    let msgClass = m.is_red ? 'red-text-msg' : '';

                    html += `<div class="chat-msg ${msgClass}" onmousedown="startSwipe(event, '${m.username}', '${m.text.replace(/'/g, "\\'")}')" ontouchstart="startSwipe(event, '${m.username}', '${m.text.replace(/'/g, "\\'")}')">
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
            let now = Date.now();
            if (now - lastMessageTime < 3000) {
                return showToast("Подожди 3 секунды перед отправкой!", 'error');
            }
            lastMessageTime = now;

            let inp = document.getElementById('chat-input');
            if(!inp.value.trim()) return;
            let isRed = false;
            let toggle = document.getElementById('red-text-toggle');
            if (toggle) isRed = toggle.checked;

            fetch('/api/chat/send', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text: inp.value, reply_user: currentReplyUser, reply_text: currentReplyText, is_red: isRed}) })
            .then(res => res.json()).then(data => { 
                if(data.success) { inp.value = ''; cancelReply(); loadChat(); } 
                else { 
                    showToast(data.error, 'error'); 
                    lastMessageTime = 0; // Сбрасываем кд, если ошибка
                } 
            });
        }
        function handleChatEnter(e) { if(e.key === 'Enter') sendChat(); }

        function checkMuteStatus() {
            let now = Math.floor(Date.now() / 1000); 
            let muteTimeLeft = muteUntil - now;
            let inputArea = document.getElementById('chat-input-area'); 
            let muteStatus = document.getElementById('chat-mute-status');
            
            if(muteTimeLeft > 1) { 
                inputArea.style.display = 'none'; 
                muteStatus.style.display = 'block'; 
                let m = Math.floor(muteTimeLeft / 60); 
                let s = muteTimeLeft % 60; 
                muteStatus.innerText = `Вы заглушены на ${m}м ${s}с`; 
            }
            else { 
                inputArea.style.display = 'flex'; 
                muteStatus.style.display = 'none'; 
            }
        }
        setInterval(checkMuteStatus, 1000);
        
        window.onload = () => { 
            setInterval(loadChat, 3000); loadChat(); checkMuteStatus(); 
        };
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    user = None
    remaining_seconds = 0
    inv_names = []
    
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if not user: 
            session.pop('user_id', None)
        elif user.is_banned:
            if time.time() >= user.ban_until:
                user.is_banned = 0
                user.ban_reason = ""
                user.ban_msg = ""
                user.ban_until = 0
                user.ban_duration = ""
                db.session.commit()
            else: 
                remaining_seconds = int(user.ban_until - time.time())
        if user and user.badge_expire > 0 and time.time() > user.badge_expire:
            user.badge = ''
            user.badge_expire = 0
            db.session.commit()
            
        if user:
            inv_items = Inventory.query.filter_by(user_id=user.id).all()
            inv_names = [item.item_name for item in inv_items]

    multi_price = int(100 * (1.2 ** (user.click_power - 1))) if user and not user.is_banned else 100
    auto_price = int(250 * (1.2 ** user.auto_income)) if user and not user.is_banned else 250
    return render_template_string(HTML_CODE, user=user, multi_price=multi_price, auto_price=auto_price, remaining_seconds=remaining_seconds, inv_names=inv_names)

@app.route('/api/user')
def api_user():
    if 'user_id' not in session: 
        return jsonify({'error': 'Auth'}), 401
    user = User.query.get(session['user_id'])
    if not user: 
        return jsonify({'error': 'No user'}), 401
    if user.is_banned: 
        return jsonify({'error': 'Banned'}), 403
    return jsonify({'success': True, 'balance': user.balance, 'click_power': user.click_power, 'auto_income': user.auto_income, 'mute_until': user.mute_until, 'skin_mult': user.skin_mult})

@app.route('/api/profile/<username>')
def api_profile(username):
    user = User.query.filter_by(username=username).first()
    if not user: 
        return jsonify({'error': 'Not found'}), 404
    date_str = time.strftime('%d.%m.%Y', time.localtime(user.created_at if user.created_at else time.time()))
    return jsonify({
        'username': user.username,
        'balance': user.balance,
        'mog_coins': user.mog_coins,
        'badge': user.badge,
        'badge_color': user.badge_color,
        'color': user.color,
        'click_power': user.click_power,
        'auto_income': user.auto_income,
        'mod_rank': user.mod_rank,
        'created_at': date_str
    })

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    u, p = data['username'], data['password']
    if re.search('[а-яА-ЯёЁ]', u) or re.search('[а-яА-ЯёЁ]', p): 
        return jsonify({'error': 'Cyrillic'}), 400
    if User.query.filter_by(username=u).first(): 
        return jsonify({'error': 'Taken'}), 400
    user = User(username=u, password=generate_password_hash(p))
    db.session.add(user)
    db.session.commit()
    session.permanent = True
    session['user_id'] = user.id
    return jsonify({'success': True}), 200

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if user and check_password_hash(user.password, data['password']):
        if user.is_banned:
            if time.time() >= user.ban_until:
                user.is_banned = 0
                user.ban_reason = ""
                user.ban_msg = ""
                user.ban_until = 0
                user.ban_duration = ""
                db.session.commit()
            else: 
                return jsonify({'banned': True}), 403
        session.permanent = True
        session['user_id'] = user.id
        return jsonify({'success': True}), 200
    return jsonify({'error': 'Bad auth'}), 401

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/api/click', methods=['POST'])
def api_click():
    if 'user_id' not in session: 
        return jsonify({'error': 'Auth'}), 401
    user = User.query.get(session['user_id'])
    if not user: 
        return jsonify({'error': 'No user'}), 401
    if user.is_banned:
        db.session.delete(user)
        db.session.commit()
        session.pop('user_id', None)
        return jsonify({'error': 'banned_deleted'}), 403
    
    amount = request.json.get('amount', 1) * user.skin_mult
    user.balance += amount
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/casino/bet', methods=['POST'])
def api_casino_bet():
    if 'user_id' not in session: 
        return jsonify({'error': 'Auth'}), 401
    data = request.json
    bet = float(data.get('bet', 0))
    mode = data.get('mode', 'coin')
    
    user = User.query.get(session['user_id'])
    if not user or bet <= 0 or user.balance < bet:
        return jsonify({'error': 'Invalid bet'}), 400
        
    if mode == 'coin':
        choice = data.get('choice')
        result = random.choice(['heads', 'tails'])
        win = (result == choice)
        if win: user.balance += bet
        else: user.balance -= bet
        db.session.commit()
        return jsonify({'success': True, 'win': win, 'result': result, 'new_balance': user.balance})
        
    elif mode == 'wheel':
        weights = [(0, 30), (0.5, 30), (1, 20), (2, 15), (5, 5)]
        total = sum(w[1] for w in weights)
        r = random.randint(1, total)
        current = 0
        mult = 1
        for val, weight in weights:
            current += weight
            if r <= current:
                mult = val
                break
        win_amount = bet * mult
        user.balance -= bet
        user.balance += win_amount
        db.session.commit()
        return jsonify({'success': True, 'mult': mult, 'new_balance': user.balance})

    return jsonify({'error': 'Invalid mode'}), 400

@app.route('/api/buy', methods=['POST'])
def api_buy():
    if 'user_id' not in session: 
        return jsonify({'error': 'Auth'}), 401
    type = request.json.get('type')
    user = User.query.get(session['user_id'])
    
    if type == 'multi':
        price = int(100 * (1.2 ** (user.click_power - 1)))
        if user.balance >= price:
            user.balance -= price
            user.click_power += 1
            db.session.commit()
            new_price = int(100 * (1.2 ** (user.click_power - 1)))
            return jsonify({'success': True, 'new_balance': user.balance, 'new_power': user.click_power, 'new_price': new_price})
    elif type == 'auto':
        price = int(250 * (1.2 ** user.auto_income))
        if user.balance >= price:
            user.balance -= price
            user.auto_income += 1
            db.session.commit()
            new_price = int(250 * (1.2 ** user.auto_income))
            return jsonify({'success': True, 'new_balance': user.balance, 'new_income': user.auto_income, 'new_price': new_price})
    return jsonify({'error': 'No money'}), 400

@app.route('/api/buy_custom', methods=['POST'])
def api_buy_custom():
    if 'user_id' not in session: 
        return jsonify({'error': 'Auth'}), 401
    data = request.json
    user = User.query.get(session['user_id'])
    
    if user.balance >= data['price']:
        existing = Inventory.query.filter_by(user_id=user.id, item_type=data['type'], item_name=data['name']).first()
        if existing:
            return jsonify({'error': 'У вас уже есть этот предмет'}), 400
            
        user.balance -= data['price']
        inv_item = Inventory(user_id=user.id, item_type=data['type'], item_name=data['name'], item_mult=data.get('mult', 0))
        db.session.add(inv_item)
        
        if data['type'] == 'badge':
            user.badge = data['name']
            user.badge_color = '#00ffcc'
            user.badge_expire = time.time() + 14 * 86400
            
        db.session.commit()
        return jsonify({'success': True, 'new_balance': user.balance})
    return jsonify({'error': 'No money'}), 400

@app.route('/api/inventory')
def api_inventory():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    user = User.query.get(session['user_id'])
    items = Inventory.query.filter_by(user_id=user.id).all()
    res = []
    for i in items:
        is_equipped = False
        if i.item_type == 'skin' and user.skin == i.item_name: is_equipped = True
        if i.item_type == 'badge' and user.badge == i.item_name: is_equipped = True
        
        res.append({'id': i.id, 'item_type': i.item_type, 'item_name': i.item_name, 'item_mult': i.item_mult, 'is_equipped': is_equipped})
    return jsonify({'items': res})

@app.route('/api/equip', methods=['POST'])
def api_equip():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    data = request.json
    user = User.query.get(session['user_id'])
    item = Inventory.query.get(data['id'])
    
    if not item or item.user_id != user.id: return jsonify({'error': 'Not found'}), 404
    
    if item.item_type == 'skin':
        user.skin = item.item_name
        user.skin_mult = item.item_mult
    elif item.item_type == 'badge':
        user.badge = item.item_name
        user.badge_expire = time.time() + 14 * 86400
        
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/unequip', methods=['POST'])
def api_unequip():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    data = request.json
    user = User.query.get(session['user_id'])
    item = Inventory.query.get(data['id'])
    
    if not item or item.user_id != user.id: return jsonify({'error': 'Not found'}), 404
    
    if item.item_type == 'skin' and user.skin == item.item_name:
        user.skin = ''
        user.skin_mult = 1.0
    elif item.item_type == 'badge' and user.badge == item.item_name:
        user.badge = ''
        user.badge_color = '#ffffff'
        user.badge_expire = 0
        
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/mod/action', methods=['POST'])
def api_mod_action():
    if 'user_id' not in session: return jsonify({'error': 'Auth'}), 401
    mod = User.query.get(session['user_id'])
    data = request.json
    action = data.get('action')
    target_name = data.get('target')
    duration = int(data.get('duration', 0))
    reason = data.get('reason', 'Без причины')
    
    target = User.query.filter_by(username=target_name).first()
    if not target: return jsonify({'error': 'Игрок не найден'}), 404
    if target.id == mod.id: return jsonify({'error': 'Себе нельзя'}), 400
    if target.mod_rank >= mod.mod_rank: return jsonify({'error': 'У вас недостаточно прав для этого игрока'}), 403
    
    if action == 'mute':
        if mod.mod_rank == 1 and duration > 15:
            return jsonify({'error': 'Младший модератор может мутить максимум на 15 минут'}), 403
        target.mute_until = time.time() + (duration * 60)
        db.session.commit()
        return jsonify({'success': True, 'msg': f'Игрок {target_name} заглушен на {duration} мин.'})
        
    elif action == 'ban':
        if mod.mod_rank < 3:
            return jsonify({'error': 'Банить могут только Администраторы'}), 403
        target.is_banned = 1
        target.ban_reason = reason
        target.ban_until = time.time() + (duration * 60)
        target.ban_duration = f"{duration}m"
        db.session.commit()
        return jsonify({'success': True, 'msg': f'Игрок {target_name} забанен на {duration} мин.'})
        
    return jsonify({'error': 'Неизвестное действие'}), 400

@app.route('/api/top')
def api_top():
    users = User.query.order_by(User.balance.desc()).limit(10).all()
    return jsonify([{'username': u.username, 'balance': u.balance, 'color': u.color, 'badge': u.badge, 'badge_color': u.badge_color, 'is_banned': u.is_banned, 'mod_rank': u.mod_rank} for u in users])

@app.route('/api/ban_info/<username>')
def api_ban_info(username):
    user = User.query.filter_by(username=username, is_banned=1).first()
    if user: 
        return jsonify({'success': True, 'username': user.username, 'ban_reason': user.ban_reason, 'ban_msg': user.ban_msg, 'remaining': max(0, int(user.ban_until - time.time()))})
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/settings', methods=['POST'])
def api_settings():
    if 'user_id' not in session: 
        return jsonify({'error': 'Auth'}), 401
    data = request.json
    user = User.query.get(session['user_id'])
    setattr(user, data['key'], data['value'])
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/reset', methods=['POST'])
def api_reset():
    if 'user_id' not in session: 
        return jsonify({'error': 'Auth'}), 401
    user = User.query.get(session['user_id'])
    user.balance = 0
    user.click_power = 1
    user.auto_income = 0
    user.color = '#ffffff'
    user.badge = ''
    user.badge_color = '#ffffff'
    user.skin = ''
    user.skin_mult = 1.0
    Inventory.query.filter_by(user_id=user.id).delete()
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/transfer', methods=['POST'])
def api_transfer():
    if 'user_id' not in session: 
        return jsonify({'error': 'Auth'}), 401
    data = request.json
    amount = data['amount']
    receiver = data['receiver']
    if amount <= 0: 
        return jsonify({'error': 'Неверная сумма'}), 400
    sender = User.query.get(session['user_id'])
    target = User.query.filter_by(username=receiver).first()
    if not target: 
        return jsonify({'error': 'Игрок не найден'}), 404
    if sender.username == receiver: 
        return jsonify({'error': 'Себе нельзя'}), 400
    if sender.balance < amount: 
        return jsonify({'error': 'Мало денег'}), 400
    sender.balance -= amount
    target.balance += amount
    db.session.add(Transfer(sender=sender.username, receiver=receiver, amount=amount, timestamp=time.time()))
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/transfers/top')
def api_transfers_top():
    period = request.args.get('period', 'all')
    now = time.time()
    start = now - 86400 if period == 'day' else (now - 2592000 if period == 'month' else 0)
    from sqlalchemy import func
    rows = db.session.query(Transfer.sender, func.sum(Transfer.amount).label('total')).filter(Transfer.timestamp >= start).group_by(Transfer.sender).order_by(func.sum(Transfer.amount).desc()).limit(10).all()
    return jsonify([{'sender': r.sender, 'total': r.total} for r in rows])

@app.route('/api/transfers/my')
def api_transfers_my():
    if 'user_id' not in session: 
        return jsonify([])
    user = User.query.get(session['user_id'])
    rows = Transfer.query.filter_by(sender=user.username).order_by(Transfer.timestamp.desc()).limit(20).all()
    return jsonify([{'receiver': r.receiver, 'amount': r.amount, 'timestamp': r.timestamp} for r in rows])

@app.route('/api/chat/get')
def api_chat_get():
    msgs = ChatMessage.query.order_by(ChatMessage.timestamp.desc()).limit(50).all()
    res = []
    for m in reversed(msgs):
        u = User.query.filter_by(username=m.username).first()
        res.append({
            'username': m.username, 
            'text': m.text, 
            'timestamp': m.timestamp, 
            'reply_user': m.reply_user, 
            'reply_text': m.reply_text, 
            'color': u.color if u else '#fff', 
            'badge': u.badge if u else '', 
            'badge_color': u.badge_color if u else '#fff',
            'is_red': m.is_red
        })
    return jsonify(res)

@app.route('/api/chat/send', methods=['POST'])
def api_chat_send():
    if 'user_id' not in session: 
        return jsonify({'error': 'Auth'}), 401
    data = request.json
    text = data.get('text', '').strip()
    if not text: 
        return jsonify({'error': 'Пустое'}), 400
    user = User.query.get(session['user_id'])
    if user.mute_until > time.time(): 
        return jsonify({'error': 'Вы заглушены!'}), 403
    
    is_red = data.get('is_red', False) and user.can_write_red
    
    msg = ChatMessage(username=user.username, text=text[:100], timestamp=time.time(), reply_user=data.get('reply_user', ''), reply_text=data.get('reply_text', '')[:50], is_red=is_red)
    db.session.add(msg)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/promo/redeem', methods=['POST'])
def api_promo_redeem():
    if 'user_id' not in session: 
        return jsonify({'error': 'Auth'}), 401
    code = request.json.get('code', '').strip()
    promo = Promocode.query.filter_by(code=code).first()
    if not promo or promo.uses_left <= 0: 
        return jsonify({'error': 'Недействительный код'}), 400
    user = User.query.get(session['user_id'])
    if promo.type == 'money': 
        user.balance += float(promo.value)
    elif promo.type == 'coins': 
        user.mog_coins += float(promo.value)
    elif promo.type == 'badge': 
        user.badge = promo.value
        user.badge_expire = time.time() + 14 * 86400
    elif promo.type == 'color': 
        user.color = promo.value
    promo.uses_left -= 1
    db.session.commit()
    return jsonify({'success': True})

ADMIN_SECRET_TOKEN = "MOG_SECRET_2026"

@app.route('/api/admin/command', methods=['POST'])
def api_admin_command():
    data = request.json
    if data.get('token') != ADMIN_SECRET_TOKEN: 
        return jsonify({'error': 'Доступ запрещен'}), 403
    cmd_str = data.get('command', '').strip()
    if not cmd_str: 
        return jsonify({'error': 'Пустая команда'})
    
    parts = cmd_str.split()
    action = parts[0]
    
    try:
        if action == '/createuser' and len(parts) >= 3:
            if User.query.filter_by(username=parts[1]).first(): 
                return jsonify({'error': 'Ник занят'})
            new_u = User(username=parts[1], password=generate_password_hash(parts[2]))
            db.session.add(new_u)
            db.session.commit()
            return jsonify({'success': True, 'msg': f'Аккаунт {parts[1]} создан'})
            
        elif action == '/promo' and len(parts) >= 5:
            p_code, p_type, p_val, p_uses = parts[1], parts[2], parts[3], int(parts[4])
            if Promocode.query.get(p_code): 
                return jsonify({'error': 'Промокод уже есть'})
            db.session.add(Promocode(code=p_code, type=p_type, value=p_val, uses_left=p_uses))
            db.session.commit()
            return jsonify({'success': True, 'msg': f'Промокод {p_code} создан'})

        target = parts[1] if len(parts) > 1 else ""
        user = User.query.filter_by(username=target).first()
        if not user: 
            return jsonify({'error': f'Игрок {target} не найден'})
            
        if action == '/give' and len(parts) >= 3:
            try: amount = float(parts[2])
            except ValueError: return jsonify({'error': 'Сумма должна быть числом'})
            user.balance += amount
            db.session.commit()
            return jsonify({'success': True, 'msg': f'Выдано {amount} ₽'})
            
        elif action == '/givecoins' and len(parts) >= 3:
            try: amount = float(parts[2])
            except ValueError: return jsonify({'error': 'Сумма должна быть числом'})
            user.mog_coins += amount
            db.session.commit()
            return jsonify({'success': True, 'msg': f'Выдано {amount} MOG Coins'})
            
        elif action == '/givebadge' and len(parts) >= 3: 
            user.badge = parts[2]
            user.badge_expire = time.time() + 14 * 86400
            db.session.add(Inventory(user_id=user.id, item_type='badge', item_name=parts[2]))
            db.session.commit()
            return jsonify({'success': True, 'msg': f'Бейдж выдан'})
            
        elif action == '/setcolor' and len(parts) >= 3: 
            user.color = parts[2]
            db.session.commit()
            return jsonify({'success': True, 'msg': f'Цвет изменен'})
            
        elif action == '/setbadgecolor' and len(parts) >= 3: 
            user.badge_color = parts[2]
            db.session.commit()
            return jsonify({'success': True, 'msg': f'Цвет бейджа изменен'})
            
        elif action == '/givered': 
            user.can_write_red = True
            db.session.commit()
            return jsonify({'success': True, 'msg': f'Доступ к красному чату выдан'})
            
        elif action == '/removered': 
            user.can_write_red = False
            db.session.commit()
            return jsonify({'success': True, 'msg': f'Доступ к красному чату забран'})

        elif action == '/giveskin' and len(parts) >= 4:
            skin_name = parts[2]
            skin_mult = float(parts[3])
            user.skin = skin_name
            user.skin_mult = skin_mult
            db.session.add(Inventory(user_id=user.id, item_type='skin', item_name=skin_name, item_mult=skin_mult))
            db.session.commit()
            return jsonify({'success': True, 'msg': f'Скин {skin_name} (x{skin_mult}) выдан'})
            
        elif action == '/setmod' and len(parts) >= 3:
            rank = int(parts[2])
            user.mod_rank = rank
            db.session.commit()
            return jsonify({'success': True, 'msg': f'Игроку {target} выдан мод-ранг {rank}'})
            
        elif action == '/ban' and len(parts) >= 3:
            duration = parts[2]
            reason = " ".join(parts[3:]) if len(parts) > 3 else "Без причины"
            sec = 60
            if 'm' in duration: sec = int(duration.replace('m','')) * 60
            elif 'h' in duration: sec = int(duration.replace('h','')) * 3600
            elif 'd' in duration: sec = int(duration.replace('d','')) * 86400
            user.is_banned = 1
            user.ban_reason = reason
            user.ban_until = time.time() + sec
            user.ban_duration = duration
            db.session.commit()
            return jsonify({'success': True, 'msg': f'Игрок {target} забанен на {duration}'})
            
        elif action == '/mute' and len(parts) >= 3:
            duration = parts[2]
            sec = 60
            if 'm' in duration: sec = int(duration.replace('m','')) * 60
            elif 'h' in duration: sec = int(duration.replace('h','')) * 3600
            user.mute_until = time.time() + sec
            db.session.commit()
            return jsonify({'success': True, 'msg': f'Игрок {target} заглушен на {duration}'})
            
        elif action == '/reset': 
            user.balance = 0
            user.click_power = 1
            user.auto_income = 0
            user.skin = ''
            user.skin_mult = 1.0
            Inventory.query.filter_by(user_id=user.id).delete()
            db.session.commit()
            return jsonify({'success': True, 'msg': f'Прогресс сброшен'})
            
        return jsonify({'error': 'Неизвестная команда'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, use_reloader=False)

import sqlite3
import os
import re
import time
import random
import string
from werkzeug.security import generate_password_hash

def get_db():
    conn = sqlite3.connect('mogclicker.db')
    conn.row_factory = sqlite3.Row
    return conn

def clear(): os.system('clear')

def parse_duration(dur_str):
    match = re.match(r'^(\d+)([smhd])$', dur_str.lower())
    if not match: return None
    val, unit = int(match.group(1)), match.group(2)
    return val * {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[unit]

def print_menu():
    print("\033[96m╔══════════════════════════════════════════╗")
    print("║      💻 MOGCLICKER ADMIN CONSOLE       ║")
    print("╚══════════════════════════════════════════╝\033[0m")
    print("\033[93m 1.\033[0m Выдать рубли        \033[93m2.\033[0m Выдать бейдж")
    print("\033[93m 3.\033[0m Цвет (ник/бейдж)    \033[93m4.\033[0m Создать аккаунт")
    print("\033[93m 5.\033[0m Сбросить прогресс   \033[93m6.\033[0m Забанить (с причиной)")
    print("\033[93m 7.\033[0m Разбанить           \033[93m8.\033[0m Замутить (в чате)")
    print("\033[93m 9.\033[0m Размутить           \033[93m10.\033[0m Создать промокод")
    print("\033[93m 0.\033[0m Выход")
    print("\033[96m════════════════════════════════════════════\033[0m")

def main():
    clear(); print_menu()
    while True:
        try:
            choice = input("\033[95mВыбери действие (0-10): \033[0m").strip()
            if choice == '0': break
            if choice not in [str(i) for i in range(11)]:
                print("\033[91m❌ Неверный выбор.\033[0m"); continue

            if choice == '4':
                u = input("\033[96mВведи ник: \033[0m").strip(); p = input("\033[96mВведи пароль: \033[0m").strip()
                with get_db() as conn:
                    try:
                        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (u, generate_password_hash(p))); conn.commit()
                        print(f"\033[92m✅ Аккаунт {u} создан!\033[0m")
                    except sqlite3.IntegrityError: print(f"\033[91m❌ Ник {u} уже занят.\033[0m")
                continue

            if choice == '10':
                code = input("\033[96mВведи промокод: \033[0m").strip()
                reward = float(input("\033[96mНаграда (₽): \033[0m").strip())
                uses = int(input("\033[96mКол-во активаций: \033[0m").strip())
                with get_db() as conn:
                    try:
                        conn.execute('INSERT INTO promocodes (code, reward, uses_left) VALUES (?, ?, ?)', (code, reward, uses))
                        conn.commit(); print(f"\033[92m✅ Промокод {code} создан на {uses} активаций!\033[0m")
                    except sqlite3.IntegrityError: print("\033[91m❌ Такой код уже есть.\033[0m")
                continue

            target = input("\033[96mВведи ник игрока: \033[0m").strip()
            with get_db() as conn:
                user = conn.execute('SELECT * FROM users WHERE username = ?', (target,)).fetchone()
                if not user: print(f"\033[91m❌ Игрок {target} не найден.\033[0m"); continue

                if choice == '1': 
                    amount = input("\033[96mСумма: \033[0m").strip()
                    conn.execute('UPDATE users SET balance = balance + ? WHERE username = ?', (float(amount), target)); conn.commit()
                    print(f"\033[92m✅ Выдано {amount} ₽.\033[0m")

                elif choice == '2': 
                    badge = input("\033[96mБейдж: \033[0m").strip()
                    conn.execute('UPDATE users SET badge = ? WHERE username = ?', (badge, target)); conn.commit()
                    print(f"\033[92m✅ Бейдж выдан.\033[0m")

                elif choice == '3': 
                    tc = input("\033[96m(1-Ник, 2-Бейдж): \033[0m").strip()
                    color = input("\033[96mЦвет (hex или rainbow): \033[0m").strip().lower()
                    if 'rain' in color or 'рад' in color: color = 'rainbow'
                    elif not color.startswith('#') and color != 'rainbow': color = '#' + color
                    if tc == '1': conn.execute('UPDATE users SET color = ? WHERE username = ?', (color, target))
                    else: conn.execute('UPDATE users SET badge_color = ? WHERE username = ?', (color, target))
                    conn.commit(); print(f"\033[92m✅ Цвет изменен.\033[0m")

                elif choice == '5': 
                    conn.execute('UPDATE users SET balance=0, click_power=1, auto_income=0, color="#ffffff", badge="", badge_color="#ffffff" WHERE username = ?', (target,))
                    conn.commit(); print(f"\033[92m✅ Прогресс сброшен.\033[0m")

                elif choice == '6':
                    reason = input("\033[96mПричина: \033[0m").strip(); msg = input("\033[96mСообщение: \033[0m").strip()
                    dur = input("\033[96mНа сколько (60m, 14s, 2h): \033[0m").strip()
                    sec = parse_duration(dur)
                    if sec is None: print("\033[91m❌ Неверный формат.\033[0m"); continue
                    conn.execute('UPDATE users SET is_banned = 1, ban_reason = ?, ban_msg = ?, ban_until = ?, ban_duration = ? WHERE username = ?', (reason, msg, time.time() + sec, dur, target))
                    conn.commit(); print(f"\033[91m🔨 Забанен на {dur}!\033[0m")
                
                elif choice == '7':
                    conn.execute('UPDATE users SET is_banned = 0 WHERE username = ?', (target,)); conn.commit()
                    print(f"\033[92m✅ Разбанен.\033[0m")

                elif choice == '8':
                    dur = input("\033[96mМут на сколько (5m, 1h): \033[0m").strip()
                    sec = parse_duration(dur)
                    if sec is None: print("\033[91m❌ Неверный формат.\033[0m"); continue
                    conn.execute('UPDATE users SET mute_until = ? WHERE username = ?', (time.time() + sec, target))
                    conn.commit(); print(f"\033[91m🔇 Замучен на {dur}!\033[0m")

                elif choice == '9':
                    conn.execute('UPDATE users SET mute_until = 0 WHERE username = ?', (target,)); conn.commit()
                    print(f"\033[92m✅ Размучен.\033[0m")

        except KeyboardInterrupt: break
        except Exception as e: print(f"\033[91m❌ Ошибка: {e}\033[0m")

if __name__ == '__main__': main()

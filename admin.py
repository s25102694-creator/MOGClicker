import os
import requests
import time

API_URL = "https://mogclicker.relaxdev.ru/api/admin/command"
TOKEN = "MOG_SECRET_2026"

def clear():
    os.system('clear')

def send_command(cmd):
    try:
        res = requests.post(API_URL, json={'token': TOKEN, 'command': cmd}, timeout=10)
        data = res.json()
        if data.get('success'):
            print(f"\033[92m✅ {data['msg']}\033[0m")
        else:
            print(f"\033[91m❌ Ошибка: {data.get('error')}\033[0m")
    except Exception as e:
        print(f"\033[91m❌ Ошибка сети: {e}\033[0m")

def print_menu():
    print("\033[96m╔══════════════════════════════════════════╗")
    print("║  💻 MOGCLICKER CLOUD CONSOLE (API)     ║")
    print("╚══════════════════════════════════════════╝\033[0m")
    print("\033[93m 1.\033[0m Выдать рубли        \033[93m2.\033[0m Выдать бейдж")
    print("\033[93m 3.\033[0m Цвет ника           \033[93m4.\033[0m Создать аккаунт")
    print("\033[93m 5.\033[0m Сбросить прогресс   \033[93m6.\033[0m Забанить игрока")
    print("\033[93m 7.\033[0m Замутить игрока     \033[93m8.\033[0m Выдать MOG Coins")
    print("\033[93m 9.\033[0m Создать промокод    \033[93m10.\033[0m Цвет бейджа")
    print("\033[93m 11.\033[0m Выдать красный чат  \033[93m12.\033[0m Забрать красный чат")
    print("\033[93m 13.\033[0m Выдать скин (Клик)  \033[93m14.\033[0m Выдать мод-ранг")
    print("\033[93m 0.\033[0m Выход")
    print("\033[96m════════════════════════════════════════════\033[0m")

def main():
    clear()
    print_menu()
    
    while True:
        try:
            choice = input("\033[95mВыбери действие (0-14): \033[0m").strip()
            if choice == '0': break
            if choice not in [str(i) for i in range(15)]:
                print("\033[91m❌ Неверный выбор.\033[0m"); continue

            if choice == '4':
                u = input("\033[96mВведи ник: \033[0m").strip()
                p = input("\033[96mВведи пароль: \033[0m").strip()
                send_command(f"/createuser {u} {p}")
                continue
                
            if choice == '9':
                code = input("\033[96mКод промокода: \033[0m").strip()
                p_type = input("\033[96mТип (money, coins, badge, color): \033[0m").strip()
                p_val = input("\033[96mЗначение (сумма, текст или #hex): \033[0m").strip()
                uses = input("\033[96mКол-во активаций: \033[0m").strip()
                send_command(f"/promo {code} {p_type} {p_val} {uses}")
                continue

            target = input("\033[96mВведи ник игрока: \033[0m").strip()
            
            if choice == '1': 
                amount = input("\033[96mСумма: \033[0m").strip()
                send_command(f"/give {target} {amount}")
            elif choice == '2': 
                badge = input("\033[96mБейдж: \033[0m").strip()
                send_command(f"/givebadge {target} {badge}")
            elif choice == '3': 
                color = input("\033[96mЦвет (hex или rainbow): \033[0m").strip().lower()
                if 'rain' in color or 'рад' in color: color = 'rainbow'
                elif not color.startswith('#') and color != 'rainbow': color = '#' + color
                send_command(f"/setcolor {target} {color}")
            elif choice == '5': 
                send_command(f"/reset {target}")
            elif choice == '6':
                dur = input("\033[96mНа сколько (60m, 2h, 1d): \033[0m").strip()
                reason = input("\033[96mПричина: \033[0m").strip()
                send_command(f"/ban {target} {dur} {reason}")
            elif choice == '7':
                dur = input("\033[96mМут на сколько (5m, 1h): \033[0m").strip()
                send_command(f"/mute {target} {dur}")
            elif choice == '8':
                amount = input("\033[96mСумма MOG Coins: \033[0m").strip()
                send_command(f"/givecoins {target} {amount}")
            elif choice == '10':
                color = input("\033[96mЦвет бейджа (hex или rainbow): \033[0m").strip().lower()
                if 'rain' in color or 'рад' in color: color = 'rainbow'
                elif not color.startswith('#') and color != 'rainbow': color = '#' + color
                send_command(f"/setbadgecolor {target} {color}")
            elif choice == '11':
                send_command(f"/givered {target}")
            elif choice == '12':
                send_command(f"/removered {target}")
            elif choice == '13':
                skin_name = input("\033[96mНазвание скина (напр. Gold): \033[0m").strip()
                skin_mult = input("\033[96mМножитель (напр. 2.0): \033[0m").strip()
                send_command(f"/giveskin {target} {skin_name} {skin_mult}")
            elif choice == '14':
                rank = input("\033[96mРанг (1 - Мл.Мод, 2 - Ст.Мод, 3 - Админ, 4 - Ст.Админ, 0 - Снять): \033[0m").strip()
                send_command(f"/setmod {target} {rank}")

        except KeyboardInterrupt: break
        except Exception as e: print(f"\033[91m❌ Ошибка: {e}\033[0m")

if __name__ == '__main__':
    main()

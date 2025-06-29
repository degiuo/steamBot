#!/usr/bin/env python3
"""
Скрипт для запуска системы управления ботами Steam
Поддерживает различные режимы работы
"""

import argparse
import asyncio
import subprocess
import sys
import os
from pathlib import Path

def setup_environment():
    """Настройка окружения"""
    print("🔧 Настройка окружения...")
    
    # Проверка Python версии
    if sys.version_info < (3, 8):
        print("❌ Требуется Python 3.8 или выше")
        sys.exit(1)
    
    # Создание необходимых директорий
    directories = [
        "data", "logs", "backups", 
        "backups/logs", "backups/configs", "backups/data"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Директории созданы")
    
    # Проверка файла конфигурации
    if not Path(".env").exists():
        if Path("config_example.env").exists():
            print("⚠️  Файл .env не найден. Скопируйте config_example.env в .env и настройте")
        else:
            print("⚠️  Файл конфигурации не найден")

def install_dependencies():
    """Установка зависимостей"""
    print("📦 Установка зависимостей...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Зависимости установлены")
    except subprocess.CalledProcessError:
        print("❌ Ошибка установки зависимостей")
        sys.exit(1)

def start_bot_system():
    """Запуск основной системы ботов"""
    print("🤖 Запуск системы ботов...")
    try:
        subprocess.run([sys.executable, "main.py"])
    except KeyboardInterrupt:
        print("\n🛑 Система ботов остановлена")

def start_api_server():
    """Запуск API сервера"""
    print("🌐 Запуск API сервера...")
    try:
        subprocess.run([sys.executable, "api_server.py"])
    except KeyboardInterrupt:
        print("\n🛑 API сервер остановлен")

def start_both():
    """Запуск и ботов, и API сервера"""
    print("🚀 Запуск полной системы...")
    import threading
    
    def run_bots():
        subprocess.run([sys.executable, "main.py"])
    
    def run_api():
        subprocess.run([sys.executable, "api_server.py"])
    
    try:
        # Запуск в отдельных потоках
        bot_thread = threading.Thread(target=run_bots, daemon=True)
        api_thread = threading.Thread(target=run_api, daemon=True)
        
        bot_thread.start()
        api_thread.start()
        
        print("✅ Система запущена!")
        print("📊 API документация: http://localhost:8000/docs")
        print("⚡ Нажмите Ctrl+C для остановки")
        
        # Ожидание завершения
        while True:
            if not bot_thread.is_alive() or not api_thread.is_alive():
                break
            import time
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Система остановлена")

def create_sample_bot():
    """Создание тестового бота"""
    print("🤖 Создание тестового бота...")
    
    from admin_panel import BotManager
    from config import Config
    
    bot_manager = BotManager()
    
    # Интерактивный ввод данных бота
    print("\nВведите данные для создания тестового бота:")
    
    bot_config = {
        'proxy': input("Прокси (http://user:pass@host:port) или пустая строка: ") or None,
        'game_app_id': int(input("App ID игры (730 для CS:GO): ") or "730"),
        'bot_name': input("Имя бота: ") or "TestBot",
        'username': input("Steam логин: "),
        'password': input("Steam пароль: "),
        'api_key': input("Steam API ключ: ") or Config.STEAM_API_KEY,
        'ma_file': input("Путь к .maFile: ")
    }
    
    # Проверка обязательных полей
    required_fields = ['username', 'password', 'api_key', 'ma_file']
    missing_fields = [field for field in required_fields if not bot_config[field]]
    
    if missing_fields:
        print(f"❌ Не заполнены обязательные поля: {', '.join(missing_fields)}")
        return
    
    success = bot_manager.create_bot(bot_config)
    
    if success:
        print("✅ Тестовый бот создан успешно!")
    else:
        print("❌ Ошибка создания тестового бота")

def show_status():
    """Показать статус системы"""
    print("📊 Статус системы:")
    
    try:
        from admin_panel import BotManager
        bot_manager = BotManager()
        
        bots = bot_manager.get_bot_list()
        notifications = bot_manager.get_admin_notifications()
        
        print(f"🤖 Всего ботов: {len(bots)}")
        print(f"✅ Активных: {len([b for b in bots if b['is_active']])}")
        print(f"⏸️  На паузе: {len([b for b in bots if not b['is_active']])}")
        print(f"⚠️  С ошибками: {len([b for b in bots if b['error_count'] > 0])}")
        print(f"🔔 Уведомлений: {len(notifications)}")
        
        if bots:
            print("\nСписок ботов:")
            for bot in bots:
                status = "🟢" if bot['is_active'] else "🔴"
                print(f"  {status} {bot['bot_name']} ({bot['bot_id']}) - ошибок: {bot['error_count']}")
        
    except Exception as e:
        print(f"❌ Ошибка получения статуса: {e}")

def main():
    parser = argparse.ArgumentParser(description="Система управления ботами Steam")
    
    parser.add_argument("--mode", "-m", 
                       choices=["bots", "api", "both", "setup", "install", "create-bot", "status"],
                       default="both",
                       help="Режим запуска")
    
    parser.add_argument("--setup", action="store_true",
                       help="Настройка окружения")
    
    args = parser.parse_args()
    
    print("🎮 === Система управления ботами Steam ===\n")
    
    if args.setup or args.mode == "setup":
        setup_environment()
        return
    
    if args.mode == "install":
        install_dependencies()
        return
    
    if args.mode == "create-bot":
        create_sample_bot()
        return
    
    if args.mode == "status":
        show_status()
        return
    
    # Проверка зависимостей перед запуском
    try:
        import steampy
        import fastapi
        import schedule
    except ImportError as e:
        print(f"❌ Отсутствует зависимость: {e}")
        print("Запустите: python start_system.py --mode install")
        return
    
    if args.mode == "bots":
        start_bot_system()
    elif args.mode == "api":
        start_api_server()
    elif args.mode == "both":
        start_both()

if __name__ == "__main__":
    main() 
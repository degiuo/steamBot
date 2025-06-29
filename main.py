import asyncio
import schedule
import time
import threading
from datetime import datetime, timedelta
from admin_panel import BotManager
from utils.logger import setup_logger
from utils.proxy_manager import ProxyManager
from config import Config

class BotOrchestrator:
    """Оркестратор для управления множественными ботами"""
    
    def __init__(self):
        self.bot_manager = BotManager()
        self.logger = setup_logger("BotOrchestrator")
        self.is_running = True
        
        # Настройка планировщика для автоматических задач
        self._setup_scheduler()

    async def run_all_bots(self):
        """Запуск всех активных ботов в асинхронном режиме"""
        self.logger.info("Запуск системы ботов")
        
        # Создаем задачи для каждого активного бота
        tasks = []
        for bot_id, bot in self.bot_manager.bots.items():
            if bot.is_active:
                task = asyncio.create_task(self.bot_worker(bot))
                tasks.append(task)
                self.logger.info(f"Запущен бот {bot_id}")
        
        # Запуск планировщика в отдельном потоке
        scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        scheduler_thread.start()
        
        # Ожидание выполнения всех задач
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            self.logger.warning("Нет активных ботов для запуска")
            # Ожидание в случае отсутствия ботов
            while self.is_running:
                await asyncio.sleep(60)

    async def bot_worker(self, bot):
        """Рабочий цикл для одного бота"""
        bot_logger = setup_logger(f"Bot_{bot.bot_id}")
        
        while self.is_running and bot.is_active:
            try:
                # 1. GetTradeOffers - Получение и обработка входящих офферов
                offers = bot.get_trade_offers()
                bot_logger.info(f"Обработано {len(offers.get('received', []))} входящих офферов")

                # 2. SyncTradeStatus - Обновление статусов ордеров
                sync_result = bot.sync_trade_status()
                if sync_result['updated_orders']:
                    bot_logger.info(f"Обновлено статусов ордеров: {len(sync_result['updated_orders'])}")

                # 3. Обработка новых ордеров из БД (заглушка)
                pending_orders = await self._get_pending_orders_for_bot(bot.bot_id)
                
                for order in pending_orders:
                    success = bot.send_trade_offer(order)
                    if success:
                        bot_logger.info(f"Ордер {order['id']} успешно обработан")
                    else:
                        bot_logger.warning(f"Ордер {order['id']} не удалось обработать")

                # 4. Периодическое обновление инвентаря (каждые 10 циклов)
                if not hasattr(bot, '_inventory_update_counter'):
                    bot._inventory_update_counter = 0
                
                bot._inventory_update_counter += 1
                if bot._inventory_update_counter >= 10:
                    bot.get_bot_inventory()
                    bot._inventory_update_counter = 0
                    bot_logger.info("Инвентарь обновлен")

                # Пауза между циклами
                await asyncio.sleep(30)  # 30 секунд между циклами

            except Exception as e:
                bot_logger.error(f"Критическая ошибка в цикле бота: {e}")
                await asyncio.sleep(300)  # При ошибке ждем 5 минут

    async def _get_pending_orders_for_bot(self, bot_id: str) -> list:
        """Получение ордеров в ожидании для конкретного бота"""
        # Заглушка для получения ордеров из БД
        # В реальной реализации здесь будет запрос к базе данных
        return [
            {
                "id": f"order_{int(time.time())}",
                "items": [{"assetid": "123456", "appid": 730}],
                "partner_steam_id": "76561198123456789"
            }
        ] if bot_id == "test_bot" else []

    def _setup_scheduler(self):
        """Настройка планировщика для автоматических задач"""
        # Ежедневные бэкапы в 2:00 ночи
        schedule.every().day.at("02:00").do(self._daily_backup_job)
        
        # Проверка здоровья ботов каждые 15 минут
        schedule.every(15).minutes.do(self._health_check_job)
        
        # Очистка старых логов каждую неделю
        schedule.every().week.do(self._cleanup_old_logs)

    def _run_scheduler(self):
        """Запуск планировщика в отдельном потоке"""
        while self.is_running:
            schedule.run_pending()
            time.sleep(60)  # Проверка каждую минуту

    def _daily_backup_job(self):
        """Ежедневное задание создания бэкапов"""
        try:
            success = self.bot_manager.create_daily_backup()
            if success:
                self.logger.info("Ежедневный бэкап создан успешно")
            else:
                self.logger.error("Ошибка создания ежедневного бэкапа")
        except Exception as e:
            self.logger.error(f"Критическая ошибка при создании бэкапа: {e}")

    def _health_check_job(self):
        """Проверка здоровья всех ботов"""
        try:
            bots_info = self.bot_manager.get_bot_list()
            
            for bot_info in bots_info:
                bot_id = bot_info['bot_id']
                error_count = bot_info['error_count']
                is_active = bot_info['is_active']
                
                # Проверка на критическое количество ошибок
                if error_count >= 5:
                    self.logger.warning(f"Бот {bot_id} имеет {error_count} ошибок")
                
                # Попытка перезапуска "мертвых" ботов
                if not is_active and bot_id in self.bot_manager.bots:
                    self.logger.info(f"Попытка восстановления бота {bot_id}")
                    self.bot_manager.resume_bot(bot_id)
                    
        except Exception as e:
            self.logger.error(f"Ошибка при проверке здоровья ботов: {e}")

    def _cleanup_old_logs(self):
        """Очистка старых лог-файлов"""
        try:
            import os
            from pathlib import Path
            
            # Удаление логов старше 30 дней
            cutoff_date = datetime.now() - timedelta(days=30)
            logs_dir = Path("logs")
            
            if logs_dir.exists():
                for log_file in logs_dir.glob("**/*.log"):
                    if log_file.stat().st_mtime < cutoff_date.timestamp():
                        log_file.unlink()
                        self.logger.info(f"Удален старый лог: {log_file}")
                        
        except Exception as e:
            self.logger.error(f"Ошибка очистки логов: {e}")

    def stop(self):
        """Остановка оркестратора"""
        self.is_running = False
        self.logger.info("Оркестратор остановлен")


def create_sample_bot():
    """Создание тестового бота для демонстрации"""
    bot_manager = BotManager()
    
    sample_config = {
        'proxy': Config.PROXY or 'http://127.0.0.1:8080',
        'game_app_id': 730,  # CS:GO
        'bot_name': 'SampleBot',
        'username': 'your_steam_login',
        'password': 'your_steam_password',
        'api_key': Config.STEAM_API_KEY or 'your_steam_api_key',
        'ma_file': 'path/to/your.maFile'
    }
    
    print("Создание тестового бота...")
    success = bot_manager.create_bot(sample_config)
    
    if success:
        print("✓ Тестовый бот создан успешно")
        return True
    else:
        print("✗ Ошибка создания тестового бота")
        return False


async def main():
    """Главная функция запуска"""
    print("=== Система ботов Steam ===")
    print("Инициализация...")
    
    orchestrator = BotOrchestrator()
    
    # Проверяем наличие ботов
    bots = orchestrator.bot_manager.get_bot_list()
    
    if not bots:
        print("Боты не найдены. Создать тестового бота? (y/n)")
        response = input().lower()
        if response == 'y':
            if create_sample_bot():
                # Перезагружаем менеджер ботов
                orchestrator.bot_manager = BotManager()
            else:
                print("Невозможно создать тестового бота. Проверьте конфигурацию.")
                return
    
    try:
        print(f"Найдено ботов: {len(orchestrator.bot_manager.bots)}")
        print("Запуск системы ботов...")
        
        # Запуск всех ботов
        await orchestrator.run_all_bots()
        
    except KeyboardInterrupt:
        print("\nПолучен сигнал остановки...")
        orchestrator.stop()
        print("Система ботов остановлена")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        orchestrator.stop()


if __name__ == "__main__":
    asyncio.run(main())
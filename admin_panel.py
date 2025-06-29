import json
import os
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
from bot.bot_core import SteamBot
from bot.models import OrderStatus
from utils.backup import create_backup
from utils.proxy_manager import ProxyManager

class BotManager:
    def __init__(self):
        self.bots: Dict[str, SteamBot] = {}
        self.bot_configs: Dict[str, Dict] = {}
        self._load_bot_configs()

    def create_bot(self, bot_config: Dict) -> bool:
        """
        Создание бота через админ панель
        Обязательные поля:
        - proxy: str
        - game_app_id: int  
        - bot_name: str
        - username: str
        - password: str
        - api_key: str
        - ma_file: str (путь к файлу)
        """
        try:
            required_fields = ['proxy', 'game_app_id', 'bot_name', 'username', 'password', 'api_key', 'ma_file']
            
            # Проверка обязательных полей
            for field in required_fields:
                if field not in bot_config or not bot_config[field]:
                    raise ValueError(f"Обязательное поле '{field}' отсутствует или пустое")

            # Генерация ID бота
            bot_id = self._generate_bot_id()
            
            # Создание экземпляра бота
            bot = SteamBot(
                bot_id=bot_id,
                api_key=bot_config['api_key'],
                username=bot_config['username'],
                password=bot_config['password'],
                ma_file=bot_config['ma_file'],
                game_app_id=int(bot_config['game_app_id']),
                proxy=bot_config['proxy'],
                bot_name=bot_config['bot_name']
            )

            # Сохранение конфигурации
            self.bot_configs[bot_id] = bot_config.copy()
            self.bot_configs[bot_id]['bot_id'] = bot_id
            self.bot_configs[bot_id]['created_at'] = datetime.now().isoformat()
            
            # Добавление в список активных ботов
            self.bots[bot_id] = bot
            
            # Сохранение конфигурации в файл
            self._save_bot_configs()
            
            print(f"Бот {bot_config['bot_name']} (ID: {bot_id}) успешно создан")
            return True
            
        except Exception as e:
            print(f"Ошибка создания бота: {e}")
            return False

    def pause_bot(self, bot_id: str) -> bool:
        """Остановка бота - Пауза"""
        try:
            if bot_id in self.bots:
                self.bots[bot_id].pause_bot()
                print(f"Бот {bot_id} поставлен на паузу")
                return True
            else:
                print(f"Бот {bot_id} не найден")
                return False
        except Exception as e:
            print(f"Ошибка паузы бота {bot_id}: {e}")
            return False

    def resume_bot(self, bot_id: str) -> bool:
        """Возобновление работы бота"""
        try:
            if bot_id in self.bots:
                self.bots[bot_id].resume_bot()
                print(f"Бот {bot_id} возобновил работу")
                return True
            else:
                print(f"Бот {bot_id} не найден")
                return False
        except Exception as e:
            print(f"Ошибка возобновления бота {bot_id}: {e}")
            return False

    def restart_bot(self, bot_id: str, force: bool = False) -> bool:
        """Перезагрузка бота"""
        try:
            if bot_id not in self.bots:
                print(f"Бот {bot_id} не найден")
                return False

            # Бэкап логов перед перезагрузкой
            log_file = f"logs/bot_{bot_id}_calls.json"
            if os.path.exists(log_file):
                backup_dir = f"backups/logs/bot_{bot_id}"
                create_backup(log_file, backup_dir)

            # Остановка бота
            if force:
                print(f"Принудительная перезагрузка бота {bot_id}")
                # Здесь должна быть логика kill процесса
            else:
                self.bots[bot_id].pause_bot()

            # Восстановление из конфигурации
            config = self.bot_configs[bot_id]
            new_bot = SteamBot(
                bot_id=bot_id,
                api_key=config['api_key'],
                username=config['username'],
                password=config['password'],
                ma_file=config['ma_file'],
                game_app_id=config['game_app_id'],
                proxy=config['proxy'],
                bot_name=config['bot_name']
            )
            
            self.bots[bot_id] = new_bot
            print(f"Бот {bot_id} успешно перезагружен")
            return True
            
        except Exception as e:
            print(f"Ошибка перезагрузки бота {bot_id}: {e}")
            return False

    def delete_bot(self, bot_id: str) -> bool:
        """Удаление бота"""
        try:
            if bot_id in self.bots:
                # Остановка бота
                self.bots[bot_id].pause_bot()
                
                # Удаление из активных ботов
                del self.bots[bot_id]
                
                # Удаление конфигурации
                if bot_id in self.bot_configs:
                    del self.bot_configs[bot_id]
                
                # Сохранение обновленной конфигурации
                self._save_bot_configs()
                
                print(f"Бот {bot_id} удален")
                return True
            else:
                print(f"Бот {bot_id} не найден")
                return False
        except Exception as e:
            print(f"Ошибка удаления бота {bot_id}: {e}")
            return False

    def get_bot_list(self, filters: Dict = None) -> List[Dict]:
        """
        Получение списка ботов с фильтрами:
        - name: по названию
        - game_app_id: по игре  
        - username: по стим логину
        """
        try:
            bots_info = []
            
            for bot_id, config in self.bot_configs.items():
                bot_info = {
                    'bot_id': bot_id,
                    'bot_name': config.get('bot_name', ''),
                    'username': config.get('username', ''),
                    'game_app_id': config.get('game_app_id', 0),
                    'proxy': config.get('proxy', ''),
                    'created_at': config.get('created_at', ''),
                    'is_active': self.bots[bot_id].is_active if bot_id in self.bots else False,
                    'error_count': self.bots[bot_id].error_count if bot_id in self.bots else 0
                }
                
                # Применение фильтров
                if filters:
                    if 'name' in filters and filters['name'].lower() not in bot_info['bot_name'].lower():
                        continue
                    if 'game_app_id' in filters and filters['game_app_id'] != bot_info['game_app_id']:
                        continue
                    if 'username' in filters and filters['username'].lower() not in bot_info['username'].lower():
                        continue
                
                bots_info.append(bot_info)
            
            return bots_info
            
        except Exception as e:
            print(f"Ошибка получения списка ботов: {e}")
            return []

    def get_bot_inventory_manual(self, bot_id: str) -> Optional[Dict]:
        """Ручное получение инвентаря бота из админ панели"""
        try:
            if bot_id in self.bots:
                inventory = self.bots[bot_id].get_bot_inventory()
                return {
                    'bot_id': bot_id,
                    'app_id': inventory.app_id,
                    'items_count': len(inventory.items),
                    'items': inventory.items,
                    'last_update': inventory.last_update
                }
            else:
                print(f"Бот {bot_id} не найден")
                return None
        except Exception as e:
            print(f"Ошибка получения инвентаря бота {bot_id}: {e}")
            return None

    def get_available_items(self) -> List[Dict]:
        """Получение всех доступных предметов от активных ботов"""
        try:
            all_items = []
            
            for bot_id, bot in self.bots.items():
                if bot.is_active and bot.inventory:
                    for item in bot.inventory.items:
                        item_info = item.copy()
                        item_info['bot_id'] = bot_id
                        item_info['bot_name'] = self.bot_configs[bot_id].get('bot_name', '')
                        all_items.append(item_info)
            
            return all_items
            
        except Exception as e:
            print(f"Ошибка получения доступных предметов: {e}")
            return []

    def get_admin_notifications(self) -> List[Dict]:
        """Получение уведомлений админа"""
        try:
            notifications = []
            notification_file = 'data/admin_notifications.json'
            
            if os.path.exists(notification_file):
                with open(notification_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            notifications.append(json.loads(line.strip()))
            
            # Сортировка по времени (новые первыми)
            notifications.sort(key=lambda x: x['timestamp'], reverse=True)
            return notifications
            
        except Exception as e:
            print(f"Ошибка получения уведомлений: {e}")
            return []

    def clear_admin_notifications(self) -> bool:
        """Очистка уведомлений админа"""
        try:
            notification_file = 'data/admin_notifications.json'
            if os.path.exists(notification_file):
                os.remove(notification_file)
            print("Уведомления очищены")
            return True
        except Exception as e:
            print(f"Ошибка очистки уведомлений: {e}")
            return False

    def create_daily_backup(self) -> bool:
        """Ежедневное создание бэкапов ботов и логов"""
        try:
            # Бэкап конфигураций ботов
            backup_dir = "backups/configs"
            Path(backup_dir).mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
            config_backup = f"{backup_dir}/bot_configs_{timestamp}.json"
            
            with open(config_backup, 'w', encoding='utf-8') as f:
                json.dump(self.bot_configs, f, ensure_ascii=False, indent=2)
            
            # Бэкап логов всех ботов
            logs_backup_created = 0
            for bot_id in self.bot_configs.keys():
                log_file = f"logs/bot_{bot_id}_calls.json"
                if os.path.exists(log_file):
                    backup_log_dir = f"backups/logs/bot_{bot_id}"
                    if create_backup(log_file, backup_log_dir):
                        logs_backup_created += 1
            
            print(f"Бэкап создан: конфигурации и {logs_backup_created} лог-файлов")
            return True
            
        except Exception as e:
            print(f"Ошибка создания бэкапа: {e}")
            return False

    def _generate_bot_id(self) -> str:
        """Генерация уникального ID для бота"""
        return f"bot_{len(self.bot_configs) + 1}_{int(datetime.now().timestamp())}"

    def _load_bot_configs(self):
        """Загрузка конфигураций ботов из файла"""
        try:
            config_file = "data/bot_configs.json"
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    self.bot_configs = json.load(f)
                    
                # Восстановление ботов из конфигурации
                for bot_id, config in self.bot_configs.items():
                    try:
                        bot = SteamBot(
                            bot_id=bot_id,
                            api_key=config['api_key'],
                            username=config['username'],
                            password=config['password'],
                            ma_file=config['ma_file'],
                            game_app_id=config['game_app_id'],
                            proxy=config['proxy'],
                            bot_name=config['bot_name']
                        )
                        self.bots[bot_id] = bot
                    except Exception as e:
                        print(f"Ошибка восстановления бота {bot_id}: {e}")
        except Exception as e:
            print(f"Ошибка загрузки конфигураций: {e}")

    def _save_bot_configs(self):
        """Сохранение конфигураций ботов в файл"""
        try:
            Path("data").mkdir(exist_ok=True)
            config_file = "data/bot_configs.json"
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.bot_configs, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"Ошибка сохранения конфигураций: {e}")


# Пример использования админ панели
if __name__ == "__main__":
    bot_manager = BotManager()
    
    # Создание нового бота
    new_bot_config = {
        'proxy': 'http://user:pass@proxy.example.com:8080',
        'game_app_id': 730,  # CS:GO
        'bot_name': 'TestBot1',
        'username': 'steam_login',
        'password': 'steam_password',
        'api_key': 'your_steam_api_key',
        'ma_file': 'path/to/maFile.maFile'
    }
    
    # bot_manager.create_bot(new_bot_config)
    
    # Получение списка ботов
    bots = bot_manager.get_bot_list()
    print("Активные боты:", bots)
    
    # Получение уведомлений
    notifications = bot_manager.get_admin_notifications()
    print("Уведомления:", len(notifications))

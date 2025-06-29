from typing import List, Dict, Optional
from datetime import datetime
import time
import json
import threading
from .models import TradeOffer, BotInventory, OrderStatus
from .steam_client import SteamClientWrapper
from .exceptions import BotError, TradeOfferError

class SteamBot:
    def __init__(self, bot_id: str, api_key: str, username: str, password: str, 
                 ma_file: str, game_app_id: int, proxy: str = None, bot_name: str = None):
        self.bot_id = bot_id
        self.bot_name = bot_name or f"Bot_{bot_id}"
        self.steam = SteamClientWrapper(api_key, username, password, ma_file, proxy)
        self.game_app_id = game_app_id
        self.inventory: Optional[BotInventory] = None
        self.last_update = datetime.now()
        self.is_active = True
        self.error_count = 0
        self.max_errors = 10
        self._lock = threading.Lock()

    def get_trade_offers(self) -> Dict:
        """GetTradeOffers - получение массива входящих ордеров, запись в базу данных"""
        try:
            self._log_function_call("GetTradeOffers", "start")
            offers = self.steam.get_trade_offers()
            
            # Сохранение в БД
            self._save_offers_to_db(offers)
            
            # Автоматическая отмена всех входящих офферов
            for offer in offers.get('received', []):
                if offer.get('trade_offer_state') == 2:  # Active
                    self.steam.cancel_trade_offer(offer['tradeofferid'])
                    self._log_function_call("CancelOffer", f"Cancelled offer {offer['tradeofferid']}")
            
            self._log_function_call("GetTradeOffers", f"success - processed {len(offers.get('received', []))} offers")
            self.error_count = 0  # Сброс счетчика ошибок при успехе
            return offers
            
        except Exception as e:
            self._handle_error("GetTradeOffers", e)
            raise

    def send_trade_offer(self, order_data: Dict) -> bool:
        """SendTradeOffer - Отправка предметов пользователю"""
        try:
            self._log_function_call("SendTradeOffer", f"Order {order_data['id']} start", order_data['id'])
            
            # 1. Поиск предметов в инвентаре
            items = self.find_items_in_inventory(order_data['items'])
            if len(items) != len(order_data['items']):
                self._update_order_status(order_data['id'], OrderStatus.PENDING)
                self._log_function_call("SendTradeOffer", f"Items not found for order {order_data['id']}", order_data['id'])
                return False

            # 2. Формирование и отправка трейд-оффера
            offer_id = self.steam.send_trade_offer(
                order_data['partner_steam_id'],
                items,
                f"Order #{order_data['id']}"
            )
            
            # 3. Обновление статуса
            self._update_order_status(order_data['id'], OrderStatus.SENT, offer_id)
            
            # 4. Автоматическое обновление инвентаря
            self.get_bot_inventory()
            
            self._log_function_call("SendTradeOffer", f"success - order {order_data['id']}, offer {offer_id}", order_data['id'])
            return True
            
        except Exception as e:
            self._handle_error("SendTradeOffer", e, order_data.get('id'))
            return False

    def sync_trade_status(self) -> Dict:
        """SyncTradeStatus - Обновление статуса ордеров"""
        try:
            self._log_function_call("SyncTradeStatus", "start")
            
            # Получаем все отправленные ордера из БД
            sent_orders = self._get_sent_orders_from_db()
            updated_orders = []
            
            for order in sent_orders:
                if order.get('offer_id'):
                    offer_status = self._check_offer_status(order['offer_id'])
                    
                    if offer_status == 'accepted':
                        self._update_order_status(order['id'], OrderStatus.COMPLETED)
                        updated_orders.append({'id': order['id'], 'status': OrderStatus.COMPLETED})
                    elif offer_status == 'declined' or offer_status == 'expired':
                        self._update_order_status(order['id'], OrderStatus.NOT_ACCEPTED)
                        updated_orders.append({'id': order['id'], 'status': OrderStatus.NOT_ACCEPTED})
            
            self._log_function_call("SyncTradeStatus", f"success - updated {len(updated_orders)} orders")
            return {'updated_orders': updated_orders}
            
        except Exception as e:
            self._handle_error("SyncTradeStatus", e)
            return {'updated_orders': []}

    def get_bot_inventory(self) -> BotInventory:
        """GetBotInventory - получение содержания инвентаря бота"""
        try:
            self._log_function_call("GetBotInventory", "start")
            
            items = self.steam.get_inventory(self.game_app_id)
            self.inventory = BotInventory(
                app_id=self.game_app_id,
                items=items,
                last_update=datetime.now().isoformat()
            )
            
            # Сохранение в БД
            self._save_inventory_to_db(self.inventory)
            
            self._log_function_call("GetBotInventory", f"success - {len(items)} items loaded")
            return self.inventory
            
        except Exception as e:
            self._handle_error("GetBotInventory", e)
            raise

    def find_items_in_inventory(self, items_to_find: List[Dict]) -> List[Dict]:
        """Поиск предметов в инвентаре"""
        if not self.inventory:
            self.get_bot_inventory()
            
        found_items = []
        for target_item in items_to_find:
            for item in self.inventory.items:
                if (item.get('assetid') == target_item.get('assetid') and 
                    item.get('appid') == target_item.get('appid')):
                    found_items.append(item)
                    break
        
        return found_items

    def pause_bot(self):
        """Остановка бота - Пауза"""
        with self._lock:
            self.is_active = False
            self._log_function_call("PauseBot", "Bot paused")

    def resume_bot(self):
        """Возобновление работы бота"""
        with self._lock:
            self.is_active = True
            self.error_count = 0
            self._log_function_call("ResumeBot", "Bot resumed")

    def _log_function_call(self, function_name: str, result: str, order_id: str = None):
        """Логирование каждого вызова функций бота"""
        log_entry = {
            'bot_id': self.bot_id,
            'function': function_name,
            'time': datetime.now().isoformat(),
            'order_id': order_id,
            'result': result
        }
        
        # Запись в файл лога
        with open(f'logs/bot_{self.bot_id}_calls.json', 'a') as f:
            json.dump(log_entry, f, ensure_ascii=False)
            f.write('\n')

    def _handle_error(self, function_name: str, error: Exception, order_id: str = None):
        """Обработка ошибок"""
        self.error_count += 1
        error_msg = f"Error in {function_name}: {str(error)}"
        
        self._log_function_call(function_name, f"error - {error_msg}", order_id)
        
        # Уведомление админа при большом количестве ошибок
        if self.error_count >= self.max_errors:
            self._notify_admin(f"Bot {self.bot_id} has {self.error_count} consecutive errors. Last error: {error_msg}")
            self.pause_bot()

    def _check_offer_status(self, offer_id: str) -> str:
        """Проверка статуса конкретного оффера"""
        try:
            # Здесь должна быть логика проверки статуса через Steam API
            # Заглушка
            return 'pending'
        except Exception:
            return 'unknown'

    def _save_offers_to_db(self, offers: Dict):
        """Сохранение офферов в базу данных"""
        # Заглушка для сохранения в БД
        with open(f'data/bot_{self.bot_id}_offers.json', 'w') as f:
            json.dump(offers, f, ensure_ascii=False, indent=2)

    def _save_inventory_to_db(self, inventory: BotInventory):
        """Сохранение инвентаря в базу данных"""
        # Заглушка для сохранения в БД
        inventory_data = {
            'bot_id': self.bot_id,
            'app_id': inventory.app_id,
            'items': inventory.items,
            'last_update': inventory.last_update
        }
        with open(f'data/bot_{self.bot_id}_inventory.json', 'w') as f:
            json.dump(inventory_data, f, ensure_ascii=False, indent=2)

    def _get_sent_orders_from_db(self) -> List[Dict]:
        """Получение отправленных ордеров из БД"""
        # Заглушка для получения из БД
        try:
            with open(f'data/bot_{self.bot_id}_sent_orders.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def _update_order_status(self, order_id: str, status: OrderStatus, offer_id: str = None):
        """Обновление статуса ордера в БД"""
        # Заглушка обновления статуса ордера
        update_data = {
            'order_id': order_id,
            'status': status.value,
            'offer_id': offer_id,
            'updated_at': datetime.now().isoformat()
        }
        print(f"Order {order_id} updated to {status.value} (OfferID: {offer_id})")

    def _notify_admin(self, message: str):
        """Уведомление админа"""
        notification = {
            'bot_id': self.bot_id,
            'bot_name': self.bot_name,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        
        # Запись в файл уведомлений
        with open('data/admin_notifications.json', 'a') as f:
            json.dump(notification, f, ensure_ascii=False)
            f.write('\n')
        
        print(f"[ADMIN ALERT] Bot {self.bot_id}: {message}")
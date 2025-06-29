from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional

class OrderStatus(str, Enum):
    PENDING = "в ожидании"
    SENT = "Отправлен"
    NOT_ACCEPTED = "Не принят"
    COMPLETED = "Завершен"

@dataclass
class TradeOffer:
    offer_id: str
    items_to_receive: List[Dict]  # [{ 'assetid': str, 'appid': int }]
    items_to_send: List[Dict]
    partner_steam_id: str
    message: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING

@dataclass
class BotInventory:
    app_id: int
    items: List[Dict]  # [{ 'assetid': str, 'name': str, ... }]
    last_update: str
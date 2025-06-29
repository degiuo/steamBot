class BotError(Exception):
    """Базовое исключение для бота"""
    pass

class TradeOfferError(BotError):
    """Ошибка при работе с трейд-офферами"""
    pass

class InventoryError(BotError):
    """Ошибка при работе с инвентарем"""
    pass

class ProxyError(BotError):
    """Ошибка прокси"""
    pass
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import asyncio
import uvicorn
from admin_panel import BotManager
from utils.backup import BackupManager

app = FastAPI(title="Steam Bots Management API", version="1.0.0")

# Настройка CORS для веб-интерфейса
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Глобальные объекты
bot_manager = BotManager()
backup_manager = BackupManager()

# Pydantic модели для API
class BotCreateRequest(BaseModel):
    proxy: str
    game_app_id: int
    bot_name: str
    username: str
    password: str
    api_key: str
    ma_file: str

class BotFilterRequest(BaseModel):
    name: Optional[str] = None
    game_app_id: Optional[int] = None
    username: Optional[str] = None

class OrderRequest(BaseModel):
    bot_id: str
    items: List[Dict]
    partner_steam_id: str

# API Endpoints
@app.get("/")
async def root():
    """Корневой endpoint"""
    return {"message": "Steam Bots Management API", "version": "1.0.0"}

@app.get("/api/bots", response_model=List[Dict])
async def get_bots(name: Optional[str] = None, game_app_id: Optional[int] = None, username: Optional[str] = None):
    """Получение списка всех ботов с возможностью фильтрации"""
    filters = {}
    if name:
        filters["name"] = name
    if game_app_id:
        filters["game_app_id"] = game_app_id
    if username:
        filters["username"] = username
    
    bots = bot_manager.get_bot_list(filters)
    return bots

@app.post("/api/bots")
async def create_bot(bot_config: BotCreateRequest):
    """Создание нового бота"""
    config_dict = bot_config.dict()
    success = bot_manager.create_bot(config_dict)
    
    if success:
        return {"status": "success", "message": "Бот успешно создан"}
    else:
        raise HTTPException(status_code=400, detail="Ошибка создания бота")

@app.post("/api/bots/{bot_id}/pause")
async def pause_bot(bot_id: str):
    """Остановка (пауза) бота"""
    success = bot_manager.pause_bot(bot_id)
    
    if success:
        return {"status": "success", "message": f"Бот {bot_id} поставлен на паузу"}
    else:
        raise HTTPException(status_code=404, detail="Бот не найден")

@app.post("/api/bots/{bot_id}/resume")
async def resume_bot(bot_id: str):
    """Возобновление работы бота"""
    success = bot_manager.resume_bot(bot_id)
    
    if success:
        return {"status": "success", "message": f"Бот {bot_id} возобновил работу"}
    else:
        raise HTTPException(status_code=404, detail="Бот не найден")

@app.post("/api/bots/{bot_id}/restart")
async def restart_bot(bot_id: str, force: bool = False):
    """Перезагрузка бота"""
    success = bot_manager.restart_bot(bot_id, force)
    
    if success:
        return {"status": "success", "message": f"Бот {bot_id} перезагружен"}
    else:
        raise HTTPException(status_code=404, detail="Бот не найден")

@app.delete("/api/bots/{bot_id}")
async def delete_bot(bot_id: str):
    """Удаление бота"""
    success = bot_manager.delete_bot(bot_id)
    
    if success:
        return {"status": "success", "message": f"Бот {bot_id} удален"}
    else:
        raise HTTPException(status_code=404, detail="Бот не найден")

@app.get("/api/bots/{bot_id}/inventory")
async def get_bot_inventory(bot_id: str):
    """Получение инвентаря бота"""
    inventory = bot_manager.get_bot_inventory_manual(bot_id)
    
    if inventory:
        return inventory
    else:
        raise HTTPException(status_code=404, detail="Бот не найден или ошибка получения инвентаря")

@app.get("/api/items")
async def get_available_items():
    """Получение всех доступных предметов от активных ботов"""
    items = bot_manager.get_available_items()
    return {"items": items, "total_count": len(items)}

@app.post("/api/orders")
async def create_order(order: OrderRequest):
    """Создание нового ордера для отправки предметов"""
    if order.bot_id not in bot_manager.bots:
        raise HTTPException(status_code=404, detail="Бот не найден")
    
    bot = bot_manager.bots[order.bot_id]
    
    order_data = {
        "id": f"api_order_{int(asyncio.get_event_loop().time())}",
        "items": order.items,
        "partner_steam_id": order.partner_steam_id
    }
    
    success = bot.send_trade_offer(order_data)
    
    if success:
        return {"status": "success", "order_id": order_data["id"], "message": "Ордер создан и отправлен"}
    else:
        raise HTTPException(status_code=400, detail="Ошибка отправки ордера")

@app.get("/api/notifications")
async def get_notifications():
    """Получение уведомлений админа"""
    notifications = bot_manager.get_admin_notifications()
    return {"notifications": notifications, "total_count": len(notifications)}

@app.delete("/api/notifications")
async def clear_notifications():
    """Очистка уведомлений админа"""
    success = bot_manager.clear_admin_notifications()
    
    if success:
        return {"status": "success", "message": "Уведомления очищены"}
    else:
        raise HTTPException(status_code=500, detail="Ошибка очистки уведомлений")

@app.post("/api/backup")
async def create_backup(background_tasks: BackgroundTasks):
    """Создание полного бэкапа системы"""
    background_tasks.add_task(backup_manager.create_full_backup)
    return {"status": "success", "message": "Создание бэкапа запущено в фоне"}

@app.get("/api/backup/info")
async def get_backup_info():
    """Получение информации о бэкапах"""
    info = backup_manager.get_backup_info()
    return info

@app.post("/api/backup/restore/{backup_type}/{filename}")
async def restore_backup(backup_type: str, filename: str):
    """Восстановление из бэкапа"""
    if backup_type == "configs":
        success = backup_manager.restore_configs_from_backup(filename)
        if success:
            # Перезагрузка менеджера ботов после восстановления
            global bot_manager
            bot_manager = BotManager()
            return {"status": "success", "message": "Конфигурации восстановлены"}
        else:
            raise HTTPException(status_code=400, detail="Ошибка восстановления")
    else:
        raise HTTPException(status_code=400, detail="Неподдерживаемый тип бэкапа")

@app.get("/api/stats")
async def get_system_stats():
    """Получение статистики системы"""
    bots = bot_manager.get_bot_list()
    
    stats = {
        "total_bots": len(bots),
        "active_bots": len([b for b in bots if b["is_active"]]),
        "paused_bots": len([b for b in bots if not b["is_active"]]),
        "bots_with_errors": len([b for b in bots if b["error_count"] > 0]),
        "total_items": len(bot_manager.get_available_items()),
        "notifications_count": len(bot_manager.get_admin_notifications())
    }
    
    return stats

@app.get("/api/health")
async def health_check():
    """Проверка здоровья API"""
    return {"status": "healthy", "timestamp": asyncio.get_event_loop().time()}

# WebSocket endpoint для real-time уведомлений (опционально)
@app.websocket("/ws/notifications")
async def websocket_notifications(websocket):
    """WebSocket для real-time уведомлений"""
    await websocket.accept()
    
    try:
        while True:
            # Отправка уведомлений каждые 10 секунд
            notifications = bot_manager.get_admin_notifications()
            await websocket.send_json({
                "type": "notifications",
                "data": notifications[:5]  # Последние 5 уведомлений
            })
            
            await asyncio.sleep(10)
            
    except Exception as e:
        print(f"WebSocket ошибка: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    print("Запуск API сервера для управления ботами Steam...")
    print("API документация доступна по адресу: http://localhost:8000/docs")
    
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 
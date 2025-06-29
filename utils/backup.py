import shutil
import gzip
import os
import json
import tarfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

class BackupManager:
    """Улучшенный менеджер бэкапов для системы ботов"""
    
    def __init__(self, base_backup_dir: str = "backups"):
        self.base_backup_dir = Path(base_backup_dir)
        self.base_backup_dir.mkdir(exist_ok=True)
        
        # Создание подпапок
        (self.base_backup_dir / "logs").mkdir(exist_ok=True)
        (self.base_backup_dir / "configs").mkdir(exist_ok=True)
        (self.base_backup_dir / "data").mkdir(exist_ok=True)

    def create_bot_logs_backup(self, bot_id: str, max_backups: int = 30) -> bool:
        """Создает бэкап логов конкретного бота"""
        try:
            log_dir = Path(f"logs/{bot_id}")
            if not log_dir.exists():
                return False
            
            backup_dir = self.base_backup_dir / "logs" / bot_id
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
            backup_name = f"logs_backup_{timestamp}.tar.gz"
            backup_path = backup_dir / backup_name
            
            # Создание архива с логами
            with tarfile.open(backup_path, "w:gz") as tar:
                tar.add(log_dir, arcname=f"logs_{bot_id}")
            
            # Удаление старых бэкапов
            self._cleanup_old_backups(backup_dir, "logs_backup_*.tar.gz", max_backups)
            
            return True
            
        except Exception as e:
            print(f"Ошибка создания бэкапа логов для бота {bot_id}: {e}")
            return False

    def create_configs_backup(self, max_backups: int = 50) -> bool:
        """Создает бэкап всех конфигураций ботов"""
        try:
            backup_dir = self.base_backup_dir / "configs"
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
            backup_name = f"bot_configs_{timestamp}.tar.gz"
            backup_path = backup_dir / backup_name
            
            # Создание архива с конфигурациями
            with tarfile.open(backup_path, "w:gz") as tar:
                # Добавляем файлы конфигураций
                if Path("data/bot_configs.json").exists():
                    tar.add("data/bot_configs.json", arcname="bot_configs.json")
                
                # Добавляем .maFile файлы (если есть)
                for ma_file in Path(".").glob("*.maFile"):
                    tar.add(ma_file, arcname=ma_file.name)
            
            # Удаление старых бэкапов
            self._cleanup_old_backups(backup_dir, "bot_configs_*.tar.gz", max_backups)
            
            return True
            
        except Exception as e:
            print(f"Ошибка создания бэкапа конфигураций: {e}")
            return False

    def create_data_backup(self, max_backups: int = 30) -> bool:
        """Создает бэкап данных (инвентарь, ордера, уведомления)"""
        try:
            backup_dir = self.base_backup_dir / "data"
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
            backup_name = f"data_backup_{timestamp}.tar.gz"
            backup_path = backup_dir / backup_name
            
            # Создание архива с данными
            with tarfile.open(backup_path, "w:gz") as tar:
                data_dir = Path("data")
                if data_dir.exists():
                    tar.add(data_dir, arcname="data")
            
            # Удаление старых бэкапов
            self._cleanup_old_backups(backup_dir, "data_backup_*.tar.gz", max_backups)
            
            return True
            
        except Exception as e:
            print(f"Ошибка создания бэкапа данных: {e}")
            return False

    def create_full_backup(self) -> Dict[str, bool]:
        """Создает полный бэкап всей системы"""
        results = {
            'configs': self.create_configs_backup(),
            'data': self.create_data_backup(),
            'logs': True
        }
        
        # Бэкап логов всех ботов
        logs_dir = Path("logs")
        if logs_dir.exists():
            for bot_log_dir in logs_dir.iterdir():
                if bot_log_dir.is_dir():
                    bot_id = bot_log_dir.name
                    self.create_bot_logs_backup(bot_id)
        
        return results

    def restore_configs_from_backup(self, backup_file: str) -> bool:
        """Восстановление конфигураций из бэкапа"""
        try:
            backup_path = self.base_backup_dir / "configs" / backup_file
            if not backup_path.exists():
                print(f"Файл бэкапа {backup_file} не найден")
                return False
            
            # Создание папки для восстановления
            restore_dir = Path("restore_temp")
            restore_dir.mkdir(exist_ok=True)
            
            # Извлечение архива
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(restore_dir)
            
            # Восстановление файлов
            config_file = restore_dir / "bot_configs.json"
            if config_file.exists():
                shutil.copy2(config_file, "data/bot_configs.json")
                print("Конфигурации восстановлены")
            
            # Очистка временной папки
            shutil.rmtree(restore_dir)
            return True
            
        except Exception as e:
            print(f"Ошибка восстановления конфигураций: {e}")
            return False

    def get_backup_info(self) -> Dict[str, List[Dict]]:
        """Получение информации о всех бэкапах"""
        backup_info = {
            'configs': [],
            'data': [],
            'logs': {}
        }
        
        try:
            # Информация о бэкапах конфигураций
            configs_dir = self.base_backup_dir / "configs"
            for backup_file in configs_dir.glob("bot_configs_*.tar.gz"):
                stat = backup_file.stat()
                backup_info['configs'].append({
                    'filename': backup_file.name,
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'path': str(backup_file)
                })
            
            # Информация о бэкапах данных
            data_dir = self.base_backup_dir / "data"
            for backup_file in data_dir.glob("data_backup_*.tar.gz"):
                stat = backup_file.stat()
                backup_info['data'].append({
                    'filename': backup_file.name,
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'path': str(backup_file)
                })
            
            # Информация о бэкапах логов по ботам
            logs_dir = self.base_backup_dir / "logs"
            for bot_dir in logs_dir.iterdir():
                if bot_dir.is_dir():
                    bot_id = bot_dir.name
                    backup_info['logs'][bot_id] = []
                    
                    for backup_file in bot_dir.glob("logs_backup_*.tar.gz"):
                        stat = backup_file.stat()
                        backup_info['logs'][bot_id].append({
                            'filename': backup_file.name,
                            'size': stat.st_size,
                            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                            'path': str(backup_file)
                        })
            
            return backup_info
            
        except Exception as e:
            print(f"Ошибка получения информации о бэкапах: {e}")
            return backup_info

    def _cleanup_old_backups(self, backup_dir: Path, pattern: str, max_backups: int):
        """Удаление старых бэкапов"""
        try:
            backups = sorted(backup_dir.glob(pattern), key=lambda x: x.stat().st_mtime)
            if len(backups) > max_backups:
                for old_backup in backups[:-max_backups]:
                    old_backup.unlink()
                    print(f"Удален старый бэкап: {old_backup.name}")
        except Exception as e:
            print(f"Ошибка очистки старых бэкапов: {e}")

    def cleanup_all_old_backups(self, days_to_keep: int = 30):
        """Очистка всех бэкапов старше указанного количества дней"""
        try:
            cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
            
            for backup_dir in [self.base_backup_dir / "configs", 
                              self.base_backup_dir / "data",
                              self.base_backup_dir / "logs"]:
                if backup_dir.exists():
                    for backup_file in backup_dir.rglob("*.tar.gz"):
                        if backup_file.stat().st_mtime < cutoff_time:
                            backup_file.unlink()
                            print(f"Удален старый бэкап: {backup_file}")
                            
        except Exception as e:
            print(f"Ошибка очистки старых бэкапов: {e}")


# Обратная совместимость со старой функцией
def create_backup(source_dir: str, backup_dir: str, max_backups: int = 30) -> bool:
    """Создает сжатый бэкап логов (обратная совместимость)"""
    backup_manager = BackupManager()
    
    if "logs" in source_dir:
        # Извлекаем bot_id из пути
        bot_id = Path(source_dir).parent.name if "bot_" in source_dir else "unknown"
        return backup_manager.create_bot_logs_backup(bot_id, max_backups)
    else:
        return backup_manager.create_data_backup(max_backups)


# Пример использования
if __name__ == "__main__":
    backup_manager = BackupManager()
    
    # Создание полного бэкапа
    results = backup_manager.create_full_backup()
    print("Результаты создания бэкапа:", results)
    
    # Получение информации о бэкапах
    info = backup_manager.get_backup_info()
    print("Информация о бэкапах:", json.dumps(info, indent=2, ensure_ascii=False))
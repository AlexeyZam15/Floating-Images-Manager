# src/utils.py
import json
import shutil
from pathlib import Path
from src.constants import CONFIG_DIR, CONFIG_FILE, GALLERY_FILE, STORAGE_DIR, APP_DIR


def ensure_app_directories():
    """Создает все необходимые папки приложения в My Documents/floating_images"""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Папки созданы в: {APP_DIR}")
        return True
    except Exception as e:
        print(f"Ошибка создания папок: {e}")
        return False


def migrate_old_files():
    """Переносит старые файлы из старой папки в новую в My Documents/floating_images"""
    old_config_dir = Path(__file__).parent.parent / "config"
    old_storage_dir = Path(__file__).parent.parent / "storage"

    ensure_app_directories()
    migrated = False

    # Переносим файл настроек
    old_config_file = old_config_dir / "settings.json"
    if old_config_file.exists():
        try:
            shutil.copy2(old_config_file, CONFIG_FILE)
            print(f"Перенесен файл настроек: {old_config_file} -> {CONFIG_FILE}")
            migrated = True
        except Exception as e:
            print(f"Ошибка переноса настроек: {e}")

    # Переносим файл галереи
    old_gallery_file = old_config_dir / "gallery.json"
    if old_gallery_file.exists():
        try:
            shutil.copy2(old_gallery_file, GALLERY_FILE)
            print(f"Перенесен файл галереи: {old_gallery_file} -> {GALLERY_FILE}")
            migrated = True
        except Exception as e:
            print(f"Ошибка переноса галереи: {e}")

    # Переносим файлы из storage
    if old_storage_dir.exists():
        try:
            for old_file in old_storage_dir.glob("*"):
                if old_file.is_file():
                    new_file = STORAGE_DIR / old_file.name
                    if not new_file.exists():
                        shutil.copy2(old_file, new_file)
                        print(f"Перенесен файл: {old_file.name}")
                        migrated = True
        except Exception as e:
            print(f"Ошибка переноса файлов storage: {e}")

    return migrated
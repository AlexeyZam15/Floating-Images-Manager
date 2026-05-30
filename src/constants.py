# src/constants.py
from pathlib import Path

# Получаем путь к папке Documents/floating_images
DOCUMENTS_DIR = Path.home() / "Documents" / "floating_images"
APP_DIR = DOCUMENTS_DIR
CONFIG_DIR = APP_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "settings.json"
GALLERY_FILE = CONFIG_DIR / "gallery.json"
STORAGE_DIR = APP_DIR / "storage"
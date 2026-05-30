# src/constants.py

from pathlib import Path
import sys
import os


def get_app_base_dir():
    """
    Определяет базовую директорию приложения, корректно работая и в разработке, и в скомпилированном EXE.

    Возвращает:
        Path: путь к директории, где должно создаваться хранилище данных
    """
    if getattr(sys, 'frozen', False):
        exe_dir = Path(os.path.dirname(sys.executable))
        return exe_dir
    else:
        return Path(__file__).parent.parent


DOCUMENTS_DIR = Path.home() / "Documents" / "floating_images"
APP_DIR = DOCUMENTS_DIR
CONFIG_DIR = APP_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "settings.json"
GALLERY_FILE = CONFIG_DIR / "gallery.json"
STORAGE_DIR = APP_DIR / "storage"
# main.py

import sys
import os
import subprocess
import time
from pathlib import Path


def setup_frozen_environment():
    """
    Настраивает окружение для замороженного EXE файла до любых импортов.
    Добавляет все необходимые пути для корректной работы encodings и других модулей.
    """
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS

        if base_path not in sys.path:
            sys.path.insert(0, base_path)

        encodings_path = os.path.join(base_path, 'encodings')
        if os.path.exists(encodings_path):
            if encodings_path not in sys.path:
                sys.path.insert(0, encodings_path)

        os.environ['PYTHONIOENCODING'] = 'utf-8'
        os.environ['PYTHONLEGACYWINDOWSSTDIO'] = 'utf-8'


setup_frozen_environment()

from src.settings import Settings
from src.gallery import ImageGallery, ensure_app_directories, migrate_old_files

if __name__ == "__main__":
    ensure_app_directories()
    migrate_old_files()

    app = ImageGallery()
    app.run()
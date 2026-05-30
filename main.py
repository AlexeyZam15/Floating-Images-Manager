import sys
import subprocess
from pathlib import Path

# Добавляем текущую папку в путь поиска модулей
sys.path.insert(0, str(Path(__file__).parent))

from src.settings import Settings
from src.gallery import ImageGallery
from src.utils import ensure_app_directories, migrate_old_files


def restart_app():
    """Перезапускает приложение"""
    try:
        subprocess.Popen([sys.executable] + sys.argv)
        sys.exit(0)
    except Exception as e:
        print(f"Ошибка перезапуска: {e}")


if __name__ == "__main__":
    # Создаем папки и мигрируем старые файлы
    ensure_app_directories()
    migrate_old_files()

    # Запускаем приложение
    app = ImageGallery()
    app.run()
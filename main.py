# main.py
import sys
import os
import subprocess
from pathlib import Path


def fix_frozen_paths():
    """
    Исправляет пути к модулям в замороженном приложении PyInstaller.
    Без этого при перезапуске exe возникает ошибка 'Failed to import encodings module'
    """
    if getattr(sys, 'frozen', False):
        # Получаем путь к временной папке, куда PyInstaller распаковывает файлы
        base_path = sys._MEIPASS

        # Добавляем base_path в sys.path если его там нет
        if base_path not in sys.path:
            sys.path.insert(0, base_path)

        # Принудительно добавляем путь к encodings
        encodings_path = os.path.join(base_path, 'encodings')
        if os.path.exists(encodings_path) and encodings_path not in sys.path:
            sys.path.insert(0, encodings_path)

        # Для Windows также добавляем library.zip если он существует
        library_zip = os.path.join(base_path, 'library.zip')
        if os.path.exists(library_zip) and library_zip not in sys.path:
            sys.path.insert(0, library_zip)


# Вызываем исправление путей ДО любого импорта
fix_frozen_paths()

# Теперь безопасно импортируем все модули
from src.settings import Settings
from src.gallery import ImageGallery
from src.utils import ensure_app_directories, migrate_old_files


def restart_app():
    """
    Перезапускает приложение с корректной передачей путей для замороженного exe.
    Использует временный BAT-файл для изоляции переменных окружения.
    """
    import tempfile

    try:
        if getattr(sys, 'frozen', False):
            # Запущено как exe
            executable_path = sys.executable

            # Создаем временный BAT-файл для запуска с правильным окружением
            bat_file = tempfile.NamedTemporaryFile(mode='w', suffix='.bat', delete=False)

            bat_content = '@echo off\n'
            bat_content += 'SET PYTHONPATH=%TEMP%\\_MEI*\\\n'
            bat_content += f'START "" "{executable_path}"\n'
            bat_content += 'TIMEOUT /T 1 /NOBREAK > NUL\n'
            bat_content += 'EXIT\n'

            bat_file.write(bat_content)
            bat_file.close()

            if sys.platform == 'win32':
                subprocess.Popen(
                    [bat_file.name],
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                    shell=True
                )
            else:
                subprocess.Popen([bat_file.name], shell=True)

            # Очистка BAT-файла
            def cleanup():
                try:
                    time.sleep(2)
                    os.unlink(bat_file.name)
                except:
                    pass

            threading.Thread(target=cleanup, daemon=True).start()

        else:
            # Запущено как скрипт
            script_path = os.path.abspath(sys.argv[0])
            args = [sys.executable, script_path] + sys.argv[1:]
            env = os.environ.copy()

            if sys.platform == 'win32':
                subprocess.Popen(
                    args,
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                    env=env
                )
            else:
                subprocess.Popen(args, env=env)

        import time
        time.sleep(0.5)
        sys.exit(0)

    except Exception as e:
        print(f"Ошибка перезапуска: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Создаем папки и мигрируем старые файлы
    ensure_app_directories()
    migrate_old_files()

    # Запускаем приложение
    app = ImageGallery()
    app.run()
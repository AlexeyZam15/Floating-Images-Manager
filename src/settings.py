import json
from pathlib import Path
from src.constants import CONFIG_DIR, CONFIG_FILE


class Settings:
    """Класс для управления настройками"""

    DEFAULT_SETTINGS = {
        "zoom_slow": 1.03,
        "zoom_normal": 1.08,
        "zoom_fast": 1.25,
        "min_zoom": 0.3,
        "max_zoom": 10.0,
        "animation_speed": 0.3,
        "border_size": 8,
        "title_bar_height": 35,
        "hide_delay": 1500,
        "always_on_top": True,
        "zoom_animation": True,
        "animation_duration": 150,
        "language": "ru"
    }

    def __init__(self):
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.load()

    def ensure_config_dir(self):
        if not CONFIG_DIR.exists():
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    def load(self):
        try:
            self.ensure_config_dir()
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    for key in self.settings:
                        if key in loaded:
                            self.settings[key] = loaded[key]
                    print(f"Настройки загружены из {CONFIG_FILE}")
            else:
                print(f"Файл настроек не найден, создаем новый: {CONFIG_FILE}")
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")

    def save(self):
        try:
            self.ensure_config_dir()
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            print(f"Настройки сохранены в {CONFIG_FILE}")
            return True
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")
            return False

    def get(self, key):
        return self.settings.get(key, self.DEFAULT_SETTINGS.get(key))

    def set(self, key, value):
        self.settings[key] = value
        self.save()

    def get_language(self):
        """Возвращает текущий язык"""
        return self.settings.get("language", "ru")

    def set_language(self, lang):
        """Устанавливает язык"""
        self.settings["language"] = lang
        self.save()

    def get_string(self, key):
        """Возвращает строку на текущем языке"""
        from src.strings import STRINGS
        lang = self.get_language()
        return STRINGS.get(lang, STRINGS['ru']).get(key, key)
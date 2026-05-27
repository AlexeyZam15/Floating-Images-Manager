import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageGrab
import os
from pathlib import Path
import time
import threading
import json
from functools import lru_cache
import shutil
import math

# ============== НАСТРОЙКИ ==============
# Получаем путь к папке с приложением
APP_DIR = Path(__file__).parent.absolute()
CONFIG_DIR = APP_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "settings.json"
GALLERY_FILE = CONFIG_DIR / "gallery.json"
STORAGE_DIR = APP_DIR / "storage"


# Функция для миграции старых файлов
def migrate_old_files():
    """Переносит старые файлы из AppData в папку с приложением"""
    old_config_dir = Path.home() / "AppData" / "Local" / "floating_images"
    old_config_file = old_config_dir / "settings.json"
    old_gallery_file = old_config_dir / "gallery.json"
    old_temp_dir = old_config_dir

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    migrated = False

    if old_config_file.exists():
        try:
            shutil.copy2(old_config_file, CONFIG_FILE)
            print(f"Перенесен файл настроек: {old_config_file} -> {CONFIG_FILE}")
            migrated = True
        except Exception as e:
            print(f"Ошибка переноса настроек: {e}")

    if old_gallery_file.exists():
        try:
            shutil.copy2(old_gallery_file, GALLERY_FILE)
            print(f"Перенесен файл галереи: {old_gallery_file} -> {GALLERY_FILE}")
            migrated = True
        except Exception as e:
            print(f"Ошибка переноса галереи: {e}")

    if old_temp_dir.exists():
        try:
            temp_files_copied = 0
            for old_temp_file in old_temp_dir.glob("clipboard_*.png"):
                new_storage_file = STORAGE_DIR / old_temp_file.name
                if not new_storage_file.exists():
                    shutil.copy2(old_temp_file, new_storage_file)
                    temp_files_copied += 1
            if temp_files_copied > 0:
                print(f"Перенесено {temp_files_copied} временных файлов в storage")
                migrated = True
        except Exception as e:
            print(f"Ошибка переноса временных файлов: {e}")

    if migrated and GALLERY_FILE.exists():
        try:
            with open(GALLERY_FILE, 'r', encoding='utf-8') as f:
                gallery_data = json.load(f)

            updated = False
            new_gallery_data = []

            for old_path in gallery_data:
                if str(old_temp_dir) in old_path or "clipboard_" in old_path:
                    filename = Path(old_path).name
                    new_path = str(STORAGE_DIR / filename)
                    if os.path.exists(new_path) or os.path.exists(old_path):
                        new_gallery_data.append(new_path)
                        updated = True
                    else:
                        print(f"Пропущен несуществующий файл: {old_path}")
                else:
                    new_gallery_data.append(old_path)

            if updated:
                with open(GALLERY_FILE, 'w', encoding='utf-8') as f:
                    json.dump(new_gallery_data, f, indent=4, ensure_ascii=False)
                print("Обновлены пути в gallery.json")
        except Exception as e:
            print(f"Ошибка обновления путей в gallery.json: {e}")

    try:
        if old_config_dir.exists():
            if old_config_file.exists() and CONFIG_FILE.exists():
                old_config_file.unlink()
            if old_gallery_file.exists() and GALLERY_FILE.exists():
                old_gallery_file.unlink()
            for old_temp_file in old_temp_dir.glob("clipboard_*.png"):
                new_storage_file = STORAGE_DIR / old_temp_file.name
                if new_storage_file.exists():
                    old_temp_file.unlink()
            try:
                if old_config_dir.exists() and not any(old_config_dir.iterdir()):
                    old_config_dir.rmdir()
            except:
                pass
    except Exception as e:
        print(f"Ошибка при удалении старых файлов: {e}")


migrate_old_files()


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
        "animation_duration": 150
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


# ============== ОКНО НАСТРОЕК ==============
class SettingsWindow:
    def __init__(self, parent, settings, on_settings_changed):
        self.parent = parent
        self.settings = settings
        self.on_settings_changed = on_settings_changed
        self.is_fullscreen = False
        self.normal_geometry = None

        self.window = tk.Toplevel(parent)
        self.window.title("Настройки программы")
        self.window.configure(bg='#2b2b2b')

        self.window.geometry("650x650")
        self.window.minsize(600, 500)
        self.window.resizable(True, True)

        self.center_window()
        self.window.transient(parent)
        self.window.grab_set()

        self.create_menu_bar()
        self.create_widgets()

        self.load_values()
        self.update_labels()

        self.window.update_idletasks()
        self.adjust_window_size()

    def adjust_window_size(self):
        self.window.update_idletasks()
        req_height = self.scrollable_frame.winfo_reqheight() + 50
        current_width = self.window.winfo_width()
        max_height = int(self.window.winfo_screenheight() * 0.8)
        new_height = min(req_height, max_height)
        self.window.geometry(f"{current_width}x{new_height}")
        self.center_window()

    def create_menu_bar(self):
        menubar = tk.Menu(self.window, bg='#2b2b2b', fg='white')
        self.window.config(menu=menubar)

        window_menu = tk.Menu(menubar, tearoff=0, bg='#2b2b2b', fg='white')
        menubar.add_cascade(label="Окно", menu=window_menu)
        window_menu.add_command(label="На весь экран (F11)", command=self.toggle_fullscreen)
        window_menu.add_separator()
        window_menu.add_command(label="Закрыть (Esc)", command=self.window.destroy)

        self.window.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.window.bind("<Escape>", lambda e: self.exit_fullscreen() if self.is_fullscreen else None)

    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.exit_fullscreen()
        else:
            self.enter_fullscreen()

    def enter_fullscreen(self):
        self.normal_geometry = self.window.geometry()
        self.window.attributes('-fullscreen', True)
        self.is_fullscreen = True

    def exit_fullscreen(self):
        self.window.attributes('-fullscreen', False)
        if self.normal_geometry:
            self.window.geometry(self.normal_geometry)
        self.is_fullscreen = False

    def center_window(self):
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')

    def create_widgets(self):
        self.canvas_frame = tk.Frame(self.window, bg='#2b2b2b')
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.canvas_frame, bg='#2b2b2b', highlightthickness=0)
        scrollbar = tk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg='#2b2b2b')

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.scrollable_frame.bind("<MouseWheel>", self.on_mousewheel)

        main_container = self.scrollable_frame

        title = tk.Label(main_container, text="⚙️ НАСТРОЙКИ ПРОГРАММЫ",
                         font=('Segoe UI', 18, 'bold'), bg='#2b2b2b', fg='white')
        title.pack(pady=(10, 20))

        zoom_frame = tk.LabelFrame(main_container, text="🎯 СКОРОСТЬ ЗУМА",
                                   bg='#2b2b2b', fg='white', font=('Segoe UI', 13, 'bold'),
                                   padx=20, pady=15)
        zoom_frame.pack(fill="x", pady=(0, 15), padx=20)

        frame1 = tk.Frame(zoom_frame, bg='#2b2b2b')
        frame1.pack(fill="x", pady=8)
        tk.Label(frame1, text="Медленный зум (Ctrl + Колесо):",
                 bg='#2b2b2b', fg='#cccccc', font=('Segoe UI', 11)).pack(side=tk.LEFT, padx=(0, 15))
        self.slow_zoom_var = tk.DoubleVar()
        self.slow_zoom_scale = tk.Scale(frame1, from_=1.01, to=1.1, resolution=0.005,
                                        orient=tk.HORIZONTAL, variable=self.slow_zoom_var,
                                        bg='#3c3c3c', fg='white', highlightthickness=0, width=18)
        self.slow_zoom_scale.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=15)
        self.slow_zoom_label = tk.Label(frame1, text="", bg='#2b2b2b', fg='#00ff00', width=8,
                                        font=('Segoe UI', 11, 'bold'))
        self.slow_zoom_label.pack(side=tk.LEFT)

        frame2 = tk.Frame(zoom_frame, bg='#2b2b2b')
        frame2.pack(fill="x", pady=8)
        tk.Label(frame2, text="Обычный зум (Колесо):",
                 bg='#2b2b2b', fg='#cccccc', font=('Segoe UI', 11)).pack(side=tk.LEFT, padx=(0, 15))
        self.normal_zoom_var = tk.DoubleVar()
        self.normal_zoom_scale = tk.Scale(frame2, from_=1.01, to=1.2, resolution=0.005,
                                          orient=tk.HORIZONTAL, variable=self.normal_zoom_var,
                                          bg='#3c3c3c', fg='white', highlightthickness=0, width=18)
        self.normal_zoom_scale.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=15)
        self.normal_zoom_label = tk.Label(frame2, text="", bg='#2b2b2b', fg='#00ff00', width=8,
                                          font=('Segoe UI', 11, 'bold'))
        self.normal_zoom_label.pack(side=tk.LEFT)

        frame3 = tk.Frame(zoom_frame, bg='#2b2b2b')
        frame3.pack(fill="x", pady=8)
        tk.Label(frame3, text="Быстрый зум (Shift + Колесо):",
                 bg='#2b2b2b', fg='#cccccc', font=('Segoe UI', 11)).pack(side=tk.LEFT, padx=(0, 15))
        self.fast_zoom_var = tk.DoubleVar()
        self.fast_zoom_scale = tk.Scale(frame3, from_=1.05, to=1.5, resolution=0.01,
                                        orient=tk.HORIZONTAL, variable=self.fast_zoom_var,
                                        bg='#3c3c3c', fg='white', highlightthickness=0, width=18)
        self.fast_zoom_scale.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=15)
        self.fast_zoom_label = tk.Label(frame3, text="", bg='#2b2b2b', fg='#00ff00', width=8,
                                        font=('Segoe UI', 11, 'bold'))
        self.fast_zoom_label.pack(side=tk.LEFT)

        limits_frame = tk.LabelFrame(main_container, text="📏 ОГРАНИЧЕНИЯ ЗУМА",
                                     bg='#2b2b2b', fg='white', font=('Segoe UI', 13, 'bold'),
                                     padx=20, pady=15)
        limits_frame.pack(fill="x", pady=(0, 15), padx=20)

        frame4 = tk.Frame(limits_frame, bg='#2b2b2b')
        frame4.pack(fill="x", pady=8)
        tk.Label(frame4, text="Минимальный зум:",
                 bg='#2b2b2b', fg='#cccccc', font=('Segoe UI', 11)).pack(side=tk.LEFT, padx=(0, 15))
        self.min_zoom_var = tk.DoubleVar()
        self.min_zoom_scale = tk.Scale(frame4, from_=0.1, to=1.0, resolution=0.05,
                                       orient=tk.HORIZONTAL, variable=self.min_zoom_var,
                                       bg='#3c3c3c', fg='white', highlightthickness=0, width=18)
        self.min_zoom_scale.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=15)
        self.min_zoom_label = tk.Label(frame4, text="", bg='#2b2b2b', fg='#00ff00', width=8,
                                       font=('Segoe UI', 11, 'bold'))
        self.min_zoom_label.pack(side=tk.LEFT)

        frame5 = tk.Frame(limits_frame, bg='#2b2b2b')
        frame5.pack(fill="x", pady=8)
        tk.Label(frame5, text="Максимальный зум:",
                 bg='#2b2b2b', fg='#cccccc', font=('Segoe UI', 11)).pack(side=tk.LEFT, padx=(0, 15))
        self.max_zoom_var = tk.DoubleVar()
        self.max_zoom_scale = tk.Scale(frame5, from_=2.0, to=20.0, resolution=0.5,
                                       orient=tk.HORIZONTAL, variable=self.max_zoom_var,
                                       bg='#3c3c3c', fg='white', highlightthickness=0, width=18)
        self.max_zoom_scale.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=15)
        self.max_zoom_label = tk.Label(frame5, text="", bg='#2b2b2b', fg='#00ff00', width=8,
                                       font=('Segoe UI', 11, 'bold'))
        self.max_zoom_label.pack(side=tk.LEFT)

        animation_frame = tk.LabelFrame(main_container, text="🎬 АНИМАЦИЯ",
                                        bg='#2b2b2b', fg='white', font=('Segoe UI', 13, 'bold'),
                                        padx=20, pady=15)
        animation_frame.pack(fill="x", pady=(0, 15), padx=20)

        self.zoom_animation_var = tk.BooleanVar()
        zoom_animation_cb = tk.Checkbutton(animation_frame, text="Включить плавную анимацию зума",
                                           variable=self.zoom_animation_var,
                                           bg='#2b2b2b', fg='white', selectcolor='#2b2b2b',
                                           font=('Segoe UI', 11))
        zoom_animation_cb.pack(anchor=tk.W, pady=5)

        frame_anim = tk.Frame(animation_frame, bg='#2b2b2b')
        frame_anim.pack(fill="x", pady=8)
        tk.Label(frame_anim, text="Длительность анимации (мс):",
                 bg='#2b2b2b', fg='#cccccc', font=('Segoe UI', 11)).pack(side=tk.LEFT, padx=(0, 15))
        self.anim_duration_var = tk.IntVar()
        self.anim_duration_scale = tk.Scale(frame_anim, from_=50, to=300, resolution=10,
                                            orient=tk.HORIZONTAL, variable=self.anim_duration_var,
                                            bg='#3c3c3c', fg='white', highlightthickness=0, width=18)
        self.anim_duration_scale.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=15)
        self.anim_duration_label = tk.Label(frame_anim, text="", bg='#2b2b2b', fg='#00ff00', width=8,
                                            font=('Segoe UI', 11, 'bold'))
        self.anim_duration_label.pack(side=tk.LEFT)

        ui_frame = tk.LabelFrame(main_container, text="🎨 ИНТЕРФЕЙС",
                                 bg='#2b2b2b', fg='white', font=('Segoe UI', 13, 'bold'),
                                 padx=20, pady=15)
        ui_frame.pack(fill="x", pady=(0, 15), padx=20)

        frame6 = tk.Frame(ui_frame, bg='#2b2b2b')
        frame6.pack(fill="x", pady=8)
        tk.Label(frame6, text="Задержка скрытия кнопок (мс):",
                 bg='#2b2b2b', fg='#cccccc', font=('Segoe UI', 11)).pack(side=tk.LEFT, padx=(0, 15))
        self.hide_delay_var = tk.IntVar()
        self.hide_delay_scale = tk.Scale(frame6, from_=500, to=5000, resolution=100,
                                         orient=tk.HORIZONTAL, variable=self.hide_delay_var,
                                         bg='#3c3c3c', fg='white', highlightthickness=0, width=18)
        self.hide_delay_scale.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=15)
        self.hide_delay_label = tk.Label(frame6, text="", bg='#2b2b2b', fg='#00ff00', width=8,
                                         font=('Segoe UI', 11, 'bold'))
        self.hide_delay_label.pack(side=tk.LEFT)

        frame7 = tk.Frame(ui_frame, bg='#2b2b2b')
        frame7.pack(fill="x", pady=8)
        tk.Label(frame7, text="Размер границы окна (пикс):",
                 bg='#2b2b2b', fg='#cccccc', font=('Segoe UI', 11)).pack(side=tk.LEFT, padx=(0, 15))
        self.border_size_var = tk.IntVar()
        self.border_size_scale = tk.Scale(frame7, from_=4, to=15, resolution=1,
                                          orient=tk.HORIZONTAL, variable=self.border_size_var,
                                          bg='#3c3c3c', fg='white', highlightthickness=0, width=18)
        self.border_size_scale.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=15)
        self.border_size_label = tk.Label(frame7, text="", bg='#2b2b2b', fg='#00ff00', width=8,
                                          font=('Segoe UI', 11, 'bold'))
        self.border_size_label.pack(side=tk.LEFT)

        button_frame = tk.Frame(main_container, bg='#2b2b2b')
        button_frame.pack(fill="x", pady=25, padx=20)

        btn_save = tk.Button(button_frame, text="💾 СОХРАНИТЬ", command=self.save_settings,
                             bg='#0078d4', fg='white', padx=20, pady=10,
                             font=('Segoe UI', 11, 'bold'), cursor='hand2')
        btn_save.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        btn_reset = tk.Button(button_frame, text="↺ СБРОСИТЬ", command=self.reset_settings,
                              bg='#3c3c3c', fg='white', padx=20, pady=10,
                              font=('Segoe UI', 11, 'bold'), cursor='hand2')
        btn_reset.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        btn_cancel = tk.Button(button_frame, text="❌ ОТМЕНА", command=self.window.destroy,
                               bg='#5a5a5a', fg='white', padx=20, pady=10,
                               font=('Segoe UI', 11, 'bold'), cursor='hand2')
        btn_cancel.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        self.slow_zoom_scale.configure(command=lambda x: self.update_labels())
        self.normal_zoom_scale.configure(command=lambda x: self.update_labels())
        self.fast_zoom_scale.configure(command=lambda x: self.update_labels())
        self.min_zoom_scale.configure(command=lambda x: self.update_labels())
        self.max_zoom_scale.configure(command=lambda x: self.update_labels())
        self.hide_delay_scale.configure(command=lambda x: self.update_labels())
        self.border_size_scale.configure(command=lambda x: self.update_labels())
        self.anim_duration_scale.configure(command=lambda x: self.update_labels())

    def on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def update_labels(self):
        self.slow_zoom_label.config(text=f"{self.slow_zoom_var.get():.2f}x")
        self.normal_zoom_label.config(text=f"{self.normal_zoom_var.get():.2f}x")
        self.fast_zoom_label.config(text=f"{self.fast_zoom_var.get():.2f}x")
        self.min_zoom_label.config(text=f"{self.min_zoom_var.get():.1f}x")
        self.max_zoom_label.config(text=f"{self.max_zoom_var.get():.1f}x")
        self.hide_delay_label.config(text=f"{self.hide_delay_var.get()} мс")
        self.border_size_label.config(text=f"{self.border_size_var.get()} px")
        self.anim_duration_label.config(text=f"{self.anim_duration_var.get()} мс")

    def load_values(self):
        self.slow_zoom_var.set(self.settings.get("zoom_slow"))
        self.normal_zoom_var.set(self.settings.get("zoom_normal"))
        self.fast_zoom_var.set(self.settings.get("zoom_fast"))
        self.min_zoom_var.set(self.settings.get("min_zoom"))
        self.max_zoom_var.set(self.settings.get("max_zoom"))
        self.hide_delay_var.set(self.settings.get("hide_delay"))
        self.border_size_var.set(self.settings.get("border_size"))
        self.zoom_animation_var.set(self.settings.get("zoom_animation"))
        self.anim_duration_var.set(self.settings.get("animation_duration"))

    def save_settings(self):
        self.settings.set("zoom_slow", self.slow_zoom_var.get())
        self.settings.set("zoom_normal", self.normal_zoom_var.get())
        self.settings.set("zoom_fast", self.fast_zoom_var.get())
        self.settings.set("min_zoom", self.min_zoom_var.get())
        self.settings.set("max_zoom", self.max_zoom_var.get())
        self.settings.set("hide_delay", self.hide_delay_var.get())
        self.settings.set("border_size", self.border_size_var.get())
        self.settings.set("zoom_animation", self.zoom_animation_var.get())
        self.settings.set("animation_duration", self.anim_duration_var.get())

        if self.on_settings_changed:
            self.on_settings_changed()

        messagebox.showinfo("Настройки", "Настройки сохранены!\nОни применятся к новым окнам.")
        self.window.destroy()

    def reset_settings(self):
        if messagebox.askyesno("Сброс настроек", "Вы уверены, что хотите сбросить все настройки к стандартным?"):
            for key, value in Settings.DEFAULT_SETTINGS.items():
                self.settings.set(key, value)
            self.load_values()
            self.update_labels()
            messagebox.showinfo("Настройки", "Настройки сброшены к стандартным")


# ============== ОСНОВНОЙ КЛАСС ПЛАВАЮЩЕГО ОКНА ==============
class FloatingImage:
    def __init__(self, master, image_path, window_id, settings):
        self.master = master
        self.image_path = image_path
        self.window_id = window_id
        self.settings = settings
        self.parent_gallery = None

        self.resizing = False
        self.resize_edge = None
        self.moving = False
        self.image_loaded = False
        self.loading_thread = None
        self.mouse_over = False

        self.resize_with_shift = False
        self.resize_with_ctrl = False

        self.user_zoom = 1.0

        # Для панорамирования
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.panning = False
        self.pan_start_image_x = 0
        self.pan_start_image_y = 0

        # Для перемещения окна
        self.window_moving = False
        self.window_move_start_x = 0
        self.window_move_start_y = 0

        self.stretch_mode = False
        self.stretch_width = 0
        self.stretch_height = 0

        self.zoom_step_slow = self.settings.get("zoom_slow")
        self.zoom_step_normal = self.settings.get("zoom_normal")
        self.zoom_step_fast = self.settings.get("zoom_fast")
        self.min_zoom = self.settings.get("min_zoom")
        self.max_zoom = self.settings.get("max_zoom")
        self.title_bar_height = self.settings.get("title_bar_height")

        self.optimal_width = 400
        self.optimal_height = 300
        self.window_width = 400
        self.window_height = 300

        self.master.title("")
        self.master.overrideredirect(True)
        self.master.attributes('-topmost', self.settings.get("always_on_top"))
        self.master.configure(bg='#2b2b2b')
        self.master.minsize(50, 50)

        self.position_away_from_main()
        self.master.geometry(f"{self.window_width}x{self.window_height}")

        self.create_window_frame()
        self.bind_events()
        self.create_context_menu()

        self.show_loading_indicator()
        self.load_image_async()

        self.hide_timer = None

        self.current_image = None
        self.photo_image = None
        self.image_x = 0
        self.image_y = 0
        self.original_image = None
        self.original_width = 0
        self.original_height = 0

    def bind_events(self):
        self.canvas.bind("<MouseWheel>", self.on_mousewheel_zoom)
        self.canvas.bind("<ButtonPress-1>", self.start_pan)
        self.canvas.bind("<B1-Motion>", self.on_pan)
        self.canvas.bind("<ButtonRelease-1>", self.stop_pan)

        self.master.bind("<ButtonPress-1>", self.on_global_press)
        self.master.bind("<B1-Motion>", self.on_global_motion)
        self.master.bind("<ButtonRelease-1>", self.on_global_release)

        self.canvas.bind("<Button-2>", self.on_middle_click_reset)
        self.master.bind("<Button-2>", self.on_middle_click_reset)

        # Устанавливаем фокус
        self.master.focus_set()

    def start_window_move(self, event):
        self.window_moving = True
        self.window_move_start_x = event.x_root - self.master.winfo_x()
        self.window_move_start_y = event.y_root - self.master.winfo_y()

    def on_window_move(self, event):
        if self.window_moving:
            x = event.x_root - self.window_move_start_x
            y = event.y_root - self.window_move_start_y
            self.master.geometry(f"+{x}+{y}")

    def stop_window_move(self, event):
        self.window_moving = False

    def start_pan(self, event):
        if not self.image_loaded or self.user_zoom <= 1.0:
            return

        try:
            if event.widget != self.canvas:
                canvas_x = self.canvas.winfo_x()
                canvas_y = self.canvas.winfo_y()
                canvas_event_x = event.x - canvas_x
                canvas_event_y = event.y - canvas_y
            else:
                canvas_event_x = event.x
                canvas_event_y = event.y
        except:
            return

        img_width = int(self.original_width * self.user_zoom)
        img_height = int(self.original_height * self.user_zoom)

        if (self.image_x <= canvas_event_x <= self.image_x + img_width and
                self.image_y <= canvas_event_y <= self.image_y + img_height):
            self.panning = True
            self.pan_start_x = canvas_event_x
            self.pan_start_y = canvas_event_y
            self.pan_start_image_x = self.image_x
            self.pan_start_image_y = self.image_y
            self.canvas.config(cursor="fleur")
            return "break"

    def on_pan(self, event):
        if self.panning and self.image_loaded and self.user_zoom > 1.0:
            try:
                if event.widget != self.canvas:
                    canvas_x = self.canvas.winfo_x()
                    canvas_y = self.canvas.winfo_y()
                    canvas_event_x = event.x - canvas_x
                    canvas_event_y = event.y - canvas_y
                else:
                    canvas_event_x = event.x
                    canvas_event_y = event.y
            except:
                return

            dx = canvas_event_x - self.pan_start_x
            dy = canvas_event_y - self.pan_start_y

            new_x = self.pan_start_image_x + dx
            new_y = self.pan_start_image_y + dy

            img_width = int(self.original_width * self.user_zoom)
            img_height = int(self.original_height * self.user_zoom)
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            min_x = min(0, canvas_width - img_width)
            max_x = max(0, canvas_width - img_width)
            min_y = min(0, canvas_height - img_height)
            max_y = max(0, canvas_height - img_height)

            self.image_x = max(min(new_x, max_x), min_x)
            self.image_y = max(min(new_y, max_y), min_y)

            if self.current_image:
                self.canvas.coords(self.current_image, self.image_x, self.image_y)

            return "break"

    def stop_pan(self, event):
        self.panning = False
        self.canvas.config(cursor="arrow")

    def position_away_from_main(self):
        try:
            main_window = self.master.master
            if main_window and main_window.winfo_exists():
                main_x = main_window.winfo_x()
                main_y = main_window.winfo_y()
                main_width = main_window.winfo_width()
                main_height = main_window.winfo_height()

                screen_width = self.master.winfo_screenwidth()
                screen_height = self.master.winfo_screenheight()

                x = main_x + main_width + 20
                y = main_y + 50

                if x + self.window_width > screen_width - 50:
                    x = main_x - self.window_width - 20

                if x < 50:
                    x = 50

                if y + self.window_height > screen_height - 50:
                    y = screen_height - self.window_height - 50
                if y < 50:
                    y = 50

                self.master.geometry(f"+{int(x)}+{int(y)}")
            else:
                self.center_on_mouse()
        except:
            self.center_on_mouse()

    def center_on_mouse(self):
        mouse_x = self.master.winfo_pointerx()
        mouse_y = self.master.winfo_pointery()
        self.master.geometry(f"+{mouse_x - self.window_width // 2}+{mouse_y - self.window_height // 2}")

    def create_context_menu(self):
        self.context_menu = tk.Menu(self.master, tearoff=0, bg='#f0f0f0', fg='black')
        self.context_menu.add_command(label="🖼️ Увеличить", command=self.zoom_in)
        self.context_menu.add_command(label="🔍 Уменьшить", command=self.zoom_out)
        self.context_menu.add_command(label="⟳ Сбросить зум", command=self.reset_zoom)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="📏 Оптимальный размер", command=self.reset_size)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="📋 Копировать путь", command=self.copy_path)
        self.context_menu.add_command(label="🗑️ Закрыть", command=self.close)

        self.master.bind("<Button-3>", self.show_context_menu)
        self.canvas.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def copy_path(self):
        self.master.clipboard_clear()
        self.master.clipboard_append(self.image_path)
        self.show_tooltip("✅ Путь скопирован", 1000)

    def show_tooltip(self, text, duration=1500):
        tooltip = tk.Toplevel(self.master)
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry(f"+{self.master.winfo_pointerx() + 10}+{self.master.winfo_pointery() + 10}")
        label = tk.Label(tooltip, text=text, bg='#ffffcc', fg='black',
                         padx=10, pady=5, font=('Segoe UI', 10),
                         relief='solid', borderwidth=1)
        label.pack()
        tooltip.after(duration, tooltip.destroy)

    def show_loading_indicator(self):
        self.loading_label = tk.Label(self.canvas, text="🔄 Загрузка...",
                                      font=('Segoe UI', 12), bg='#2b2b2b', fg='white')
        self.loading_label.place(relx=0.5, rely=0.5, anchor='center')

    def hide_loading_indicator(self):
        if hasattr(self, 'loading_label') and self.loading_label:
            self.loading_label.destroy()
            self.loading_label = None

    def load_image_async(self):
        def load():
            try:
                original = Image.open(self.image_path)
                if original.mode not in ('RGB', 'RGBA'):
                    original = original.convert('RGB')
                self.master.after(0, self.on_image_loaded, original)
            except Exception as e:
                self.master.after(0, self.on_image_load_error, str(e))

        self.loading_thread = threading.Thread(target=load, daemon=True)
        self.loading_thread.start()

    def on_image_loaded(self, original_image):
        self.original_image = original_image
        self.original_width = self.original_image.width
        self.original_height = self.original_image.height

        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()

        max_width = min(self.original_width, int(screen_width * 0.6))
        max_height = min(self.original_height, int(screen_height * 0.6))

        if self.original_width > max_width or self.original_height > max_height:
            ratio = min(max_width / self.original_width, max_height / self.original_height)
            self.display_width = int(self.original_width * ratio)
            self.display_height = int(self.original_height * ratio)
            self.user_zoom = ratio
        else:
            self.display_width = self.original_width
            self.display_height = self.original_height
            self.user_zoom = 1.0

        self.optimal_width = self.display_width
        self.optimal_height = self.display_height

        self.window_width = self.display_width
        self.window_height = self.display_height
        self.master.geometry(f"{self.window_width}x{self.window_height}")

        self.update_canvas_size()
        self.update_image()

        self.hide_loading_indicator()
        self.image_loaded = True

        self.update_borders_position()

    def on_image_load_error(self, error_msg):
        self.hide_loading_indicator()
        messagebox.showerror("Ошибка", f"Не удалось загрузить {self.image_path}\n{error_msg}")
        self.master.destroy()

    def create_window_frame(self):
        self.canvas = tk.Canvas(self.master, bg='#2b2b2b', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.focus_set()

        self.master.update_idletasks()
        self.update_canvas_size()

        self.title_frame = tk.Frame(self.master, bg='#333333', height=35)
        self.title_frame.place(x=0, y=0, relwidth=1)

        filename = os.path.basename(self.image_path)
        if len(filename) > 40:
            filename = filename[:37] + "..."
        self.title_label = tk.Label(self.title_frame, text=filename, bg='#333333', fg='white',
                                    font=('Segoe UI', 10))
        self.title_label.pack(side=tk.LEFT, padx=10, expand=True, fill=tk.X)

        self.close_btn = tk.Button(self.title_frame, text="✖", font=('Segoe UI', 12, 'bold'),
                                   command=self.close, bg='#333333', fg='white',
                                   bd=0, activebackground='#e81123', activeforeground='white',
                                   width=4, cursor='hand2')
        self.close_btn.pack(side=tk.RIGHT, padx=5)

        self.title_label.bind("<Button-1>", self.start_window_move)
        self.title_label.bind("<B1-Motion>", self.on_window_move)
        self.title_label.bind("<ButtonRelease-1>", self.stop_window_move)
        self.title_frame.bind("<Button-1>", self.start_window_move)
        self.title_frame.bind("<B1-Motion>", self.on_window_move)
        self.title_frame.bind("<ButtonRelease-1>", self.stop_window_move)

        self.canvas.bind("<Configure>", self.on_canvas_configure)

        self.master.bind("<Enter>", self.on_mouse_enter)
        self.master.bind("<Leave>", self.on_mouse_leave)
        self.canvas.bind("<Enter>", self.on_mouse_enter)
        self.canvas.bind("<Leave>", self.on_mouse_leave)

        self.create_resize_borders()
        self.title_frame.place_forget()

    def on_mouse_enter(self, event):
        self.mouse_over = True
        if self.hide_timer:
            self.master.after_cancel(self.hide_timer)
            self.hide_timer = None
        self.show_all_ui()

    def on_mouse_leave(self, event):
        x = self.master.winfo_pointerx()
        y = self.master.winfo_pointery()
        widget = self.master.winfo_containing(x, y)

        if widget == self.title_frame or widget in self.title_frame.winfo_children():
            return

        self.mouse_over = False
        self.start_hide_timer()

    def start_hide_timer(self):
        if self.hide_timer:
            self.master.after_cancel(self.hide_timer)
        self.hide_timer = self.master.after(800, self.hide_all_ui)

    def show_all_ui(self):
        if self.image_loaded:
            self.title_frame.place(x=0, y=0, relwidth=1)
            self.show_resize_borders()

    def hide_all_ui(self):
        if not self.mouse_over:
            self.title_frame.place_forget()
            self.hide_resize_borders()

    def create_resize_borders(self):
        border_size = 8

        self.top_frame = tk.Frame(self.master, bg='#2b2b2b', height=border_size, cursor='size_ns')
        self.top_frame.place(x=0, y=0, width=self.master.winfo_width(), height=border_size)

        self.bottom_frame = tk.Frame(self.master, bg='#2b2b2b', height=border_size, cursor='size_ns')
        self.bottom_frame.place(x=0, y=self.master.winfo_height() - border_size,
                                width=self.master.winfo_width(), height=border_size)

        self.left_frame = tk.Frame(self.master, bg='#2b2b2b', width=border_size, cursor='size_we')
        self.left_frame.place(x=0, y=0, width=border_size, height=self.master.winfo_height())

        self.right_frame = tk.Frame(self.master, bg='#2b2b2b', width=border_size, cursor='size_we')
        self.right_frame.place(x=self.master.winfo_width() - border_size, y=0,
                               width=border_size, height=self.master.winfo_height())

        corner_size = 12
        self.top_left = tk.Frame(self.master, bg='#2b2b2b', width=corner_size, height=corner_size, cursor='size_nw_se')
        self.top_left.place(x=0, y=0, width=corner_size, height=corner_size)

        self.top_right = tk.Frame(self.master, bg='#2b2b2b', width=corner_size, height=corner_size, cursor='size_ne_sw')
        self.top_right.place(x=self.master.winfo_width() - corner_size, y=0, width=corner_size, height=corner_size)

        self.bottom_left = tk.Frame(self.master, bg='#2b2b2b', width=corner_size, height=corner_size,
                                    cursor='size_ne_sw')
        self.bottom_left.place(x=0, y=self.master.winfo_height() - corner_size, width=corner_size, height=corner_size)

        self.bottom_right = tk.Frame(self.master, bg='#2b2b2b', width=corner_size, height=corner_size,
                                     cursor='size_nw_se')
        self.bottom_right.place(x=self.master.winfo_width() - corner_size,
                                y=self.master.winfo_height() - corner_size,
                                width=corner_size, height=corner_size)

        for frame in [self.bottom_frame, self.top_frame, self.left_frame, self.right_frame,
                      self.top_left, self.top_right, self.bottom_left, self.bottom_right]:
            frame.bind("<Button-1>", self.start_resize)
            frame.bind("<B1-Motion>", self.on_resize)
            frame.bind("<ButtonRelease-1>", self.stop_resize)
            frame.bind("<Shift-Button-1>", self.start_resize_with_shift)
            frame.bind("<Control-Button-1>", self.start_resize_with_ctrl)

        self.hide_resize_borders()

    def start_resize_with_shift(self, event):
        self.resize_with_shift = True
        self.resize_with_ctrl = False
        self.start_resize(event)

    def start_resize_with_ctrl(self, event):
        self.resize_with_shift = False
        self.resize_with_ctrl = True
        self.start_resize(event)

    def show_resize_borders(self):
        if not hasattr(self, 'top_frame'):
            return

        current_width = self.master.winfo_width()
        current_height = self.master.winfo_height()
        border_size = 8
        corner_size = 12

        self.top_frame.configure(bg='#ffffff')
        self.top_frame.place(x=0, y=0, width=current_width, height=border_size)

        self.bottom_frame.configure(bg='#ffffff')
        self.bottom_frame.place(x=0, y=current_height - border_size, width=current_width, height=border_size)

        self.left_frame.configure(bg='#ffffff')
        self.left_frame.place(x=0, y=0, width=border_size, height=current_height)

        self.right_frame.configure(bg='#ffffff')
        self.right_frame.place(x=current_width - border_size, y=0, width=border_size, height=current_height)

        self.top_left.configure(bg='#ffffff')
        self.top_left.place(x=0, y=0, width=corner_size, height=corner_size)

        self.top_right.configure(bg='#ffffff')
        self.top_right.place(x=current_width - corner_size, y=0, width=corner_size, height=corner_size)

        self.bottom_left.configure(bg='#ffffff')
        self.bottom_left.place(x=0, y=current_height - corner_size, width=corner_size, height=corner_size)

        self.bottom_right.configure(bg='#ffffff')
        self.bottom_right.place(x=current_width - corner_size, y=current_height - corner_size,
                                width=corner_size, height=corner_size)

    def hide_resize_borders(self):
        if not hasattr(self, 'top_frame'):
            return

        for frame in [self.top_frame, self.bottom_frame, self.left_frame, self.right_frame,
                      self.top_left, self.top_right, self.bottom_left, self.bottom_right]:
            if frame:
                frame.place_forget()

    def start_resize(self, event):
        widget = event.widget
        if widget == self.top_frame:
            self.resize_edge = 'top'
        elif widget == self.bottom_frame:
            self.resize_edge = 'bottom'
        elif widget == self.left_frame:
            self.resize_edge = 'left'
        elif widget == self.right_frame:
            self.resize_edge = 'right'
        elif widget == self.top_left:
            self.resize_edge = 'top_left'
        elif widget == self.top_right:
            self.resize_edge = 'top_right'
        elif widget == self.bottom_left:
            self.resize_edge = 'bottom_left'
        elif widget == self.bottom_right:
            self.resize_edge = 'bottom_right'

        self.resizing = True
        self.resize_start_x = self.master.winfo_pointerx()
        self.resize_start_y = self.master.winfo_pointery()
        self.resize_start_width = self.master.winfo_width()
        self.resize_start_height = self.master.winfo_height()
        self.resize_start_left = self.master.winfo_x()
        self.resize_start_top = self.master.winfo_y()

        if self.image_loaded:
            self.original_aspect_ratio = self.original_width / self.original_height

    def on_resize(self, event):
        if not self.resizing or not self.image_loaded:
            return

        current_x = self.master.winfo_pointerx()
        current_y = self.master.winfo_pointery()
        delta_x = current_x - self.resize_start_x
        delta_y = current_y - self.resize_start_y

        new_width = self.resize_start_width
        new_height = self.resize_start_height
        new_x = self.resize_start_left
        new_y = self.resize_start_top

        min_width = 50
        min_height = 50

        if self.resize_edge == 'right':
            new_width = max(min_width, self.resize_start_width + delta_x)
        elif self.resize_edge == 'left':
            new_width = max(min_width, self.resize_start_width - delta_x)
            new_x = self.resize_start_left + (self.resize_start_width - new_width)
        elif self.resize_edge == 'bottom':
            new_height = max(min_height, self.resize_start_height + delta_y)
        elif self.resize_edge == 'top':
            new_height = max(min_height, self.resize_start_height - delta_y)
            new_y = self.resize_start_top + (self.resize_start_height - new_height)
        elif self.resize_edge == 'top_left':
            new_width = max(min_width, self.resize_start_width - delta_x)
            new_x = self.resize_start_left + (self.resize_start_width - new_width)
            new_height = max(min_height, self.resize_start_height - delta_y)
            new_y = self.resize_start_top + (self.resize_start_height - new_height)
        elif self.resize_edge == 'top_right':
            new_width = max(min_width, self.resize_start_width + delta_x)
            new_height = max(min_height, self.resize_start_height - delta_y)
            new_y = self.resize_start_top + (self.resize_start_height - new_height)
        elif self.resize_edge == 'bottom_left':
            new_width = max(min_width, self.resize_start_width - delta_x)
            new_x = self.resize_start_left + (self.resize_start_width - new_width)
            new_height = max(min_height, self.resize_start_height + delta_y)
        elif self.resize_edge == 'bottom_right':
            new_width = max(min_width, self.resize_start_width + delta_x)
            new_height = max(min_height, self.resize_start_height + delta_y)

        if self.resize_with_shift:
            aspect_ratio = self.original_width / self.original_height

            if self.resize_edge in ['left', 'right']:
                target_width = new_width
                target_height = int(target_width / aspect_ratio)
            elif self.resize_edge in ['top', 'bottom']:
                target_height = new_height
                target_width = int(target_height * aspect_ratio)
            else:
                width_change = abs(new_width - self.resize_start_width)
                height_change = abs(new_height - self.resize_start_height)
                if width_change >= height_change:
                    target_width = new_width
                    target_height = int(target_width / aspect_ratio)
                else:
                    target_height = new_height
                    target_width = int(target_height * aspect_ratio)

            if target_width < min_width:
                target_width = min_width
                target_height = int(target_width / aspect_ratio)
            if target_height < min_height:
                target_height = min_height
                target_width = int(target_height * aspect_ratio)

            if self.resize_edge in ['top', 'top_left', 'top_right']:
                new_y = self.resize_start_top + (self.resize_start_height - target_height)
            if self.resize_edge in ['left', 'top_left', 'bottom_left']:
                new_x = self.resize_start_left + (self.resize_start_width - target_width)

            self.master.geometry(f"{target_width}x{target_height}+{new_x}+{new_y}")

            self.window_width = target_width
            self.window_height = target_height
            self.user_zoom = target_width / self.original_width
            self.stretch_mode = False

            self.update_borders_position()
            self.update_image()
            return

        elif self.resize_with_ctrl:
            self.master.geometry(f"{new_width}x{new_height}+{new_x}+{new_y}")
            self.window_width = new_width
            self.window_height = new_height
            self.stretch_mode = False
            self.update_borders_position()
        else:
            self.master.geometry(f"{new_width}x{new_height}+{new_x}+{new_y}")
            self.window_width = new_width
            self.window_height = new_height
            self.stretch_mode = True
            self.stretch_width = new_width
            self.stretch_height = new_height
            self.user_zoom = 1.0

            self.update_borders_position()
            self.update_image()

    def update_image(self):
        if not self.image_loaded:
            return

        try:
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            if canvas_width <= 0 or canvas_height <= 0:
                canvas_width = self.window_width
                canvas_height = self.window_height

            if self.stretch_mode and self.stretch_width > 0 and self.stretch_height > 0:
                img_width = self.stretch_width
                img_height = self.stretch_height
            else:
                img_width = int(self.original_width * self.user_zoom)
                img_height = int(self.original_height * self.user_zoom)

            if img_width > 0 and img_height > 0:
                pil_image = self.get_scaled_image(img_width, img_height)
                if pil_image:
                    self.photo_image = ImageTk.PhotoImage(pil_image)
                    self.canvas.delete("all")

                    self.image_x = (canvas_width - img_width) // 2
                    self.image_y = (canvas_height - img_height) // 2

                    self.current_image = self.canvas.create_image(self.image_x, self.image_y, anchor=tk.NW,
                                                                  image=self.photo_image)

        except Exception as e:
            print(f"Ошибка обновления: {e}")

    def update_canvas_size(self):
        """Обновляет размер canvas"""
        width = self.master.winfo_width()
        height = self.master.winfo_height()
        if width > 0 and height > 0:
            self.canvas.config(width=width, height=height)

    def stop_resize(self, event):
        self.resizing = False
        self.resize_edge = None
        self.resize_with_shift = False
        self.resize_with_ctrl = False

        if self.stretch_mode:
            self.optimal_width = self.window_width
            self.optimal_height = self.window_height

    def exit_stretch_mode(self):
        if self.stretch_mode:
            self.stretch_mode = False
            self.stretch_width = 0
            self.stretch_height = 0
            if self.window_width > 0 and self.original_width > 0:
                self.user_zoom = self.window_width / self.original_width
            self.update_image()

    def update_borders_position(self):
        if not self.mouse_over:
            return

        current_width = self.master.winfo_width()
        current_height = self.master.winfo_height()
        border_size = 8
        corner_size = 12

        if hasattr(self, 'top_frame'):
            self.top_frame.place(x=0, y=0, width=current_width, height=border_size)
            self.bottom_frame.place(x=0, y=current_height - border_size, width=current_width, height=border_size)
            self.left_frame.place(x=0, y=0, width=border_size, height=current_height)
            self.right_frame.place(x=current_width - border_size, y=0, width=border_size, height=current_height)
            self.top_left.place(x=0, y=0, width=corner_size, height=corner_size)
            self.top_right.place(x=current_width - corner_size, y=0, width=corner_size, height=corner_size)
            self.bottom_left.place(x=0, y=current_height - corner_size, width=corner_size, height=corner_size)
            self.bottom_right.place(x=current_width - corner_size, y=current_height - corner_size,
                                    width=corner_size, height=corner_size)

    def on_mousewheel_zoom(self, event):
        if not self.image_loaded:
            return "break"

        if event.state & 0x0001:
            zoom_step = self.zoom_step_fast
        elif event.state & 0x0004:
            zoom_step = self.zoom_step_slow
        else:
            zoom_step = self.zoom_step_normal

        if event.delta > 0:
            factor = zoom_step
        else:
            factor = 1.0 / zoom_step

        new_zoom = self.user_zoom * factor
        if new_zoom < self.min_zoom:
            new_zoom = self.min_zoom
        if new_zoom > self.max_zoom:
            new_zoom = self.max_zoom

        if new_zoom == self.user_zoom:
            return "break"

        cursor_x = event.x
        cursor_y = event.y

        old_width = int(self.original_width * self.user_zoom)
        old_height = int(self.original_height * self.user_zoom)

        if old_width > 0 and old_height > 0:
            if (self.image_x <= cursor_x <= self.image_x + old_width and
                    self.image_y <= cursor_y <= self.image_y + old_height):
                rel_x = (cursor_x - self.image_x) / old_width
                rel_y = (cursor_y - self.image_y) / old_height
            else:
                rel_x = 0.5
                rel_y = 0.5
        else:
            rel_x = 0.5
            rel_y = 0.5

        self.user_zoom = new_zoom

        new_width = int(self.original_width * self.user_zoom)
        new_height = int(self.original_height * self.user_zoom)

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        new_x = cursor_x - (rel_x * new_width)
        new_y = cursor_y - (rel_y * new_height)

        if new_width >= canvas_width:
            new_x = max(min(new_x, 0), canvas_width - new_width)
        else:
            new_x = (canvas_width - new_width) // 2

        if new_height >= canvas_height:
            new_y = max(min(new_y, 0), canvas_height - new_height)
        else:
            new_y = (canvas_height - new_height) // 2

        self.image_x = new_x
        self.image_y = new_y

        self.update_zoomed_image(new_width, new_height)

        return "break"

    def update_zoomed_image(self, width, height):
        if width > 0 and height > 0:
            pil_image = self.get_scaled_image(width, height)
            if pil_image:
                self.photo_image = ImageTk.PhotoImage(pil_image)
                self.canvas.delete("all")
                self.current_image = self.canvas.create_image(self.image_x, self.image_y, anchor=tk.NW,
                                                              image=self.photo_image)

    def on_global_press(self, event):
        if event.widget == self.title_frame or event.widget in self.title_frame.winfo_children():
            return

        resize_frames = [self.top_frame, self.bottom_frame, self.left_frame, self.right_frame,
                         self.top_left, self.top_right, self.bottom_left, self.bottom_right]
        if event.widget in resize_frames:
            return

        if event.widget == self.master:
            canvas_x = self.canvas.winfo_x()
            canvas_y = self.canvas.winfo_y()
            if (canvas_x <= event.x <= canvas_x + self.canvas.winfo_width() and
                    canvas_y <= event.y <= canvas_y + self.canvas.winfo_height()):
                fake_event = type('obj', (object,), {
                    'x': event.x - canvas_x,
                    'y': event.y - canvas_y,
                    'widget': self.canvas
                })()
                self.start_pan(fake_event)

    def on_global_motion(self, event):
        if self.panning:
            canvas_x = self.canvas.winfo_x()
            canvas_y = self.canvas.winfo_y()
            fake_event = type('obj', (object,), {
                'x': event.x - canvas_x,
                'y': event.y - canvas_y,
                'widget': self.canvas
            })()
            self.on_pan(fake_event)

    def on_global_release(self, event):
        if self.panning:
            self.stop_pan(event)

    def on_middle_click_reset(self, event):
        if self.image_loaded:
            self.reset_zoom()
            return "break"

    def on_canvas_configure(self, event):
        if self.image_loaded:
            self.update_canvas_size()
            img_width = int(self.original_width * self.user_zoom)
            img_height = int(self.original_height * self.user_zoom)
            canvas_width = event.width
            canvas_height = event.height

            if img_width <= canvas_width:
                self.image_x = (canvas_width - img_width) // 2
            else:
                self.image_x = max(min(self.image_x, 0), canvas_width - img_width)

            if img_height <= canvas_height:
                self.image_y = (canvas_height - img_height) // 2
            else:
                self.image_y = max(min(self.image_y, 0), canvas_height - img_height)

            self.update_zoomed_image(img_width, img_height)

    @lru_cache(maxsize=32)
    def get_scaled_image(self, width, height):
        if width > 0 and height > 0:
            return self.original_image.resize((width, height), Image.Resampling.LANCZOS)
        return None

    def zoom_in(self):
        if self.image_loaded and self.user_zoom < self.max_zoom:
            class FakeEvent:
                def __init__(self):
                    self.delta = 120
                    self.state = 0
                    self.x = self.canvas.winfo_width() // 2
                    self.y = self.canvas.winfo_height() // 2

            fake_event = FakeEvent()
            self.on_mousewheel_zoom(fake_event)

    def zoom_out(self):
        if self.image_loaded and self.user_zoom > self.min_zoom:
            class FakeEvent:
                def __init__(self):
                    self.delta = -120
                    self.state = 0
                    self.x = self.canvas.winfo_width() // 2
                    self.y = self.canvas.winfo_height() // 2

            fake_event = FakeEvent()
            self.on_mousewheel_zoom(fake_event)

    def reset_zoom(self):
        if self.image_loaded:
            self.user_zoom = 1.0

            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            img_width = self.original_width
            img_height = self.original_height

            self.image_x = (canvas_width - img_width) // 2
            self.image_y = (canvas_height - img_height) // 2

            self.update_zoomed_image(img_width, img_height)
            self.show_tooltip("✅ Зум сброшен", 1000)

    def reset_size(self):
        if hasattr(self, 'optimal_width') and hasattr(self, 'optimal_height'):
            current_x = self.master.winfo_x()
            current_y = self.master.winfo_y()
            self.window_width = self.optimal_width
            self.window_height = self.optimal_height
            self.stretch_mode = False
            self.user_zoom = self.optimal_width / self.original_width
            self.master.geometry(f"{self.window_width}x{self.window_height}+{current_x}+{current_y}")
            self.update_borders_position()
            if self.image_loaded:
                self.update_image()

    def close(self):
        if hasattr(self, 'get_scaled_image'):
            self.get_scaled_image.cache_clear()

        if hasattr(self, 'parent_gallery') and self.parent_gallery:
            try:
                self.parent_gallery.on_floating_window_close(self)
            except:
                pass

        self.master.destroy()


# ============== ГЛАВНОЕ ОКНО ==============
class ImageGallery:
    def __init__(self):
        self.settings = Settings()
        self.windows = []
        self.window_counter = 1
        self.image_files = []
        self.stored_files = []

        # Флаг для отслеживания состояния скрытия окон
        self.all_windows_hidden = False

        self.root = tk.Tk()
        self.root.title("Менеджер плавающих картинок")
        self.root.configure(bg='#2b2b2b')

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        width = int(screen_width * 0.8)
        height = int(screen_height * 0.8)
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(800, 600)

        self.center_main_window()

        self.create_menu()
        self.create_widgets()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.setup_hotkeys()
        self.load_gallery()

        # Фокус на главное окно
        self.root.focus_force()

    def toggle_all_windows(self, event=None):
        """Скрыть или показать все окна с картинками"""
        # Очищаем список от закрытых окон
        self.cleanup_closed_windows()

        if not self.windows:
            self.info_label.config(text="⚠️ Нет открытых окон")
            return

        if self.all_windows_hidden:
            # Показываем все окна
            shown = 0
            for window in self.windows:
                try:
                    if hasattr(window, 'master') and window.master.winfo_exists():
                        window.master.deiconify()
                        window.master.lift()
                        # Обновляем содержимое
                        if hasattr(window, 'update_canvas_size'):
                            window.update_canvas_size()
                        if hasattr(window, 'update_image'):
                            window.update_image()
                        shown += 1
                except Exception as e:
                    print(f"Ошибка при показе окна: {e}")
            self.all_windows_hidden = False
            self.info_label.config(text=f"🪟 Показано {shown} окон")
        else:
            # Скрываем все окна
            hidden = 0
            for window in self.windows:
                try:
                    if hasattr(window, 'master') and window.master.winfo_exists():
                        window.master.withdraw()
                        hidden += 1
                except Exception as e:
                    print(f"Ошибка при скрытии окна: {e}")
            self.all_windows_hidden = True
            self.info_label.config(text=f"👁️ Скрыто {hidden} окон (нажмите H для показа)")

    def setup_hotkeys(self):
        def handle_hotkey(event):
            # Глобальная обработка H (без модификаторов)
            if event.keysym.lower() == 'h':
                # Проверяем, что не нажаты модификаторы (Ctrl, Alt, Shift)
                if not (event.state & 0x4 or event.state & 0x1 or event.state & 0x20000):
                    self.toggle_all_windows(event)
                    return "break"

            # Остальные горячие клавиши
            if event.state & 0x4 and event.keycode == 86:  # Ctrl+V
                self.paste_from_clipboard()
                return "break"
            elif event.state & 0x4 and event.keycode == 79:  # Ctrl+O
                self.open_images()
                return "break"
            elif event.state & 0x4 and event.keycode == 65:  # Ctrl+A
                self.show_all()
                return "break"
            elif event.state & 0x4 and event.keycode == 83:  # Ctrl+S
                self.open_settings()
                return "break"
            elif event.state & 0x4 and event.keycode == 87:  # Ctrl+W
                self.close_all()
                return "break"
            elif event.state & 0x4 and event.keycode == 81:  # Ctrl+Q
                self.on_close()
                return "break"
            elif event.keycode == 46:  # Delete
                self.remove_selected()
                return "break"
            elif event.keysym == 'F1':
                self.open_settings()
                return "break"
            elif event.keysym == 'Escape':
                if self.windows:
                    self.close_all()
                return "break"

        self.root.bind_all("<Key>", handle_hotkey)
        self.image_listbox.bind("<Key>", handle_hotkey)
        self.root.focus_force()

    def save_gallery(self):
        try:
            GALLERY_FILE.parent.mkdir(parents=True, exist_ok=True)

            existing_files = []
            for f in self.image_files:
                if os.path.exists(f):
                    existing_files.append(f)
                else:
                    print(f"Файл не существует, пропускаем: {f}")

            print(f"Сохранение {len(existing_files)} картинок в {GALLERY_FILE}")

            with open(GALLERY_FILE, 'w', encoding='utf-8') as f:
                json.dump(existing_files, f, indent=4, ensure_ascii=False)
            print(f"Список успешно сохранен")
            return True
        except Exception as e:
            print(f"Ошибка сохранения списка: {e}")
            return False

    def load_gallery(self):
        try:
            if GALLERY_FILE.exists():
                with open(GALLERY_FILE, 'r', encoding='utf-8') as f:
                    loaded_files = json.load(f)
                    print(f"Загружено {len(loaded_files)} картинок из файла {GALLERY_FILE}")

                    self.image_files.clear()
                    self.image_listbox.delete(0, tk.END)

                    added = 0
                    for file in loaded_files:
                        if os.path.exists(file):
                            self.image_files.append(file)
                            if str(STORAGE_DIR) in file:
                                filename = f"[Буфер] {Path(file).stem.replace('clipboard_', '')}"
                            else:
                                filename = os.path.basename(file)
                                if len(filename) > 60:
                                    filename = filename[:57] + "..."

                            self.image_listbox.insert(tk.END, filename)
                            added += 1
                            print(f"  Добавлена картинка: {filename} -> {file}")
                        else:
                            print(f"Файл не существует, пропускаем: {file}")

                    if added > 0:
                        self.info_label.config(text=f"📂 Загружено {added} картинок из прошлого сеанса")
                    else:
                        self.info_label.config(text="✅ Готов к работе! H - скрыть/показать окна")

                    self.image_listbox.update_idletasks()
            else:
                print(f"Файл списка не найден: {GALLERY_FILE}")
                self.info_label.config(text="✅ Готов к работе! H - скрыть/показать окна")
        except Exception as e:
            print(f"Ошибка загрузки списка: {e}")
            self.info_label.config(text="✅ Готов к работе! H - скрыть/показать окна")

    def center_main_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def open_settings(self):
        SettingsWindow(self.root, self.settings, self.on_settings_changed)

    def on_settings_changed(self):
        zoom_normal = self.settings.get("zoom_normal")
        self.info_label.config(text=f"✅ Настройки обновлены! Обычный зум: +{int((zoom_normal - 1) * 100)}%")
        self.root.after(3000, lambda: self.info_label.config(
            text="✅ Готов к работе! H - скрыть/показать окна"))

    def create_menu(self):
        menubar = tk.Menu(self.root, bg='#2b2b2b', fg='white')
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0, bg='#2b2b2b', fg='white')
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Открыть картинки (Ctrl+O)", command=self.open_images)
        file_menu.add_command(label="Вставить из буфера (Ctrl+V)", command=self.paste_from_clipboard)
        file_menu.add_separator()
        file_menu.add_command(label="Показать все (Ctrl+A)", command=self.show_all)
        file_menu.add_command(label="Закрыть все окна (Ctrl+W)", command=self.close_all)
        file_menu.add_separator()
        file_menu.add_command(label="Выход (Ctrl+Q)", command=self.on_close)

        edit_menu = tk.Menu(menubar, tearoff=0, bg='#2b2b2b', fg='white')
        menubar.add_cascade(label="Правка", menu=edit_menu)
        edit_menu.add_command(label="Удалить выбранные (Del)", command=self.remove_selected)
        edit_menu.add_command(label="Очистить список", command=self.clear_list)

        view_menu = tk.Menu(menubar, tearoff=0, bg='#2b2b2b', fg='white')
        menubar.add_cascade(label="Вид", menu=view_menu)
        view_menu.add_command(label="Скрыть/Показать все окна (H)", command=self.toggle_all_windows)
        view_menu.add_separator()
        view_menu.add_command(label="Каскадом", command=self.arrange_cascade)
        view_menu.add_command(label="Сеткой", command=self.arrange_grid)

        settings_menu = tk.Menu(menubar, tearoff=0, bg='#2b2b2b', fg='white')
        menubar.add_cascade(label="Настройки", menu=settings_menu)
        settings_menu.add_command(label="Настройки (Ctrl+S / F1)", command=self.open_settings)
        settings_menu.add_separator()
        settings_menu.add_command(label="Сбросить настройки", command=self.reset_settings)

        help_menu = tk.Menu(menubar, tearoff=0, bg='#2b2b2b', fg='white')
        menubar.add_cascade(label="Помощь", menu=help_menu)
        help_menu.add_command(label="Горячие клавиши", command=self.show_shortcuts)
        help_menu.add_command(label="О программе", command=self.show_about)

    def show_shortcuts(self):
        shortcuts_text = """ГОРЯЧИЕ КЛАВИШИ:

Главное окно:
• H - скрыть/показать все окна с картинками
• Ctrl+O - открыть картинки
• Ctrl+V - вставить из буфера
• Ctrl+A - показать все картинки
• Ctrl+W - закрыть все окна с картинками
• Ctrl+Q - выход из программы
• Ctrl+S или F1 - настройки
• Del - удалить выбранные из списка
• Esc - закрыть все окна с картинками

Окно с картинкой:
• Колесо мыши - обычный зум
• Ctrl + Колесо - медленный зум
• Shift + Колесо - быстрый зум
• Ctrl + ЛКМ - панорамирование
• Средняя кнопка мыши - сброс зума
• ПКМ - контекстное меню
• Перетаскивание за заголовок - перемещение окна
• Тянуть за границы:
  - Обычное растягивание - масштабирование картинки
  - Shift + растягивание - масштабирование с сохранением пропорций
  - Ctrl + растягивание - изменение только размера окна

Управление списком:
• Двойной клик - открыть картинку
• Shift/Ctrl + клик - выделить несколько"""

        messagebox.showinfo("Горячие клавиши", shortcuts_text)

    def show_about(self):
        about_text = """Менеджер плавающих картинок
Версия 2.7

Программа для просмотра изображений в плавающих окнах.

Особенности:
• Плавающие окна поверх всех программ
• Плавный зум с анимацией (60 fps)
• Масштабирование с привязкой к курсору
• Панорамирование при увеличении
• Вставка из буфера обмена
• Сохранение настроек
• Интеллектуальное изменение размера окон
• Сохранение списка картинок между сеансами
• Все файлы хранятся в папке с программой
• Картинки из буфера сохраняются в папку storage/
• Настраиваемая скорость и плавность зума
• Скрытие/показ всех окон по клавише H

Управление изменением размера:
• Обычное растягивание - масштабирует картинку
• Shift + растягивание - масштабирует с сохранением пропорций
• Ctrl + растягивание - изменяет размер окна

© 2024"""

        messagebox.showinfo("О программе", about_text)

    def reset_settings(self):
        if messagebox.askyesno("Сброс настроек", "Вы уверены, что хотите сбросить все настройки к стандартным?"):
            for key, value in Settings.DEFAULT_SETTINGS.items():
                self.settings.set(key, value)
            self.on_settings_changed()
            messagebox.showinfo("Настройки", "Настройки сброшены к стандартным")

    def create_widgets(self):
        main_container = tk.Frame(self.root, bg='#2b2b2b')
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        title = tk.Label(main_container, text="🖼️ МЕНЕДЖЕР ПЛАВАЮЩИХ КАРТИНОК",
                         font=('Segoe UI', 20, 'bold'), bg='#2b2b2b', fg='white')
        title.pack(pady=(0, 20))

        list_frame = tk.Frame(main_container, bg='#2b2b2b')
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        scrollbar = tk.Scrollbar(list_frame, bg='#2b2b2b')
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.image_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                        selectmode=tk.EXTENDED,
                                        bg='#3c3c3c', fg='white',
                                        selectbackground='#0078d4',
                                        font=('Consolas', 11))
        self.image_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.image_listbox.yview)
        self.image_listbox.bind("<Double-Button-1>", self.on_double_click)

        button_frame = tk.Frame(main_container, bg='#2b2b2b')
        button_frame.pack(pady=15, fill=tk.X)

        btn_open = tk.Button(button_frame, text="📁 ОТКРЫТЬ (Ctrl+O)",
                             command=self.open_images, bg='#3c3c3c', fg='white',
                             padx=15, pady=10, font=('Segoe UI', 11, 'bold'), cursor='hand2')
        btn_open.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        btn_paste = tk.Button(button_frame, text="📋 ВСТАВИТЬ (Ctrl+V)",
                              command=self.paste_from_clipboard, bg='#0078d4', fg='white',
                              padx=15, pady=10, font=('Segoe UI', 11, 'bold'), cursor='hand2')
        btn_paste.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        btn_show = tk.Button(button_frame, text="🖼️ ПОКАЗАТЬ ВЫБР.",
                             command=self.show_selected, bg='#3c3c3c', fg='white',
                             padx=15, pady=10, font=('Segoe UI', 11, 'bold'), cursor='hand2')
        btn_show.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        btn_show_all = tk.Button(button_frame, text="✨ ПОКАЗАТЬ ВСЕ (Ctrl+A)",
                                 command=self.show_all, bg='#107c10', fg='white',
                                 padx=15, pady=10, font=('Segoe UI', 11, 'bold'), cursor='hand2')
        btn_show_all.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        btn_hide = tk.Button(button_frame, text="👁️ СКРЫТЬ/ПОКАЗАТЬ (H)",
                             command=self.toggle_all_windows, bg='#ff8c00', fg='white',
                             padx=15, pady=10, font=('Segoe UI', 11, 'bold'), cursor='hand2')
        btn_hide.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        btn_close = tk.Button(button_frame, text="✖ ЗАКРЫТЬ ВСЕ (Ctrl+W)",
                              command=self.close_all, bg='#8b0000', fg='white',
                              padx=15, pady=10, font=('Segoe UI', 11, 'bold'), cursor='hand2')
        btn_close.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        btn_settings = tk.Button(button_frame, text="⚙️ НАСТРОЙКИ (F1)",
                                 command=self.open_settings, bg='#5a5a5a', fg='white',
                                 padx=15, pady=10, font=('Segoe UI', 11, 'bold'), cursor='hand2')
        btn_settings.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        self.info_label = tk.Label(main_container,
                                   text=f"✅ Готов к работе! H - скрыть/показать окна",
                                   font=('Segoe UI', 11), bg='#2b2b2b', fg='#888888')
        self.info_label.pack(pady=(0, 10))

        self.root.bind("<F1>", lambda e: self.open_settings())

    def on_double_click(self, event):
        selection = self.image_listbox.curselection()
        if not selection:
            return
        opened = 0
        for idx in selection:
            if idx < len(self.image_files):
                image_path = self.image_files[idx]
                self.create_floating_window(image_path)
                opened += 1
        if opened > 0:
            self.info_label.config(text=f"🪟 Открыто {opened} картинок")
            # Сбрасываем флаг скрытия, так как появились новые окна
            self.all_windows_hidden = False

    def open_images(self):
        files = filedialog.askopenfilenames(
            title="Выберите картинки",
            filetypes=[("Изображения", "*.jpg *.jpeg *.png *.gif *.bmp *.webp"), ("Все файлы", "*.*")]
        )
        if files:
            added = 0
            for file in files:
                if file not in self.image_files:
                    self.image_files.append(file)
                    filename = os.path.basename(file)
                    if len(filename) > 60:
                        filename = filename[:57] + "..."
                    self.image_listbox.insert(tk.END, filename)
                    added += 1
            self.info_label.config(text=f"✅ Добавлено {added} картинок (всего: {len(self.image_files)})")
            self.save_gallery()

    def paste_from_clipboard(self):
        try:
            self.root.lift()
            self.root.focus_force()
            img = ImageGrab.grabclipboard()
            if img is None:
                messagebox.showinfo("Информация", "В буфере обмена нет изображения")
                return
            if isinstance(img, Image.Image):
                if img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                STORAGE_DIR.mkdir(parents=True, exist_ok=True)
                timestamp = int(time.time() * 1000)
                storage_file = STORAGE_DIR / f"clipboard_{timestamp}.png"
                img.save(storage_file)

                self.image_files.append(str(storage_file))
                self.stored_files.append(str(storage_file))

                display_name = f"[Буфер] {time.strftime('%Y-%m-%d %H:%M:%S')}"
                self.image_listbox.insert(tk.END, display_name)
                self.image_listbox.see(tk.END)
                self.info_label.config(
                    text=f"✅ Картинка из буфера добавлена и сохранена (всего: {len(self.image_files)})")
                self.save_gallery()
            else:
                messagebox.showinfo("Информация", "В буфере не изображение")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось вставить из буфера\n\n{str(e)}")

    def remove_selected(self):
        selected = self.image_listbox.curselection()
        if not selected:
            messagebox.showinfo("Информация", "Выберите картинки для удаления")
            return

        deleted_count = 0
        for idx in reversed(selected):
            if idx < len(self.image_files):
                file_path = self.image_files[idx]
                if file_path in self.stored_files:
                    try:
                        os.remove(file_path)
                        self.stored_files.remove(file_path)
                        print(f"Удален сохраненный файл: {file_path}")
                    except Exception as e:
                        print(f"Ошибка удаления {file_path}: {e}")

                del self.image_files[idx]
                self.image_listbox.delete(idx)
                deleted_count += 1

        self.info_label.config(text=f"🗑️ Удалено {deleted_count} картинок (осталось: {len(self.image_files)})")
        self.save_gallery()

    def clear_list(self):
        if self.image_files:
            for stored_file in self.stored_files:
                try:
                    if os.path.exists(stored_file):
                        os.remove(stored_file)
                        print(f"Удален сохраненный файл: {stored_file}")
                except Exception as e:
                    print(f"Ошибка удаления {stored_file}: {e}")

            self.stored_files.clear()
            self.image_files.clear()
            self.image_listbox.delete(0, tk.END)
            self.info_label.config(text="📭 Список очищен")
            self.save_gallery()

    def show_selected(self):
        selected_indices = self.image_listbox.curselection()
        if not selected_indices:
            messagebox.showinfo("Информация", "Выберите картинки из списка")
            return
        if not self.image_files:
            messagebox.showinfo("Информация", "Сначала добавьте картинки")
            return
        for idx in selected_indices:
            if idx < len(self.image_files):
                self.create_floating_window(self.image_files[idx])
        # Сбрасываем флаг скрытия
        self.all_windows_hidden = False

    def show_all(self):
        if not self.image_files:
            messagebox.showinfo("Информация", "Сначала добавьте картинки")
            return
        for image_path in self.image_files:
            self.create_floating_window(image_path)
        # Сбрасываем флаг скрытия
        self.all_windows_hidden = False

    def cleanup_closed_windows(self):
        still_alive = []
        for window in self.windows:
            try:
                if window.master.winfo_exists():
                    still_alive.append(window)
            except:
                pass
        self.windows = still_alive
        return len(self.windows)

    def arrange_cascade(self):
        self.cleanup_closed_windows()

        if not self.windows:
            self.info_label.config(text="⚠️ Нет открытых окон для расположения")
            return

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        start_x = 50
        start_y = 50
        offset_x = 30
        offset_y = 30

        windows_info = []
        for window in self.windows:
            try:
                if window.master.winfo_exists():
                    windows_info.append(window)
            except:
                continue

        if not windows_info:
            self.info_label.config(text="⚠️ Нет открытых окон для расположения")
            return

        for i, window in enumerate(windows_info):
            try:
                x = start_x + (i % 10) * offset_x
                y = start_y + (i // 10) * offset_y

                width = window.window_width if hasattr(window, 'window_width') else 400
                height = window.window_height if hasattr(window, 'window_height') else 300

                if x + width > screen_width - 50:
                    x = max(50, screen_width - width - 50)
                if y + height > screen_height - 50:
                    y = max(50, screen_height - height - 50)

                x = max(50, x)
                y = max(50, y)

                window.master.geometry(f"+{int(x)}+{int(y)}")
            except Exception as e:
                print(f"Ошибка при расположении окна: {e}")
                continue

        self.info_label.config(text=f"✅ {len(windows_info)} окон расположены каскадом")

    def arrange_grid(self):
        self.cleanup_closed_windows()

        if not self.windows:
            self.info_label.config(text="⚠️ Нет открытых окон для расположения")
            return

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        windows_info = []
        for window in self.windows:
            try:
                if window.master.winfo_exists():
                    width = window.window_width if hasattr(window, 'window_width') else 400
                    height = window.window_height if hasattr(window, 'window_height') else 300
                    windows_info.append({
                        'window': window,
                        'width': width,
                        'height': height
                    })
            except:
                continue

        if not windows_info:
            self.info_label.config(text="⚠️ Нет открытых окон для расположения")
            return

        window_count = len(windows_info)

        if window_count <= 3:
            cols = window_count
        elif window_count <= 6:
            cols = 3
        elif window_count <= 9:
            cols = 3
        else:
            cols = 4

        max_width = max(info['width'] for info in windows_info)
        max_height = max(info['height'] for info in windows_info)

        min_spacing_x = 20
        min_spacing_y = 20

        available_width = screen_width - 100
        available_height = screen_height - 100

        if cols > 0:
            max_cell_width = available_width / cols
            if max_width > max_cell_width - min_spacing_x:
                spacing_x = min_spacing_x
                cell_width = (available_width - (cols - 1) * spacing_x) / cols
                if max_width > cell_width:
                    use_overlap = True
                else:
                    use_overlap = False
            else:
                spacing_x = min_spacing_x + (available_width - (max_width * cols + (cols - 1) * min_spacing_x)) / (
                        cols - 1) if cols > 1 else min_spacing_x
                cell_width = max_width
                use_overlap = False
        else:
            spacing_x = min_spacing_x
            cell_width = max_width
            use_overlap = False

        rows = (window_count + cols - 1) // cols

        total_height = rows * max_height + (rows - 1) * min_spacing_y
        if total_height > available_height:
            spacing_y = min_spacing_y
            use_overlap_vertical = True
        else:
            spacing_y = min_spacing_y + (available_height - total_height) / (rows - 1) if rows > 1 else min_spacing_y
            use_overlap_vertical = False

        total_width = cols * max_width + (cols - 1) * spacing_x
        total_height_calc = rows * max_height + (rows - 1) * spacing_y

        start_x = max(50, (screen_width - total_width) // 2)
        start_y = max(50, (screen_height - total_height_calc) // 2)

        positioned = 0
        for i, info in enumerate(windows_info):
            try:
                row = i // cols
                col = i % cols

                if use_overlap:
                    x = start_x + col * (max_width // 2)
                    y = start_y + row * (max_height // 2)
                else:
                    x = start_x + col * (max_width + spacing_x)
                    y = start_y + row * (max_height + spacing_y)

                x = max(20, min(x, screen_width - info['width'] - 20))
                y = max(20, min(y, screen_height - info['height'] - 20))

                info['window'].master.geometry(f"+{int(x)}+{int(y)}")
                positioned += 1

            except Exception as e:
                print(f"Ошибка при расположении окна: {e}")
                continue

        self.info_label.config(text=f"✅ {positioned} окон расположены сеткой ({cols}x{rows})")

    def create_floating_window(self, image_path):
        try:
            self.cleanup_closed_windows()

            win = tk.Toplevel()
            window_id = self.window_counter
            self.window_counter += 1
            floating = FloatingImage(win, image_path, window_id, self.settings)
            floating.parent_gallery = self
            self.windows.append(floating)

            self.info_label.config(text=f"🪟 Открыто окон: {len(self.windows)}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть изображение\n{str(e)}")

    def on_floating_window_close(self, floating_window):
        try:
            if floating_window in self.windows:
                self.windows.remove(floating_window)
            self.info_label.config(text=f"🪟 Открыто окон: {len(self.windows)}")
        except:
            pass

    def close_all(self):
        windows_copy = self.windows[:]
        for window in windows_copy:
            try:
                window.close()
            except:
                pass
        self.windows.clear()
        self.all_windows_hidden = False
        self.info_label.config(text="✅ Все окна закрыты")

    def on_close(self):
        print("Закрытие программы, сохраняем список...")
        self.save_gallery()
        self.close_all()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = ImageGallery()
    app.run()
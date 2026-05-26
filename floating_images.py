import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageGrab
import os
from pathlib import Path
import time
import threading
import json
from functools import lru_cache

# ============== НАСТРОЙКИ ==============
CONFIG_FILE = Path.home() / "AppData" / "Local" / "floating_images" / "settings.json"


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
        "always_on_top": True
    }

    def __init__(self):
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.load()

    def ensure_config_dir(self):
        config_dir = CONFIG_FILE.parent
        if not config_dir.exists():
            config_dir.mkdir(parents=True, exist_ok=True)

    def load(self):
        try:
            self.ensure_config_dir()
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    for key in self.settings:
                        if key in loaded:
                            self.settings[key] = loaded[key]
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")

    def save(self):
        try:
            self.ensure_config_dir()
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
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

        self.window.geometry("650x600")
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
        self.slow_zoom_scale = tk.Scale(frame1, from_=1.01, to=1.1, resolution=0.01,
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
        self.normal_zoom_scale = tk.Scale(frame2, from_=1.01, to=1.2, resolution=0.01,
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

    def load_values(self):
        self.slow_zoom_var.set(self.settings.get("zoom_slow"))
        self.normal_zoom_var.set(self.settings.get("zoom_normal"))
        self.fast_zoom_var.set(self.settings.get("zoom_fast"))
        self.min_zoom_var.set(self.settings.get("min_zoom"))
        self.max_zoom_var.set(self.settings.get("max_zoom"))
        self.hide_delay_var.set(self.settings.get("hide_delay"))
        self.border_size_var.set(self.settings.get("border_size"))

    def save_settings(self):
        self.settings.set("zoom_slow", self.slow_zoom_var.get())
        self.settings.set("zoom_normal", self.normal_zoom_var.get())
        self.settings.set("zoom_fast", self.fast_zoom_var.get())
        self.settings.set("min_zoom", self.min_zoom_var.get())
        self.settings.set("max_zoom", self.max_zoom_var.get())
        self.settings.set("hide_delay", self.hide_delay_var.get())
        self.settings.set("border_size", self.border_size_var.get())

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
        self.panning = False
        self.image_loaded = False
        self.loading_thread = None
        self.mouse_over = False

        # Для отслеживания модификаторов при ресайзе
        self.resize_with_shift = False
        self.resize_with_ctrl = False

        self.user_zoom = 1.0
        self.target_zoom = 1.0
        self.zoom_animation_id = None

        # Для искаженного отображения
        self.stretch_mode = False  # Режим растягивания (без сохранения пропорций)
        self.stretch_width = 0
        self.stretch_height = 0

        self.zoom_step_slow = self.settings.get("zoom_slow")
        self.zoom_step_normal = self.settings.get("zoom_normal")
        self.zoom_step_fast = self.settings.get("zoom_fast")
        self.min_zoom = self.settings.get("min_zoom")
        self.max_zoom = self.settings.get("max_zoom")
        self.animation_speed = self.settings.get("animation_speed")
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

        self.resize_after_id = None
        self.last_cursor_x = 0
        self.last_cursor_y = 0

        self.hide_timer = None

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
                                      font=('Segoe UI', 12), bg='#f0f0f0')
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
            self.target_zoom = ratio
        else:
            self.display_width = self.original_width
            self.display_height = self.original_height
            self.user_zoom = 1.0
            self.target_zoom = 1.0

        self.optimal_width = self.display_width
        self.optimal_height = self.display_height

        self.window_width = self.display_width
        self.window_height = self.display_height
        self.master.geometry(f"{self.window_width}x{self.window_height}")

        # Синхронизируем canvas
        self.update_canvas_size()

        self.hide_loading_indicator()
        self.master.after(50, self.update_image)
        self.image_loaded = True

        # Обновляем позиции границ
        self.update_borders_position()

    def on_image_load_error(self, error_msg):
        self.hide_loading_indicator()
        messagebox.showerror("Ошибка", f"Не удалось загрузить {self.image_path}\n{error_msg}")
        self.master.destroy()

    def create_window_frame(self):
        # Canvas для изображения (занимает всё окно)
        self.canvas = tk.Canvas(self.master, bg='#2b2b2b', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Сразу синхронизируем размер canvas
        self.master.update_idletasks()
        self.update_canvas_size()

        # Верхняя панель (плавающая поверх canvas)
        self.title_frame = tk.Frame(self.master, bg='#333333', height=35)
        self.title_frame.place(x=0, y=0, relwidth=1)

        # Название файла
        filename = os.path.basename(self.image_path)
        if len(filename) > 40:
            filename = filename[:37] + "..."
        self.title_label = tk.Label(self.title_frame, text=filename, bg='#333333', fg='white',
                                    font=('Segoe UI', 10))
        self.title_label.pack(side=tk.LEFT, padx=10, expand=True, fill=tk.X)

        # Кнопка закрытия
        self.close_btn = tk.Button(self.title_frame, text="✖", font=('Segoe UI', 12, 'bold'),
                                   command=self.close, bg='#333333', fg='white',
                                   bd=0, activebackground='#e81123', activeforeground='white',
                                   width=4, cursor='hand2')
        self.close_btn.pack(side=tk.RIGHT, padx=5)

        # Привязываем перемещение
        self.title_label.bind("<Button-1>", self.start_move)
        self.title_label.bind("<B1-Motion>", self.on_move)
        self.title_label.bind("<ButtonRelease-1>", self.stop_move)
        self.title_frame.bind("<Button-1>", self.start_move)
        self.title_frame.bind("<B1-Motion>", self.on_move)
        self.title_frame.bind("<ButtonRelease-1>", self.stop_move)

        # Привязываем события мыши
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        self.canvas.bind("<Motion>", self.on_mouse_move)

        # Отслеживаем наведение на всё окно
        self.master.bind("<Enter>", self.on_mouse_enter)
        self.master.bind("<Leave>", self.on_mouse_leave)
        self.canvas.bind("<Enter>", self.on_mouse_enter)
        self.canvas.bind("<Leave>", self.on_mouse_leave)

        # Создаем границы для ресайза
        self.create_resize_borders()

        # Изначально скрываем верхнюю панель
        self.title_frame.place_forget()

    def on_mouse_enter(self, event):
        """Мышь вошла в окно"""
        self.mouse_over = True
        if self.hide_timer:
            self.master.after_cancel(self.hide_timer)
            self.hide_timer = None
        self.show_all_ui()

    def on_mouse_leave(self, event):
        """Мышь вышла из окна"""
        # Проверяем, не наведена ли мышь на панель
        x = self.master.winfo_pointerx()
        y = self.master.winfo_pointery()
        widget = self.master.winfo_containing(x, y)

        if widget == self.title_frame or widget in self.title_frame.winfo_children():
            return

        self.mouse_over = False
        self.start_hide_timer()

    def start_hide_timer(self):
        """Запускает таймер скрытия UI"""
        if self.hide_timer:
            self.master.after_cancel(self.hide_timer)
        self.hide_timer = self.master.after(800, self.hide_all_ui)

    def show_all_ui(self):
        """Показывает все UI элементы"""
        if self.image_loaded:
            # Показываем верхнюю панель
            self.title_frame.place(x=0, y=0, relwidth=1)
            # Показываем границы (делаем их видимыми)
            self.show_resize_borders()

    def hide_all_ui(self):
        """Скрывает все UI элементы"""
        if not self.mouse_over:
            # Скрываем верхнюю панель
            self.title_frame.place_forget()
            # Скрываем границы
            self.hide_resize_borders()

    def on_mouse_move(self, event):
        self.last_cursor_x = event.x
        self.last_cursor_y = event.y

    def create_resize_borders(self):
        """Создает зоны для изменения размера"""
        border_size = 8

        # Верхняя граница
        self.top_frame = tk.Frame(self.master, bg='#2b2b2b', height=border_size, cursor='size_ns')
        self.top_frame.place(x=0, y=0, width=self.master.winfo_width(), height=border_size)

        # Нижняя граница
        self.bottom_frame = tk.Frame(self.master, bg='#2b2b2b', height=border_size, cursor='size_ns')
        self.bottom_frame.place(x=0, y=self.master.winfo_height() - border_size,
                                width=self.master.winfo_width(), height=border_size)

        # Левая граница
        self.left_frame = tk.Frame(self.master, bg='#2b2b2b', width=border_size, cursor='size_we')
        self.left_frame.place(x=0, y=0, width=border_size, height=self.master.winfo_height())

        # Правая граница
        self.right_frame = tk.Frame(self.master, bg='#2b2b2b', width=border_size, cursor='size_we')
        self.right_frame.place(x=self.master.winfo_width() - border_size, y=0,
                               width=border_size, height=self.master.winfo_height())

        # Уголки для диагонального ресайза
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

        # Привязываем события для всех границ
        for frame in [self.bottom_frame, self.top_frame, self.left_frame, self.right_frame,
                      self.top_left, self.top_right, self.bottom_left, self.bottom_right]:
            frame.bind("<Button-1>", self.start_resize)
            frame.bind("<B1-Motion>", self.on_resize)
            frame.bind("<ButtonRelease-1>", self.stop_resize)
            # Привязываем события для отслеживания модификаторов
            frame.bind("<Shift-Button-1>", self.start_resize_with_shift)
            frame.bind("<Control-Button-1>", self.start_resize_with_ctrl)

        # Изначально скрываем границы
        self.hide_resize_borders()

    def start_resize_with_shift(self, event):
        """Начало ресайза с зажатым Shift (масштабирование с сохранением пропорций)"""
        self.resize_with_shift = True
        self.resize_with_ctrl = False
        self.start_resize(event)

    def start_resize_with_ctrl(self, event):
        """Начало ресайза с зажатым Ctrl (простое изменение окна)"""
        self.resize_with_shift = False
        self.resize_with_ctrl = True
        self.start_resize(event)

    def show_resize_borders(self):
        """Показывает границы для изменения размера (белые)"""
        if not hasattr(self, 'top_frame'):
            return

        current_width = self.master.winfo_width()
        current_height = self.master.winfo_height()
        border_size = 8
        corner_size = 12

        # Показываем и делаем белыми
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
        """Полностью скрывает границы для изменения размера"""
        if not hasattr(self, 'top_frame'):
            return

        # Полностью убираем границы
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

        # Сохраняем начальное соотношение сторон изображения
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

        # Рассчитываем новые размеры окна
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

        # Обработка Shift
        if self.resize_with_shift:
            aspect_ratio = self.original_width / self.original_height

            # Рассчитываем правильные размеры сохраняя пропорции
            if self.resize_edge in ['left', 'right']:
                target_width = new_width
                target_height = int(target_width / aspect_ratio)
            elif self.resize_edge in ['top', 'bottom']:
                target_height = new_height
                target_width = int(target_height * aspect_ratio)
            else:  # углы
                width_change = abs(new_width - self.resize_start_width)
                height_change = abs(new_height - self.resize_start_height)
                if width_change >= height_change:
                    target_width = new_width
                    target_height = int(target_width / aspect_ratio)
                else:
                    target_height = new_height
                    target_width = int(target_height * aspect_ratio)

            # Проверяем минимальные размеры
            if target_width < min_width:
                target_width = min_width
                target_height = int(target_width / aspect_ratio)
            if target_height < min_height:
                target_height = min_height
                target_width = int(target_height * aspect_ratio)

            # Корректируем позицию
            if self.resize_edge in ['top', 'top_left', 'top_right']:
                new_y = self.resize_start_top + (self.resize_start_height - target_height)
            if self.resize_edge in ['left', 'top_left', 'bottom_left']:
                new_x = self.resize_start_left + (self.resize_start_width - target_width)

            # Применяем размер окна
            self.master.geometry(f"{target_width}x{target_height}+{new_x}+{new_y}")

            # Обновляем внутренние переменные
            self.window_width = target_width
            self.window_height = target_height
            self.user_zoom = target_width / self.original_width
            self.target_zoom = self.user_zoom
            self.stretch_mode = False

            # ✅ ОПТИМИЗАЦИЯ: обновляем изображение без полной перерисовки
            # Просто меняем размер существующего изображения
            img_width = int(self.original_width * self.user_zoom)
            img_height = int(self.original_height * self.user_zoom)

            if img_width > 0 and img_height > 0:
                # Используем метод scale для canvas вместо полной перерисовки
                # Это значительно снижает дерганье
                current_image = self.canvas.find_withtag("image")
                if current_image:
                    # Меняем размер canvas
                    self.canvas.config(width=target_width, height=target_height)

                    # Обновляем изображение
                    pil_image = self.get_scaled_image(img_width, img_height)
                    if pil_image:
                        self.photo_image = ImageTk.PhotoImage(pil_image)
                        self.canvas.itemconfig(current_image[0], image=self.photo_image)

                        # Центрируем
                        x = (target_width - img_width) // 2
                        y = (target_height - img_height) // 2
                        self.canvas.coords(current_image[0], max(0, x), max(0, y))
                else:
                    # Если изображения нет, создаем заново
                    pil_image = self.get_scaled_image(img_width, img_height)
                    if pil_image:
                        self.photo_image = ImageTk.PhotoImage(pil_image)
                        self.canvas.delete("all")
                        x = (target_width - img_width) // 2
                        y = (target_height - img_height) // 2
                        self.canvas.create_image(max(0, x), max(0, y), anchor=tk.NW, image=self.photo_image,
                                                 tags="image")

                self.canvas.config(scrollregion="")

            self.update_borders_position()
            return

        elif self.resize_with_ctrl:
            # Ctrl: только размер окна
            self.master.geometry(f"{new_width}x{new_height}+{new_x}+{new_y}")
            self.window_width = new_width
            self.window_height = new_height
            self.stretch_mode = False
            self.update_borders_position()
            self.update_image()
        else:
            # Обычное растягивание
            self.master.geometry(f"{new_width}x{new_height}+{new_x}+{new_y}")
            self.window_width = new_width
            self.window_height = new_height
            self.stretch_mode = True
            self.stretch_width = new_width
            self.stretch_height = new_height
            self.user_zoom = 1.0
            self.target_zoom = 1.0

            if self.zoom_animation_id:
                self.master.after_cancel(self.zoom_animation_id)
                self.zoom_animation_id = None

            self.update_borders_position()

            # Оптимизированное обновление для обычного режима
            current_image = self.canvas.find_withtag("image")
            if current_image and new_width > 0 and new_height > 0:
                pil_image = self.get_scaled_image(new_width, new_height)
                if pil_image:
                    self.photo_image = ImageTk.PhotoImage(pil_image)
                    self.canvas.itemconfig(current_image[0], image=self.photo_image)
                    self.canvas.coords(current_image[0], 0, 0)
                    self.canvas.config(width=new_width, height=new_height)
                    self.canvas.config(scrollregion=(0, 0, new_width, new_height))
            else:
                self.canvas.delete("all")
                if new_width > 0 and new_height > 0:
                    pil_image = self.get_scaled_image(new_width, new_height)
                    if pil_image:
                        self.photo_image = ImageTk.PhotoImage(pil_image)
                        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_image, tags="image")
                        self.canvas.config(scrollregion=(0, 0, new_width, new_height))

    def update_image(self):
        if not self.image_loaded:
            return

        try:
            # Получаем актуальные размеры canvas
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            if canvas_width <= 0 or canvas_height <= 0:
                canvas_width = self.window_width
                canvas_height = self.window_height

            # Определяем размеры для отображения
            if self.stretch_mode and self.stretch_width > 0 and self.stretch_height > 0:
                # Режим растягивания: картинка под размер окна
                img_width = self.stretch_width
                img_height = self.stretch_height

                if img_width > 0 and img_height > 0:
                    pil_image = self.get_scaled_image(img_width, img_height)
                    if pil_image:
                        self.photo_image = ImageTk.PhotoImage(pil_image)
                        self.canvas.delete("all")
                        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_image, tags="image")
                        self.canvas.config(scrollregion=(0, 0, img_width, img_height))
            else:
                # Нормальный режим: картинка с сохранением пропорций
                img_width = int(self.original_width * self.user_zoom)
                img_height = int(self.original_height * self.user_zoom)

                if img_width > 0 and img_height > 0:
                    pil_image = self.get_scaled_image(img_width, img_height)
                    if pil_image:
                        self.photo_image = ImageTk.PhotoImage(pil_image)
                        self.canvas.delete("all")

                        # Центрируем изображение в canvas
                        x = max(0, (canvas_width - img_width) // 2)
                        y = max(0, (canvas_height - img_height) // 2)

                        self.canvas.create_image(x, y, anchor=tk.NW, image=self.photo_image, tags="image")

                        # Настраиваем прокрутку только если изображение больше canvas
                        if img_width > canvas_width or img_height > canvas_height:
                            self.canvas.config(scrollregion=(0, 0, img_width, img_height))
                        else:
                            self.canvas.config(scrollregion="")

        except Exception as e:
            print(f"Ошибка обновления: {e}")

    def update_canvas_size(self):
        """Синхронизирует размер canvas с окном"""
        width = self.master.winfo_width()
        height = self.master.winfo_height()
        if width > 0 and height > 0:
            self.canvas.config(width=width, height=height)
            # ✅ НЕ устанавливаем scrollregion здесь! Пусть update_image это делает

    def force_update_canvas(self):
        """Принудительно обновляет Canvas и его размеры"""
        if not self.image_loaded:
            return

        width = self.master.winfo_width()
        height = self.master.winfo_height()

        if width > 0 and height > 0:
            self.canvas.config(width=width, height=height)
            self.canvas.update_idletasks()

            # Обновляем изображение
            self.update_image()

    def stop_resize(self, event):
        self.resizing = False
        self.resize_edge = None
        self.resize_with_shift = False
        self.resize_with_ctrl = False

        # Если были в режиме растягивания, сохраняем текущий размер как оптимальный
        if self.stretch_mode:
            self.optimal_width = self.window_width
            self.optimal_height = self.window_height
            # НЕ сбрасываем stretch_mode здесь, пусть остается до следующего зума или ресайза

    def exit_stretch_mode(self):
        """Выход из режима растягивания при начале зума"""
        if self.stretch_mode:
            self.stretch_mode = False
            self.stretch_width = 0
            self.stretch_height = 0
            # Восстанавливаем нормальные пропорции на основе текущего размера окна
            if self.window_width > 0 and self.original_width > 0:
                self.user_zoom = self.window_width / self.original_width
                self.target_zoom = self.user_zoom
            self.update_image()

    def update_borders_position(self):
        """Обновляет позиции границ при изменении размера окна"""
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

    def get_zoom_step(self, event):
        if event.state & 0x1:
            return self.zoom_step_fast
        elif event.state & 0x4:
            return self.zoom_step_slow
        else:
            return self.zoom_step_normal

    def animate_zoom_to_cursor(self, zoom_factor):
        if not self.image_loaded:
            return

        # Выходим из режима растягивания при зуме
        self.exit_stretch_mode()

        if self.zoom_animation_id:
            self.master.after_cancel(self.zoom_animation_id)

        cursor_x = self.last_cursor_x
        cursor_y = self.last_cursor_y
        coords = self.canvas.coords("image")
        if not coords:
            return

        img_x, img_y = coords
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width <= 0 or canvas_height <= 0:
            canvas_width = self.window_width
            canvas_height = self.window_height

        if cursor_x < 0 or cursor_x > canvas_width or cursor_y < 0 or cursor_y > canvas_height:
            cursor_x = canvas_width // 2
            cursor_y = canvas_height // 2

        if self.user_zoom > 0:
            self.zoom_rel_x = (cursor_x - img_x) / (self.original_width * self.user_zoom)
            self.zoom_rel_y = (cursor_y - img_y) / (self.original_height * self.user_zoom)
        else:
            self.zoom_rel_x = 0.5
            self.zoom_rel_y = 0.5

        self.target_zoom = self.user_zoom * zoom_factor
        self.target_zoom = max(self.min_zoom, min(self.max_zoom, self.target_zoom))
        self.zoom_rel_x = max(0.0, min(1.0, self.zoom_rel_x))
        self.zoom_rel_y = max(0.0, min(1.0, self.zoom_rel_y))
        self.animate_zoom_with_cursor()

    def animate_zoom_with_cursor(self):
        if abs(self.user_zoom - self.target_zoom) < 0.005:
            self.user_zoom = self.target_zoom
            # Обновляем размер окна при зуме
            new_width = int(self.original_width * self.user_zoom)
            new_height = int(self.original_height * self.user_zoom)
            if new_width >= 50 and new_height >= 50:
                # Сохраняем позицию окна
                current_x = self.master.winfo_x()
                current_y = self.master.winfo_y()
                self.window_width = new_width
                self.window_height = new_height
                self.master.geometry(f"{new_width}x{new_height}+{current_x}+{current_y}")
                self.update_borders_position()

            self.update_image()
            coords = self.canvas.coords("image")
            if coords:
                img_x, img_y = coords
                cursor_x = self.last_cursor_x
                cursor_y = self.last_cursor_y
                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()

                if canvas_width <= 0 or canvas_height <= 0:
                    canvas_width = self.window_width
                    canvas_height = self.window_height

                if cursor_x < 0 or cursor_x > canvas_width or cursor_y < 0 or cursor_y > canvas_height:
                    cursor_x = canvas_width // 2
                    cursor_y = canvas_height // 2

                new_img_x = cursor_x - self.zoom_rel_x * (self.original_width * self.user_zoom)
                new_img_y = cursor_y - self.zoom_rel_y * (self.original_height * self.user_zoom)
                img_width = self.original_width * self.user_zoom
                img_height = self.original_height * self.user_zoom
                min_x = min(0, canvas_width - img_width)
                max_x = max(0, canvas_width - img_width)
                min_y = min(0, canvas_height - img_height)
                max_y = max(0, canvas_height - img_height)
                new_img_x = max(min_x, min(max_x, new_img_x))
                new_img_y = max(min_y, min(max_y, new_img_y))
                self.canvas.coords("image", new_img_x, new_img_y)
            self.zoom_animation_id = None
            return

        self.user_zoom += (self.target_zoom - self.user_zoom) * 0.3
        # Обновляем размер окна при зуме
        new_width = int(self.original_width * self.user_zoom)
        new_height = int(self.original_height * self.user_zoom)
        if new_width >= 50 and new_height >= 50:
            current_x = self.master.winfo_x()
            current_y = self.master.winfo_y()
            self.window_width = new_width
            self.window_height = new_height
            self.master.geometry(f"{new_width}x{new_height}+{current_x}+{current_y}")
            self.update_borders_position()

        self.update_image()

        coords = self.canvas.coords("image")
        if coords:
            img_x, img_y = coords
            cursor_x = self.last_cursor_x
            cursor_y = self.last_cursor_y
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            if canvas_width <= 0 or canvas_height <= 0:
                canvas_width = self.window_width
                canvas_height = self.window_height

            if cursor_x < 0 or cursor_x > canvas_width or cursor_y < 0 or cursor_y > canvas_height:
                cursor_x = canvas_width // 2
                cursor_y = canvas_height // 2

            new_img_x = cursor_x - self.zoom_rel_x * (self.original_width * self.user_zoom)
            new_img_y = cursor_y - self.zoom_rel_y * (self.original_height * self.user_zoom)
            img_width = self.original_width * self.user_zoom
            img_height = self.original_height * self.user_zoom
            min_x = min(0, canvas_width - img_width)
            max_x = max(0, canvas_width - img_width)
            min_y = min(0, canvas_height - img_height)
            max_y = max(0, canvas_height - img_height)
            new_img_x = max(min_x, min(max_x, new_img_x))
            new_img_y = max(min_y, min(max_y, new_img_y))
            self.canvas.coords("image", new_img_x, new_img_y)

        self.zoom_animation_id = self.master.after(16, self.animate_zoom_with_cursor)

    def bind_events(self):
        self.canvas.bind("<Control-Button-1>", self.start_pan)
        self.canvas.bind("<Control-B1-Motion>", self.on_pan)
        self.canvas.bind("<Control-ButtonRelease-1>", self.stop_pan)

        self.canvas.bind("<MouseWheel>", self.on_mousewheel_zoom)
        self.canvas.bind("<Button-4>", self.on_mousewheel_zoom)
        self.canvas.bind("<Button-5>", self.on_mousewheel_zoom)
        self.canvas.bind("<Control-MouseWheel>", self.on_mousewheel_zoom)
        self.canvas.bind("<Shift-MouseWheel>", self.on_mousewheel_zoom)
        self.canvas.bind("<Control-Button-4>", self.on_mousewheel_zoom)
        self.canvas.bind("<Control-Button-5>", self.on_mousewheel_zoom)
        self.canvas.bind("<Shift-Button-4>", self.on_mousewheel_zoom)
        self.canvas.bind("<Shift-Button-5>", self.on_mousewheel_zoom)

        self.canvas.bind("<Button-2>", self.on_middle_click_reset)
        self.master.bind("<Button-2>", self.on_middle_click_reset)

    def on_middle_click_reset(self, event):
        self.reset_all()
        return "break"

    def on_mousewheel_zoom(self, event):
        if not self.image_loaded:
            return "break"
        self.last_cursor_x = event.x
        self.last_cursor_y = event.y
        zoom_step = self.get_zoom_step(event)

        if hasattr(event, 'delta'):
            if event.delta > 0:
                self.animate_zoom_to_cursor(zoom_step)
            elif event.delta < 0:
                self.animate_zoom_to_cursor(1.0 / zoom_step)
        else:
            if event.num == 4:
                self.animate_zoom_to_cursor(zoom_step)
            elif event.num == 5:
                self.animate_zoom_to_cursor(1.0 / zoom_step)
        return "break"

    def start_move(self, event):
        self.moving = True
        self.move_start_x = event.x_root - self.master.winfo_x()
        self.move_start_y = event.y_root - self.master.winfo_y()

    def on_move(self, event):
        if self.moving:
            x = event.x_root - self.move_start_x
            y = event.y_root - self.move_start_y
            self.master.geometry(f"+{x}+{y}")

    def stop_move(self, event):
        self.moving = False

    def start_pan(self, event):
        if self.image_loaded and self.user_zoom > 1.0:
            self.panning = True
            self.pan_start_x = event.x
            self.pan_start_y = event.y
            coords = self.canvas.coords("image")
            if coords:
                self.image_start_x = coords[0]
                self.image_start_y = coords[1]
            self.canvas.config(cursor="fleur")

    def on_pan(self, event):
        if self.panning and self.image_loaded and self.user_zoom > 1.0:
            dx = event.x - self.pan_start_x
            dy = event.y - self.pan_start_y
            new_x = self.image_start_x + dx
            new_y = self.image_start_y + dy
            img_width = int(self.original_width * self.user_zoom)
            img_height = int(self.original_height * self.user_zoom)
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            min_x = min(0, canvas_width - img_width)
            max_x = max(0, canvas_width - img_width)
            min_y = min(0, canvas_height - img_height)
            max_y = max(0, canvas_height - img_height)
            new_x = max(min_x, min(max_x, new_x))
            new_y = max(min_y, min(max_y, new_y))
            self.canvas.coords("image", new_x, new_y)

    def stop_pan(self, event):
        self.panning = False
        self.canvas.config(cursor="arrow")

    def on_canvas_configure(self, event):
        if self.image_loaded:
            self.update_canvas_size()
            self.update_image()

    @lru_cache(maxsize=32)
    def get_scaled_image(self, width, height):
        if width > 0 and height > 0:
            return self.original_image.resize((width, height), Image.Resampling.LANCZOS)
        return None

    def zoom_in(self):
        if self.image_loaded and self.target_zoom < self.max_zoom:
            self.exit_stretch_mode()
            self.animate_zoom_to_cursor(self.zoom_step_normal)

    def zoom_out(self):
        if self.image_loaded and self.target_zoom > self.min_zoom:
            self.exit_stretch_mode()
            self.animate_zoom_to_cursor(1.0 / self.zoom_step_normal)

    def reset_zoom(self):
        if self.image_loaded:
            self.exit_stretch_mode()
            self.target_zoom = 1.0
            self.update_image()
            if self.zoom_animation_id:
                self.master.after_cancel(self.zoom_animation_id)
            self.animate_zoom()

    def animate_zoom(self):
        if abs(self.user_zoom - self.target_zoom) < 0.01:
            self.user_zoom = self.target_zoom
            # Обновляем размер окна
            new_width = int(self.original_width * self.user_zoom)
            new_height = int(self.original_height * self.user_zoom)
            if new_width >= 50 and new_height >= 50:
                current_x = self.master.winfo_x()
                current_y = self.master.winfo_y()
                self.window_width = new_width
                self.window_height = new_height
                self.master.geometry(f"{new_width}x{new_height}+{current_x}+{current_y}")
                self.update_borders_position()
            self.update_image()
            self.zoom_animation_id = None
            return
        self.user_zoom += (self.target_zoom - self.user_zoom) * 0.3
        # Обновляем размер окна
        new_width = int(self.original_width * self.user_zoom)
        new_height = int(self.original_height * self.user_zoom)
        if new_width >= 50 and new_height >= 50:
            current_x = self.master.winfo_x()
            current_y = self.master.winfo_y()
            self.window_width = new_width
            self.window_height = new_height
            self.master.geometry(f"{new_width}x{new_height}+{current_x}+{current_y}")
            self.update_borders_position()
        self.update_image()
        self.zoom_animation_id = self.master.after(16, self.animate_zoom)

    def reset_size(self):
        if hasattr(self, 'optimal_width') and hasattr(self, 'optimal_height'):
            current_x = self.master.winfo_x()
            current_y = self.master.winfo_y()
            self.window_width = self.optimal_width
            self.window_height = self.optimal_height
            self.stretch_mode = False
            self.user_zoom = self.optimal_width / self.original_width
            self.target_zoom = self.user_zoom
            self.master.geometry(f"{self.window_width}x{self.window_height}+{current_x}+{current_y}")
            self.update_borders_position()
            if self.image_loaded:
                self.update_image()

    def reset_all(self):
        self.reset_zoom()
        self.reset_size()
        self.show_tooltip("✅ Зум и размер окна сброшены", 1500)

    def close(self):
        if hasattr(self, 'get_scaled_image'):
            self.get_scaled_image.cache_clear()
        if self.zoom_animation_id:
            self.master.after_cancel(self.zoom_animation_id)

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
        self.temp_files = []

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

    def center_main_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def setup_hotkeys(self):
        def handle_hotkey(event):
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

    def open_settings(self):
        SettingsWindow(self.root, self.settings, self.on_settings_changed)

    def on_settings_changed(self):
        zoom_normal = self.settings.get("zoom_normal")
        self.info_label.config(text=f"✅ Настройки обновлены! Обычный зум: +{int((zoom_normal - 1) * 100)}%")
        self.root.after(3000, lambda: self.info_label.config(
            text="✅ Готов к работе! F1 - настройки, Ctrl+S - открыть настройки"))

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

        settings_menu = tk.Menu(menubar, tearoff=0, bg='#2b2b2b', fg='white')
        menubar.add_cascade(label="Настройки", menu=settings_menu)
        settings_menu.add_command(label="Настройки (Ctrl+S / F1)", command=self.open_settings)
        settings_menu.add_separator()
        settings_menu.add_command(label="Сбросить настройки", command=self.reset_settings)

        view_menu = tk.Menu(menubar, tearoff=0, bg='#2b2b2b', fg='white')
        menubar.add_cascade(label="Вид", menu=view_menu)
        view_menu.add_command(label="Каскадом", command=self.arrange_cascade)
        view_menu.add_command(label="Сеткой", command=self.arrange_grid)

        help_menu = tk.Menu(menubar, tearoff=0, bg='#2b2b2b', fg='white')
        menubar.add_cascade(label="Помощь", menu=help_menu)
        help_menu.add_command(label="Горячие клавиши", command=self.show_shortcuts)
        help_menu.add_command(label="О программе", command=self.show_about)

    def show_shortcuts(self):
        shortcuts_text = """ГОРЯЧИЕ КЛАВИШИ:

Главное окно:
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
Версия 2.1

Программа для просмотра изображений в плавающих окнах.

Особенности:
• Плавающие окна поверх всех программ
• Масштабирование с привязкой к курсору
• Панорамирование при увеличении
• Вставка из буфера обмена
• Сохранение настроек
• Интеллектуальное изменение размера окон

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

        btn_close = tk.Button(button_frame, text="✖ ЗАКРЫТЬ ВСЕ (Ctrl+W)",
                              command=self.close_all, bg='#8b0000', fg='white',
                              padx=15, pady=10, font=('Segoe UI', 11, 'bold'), cursor='hand2')
        btn_close.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        btn_settings = tk.Button(button_frame, text="⚙️ НАСТРОЙКИ (F1)",
                                 command=self.open_settings, bg='#5a5a5a', fg='white',
                                 padx=15, pady=10, font=('Segoe UI', 11, 'bold'), cursor='hand2')
        btn_settings.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        self.info_label = tk.Label(main_container,
                                   text=f"✅ Готов к работе! Нажмите F1 для справки",
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
                temp_dir = Path.home() / "AppData" / "Local" / "Temp" / "floating_images"
                temp_dir.mkdir(exist_ok=True)
                timestamp = int(time.time() * 1000)
                temp_file = temp_dir / f"clipboard_{timestamp}.png"
                img.save(temp_file)
                self.image_files.append(str(temp_file))
                self.temp_files.append(str(temp_file))
                filename = f"[Буфер] {time.strftime('%H:%M:%S')}"
                self.image_listbox.insert(tk.END, filename)
                self.image_listbox.see(tk.END)
                self.info_label.config(text=f"✅ Картинка из буфера добавлена (всего: {len(self.image_files)})")
            else:
                messagebox.showinfo("Информация", "В буфере не изображение")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось вставить из буфера\n\n{str(e)}")

    def remove_selected(self):
        selected = self.image_listbox.curselection()
        if not selected:
            messagebox.showinfo("Информация", "Выберите картинки для удаления")
            return
        for idx in reversed(selected):
            if idx < len(self.image_files):
                file_path = self.image_files[idx]
                if file_path in self.temp_files:
                    try:
                        os.remove(file_path)
                        self.temp_files.remove(file_path)
                    except:
                        pass
                del self.image_files[idx]
                self.image_listbox.delete(idx)
        self.info_label.config(text=f"🗑️ Удалено {len(selected)} картинок (осталось: {len(self.image_files)})")

    def clear_list(self):
        if self.image_files:
            for temp_file in self.temp_files:
                try:
                    os.remove(temp_file)
                except:
                    pass
            self.temp_files.clear()
            self.image_files.clear()
            self.image_listbox.delete(0, tk.END)
            self.info_label.config(text="📭 Список очищен")

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

    def show_all(self):
        if not self.image_files:
            messagebox.showinfo("Информация", "Сначала добавьте картинки")
            return
        for image_path in self.image_files:
            self.create_floating_window(image_path)

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
        self.info_label.config(text="✅ Все окна закрыты")

    def on_close(self):
        for temp_file in self.temp_files:
            try:
                os.remove(temp_file)
            except:
                pass
        self.close_all()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = ImageGallery()
    app.run()
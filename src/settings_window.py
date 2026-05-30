# src/settings_window.py

import tkinter as tk
from tkinter import messagebox
import sys
import subprocess
import threading  # Добавьте эту строку в существующие импорты


class SettingsWindow:
    def __init__(self, parent, settings, on_settings_changed):
        """
        Инициализирует окно настроек, сохраняя ссылку на галерею и корневое окно.

        Аргументы:
            parent: корневое окно Tk или экземпляр ImageGallery
            settings: объект настроек
            on_settings_changed: callback при изменении настроек
        """
        self.parent = parent
        self.settings = settings
        self.on_settings_changed = on_settings_changed
        self.is_fullscreen = False
        self.normal_geometry = None

        # Сохраняем ссылку на галерею, если parent не является галереей
        if hasattr(parent, 'root') and hasattr(parent, 'close_all'):
            # parent уже является галереей
            self.gallery = parent
            self.root_window = parent.root
        elif hasattr(parent, 'master') and hasattr(parent.master, 'close_all'):
            # parent - это Toplevel, а его master - галерея
            self.gallery = parent.master
            self.root_window = parent
        else:
            # Пытаемся найти галерею в родителях
            self.gallery = None
            self.root_window = parent
            temp = parent
            while temp:
                if hasattr(temp, 'close_all') and hasattr(temp, 'root'):
                    self.gallery = temp
                    self.root_window = temp.root
                    break
                temp = getattr(temp, 'master', None)

        self.window = tk.Toplevel(parent)
        self.window.title(self.settings.get_string('settings_title'))
        self.window.configure(bg='#2b2b2b')
        self.window.geometry("700x700")
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

    def save_settings(self):
        """
        Сохраняет все настройки и при изменении языка обновляет интерфейс без перезапуска.
        Только сохраняет настройки и уведомляет главное окно о необходимости обновить UI.
        """
        old_lang = self.settings.get_language()
        new_lang = self.language_var.get()

        # Сохраняем все настройки
        self.settings.set("zoom_slow", self.slow_zoom_var.get())
        self.settings.set("zoom_normal", self.normal_zoom_var.get())
        self.settings.set("zoom_fast", self.fast_zoom_var.get())
        self.settings.set("min_zoom", self.min_zoom_var.get())
        self.settings.set("max_zoom", self.max_zoom_var.get())
        self.settings.set("hide_delay", self.hide_delay_var.get())
        self.settings.set("border_size", self.border_size_var.get())
        self.settings.set("zoom_animation", self.zoom_animation_var.get())
        self.settings.set("animation_duration", self.anim_duration_var.get())

        # Проверяем, изменился ли язык
        if old_lang != new_lang:
            self.settings.set_language(new_lang)
            self.settings.save()

            # Обновляем интерфейс главного окна
            if hasattr(self, 'gallery') and self.gallery:
                if hasattr(self.gallery, 'update_ui_language'):
                    self.gallery.update_ui_language()

            # Показываем уведомление об успешной смене языка
            messagebox.showinfo(
                self.get_string('settings_title'),
                self.get_string('settings_saved')
            )

            self.window.destroy()
        else:
            # Язык не изменился - просто применяем настройки
            if self.on_settings_changed:
                self.on_settings_changed()

            messagebox.showinfo(
                self.get_string('settings_title'),
                self.get_string('settings_saved')
            )
            self.window.destroy()

    def restart_app(self):
        """
        Перезапускает приложение после смены языка.
        Использует прямой вызов процесса без BAT-файлов.
        """
        import subprocess
        import sys
        import os
        import time

        self.settings.save()

        if hasattr(self, 'gallery') and self.gallery:
            try:
                if hasattr(self.gallery, 'save_gallery'):
                    self.gallery.save_gallery()
                if hasattr(self.gallery, 'close_all'):
                    self.gallery.close_all()
            except:
                pass

        if getattr(sys, 'frozen', False):
            executable_path = sys.executable

            if sys.platform == 'win32':
                subprocess.Popen(
                    [executable_path],
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                    shell=False
                )
            else:
                subprocess.Popen([executable_path])
        else:
            script_path = os.path.abspath(sys.argv[0])
            if sys.platform == 'win32':
                subprocess.Popen(
                    [sys.executable, script_path],
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                subprocess.Popen([sys.executable, script_path])

        time.sleep(0.5)

        self.window.destroy()

        if hasattr(self, 'gallery') and self.gallery:
            try:
                if hasattr(self.gallery, 'root'):
                    self.gallery.root.quit()
                    self.gallery.root.destroy()
            except:
                pass
        elif hasattr(self, 'root_window') and self.root_window:
            try:
                self.root_window.quit()
                self.root_window.destroy()
            except:
                pass

        os._exit(0)

    def get_string(self, key):
        return self.settings.get_string(key)

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
        menubar.add_cascade(label=self.get_string('settings_window'), menu=window_menu)
        window_menu.add_command(label=self.get_string('settings_fullscreen'), command=self.toggle_fullscreen)
        window_menu.add_separator()
        window_menu.add_command(label=self.get_string('settings_close'), command=self.window.destroy)

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

        title = tk.Label(main_container, text=self.get_string('settings_main_title'),
                         font=('Segoe UI', 18, 'bold'), bg='#2b2b2b', fg='white')
        title.pack(pady=(10, 20))

        # Язык
        lang_frame = tk.LabelFrame(main_container, text=self.get_string('settings_language'),
                                   bg='#2b2b2b', fg='white', font=('Segoe UI', 13, 'bold'),
                                   padx=20, pady=15)
        lang_frame.pack(fill="x", pady=(0, 15), padx=20)

        lang_inner = tk.Frame(lang_frame, bg='#2b2b2b')
        lang_inner.pack(fill="x", pady=8)

        tk.Label(lang_inner, text=self.get_string('settings_language_label'),
                 bg='#2b2b2b', fg='#cccccc', font=('Segoe UI', 11)).pack(side=tk.LEFT, padx=(0, 15))

        self.language_var = tk.StringVar(value=self.settings.get_language())
        lang_ru = tk.Radiobutton(lang_inner, text="Русский", variable=self.language_var, value="ru",
                                 bg='#2b2b2b', fg='white', selectcolor='#2b2b2b', font=('Segoe UI', 11))
        lang_ru.pack(side=tk.LEFT, padx=10)
        lang_en = tk.Radiobutton(lang_inner, text="English", variable=self.language_var, value="en",
                                 bg='#2b2b2b', fg='white', selectcolor='#2b2b2b', font=('Segoe UI', 11))
        lang_en.pack(side=tk.LEFT, padx=10)

        # Скорость зума
        zoom_frame = tk.LabelFrame(main_container, text=self.get_string('settings_zoom_speed'),
                                   bg='#2b2b2b', fg='white', font=('Segoe UI', 13, 'bold'),
                                   padx=20, pady=15)
        zoom_frame.pack(fill="x", pady=(0, 15), padx=20)

        # Slow zoom
        frame1 = tk.Frame(zoom_frame, bg='#2b2b2b')
        frame1.pack(fill="x", pady=8)
        tk.Label(frame1, text=self.get_string('settings_slow_zoom'),
                 bg='#2b2b2b', fg='#cccccc', font=('Segoe UI', 11)).pack(side=tk.LEFT, padx=(0, 15))
        self.slow_zoom_var = tk.DoubleVar()
        self.slow_zoom_scale = tk.Scale(frame1, from_=1.01, to=1.1, resolution=0.005,
                                        orient=tk.HORIZONTAL, variable=self.slow_zoom_var,
                                        bg='#3c3c3c', fg='white', highlightthickness=0, width=18)
        self.slow_zoom_scale.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=15)
        self.slow_zoom_label = tk.Label(frame1, text="", bg='#2b2b2b', fg='#00ff00', width=8,
                                        font=('Segoe UI', 11, 'bold'))
        self.slow_zoom_label.pack(side=tk.LEFT)

        # Normal zoom
        frame2 = tk.Frame(zoom_frame, bg='#2b2b2b')
        frame2.pack(fill="x", pady=8)
        tk.Label(frame2, text=self.get_string('settings_normal_zoom'),
                 bg='#2b2b2b', fg='#cccccc', font=('Segoe UI', 11)).pack(side=tk.LEFT, padx=(0, 15))
        self.normal_zoom_var = tk.DoubleVar()
        self.normal_zoom_scale = tk.Scale(frame2, from_=1.01, to=1.2, resolution=0.005,
                                          orient=tk.HORIZONTAL, variable=self.normal_zoom_var,
                                          bg='#3c3c3c', fg='white', highlightthickness=0, width=18)
        self.normal_zoom_scale.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=15)
        self.normal_zoom_label = tk.Label(frame2, text="", bg='#2b2b2b', fg='#00ff00', width=8,
                                          font=('Segoe UI', 11, 'bold'))
        self.normal_zoom_label.pack(side=tk.LEFT)

        # Fast zoom
        frame3 = tk.Frame(zoom_frame, bg='#2b2b2b')
        frame3.pack(fill="x", pady=8)
        tk.Label(frame3, text=self.get_string('settings_fast_zoom'),
                 bg='#2b2b2b', fg='#cccccc', font=('Segoe UI', 11)).pack(side=tk.LEFT, padx=(0, 15))
        self.fast_zoom_var = tk.DoubleVar()
        self.fast_zoom_scale = tk.Scale(frame3, from_=1.05, to=1.5, resolution=0.01,
                                        orient=tk.HORIZONTAL, variable=self.fast_zoom_var,
                                        bg='#3c3c3c', fg='white', highlightthickness=0, width=18)
        self.fast_zoom_scale.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=15)
        self.fast_zoom_label = tk.Label(frame3, text="", bg='#2b2b2b', fg='#00ff00', width=8,
                                        font=('Segoe UI', 11, 'bold'))
        self.fast_zoom_label.pack(side=tk.LEFT)

        # Ограничения зума
        limits_frame = tk.LabelFrame(main_container, text=self.get_string('settings_zoom_limits'),
                                     bg='#2b2b2b', fg='white', font=('Segoe UI', 13, 'bold'),
                                     padx=20, pady=15)
        limits_frame.pack(fill="x", pady=(0, 15), padx=20)

        # Min zoom
        frame4 = tk.Frame(limits_frame, bg='#2b2b2b')
        frame4.pack(fill="x", pady=8)
        tk.Label(frame4, text=self.get_string('settings_min_zoom'),
                 bg='#2b2b2b', fg='#cccccc', font=('Segoe UI', 11)).pack(side=tk.LEFT, padx=(0, 15))
        self.min_zoom_var = tk.DoubleVar()
        self.min_zoom_scale = tk.Scale(frame4, from_=0.1, to=1.0, resolution=0.05,
                                       orient=tk.HORIZONTAL, variable=self.min_zoom_var,
                                       bg='#3c3c3c', fg='white', highlightthickness=0, width=18)
        self.min_zoom_scale.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=15)
        self.min_zoom_label = tk.Label(frame4, text="", bg='#2b2b2b', fg='#00ff00', width=8,
                                       font=('Segoe UI', 11, 'bold'))
        self.min_zoom_label.pack(side=tk.LEFT)

        # Max zoom
        frame5 = tk.Frame(limits_frame, bg='#2b2b2b')
        frame5.pack(fill="x", pady=8)
        tk.Label(frame5, text=self.get_string('settings_max_zoom'),
                 bg='#2b2b2b', fg='#cccccc', font=('Segoe UI', 11)).pack(side=tk.LEFT, padx=(0, 15))
        self.max_zoom_var = tk.DoubleVar()
        self.max_zoom_scale = tk.Scale(frame5, from_=2.0, to=20.0, resolution=0.5,
                                       orient=tk.HORIZONTAL, variable=self.max_zoom_var,
                                       bg='#3c3c3c', fg='white', highlightthickness=0, width=18)
        self.max_zoom_scale.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=15)
        self.max_zoom_label = tk.Label(frame5, text="", bg='#2b2b2b', fg='#00ff00', width=8,
                                       font=('Segoe UI', 11, 'bold'))
        self.max_zoom_label.pack(side=tk.LEFT)

        # Анимация
        animation_frame = tk.LabelFrame(main_container, text=self.get_string('settings_animation'),
                                        bg='#2b2b2b', fg='white', font=('Segoe UI', 13, 'bold'),
                                        padx=20, pady=15)
        animation_frame.pack(fill="x", pady=(0, 15), padx=20)

        self.zoom_animation_var = tk.BooleanVar()
        zoom_animation_cb = tk.Checkbutton(animation_frame, text=self.get_string('settings_zoom_animation'),
                                           variable=self.zoom_animation_var,
                                           bg='#2b2b2b', fg='white', selectcolor='#2b2b2b',
                                           font=('Segoe UI', 11))
        zoom_animation_cb.pack(anchor=tk.W, pady=5)

        frame_anim = tk.Frame(animation_frame, bg='#2b2b2b')
        frame_anim.pack(fill="x", pady=8)
        tk.Label(frame_anim, text=self.get_string('settings_anim_duration'),
                 bg='#2b2b2b', fg='#cccccc', font=('Segoe UI', 11)).pack(side=tk.LEFT, padx=(0, 15))
        self.anim_duration_var = tk.IntVar()
        self.anim_duration_scale = tk.Scale(frame_anim, from_=50, to=300, resolution=10,
                                            orient=tk.HORIZONTAL, variable=self.anim_duration_var,
                                            bg='#3c3c3c', fg='white', highlightthickness=0, width=18)
        self.anim_duration_scale.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=15)
        self.anim_duration_label = tk.Label(frame_anim, text="", bg='#2b2b2b', fg='#00ff00', width=8,
                                            font=('Segoe UI', 11, 'bold'))
        self.anim_duration_label.pack(side=tk.LEFT)

        # Интерфейс
        ui_frame = tk.LabelFrame(main_container, text=self.get_string('settings_ui'),
                                 bg='#2b2b2b', fg='white', font=('Segoe UI', 13, 'bold'),
                                 padx=20, pady=15)
        ui_frame.pack(fill="x", pady=(0, 15), padx=20)

        # Hide delay
        frame6 = tk.Frame(ui_frame, bg='#2b2b2b')
        frame6.pack(fill="x", pady=8)
        tk.Label(frame6, text=self.get_string('settings_hide_delay'),
                 bg='#2b2b2b', fg='#cccccc', font=('Segoe UI', 11)).pack(side=tk.LEFT, padx=(0, 15))
        self.hide_delay_var = tk.IntVar()
        self.hide_delay_scale = tk.Scale(frame6, from_=500, to=5000, resolution=100,
                                         orient=tk.HORIZONTAL, variable=self.hide_delay_var,
                                         bg='#3c3c3c', fg='white', highlightthickness=0, width=18)
        self.hide_delay_scale.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=15)
        self.hide_delay_label = tk.Label(frame6, text="", bg='#2b2b2b', fg='#00ff00', width=8,
                                         font=('Segoe UI', 11, 'bold'))
        self.hide_delay_label.pack(side=tk.LEFT)

        # Border size
        frame7 = tk.Frame(ui_frame, bg='#2b2b2b')
        frame7.pack(fill="x", pady=8)
        tk.Label(frame7, text=self.get_string('settings_border_size'),
                 bg='#2b2b2b', fg='#cccccc', font=('Segoe UI', 11)).pack(side=tk.LEFT, padx=(0, 15))
        self.border_size_var = tk.IntVar()
        self.border_size_scale = tk.Scale(frame7, from_=4, to=15, resolution=1,
                                          orient=tk.HORIZONTAL, variable=self.border_size_var,
                                          bg='#3c3c3c', fg='white', highlightthickness=0, width=18)
        self.border_size_scale.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=15)
        self.border_size_label = tk.Label(frame7, text="", bg='#2b2b2b', fg='#00ff00', width=8,
                                          font=('Segoe UI', 11, 'bold'))
        self.border_size_label.pack(side=tk.LEFT)

        # Кнопки
        button_frame = tk.Frame(main_container, bg='#2b2b2b')
        button_frame.pack(fill="x", pady=25, padx=20)

        btn_save = tk.Button(button_frame, text=self.get_string('settings_save'), command=self.save_settings,
                             bg='#0078d4', fg='white', padx=20, pady=10,
                             font=('Segoe UI', 11, 'bold'), cursor='hand2')
        btn_save.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        btn_reset = tk.Button(button_frame, text=self.get_string('settings_reset'), command=self.reset_settings,
                              bg='#3c3c3c', fg='white', padx=20, pady=10,
                              font=('Segoe UI', 11, 'bold'), cursor='hand2')
        btn_reset.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        btn_cancel = tk.Button(button_frame, text=self.get_string('settings_cancel'), command=self.window.destroy,
                               bg='#5a5a5a', fg='white', padx=20, pady=10,
                               font=('Segoe UI', 11, 'bold'), cursor='hand2')
        btn_cancel.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        # Привязка обновления меток
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

    def reset_settings(self):
        if messagebox.askyesno(self.get_string('settings_title'), self.get_string('settings_reset_confirm')):
            from src.settings import Settings
            for key, value in Settings.DEFAULT_SETTINGS.items():
                self.settings.set(key, value)
            self.load_values()
            self.update_labels()
            messagebox.showinfo(self.get_string('settings_title'), self.get_string('settings_reset_done'))
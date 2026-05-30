# src/gallery.py

import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import ImageGrab
import os
import time
import json
from pathlib import Path

from src.constants import GALLERY_FILE, STORAGE_DIR, APP_DIR
from src.settings import Settings
from src.settings_window import SettingsWindow
from src.floating_image import FloatingImage
from src.utils import ensure_app_directories


class ImageGallery:
    """Главное окно галереи с управлением плавающими изображениями"""

    def __init__(self):
        """Инициализирует главное окно галереи, загружает настройки и создает интерфейс"""
        self.settings = Settings()
        self.windows = []
        self.window_counter = 1
        self.image_files = []
        self.stored_files = []
        self.all_windows_hidden = False

        self.root = tk.Tk()
        self.root.title(self.settings.get_string('app_title'))
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

        self.root.focus_force()

    def show_tooltip(self, event, text):
        """Показывает всплывающую подсказку при наведении на кнопку панели инструментов.

        Аргументы:
            event: событие наведения мыши
            text: текст подсказки
        """
        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.wm_overrideredirect(True)

        # Получаем координаты кнопки
        x = event.widget.winfo_rootx() + event.widget.winfo_width() // 2
        y = event.widget.winfo_rooty() + event.widget.winfo_height() + 5

        self.tooltip.wm_geometry(f"+{x - 50}+{y}")

        label = tk.Label(self.tooltip, text=text, bg='#ffffcc', fg='black',
                         padx=8, pady=4, font=('Segoe UI', 9),
                         relief='solid', borderwidth=1)
        label.pack()

    def hide_tooltip(self, event):
        """Скрывает всплывающую подсказку при уходе мыши с кнопки."""
        if hasattr(self, 'tooltip') and self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

    def get_string(self, key):
        """Возвращает локализованную строку по ключу"""
        return self.settings.get_string(key)

    def toggle_language(self):
        """
        Переключает язык между русским и английским с последующим перезапуском приложения.
        Кнопка вызывает этот метод для смены языка.
        """
        current_lang = self.settings.get_language()
        new_lang = "en" if current_lang == "ru" else "ru"
        self.settings.set_language(new_lang)

        # Показываем сообщение о смене языка
        messagebox.showinfo(
            self.get_string('settings_title'),
            self.get_string('language_changed')
        )

        # Перезапускаем приложение
        self.restart_app()

    def restart_app(self):
        """
        Перезапускает приложение, сохраняя настройки и закрывая все окна.
        Запускает новый процесс перед завершением текущего.
        Исправляет ошибку с encodings при переключении языка.
        """
        import subprocess
        import sys
        import os
        import time

        # Сохраняем настройки и галерею перед перезапуском
        self.settings.save()
        self.save_gallery()

        # Определяем способ запуска (exe или скрипт)
        if getattr(sys, 'frozen', False):
            executable_path = sys.executable
            args = [executable_path]

            # Устанавливаем переменные окружения для encodings
            env = os.environ.copy()
            if hasattr(sys, '_MEIPASS'):
                env['PYTHONPATH'] = sys._MEIPASS
                env['PATH'] = sys._MEIPASS + os.pathsep + env.get('PATH', '')
        else:
            script_path = os.path.abspath(sys.argv[0])
            args = [sys.executable, script_path] + sys.argv[1:]
            env = os.environ.copy()

        # Запускаем новый процесс
        if sys.platform == 'win32':
            subprocess.Popen(
                args,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                env=env
            )
        else:
            subprocess.Popen(args, env=env)

        # Даем время на запуск нового процесса
        time.sleep(0.5)

        # Закрываем все окна
        self.close_all()

        # Завершаем текущий процесс
        self.root.quit()
        self.root.destroy()
        os._exit(0)

    def center_main_window(self):
        """Центрирует главное окно на экране"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def create_menu(self):
        """Создает главное меню приложения"""
        menubar = tk.Menu(self.root, bg='#2b2b2b', fg='white')
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0, bg='#2b2b2b', fg='white')
        menubar.add_cascade(label=self.get_string('menu_file'), menu=file_menu)
        file_menu.add_command(label=self.get_string('menu_open'), command=self.open_images)
        file_menu.add_command(label=self.get_string('menu_paste'), command=self.paste_from_clipboard)
        file_menu.add_separator()
        file_menu.add_command(label=self.get_string('menu_show_all'), command=self.show_all)
        file_menu.add_command(label=self.get_string('menu_close_all'), command=self.close_all)
        file_menu.add_separator()
        file_menu.add_command(label=self.get_string('menu_open_folder'), command=self.open_app_folder)
        file_menu.add_separator()
        file_menu.add_command(label=self.get_string('menu_exit'), command=self.on_close)

        edit_menu = tk.Menu(menubar, tearoff=0, bg='#2b2b2b', fg='white')
        menubar.add_cascade(label=self.get_string('menu_edit'), menu=edit_menu)
        edit_menu.add_command(label=self.get_string('menu_delete'), command=self.remove_selected)
        edit_menu.add_command(label=self.get_string('menu_clear'), command=self.clear_list)

        view_menu = tk.Menu(menubar, tearoff=0, bg='#2b2b2b', fg='white')
        menubar.add_cascade(label=self.get_string('menu_view'), menu=view_menu)
        view_menu.add_command(label=self.get_string('menu_toggle_windows'), command=self.toggle_all_windows)
        view_menu.add_separator()
        view_menu.add_command(label=self.get_string('menu_cascade'), command=self.arrange_cascade)
        view_menu.add_command(label=self.get_string('menu_grid'), command=self.arrange_grid)

        settings_menu = tk.Menu(menubar, tearoff=0, bg='#2b2b2b', fg='white')
        menubar.add_cascade(label=self.get_string('menu_settings'), menu=settings_menu)
        settings_menu.add_command(label=self.get_string('menu_settings_item'), command=self.open_settings)
        settings_menu.add_separator()
        settings_menu.add_command(label=self.get_string('menu_reset_settings'), command=self.reset_settings)

        help_menu = tk.Menu(menubar, tearoff=0, bg='#2b2b2b', fg='white')
        menubar.add_cascade(label=self.get_string('menu_help'), menu=help_menu)
        help_menu.add_command(label=self.get_string('menu_shortcuts'), command=self.show_shortcuts)
        help_menu.add_command(label=self.get_string('menu_about'), command=self.show_about)

    def create_widgets(self):
        """Создает все виджеты главного окна с панелью инструментов в стиле Delphi.

        Панель инструментов содержит иконки (символы эмодзи) всех основных функций:
        - Открыть, Вставить, Показать выбранные, Показать все
        - Скрыть/показать окна, Каскад, Сетка
        - Настройки, Папка, Удалить, Очистить
        - Выход

        Все подсказки на кнопках используют мультиязычную систему через get_string().
        """
        main_container = tk.Frame(self.root, bg='#2b2b2b')
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Создаем панель для кнопки языка в левом верхнем углу
        lang_button_container = tk.Frame(main_container, bg='#2b2b2b')
        lang_button_container.pack(fill=tk.X, pady=(0, 10))

        # Кнопка переключения языка слева сверху
        current_lang = self.settings.get_language()
        lang_button_text = "EN" if current_lang == "ru" else "RU"
        self.lang_button = tk.Button(
            lang_button_container,
            text=lang_button_text,
            command=self.toggle_language,
            bg='#0078d4',
            fg='white',
            width=4,
            height=1,
            font=('Segoe UI', 10, 'bold'),
            cursor='hand2',
            relief=tk.RAISED
        )
        self.lang_button.pack(side=tk.LEFT, anchor='nw')

        title = tk.Label(main_container, text=self.get_string('app_title'),
                         font=('Segoe UI', 20, 'bold'), bg='#2b2b2b', fg='white')
        title.pack(pady=(0, 20))

        # Панель инструментов в стиле Delphi - все кнопки-иконки в ряд
        toolbar = tk.Frame(main_container, bg='#3c3c3c', height=35, relief=tk.FLAT, bd=1)
        toolbar.pack(fill=tk.X, pady=(0, 15))
        toolbar.pack_propagate(False)

        # Стиль для кнопок панели инструментов
        button_style = {
            'bg': '#3c3c3c',
            'fg': '#ffffff',
            'font': ('Segoe UI', 14),
            'width': 3,
            'height': 1,
            'relief': tk.FLAT,
            'cursor': 'hand2',
            'activebackground': '#5a5a5a',
            'activeforeground': '#ffffff'
        }

        # Первая группа: работа с файлами
        btn_open = tk.Button(toolbar, text="📂", command=self.open_images,
                             **button_style)
        btn_open.pack(side=tk.LEFT, padx=2, pady=3)
        btn_open.bind("<Enter>", lambda e, t=self.get_string('tooltip_open'): self.show_tooltip(e, t))
        btn_open.bind("<Leave>", self.hide_tooltip)

        btn_paste = tk.Button(toolbar, text="📋", command=self.paste_from_clipboard,
                              **button_style)
        btn_paste.pack(side=tk.LEFT, padx=2, pady=3)
        btn_paste.bind("<Enter>", lambda e, t=self.get_string('tooltip_paste'): self.show_tooltip(e, t))
        btn_paste.bind("<Leave>", self.hide_tooltip)

        # Разделитель
        tk.Frame(toolbar, bg='#5a5a5a', width=2, height=25).pack(side=tk.LEFT, padx=5, pady=3)

        # Вторая группа: показ изображений
        btn_show_sel = tk.Button(toolbar, text="🖼️", command=self.show_selected,
                                 **button_style)
        btn_show_sel.pack(side=tk.LEFT, padx=2, pady=3)
        btn_show_sel.bind("<Enter>", lambda e, t=self.get_string('tooltip_show_selected'): self.show_tooltip(e, t))
        btn_show_sel.bind("<Leave>", self.hide_tooltip)

        btn_show_all = tk.Button(toolbar, text="✨", command=self.show_all,
                                 **button_style)
        btn_show_all.pack(side=tk.LEFT, padx=2, pady=3)
        btn_show_all.bind("<Enter>", lambda e, t=self.get_string('tooltip_show_all'): self.show_tooltip(e, t))
        btn_show_all.bind("<Leave>", self.hide_tooltip)

        # Разделитель
        tk.Frame(toolbar, bg='#5a5a5a', width=2, height=25).pack(side=tk.LEFT, padx=5, pady=3)

        # Третья группа: управление окнами
        btn_toggle = tk.Button(toolbar, text="👁️", command=self.toggle_all_windows,
                               **button_style)
        btn_toggle.pack(side=tk.LEFT, padx=2, pady=3)
        btn_toggle.bind("<Enter>", lambda e, t=self.get_string('tooltip_toggle_windows'): self.show_tooltip(e, t))
        btn_toggle.bind("<Leave>", self.hide_tooltip)

        btn_cascade = tk.Button(toolbar, text="📐", command=self.arrange_cascade,
                                **button_style)
        btn_cascade.pack(side=tk.LEFT, padx=2, pady=3)
        btn_cascade.bind("<Enter>", lambda e, t=self.get_string('tooltip_cascade'): self.show_tooltip(e, t))
        btn_cascade.bind("<Leave>", self.hide_tooltip)

        btn_grid = tk.Button(toolbar, text="🔲", command=self.arrange_grid,
                             **button_style)
        btn_grid.pack(side=tk.LEFT, padx=2, pady=3)
        btn_grid.bind("<Enter>", lambda e, t=self.get_string('tooltip_grid'): self.show_tooltip(e, t))
        btn_grid.bind("<Leave>", self.hide_tooltip)

        btn_close_all = tk.Button(toolbar, text="✖", command=self.close_all,
                                  **button_style)
        btn_close_all.pack(side=tk.LEFT, padx=2, pady=3)
        btn_close_all.bind("<Enter>", lambda e, t=self.get_string('tooltip_close_all'): self.show_tooltip(e, t))
        btn_close_all.bind("<Leave>", self.hide_tooltip)

        # Разделитель
        tk.Frame(toolbar, bg='#5a5a5a', width=2, height=25).pack(side=tk.LEFT, padx=5, pady=3)

        # Четвертая группа: инструменты
        btn_settings = tk.Button(toolbar, text="⚙️", command=self.open_settings,
                                 **button_style)
        btn_settings.pack(side=tk.LEFT, padx=2, pady=3)
        btn_settings.bind("<Enter>", lambda e, t=self.get_string('tooltip_settings'): self.show_tooltip(e, t))
        btn_settings.bind("<Leave>", self.hide_tooltip)

        btn_folder = tk.Button(toolbar, text="📂", command=self.open_app_folder,
                               **button_style)
        btn_folder.pack(side=tk.LEFT, padx=2, pady=3)
        btn_folder.bind("<Enter>", lambda e, t=self.get_string('tooltip_app_folder'): self.show_tooltip(e, t))
        btn_folder.bind("<Leave>", self.hide_tooltip)

        # Разделитель
        tk.Frame(toolbar, bg='#5a5a5a', width=2, height=25).pack(side=tk.LEFT, padx=5, pady=3)

        # Пятая группа: редактирование списка
        btn_delete = tk.Button(toolbar, text="🗑️", command=self.remove_selected,
                               **button_style)
        btn_delete.pack(side=tk.LEFT, padx=2, pady=3)
        btn_delete.bind("<Enter>", lambda e, t=self.get_string('tooltip_delete'): self.show_tooltip(e, t))
        btn_delete.bind("<Leave>", self.hide_tooltip)

        btn_clear = tk.Button(toolbar, text="📭", command=self.clear_list,
                              **button_style)
        btn_clear.pack(side=tk.LEFT, padx=2, pady=3)
        btn_clear.bind("<Enter>", lambda e, t=self.get_string('tooltip_clear_list'): self.show_tooltip(e, t))
        btn_clear.bind("<Leave>", self.hide_tooltip)

        # Разделитель
        tk.Frame(toolbar, bg='#5a5a5a', width=2, height=25).pack(side=tk.LEFT, padx=5, pady=3)

        # Шестая группа: выход
        btn_exit = tk.Button(toolbar, text="🚪", command=self.on_close,
                             **button_style)
        btn_exit.pack(side=tk.LEFT, padx=2, pady=3)
        btn_exit.bind("<Enter>", lambda e, t=self.get_string('tooltip_exit'): self.show_tooltip(e, t))
        btn_exit.bind("<Leave>", self.hide_tooltip)

        # Список изображений
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

        self.info_label = tk.Label(main_container,
                                   text=f"{self.get_string('ready')}\n{self.get_string('data_folder')} {APP_DIR}",
                                   font=('Segoe UI', 10), bg='#2b2b2b', fg='#888888', justify=tk.LEFT)
        self.info_label.pack(pady=(0, 10))

        self.root.bind("<F1>", lambda e: self.open_settings())

    def setup_hotkeys(self):
        """Настраивает глобальные горячие клавиши"""

        def handle_hotkey(event):
            keycode = event.keycode

            if keycode in (72, 56) and not (event.state & 0x4 or event.state & 0x1 or event.state & 0x20000):
                self.toggle_all_windows(event)
                return "break"
            if event.state & 0x4 and keycode == 86:
                self.paste_from_clipboard()
                return "break"
            if event.state & 0x4 and keycode == 79:
                self.open_images()
                return "break"
            if event.state & 0x4 and keycode == 65:
                self.show_all()
                return "break"
            if event.state & 0x4 and keycode == 83:
                self.open_settings()
                return "break"
            if event.state & 0x4 and keycode == 87:
                self.close_all()
                return "break"
            if event.state & 0x4 and keycode == 81:
                self.on_close()
                return "break"
            if keycode == 46:
                self.remove_selected()
                return "break"
            if keycode == 112:
                self.open_settings()
                return "break"
            if keycode == 27 and self.windows:
                self.close_all()
                return "break"

        self.root.bind_all("<Key>", handle_hotkey)
        self.root.focus_force()

    def toggle_all_windows(self, event=None):
        """Скрывает или показывает все открытые плавающие окна"""
        self.cleanup_closed_windows()
        if not self.windows:
            self.info_label.config(text=self.get_string('no_windows'))
            return

        if self.all_windows_hidden:
            shown = 0
            for window in self.windows:
                try:
                    if hasattr(window, 'master') and window.master.winfo_exists():
                        window.master.deiconify()
                        window.master.lift()
                        if hasattr(window, 'update_image'):
                            window.update_image()
                        if hasattr(window, 'update_canvas_size'):
                            window.update_canvas_size()
                        shown += 1
                except Exception as e:
                    print(f"Ошибка при показе окна: {e}")
            self.all_windows_hidden = False
            self.info_label.config(text=self.get_string('windows_shown').format(shown))
        else:
            hidden = 0
            for window in self.windows:
                try:
                    if hasattr(window, 'master') and window.master.winfo_exists():
                        window.master.withdraw()
                        hidden += 1
                except Exception as e:
                    print(f"Ошибка при скрытии окна: {e}")
            self.all_windows_hidden = True
            self.info_label.config(text=self.get_string('windows_hidden').format(hidden))

    def open_app_folder(self):
        """Открывает папку приложения в проводнике"""
        try:
            if APP_DIR.exists():
                os.startfile(str(APP_DIR))
                self.info_label.config(text=f"{self.get_string('folder_opened')} {APP_DIR}")
            else:
                ensure_app_directories()
                os.startfile(str(APP_DIR))
                self.info_label.config(text=f"{self.get_string('folder_created')} {APP_DIR}")
        except Exception as e:
            messagebox.showerror(self.get_string('folder_error'), f"{str(e)}")

    def save_gallery(self):
        """Сохраняет список изображений в JSON файл"""
        try:
            GALLERY_FILE.parent.mkdir(parents=True, exist_ok=True)
            existing_files = [f for f in self.image_files if os.path.exists(f)]
            with open(GALLERY_FILE, 'w', encoding='utf-8') as f:
                json.dump(existing_files, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Ошибка сохранения списка: {e}")
            return False

    def load_gallery(self):
        """Загружает список изображений из JSON файла"""
        try:
            if GALLERY_FILE.exists():
                with open(GALLERY_FILE, 'r', encoding='utf-8') as f:
                    loaded_files = json.load(f)
                    self.image_files.clear()
                    self.image_listbox.delete(0, tk.END)
                    added = 0
                    for file in loaded_files:
                        if os.path.exists(file):
                            self.image_files.append(file)
                            if str(STORAGE_DIR) in file:
                                filename = f"[Clipboard] {Path(file).stem.replace('clipboard_', '')}"
                            else:
                                filename = os.path.basename(file)
                                if len(filename) > 60:
                                    filename = filename[:57] + "..."
                            self.image_listbox.insert(tk.END, filename)
                            added += 1
                    if added > 0:
                        self.info_label.config(text=self.get_string('gallery_loaded').format(added))
                    else:
                        self.info_label.config(text=self.get_string('ready'))
            else:
                self.info_label.config(text=self.get_string('ready'))
        except Exception as e:
            print(f"Ошибка загрузки списка: {e}")
            self.info_label.config(text=self.get_string('ready'))

    def open_settings(self):
        """Открывает окно настроек"""
        SettingsWindow(self.root, self.settings, self.on_settings_changed)

    def on_settings_changed(self):
        """Обработчик изменения настроек"""
        zoom_normal = self.settings.get("zoom_normal")
        self.info_label.config(text=self.get_string('settings_updated').format(int((zoom_normal - 1) * 100)))
        self.root.after(3000, lambda: self.info_label.config(text=self.get_string('ready')))

    def reset_settings(self):
        """Сбрасывает все настройки к значениям по умолчанию"""
        if messagebox.askyesno(self.get_string('settings_title'), self.get_string('settings_reset_confirm')):
            for key, value in Settings.DEFAULT_SETTINGS.items():
                self.settings.set(key, value)
            self.on_settings_changed()
            messagebox.showinfo(self.get_string('settings_title'), self.get_string('settings_reset_done'))

    def show_shortcuts(self):
        """Показывает окно с горячими клавишами"""
        messagebox.showinfo(self.get_string('shortcuts_title'), self.get_string('shortcuts_text'))

    def show_about(self):
        """Показывает окно 'О программе'"""
        messagebox.showinfo(self.get_string('about_title'), self.get_string('about_text'))

    def on_double_click(self, event):
        """Обработчик двойного клика по списку изображений"""
        selection = self.image_listbox.curselection()
        if not selection:
            return
        opened = 0
        for idx in selection:
            if idx < len(self.image_files):
                self.create_floating_window(self.image_files[idx])
                opened += 1
        if opened > 0:
            self.info_label.config(text=self.get_string('images_opened').format(opened))
            self.all_windows_hidden = False

    def open_images(self):
        """Открывает диалог выбора изображений и добавляет их в галерею"""
        files = filedialog.askopenfilenames(
            title="Выберите картинки",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.gif *.bmp *.webp"), ("All files", "*.*")]
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
            self.info_label.config(text=self.get_string('image_added').format(added, len(self.image_files)))
            self.save_gallery()

    def paste_from_clipboard(self):
        """Вставляет изображение из буфера обмена и сохраняет его"""
        try:
            self.root.lift()
            self.root.focus_force()
            img = ImageGrab.grabclipboard()
            if img is None:
                messagebox.showinfo("Информация", self.get_string('clipboard_no_image'))
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

                display_name = f"[Clipboard] {time.strftime('%Y-%m-%d %H:%M:%S')}"
                self.image_listbox.insert(tk.END, display_name)
                self.image_listbox.see(tk.END)
                self.info_label.config(text=self.get_string('clipboard_added').format(len(self.image_files)))
                self.save_gallery()
            else:
                messagebox.showinfo("Информация", self.get_string('clipboard_not_image'))
        except Exception as e:
            messagebox.showerror("Ошибка", f"{self.get_string('clipboard_error')}\n\n{str(e)}")

    def remove_selected(self):
        """Удаляет выбранные изображения из галереи"""
        selected = self.image_listbox.curselection()
        if not selected:
            messagebox.showinfo("Информация", self.get_string('select_images'))
            return

        deleted_count = 0
        for idx in reversed(selected):
            if idx < len(self.image_files):
                file_path = self.image_files[idx]
                if file_path in self.stored_files:
                    try:
                        os.remove(file_path)
                        self.stored_files.remove(file_path)
                    except Exception as e:
                        print(f"Ошибка удаления {file_path}: {e}")
                del self.image_files[idx]
                self.image_listbox.delete(idx)
                deleted_count += 1

        self.info_label.config(text=self.get_string('deleted').format(deleted_count, len(self.image_files)))
        self.save_gallery()

    def clear_list(self):
        """Очищает весь список изображений и удаляет сохраненные файлы"""
        if self.image_files:
            for stored_file in self.stored_files:
                try:
                    if os.path.exists(stored_file):
                        os.remove(stored_file)
                except Exception as e:
                    print(f"Ошибка удаления {stored_file}: {e}")
            self.stored_files.clear()
            self.image_files.clear()
            self.image_listbox.delete(0, tk.END)
            self.info_label.config(text=self.get_string('list_cleared'))
            self.save_gallery()

    def show_selected(self):
        """Показывает выбранные изображения в плавающих окнах"""
        selected_indices = self.image_listbox.curselection()
        if not selected_indices:
            messagebox.showinfo("Информация", self.get_string('select_from_list'))
            return
        if not self.image_files:
            messagebox.showinfo("Информация", self.get_string('add_images_first'))
            return
        for idx in selected_indices:
            if idx < len(self.image_files):
                self.create_floating_window(self.image_files[idx])
        self.all_windows_hidden = False

    def show_all(self):
        """Показывает все изображения из галереи в плавающих окнах"""
        if not self.image_files:
            messagebox.showinfo("Информация", self.get_string('add_images_first'))
            return
        for image_path in self.image_files:
            self.create_floating_window(image_path)
        self.all_windows_hidden = False

    def cleanup_closed_windows(self):
        """Удаляет из списка закрытые окна"""
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
        """Располагает все окна каскадом"""
        self.cleanup_closed_windows()
        if not self.windows:
            self.info_label.config(text=self.get_string('no_windows_arrange'))
            return

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        start_x, start_y = 50, 50
        offset_x, offset_y = 30, 30

        windows_info = [w for w in self.windows if hasattr(w, 'master') and w.master.winfo_exists()]
        if not windows_info:
            self.info_label.config(text=self.get_string('no_windows_arrange'))
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
                window.master.geometry(f"+{int(max(50, x))}+{int(max(50, y))}")
            except Exception as e:
                print(f"Ошибка при расположении окна: {e}")

        self.info_label.config(text=self.get_string('arranged_cascade').format(len(windows_info)))

    def arrange_grid(self):
        """Располагает все окна сеткой"""
        self.cleanup_closed_windows()
        if not self.windows:
            self.info_label.config(text=self.get_string('no_windows_arrange'))
            return

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        windows_info = []
        for window in self.windows:
            try:
                if window.master.winfo_exists():
                    windows_info.append({
                        'window': window,
                        'width': window.window_width if hasattr(window, 'window_width') else 400,
                        'height': window.window_height if hasattr(window, 'window_height') else 300
                    })
            except:
                continue

        if not windows_info:
            self.info_label.config(text=self.get_string('no_windows_arrange'))
            return

        window_count = len(windows_info)
        cols = min(window_count, 4)
        rows = (window_count + cols - 1) // cols

        max_width = max(info['width'] for info in windows_info)
        max_height = max(info['height'] for info in windows_info)

        spacing_x, spacing_y = 20, 20

        total_width = cols * max_width + (cols - 1) * spacing_x
        total_height = rows * max_height + (rows - 1) * spacing_y

        start_x = max(50, (screen_width - total_width) // 2)
        start_y = max(50, (screen_height - total_height) // 2)

        for i, info in enumerate(windows_info):
            try:
                row = i // cols
                col = i % cols
                x = start_x + col * (max_width + spacing_x)
                y = start_y + row * (max_height + spacing_y)
                x = max(20, min(x, screen_width - info['width'] - 20))
                y = max(20, min(y, screen_height - info['height'] - 20))
                info['window'].master.geometry(f"+{int(x)}+{int(y)}")
            except Exception as e:
                print(f"Ошибка при расположении окна: {e}")

        self.info_label.config(text=self.get_string('arranged_grid').format(window_count, cols, rows))

    def create_floating_window(self, image_path):
        """Создает новое плавающее окно с изображением"""
        try:
            self.cleanup_closed_windows()
            win = tk.Toplevel()
            window_id = self.window_counter
            self.window_counter += 1
            floating = FloatingImage(win, image_path, window_id, self.settings)
            floating.parent_gallery = self
            self.windows.append(floating)
            self.info_label.config(text=self.get_string('windows_opened').format(len(self.windows)))
        except Exception as e:
            messagebox.showerror("Ошибка", f"{self.get_string('error_open_image')}\n{str(e)}")

    def on_floating_window_close(self, floating_window):
        """Обработчик закрытия плавающего окна"""
        try:
            if floating_window in self.windows:
                self.windows.remove(floating_window)
            self.info_label.config(text=self.get_string('windows_opened').format(len(self.windows)))
        except:
            pass

    def close_all(self):
        """Закрывает все плавающие окна"""
        windows_copy = self.windows[:]
        for window in windows_copy:
            try:
                window.close()
            except:
                pass
        self.windows.clear()
        self.all_windows_hidden = False
        self.info_label.config(text=self.get_string('all_closed'))

    def on_close(self):
        """Обработчик закрытия главного окна"""
        print(self.get_string('exiting'))
        self.save_gallery()
        self.close_all()
        self.root.destroy()

    def run(self):
        """Запускает главный цикл приложения"""
        self.root.mainloop()
# src/floating_image.py
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import os
import threading


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
        self.keep_aspect = True

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

        # Переменные для изображения
        self.img_width = 0
        self.img_height = 0
        self.display_width = 0
        self.display_height = 0
        self.image_x = 0
        self.image_y = 0
        self.current_image = None
        self.photo_image = None
        self.original_image = None
        self.original_width = 0
        self.original_height = 0
        self._last_canvas_size = (0, 0)

        # Таймеры
        self.hide_timer = None
        self._zoom_timer = None

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

    def get_string(self, key):
        return self.settings.get_string(key)

    def on_mousewheel_zoom(self, event):
        try:
            if not self.image_loaded:
                return "break"

            if self._zoom_timer:
                self.master.after_cancel(self._zoom_timer)
                self._zoom_timer = None

            self.keep_aspect = True

            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            if canvas_width <= 0 or canvas_height <= 0:
                return "break"

            if event.state & 0x0001:
                zoom_step = self.zoom_step_fast
            elif event.state & 0x0004:
                zoom_step = self.zoom_step_slow
            else:
                zoom_step = self.zoom_step_normal

            cursor_x = event.x
            cursor_y = event.y

            if self.display_width > 0 and self.display_height > 0:
                img_point_x = (cursor_x - self.image_x) / self.display_width
                img_point_y = (cursor_y - self.image_y) / self.display_height
                img_point_x = max(0, min(1, img_point_x))
                img_point_y = max(0, min(1, img_point_y))
            else:
                img_point_x, img_point_y = 0.5, 0.5

            if event.delta > 0:
                new_zoom = min(self.user_zoom * zoom_step, self.max_zoom)
            else:
                new_zoom = max(self.user_zoom / zoom_step, self.min_zoom)

            if new_zoom == self.user_zoom:
                return "break"

            self.user_zoom = new_zoom

            new_display_width = int(self.original_width * self.user_zoom)
            new_display_height = int(self.original_height * self.user_zoom)

            new_image_x = cursor_x - img_point_x * new_display_width
            new_image_y = cursor_y - img_point_y * new_display_height

            if new_display_width <= canvas_width:
                new_image_x = (canvas_width - new_display_width) // 2
            else:
                min_x = canvas_width - new_display_width
                max_x = 0
                new_image_x = max(min(new_image_x, max_x), min_x)

            if new_display_height <= canvas_height:
                new_image_y = (canvas_height - new_display_height) // 2
            else:
                min_y = canvas_height - new_display_height
                max_y = 0
                new_image_y = max(min(new_image_y, max_y), min_y)

            self.display_width = new_display_width
            self.display_height = new_display_height
            self.image_x = new_image_x
            self.image_y = new_image_y

            resized = self.original_image.resize((self.display_width, self.display_height), Image.Resampling.NEAREST)
            self.photo_image = ImageTk.PhotoImage(resized)

            self.canvas.delete("all")
            self.current_image = self.canvas.create_image(
                int(self.image_x), int(self.image_y),
                anchor=tk.NW,
                image=self.photo_image
            )

            self._zoom_timer = self.master.after(200, self.update_image_quality)

            percent = int(self.user_zoom * 100)
            self.show_tooltip(self.get_string('img_zoom_percent').format(percent), 200)

        except Exception as e:
            print(f"Ошибка в зуме: {e}")

        return "break"

    def update_image_quality(self):
        if not self.image_loaded or self._zoom_timer is None:
            return

        try:
            resized = self.original_image.resize((self.display_width, self.display_height), Image.Resampling.LANCZOS)
            self.photo_image = ImageTk.PhotoImage(resized)

            self.canvas.delete("all")
            self.current_image = self.canvas.create_image(
                int(self.image_x), int(self.image_y),
                anchor=tk.NW,
                image=self.photo_image
            )
        except Exception as e:
            print(f"Ошибка повышения качества: {e}")

        self._zoom_timer = None

    def reset_zoom(self):
        if self.image_loaded:
            self.user_zoom = 1.0
            self.update_image()
            self.show_tooltip(self.get_string('img_zoom_reset'), 1000)

    def reset_window(self):
        if not self.image_loaded:
            return

        self.user_zoom = 1.0

        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()

        max_width = min(self.original_width, int(screen_width * 0.6))
        max_height = min(self.original_height, int(screen_height * 0.6))

        if self.original_width > max_width or self.original_height > max_height:
            ratio = min(max_width / self.original_width, max_height / self.original_height)
            self.window_width = int(self.original_width * ratio)
            self.window_height = int(self.original_height * ratio)
        else:
            self.window_width = self.original_width
            self.window_height = self.original_height

        self.position_away_from_main()

        self.master.geometry(
            f"{self.window_width}x{self.window_height}+{self.master.winfo_x()}+{self.master.winfo_y()}")

        self.calculate_image_size()
        self.clamp_image_position()
        self.redraw_image()

        self.keep_aspect = True

        self.show_tooltip(self.get_string('img_window_reset'), 1500)

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
            img_aspect = self.original_width / self.original_height

            if self.resize_edge in ['right', 'left', 'top_left', 'bottom_left', 'top_right', 'bottom_right']:
                new_height = int(new_width / img_aspect)
            elif self.resize_edge in ['top', 'bottom']:
                new_width = int(new_height * img_aspect)

            new_width = max(min_width, new_width)
            new_height = max(min_height, new_height)

            if self.resize_edge == 'left':
                new_x = self.resize_start_left + (self.resize_start_width - new_width)
            elif self.resize_edge == 'top':
                new_y = self.resize_start_top + (self.resize_start_height - new_height)
            elif self.resize_edge == 'top_left':
                new_x = self.resize_start_left + (self.resize_start_width - new_width)
                new_y = self.resize_start_top + (self.resize_start_height - new_height)
            elif self.resize_edge == 'top_right':
                new_y = self.resize_start_top + (self.resize_start_height - new_height)
            elif self.resize_edge == 'bottom_left':
                new_x = self.resize_start_left + (self.resize_start_width - new_width)

        self.master.geometry(f"{new_width}x{new_height}+{new_x}+{new_y}")
        self.window_width = new_width
        self.window_height = new_height

        self.update_image_resize_live()

    def update_image_resize_live(self):
        if not self.image_loaded:
            return

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width <= 0 or canvas_height <= 0:
            return

        if self.resize_with_shift:
            self.keep_aspect = True
            img_width = int(self.original_width * self.user_zoom)
            img_height = int(self.original_height * self.user_zoom)
            scale = min(canvas_width / img_width, canvas_height / img_height)
            self.display_width = int(img_width * scale)
            self.display_height = int(img_height * scale)
            self.image_x = (canvas_width - self.display_width) // 2
            self.image_y = (canvas_height - self.display_height) // 2
        elif self.resize_with_ctrl:
            self.image_x = (canvas_width - self.display_width) // 2
            self.image_y = (canvas_height - self.display_height) // 2
        else:
            self.keep_aspect = False
            self.display_width = canvas_width
            self.display_height = canvas_height
            self.image_x = 0
            self.image_y = 0

        try:
            resized = self.original_image.resize((self.display_width, self.display_height), Image.Resampling.BILINEAR)
            self.photo_image = ImageTk.PhotoImage(resized)
            self.canvas.delete("all")
            self.current_image = self.canvas.create_image(
                int(self.image_x), int(self.image_y),
                anchor=tk.NW,
                image=self.photo_image
            )
        except Exception as e:
            pass

    def stop_resize(self, event):
        self.resizing = False

        if self.image_loaded:
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            if self.resize_with_shift:
                self.keep_aspect = True
                img_width = int(self.original_width * self.user_zoom)
                img_height = int(self.original_height * self.user_zoom)
                scale = min(canvas_width / img_width, canvas_height / img_height)
                self.display_width = int(img_width * scale)
                self.display_height = int(img_height * scale)
                self.image_x = (canvas_width - self.display_width) // 2
                self.image_y = (canvas_height - self.display_height) // 2
            elif not self.resize_with_ctrl:
                self.keep_aspect = False
                self.display_width = canvas_width
                self.display_height = canvas_height
                self.image_x = 0
                self.image_y = 0
                self.user_zoom = 1.0

            try:
                resized = self.original_image.resize((self.display_width, self.display_height),
                                                     Image.Resampling.LANCZOS)
                self.photo_image = ImageTk.PhotoImage(resized)
                self.canvas.delete("all")
                self.current_image = self.canvas.create_image(
                    int(self.image_x), int(self.image_y),
                    anchor=tk.NW,
                    image=self.photo_image
                )
            except Exception as e:
                print(f"Ошибка финальной перерисовки: {e}")

        self.resize_with_shift = False
        self.resize_with_ctrl = False
        self.resize_edge = None

        if self.mouse_over:
            self.show_resize_borders()

    def calculate_image_size(self):
        if not self.original_image:
            return

        try:
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            if canvas_width <= 0 or canvas_height <= 0:
                return

            if self.keep_aspect:
                img_width = int(self.original_width * self.user_zoom)
                img_height = int(self.original_height * self.user_zoom)
                scale = min(canvas_width / img_width, canvas_height / img_height)
                self.display_width = int(img_width * scale)
                self.display_height = int(img_height * scale)
            else:
                self.display_width = canvas_width
                self.display_height = canvas_height

        except Exception as e:
            print(f"calculate_image_size ошибка: {e}")

    def redraw_image(self):
        if not self.original_image or self.display_width <= 0 or self.display_height <= 0:
            return

        try:
            resized = self.original_image.resize((self.display_width, self.display_height), Image.Resampling.LANCZOS)
            self.photo_image = ImageTk.PhotoImage(resized)
            self.canvas.delete("all")

            if self.keep_aspect:
                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()
                self.image_x = (canvas_width - self.display_width) // 2
                self.image_y = (canvas_height - self.display_height) // 2

            self.current_image = self.canvas.create_image(
                int(self.image_x), int(self.image_y),
                anchor=tk.NW,
                image=self.photo_image
            )
        except Exception as e:
            print(f"redraw_image ошибка: {e}")

    def clamp_image_position(self):
        try:
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            if canvas_width <= 0 or canvas_height <= 0:
                return

            if self.display_width <= canvas_width:
                self.image_x = (canvas_width - self.display_width) // 2
            else:
                min_x = canvas_width - self.display_width
                max_x = 0
                self.image_x = max(min(self.image_x, max_x), min_x)

            if self.display_height <= canvas_height:
                self.image_y = (canvas_height - self.display_height) // 2
            else:
                min_y = canvas_height - self.display_height
                max_y = 0
                self.image_y = max(min(self.image_y, max_y), min_y)

        except Exception as e:
            print(f"clamp_image_position ошибка: {e}")

    def update_image(self):
        if not self.image_loaded:
            return

        try:
            self.calculate_image_size()
            self.clamp_image_position()
            self.redraw_image()
        except Exception as e:
            print(f"update_image ошибка: {e}")

    def bind_events(self):
        self.canvas.bind("<MouseWheel>", self.on_mousewheel_zoom)
        self.canvas.bind("<Button-4>", self.on_mousewheel_zoom)
        self.canvas.bind("<Button-5>", self.on_mousewheel_zoom)

        self.canvas.bind("<ButtonPress-1>", self.start_pan)
        self.canvas.bind("<B1-Motion>", self.on_pan)
        self.canvas.bind("<ButtonRelease-1>", self.stop_pan)

        self.canvas.bind("<Configure>", self.on_canvas_configure)

        self.master.bind("<ButtonPress-1>", self.on_global_press)
        self.master.bind("<B1-Motion>", self.on_global_motion)
        self.master.bind("<ButtonRelease-1>", self.on_global_release)

        self.canvas.bind("<Button-2>", self.on_middle_click_reset)
        self.master.bind("<Button-2>", self.on_middle_click_reset)

        self.master.bind("<Control-a>", lambda e: self.toggle_keep_aspect())
        self.master.bind("<KP_Add>", lambda e: self.zoom_in())
        self.master.bind("<KP_Subtract>", lambda e: self.zoom_out())
        self.master.bind("<plus>", lambda e: self.zoom_in())
        self.master.bind("<minus>", lambda e: self.zoom_out())

        self.canvas.focus_set()
        self.canvas.bind("<Enter>", lambda e: self.canvas.focus_set())

        self.master.bind("<Enter>", self.on_mouse_enter)
        self.master.bind("<Leave>", self.on_mouse_leave)
        self.canvas.bind("<Enter>", self.on_mouse_enter)
        self.canvas.bind("<Leave>", self.on_mouse_leave)

    def toggle_keep_aspect(self):
        self.keep_aspect = True
        self.show_tooltip(self.get_string('img_mode_keep_aspect'), 1500)

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
            self.user_zoom = ratio
        else:
            self.user_zoom = 1.0

        self.window_width = min(self.original_width, max_width)
        self.window_height = min(self.original_height, max_height)

        self.master.geometry(f"{self.window_width}x{self.window_height}")

        self.update_canvas_size()
        self.calculate_image_size()

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        self.image_x = (canvas_width - self.display_width) // 2
        self.image_y = (canvas_height - self.display_height) // 2

        self.redraw_image()
        self.hide_loading_indicator()
        self.image_loaded = True
        self.update_borders_position()

    def on_canvas_configure(self, event):
        if self.image_loaded and not self.resizing:
            self.update_image()

    def zoom_in(self):
        if self.image_loaded:
            new_zoom = min(self.user_zoom * self.zoom_step_normal, self.max_zoom)
            if new_zoom != self.user_zoom:
                self.user_zoom = new_zoom
                self.calculate_image_size()
                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()
                self.image_x = (canvas_width - self.display_width) // 2
                self.image_y = (canvas_height - self.display_height) // 2
                self.clamp_image_position()
                self.redraw_image()
                self.show_tooltip(self.get_string('img_zoom_percent').format(int(self.user_zoom * 100)), 500)

    def zoom_out(self):
        if self.image_loaded:
            new_zoom = max(self.user_zoom / self.zoom_step_normal, self.min_zoom)
            if new_zoom != self.user_zoom:
                self.user_zoom = new_zoom
                self.calculate_image_size()
                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()
                self.image_x = (canvas_width - self.display_width) // 2
                self.image_y = (canvas_height - self.display_height) // 2
                self.clamp_image_position()
                self.redraw_image()
                self.show_tooltip(self.get_string('img_zoom_percent').format(int(self.user_zoom * 100)), 500)

    def start_pan(self, event):
        if not self.image_loaded:
            return

        if self.user_zoom > 1.0 and self.keep_aspect:
            self.panning = True
            self.pan_start_x = event.x
            self.pan_start_y = event.y
            self.pan_start_image_x = self.image_x
            self.pan_start_image_y = self.image_y
            self.canvas.config(cursor="fleur")
        else:
            self.window_moving = True
            self.window_move_start_x = event.x_root - self.master.winfo_x()
            self.window_move_start_y = event.y_root - self.master.winfo_y()
            self.canvas.config(cursor="fleur")

        return "break"

    def on_pan(self, event):
        if self.panning and self.user_zoom > 1.0 and self.keep_aspect:
            dx = event.x - self.pan_start_x
            dy = event.y - self.pan_start_y
            self.image_x = self.pan_start_image_x + dx
            self.image_y = self.pan_start_image_y + dy
            self.clamp_image_position()
            if self.current_image:
                self.canvas.coords(self.current_image, self.image_x, self.image_y)
            return "break"
        elif self.window_moving:
            x = event.x_root - self.window_move_start_x
            y = event.y_root - self.window_move_start_y
            self.master.geometry(f"+{x}+{y}")
            return "break"

    def stop_pan(self, event):
        self.panning = False
        self.window_moving = False
        self.canvas.config(cursor="arrow")

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

        self.resize_with_shift = bool(event.state & 0x0001)
        self.resize_with_ctrl = bool(event.state & 0x0004)

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
        self.context_menu.add_command(label=self.get_string('ctx_zoom_in'), command=self.zoom_in)
        self.context_menu.add_command(label=self.get_string('ctx_zoom_out'), command=self.zoom_out)
        self.context_menu.add_separator()
        self.context_menu.add_command(label=self.get_string('ctx_reset_window'), command=self.reset_window)
        self.context_menu.add_separator()
        self.context_menu.add_command(label=self.get_string('ctx_keep_aspect'), command=self.toggle_keep_aspect)
        self.context_menu.add_separator()
        self.context_menu.add_command(label=self.get_string('ctx_optimal_size'), command=self.reset_size)
        self.context_menu.add_separator()
        self.context_menu.add_command(label=self.get_string('ctx_copy_path'), command=self.copy_path)
        self.context_menu.add_command(label=self.get_string('ctx_close'), command=self.close)

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
        self.show_tooltip(self.get_string('img_path_copied'), 1000)

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
        self.loading_label = tk.Label(self.canvas, text=self.get_string('img_loading'),
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
            frame.bind("<Shift-Button-1>", lambda e: setattr(self, 'resize_with_shift', True) or self.start_resize(e))
            frame.bind("<Control-Button-1>", lambda e: setattr(self, 'resize_with_ctrl', True) or self.start_resize(e))

        self.hide_resize_borders()

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

    def update_canvas_size(self):
        width = self.master.winfo_width()
        height = self.master.winfo_height()
        if width > 0 and height > 0:
            self.canvas.config(width=width, height=height)

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

    def reset_size(self):
        if hasattr(self, 'optimal_width') and hasattr(self, 'optimal_height'):
            current_x = self.master.winfo_x()
            current_y = self.master.winfo_y()
            self.window_width = self.optimal_width
            self.window_height = self.optimal_height
            self.user_zoom = 1.0
            self.master.geometry(f"{self.window_width}x{self.window_height}+{current_x}+{current_y}")
            self.update_borders_position()
            if self.image_loaded:
                self.update_image()

    def close(self):
        if hasattr(self, 'parent_gallery') and self.parent_gallery:
            try:
                self.parent_gallery.on_floating_window_close(self)
            except:
                pass
        self.master.destroy()
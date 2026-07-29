import sys
from PyQt6.QtCore import Qt, QTimer, QTime, QSettings
from PyQt6.QtGui import QIcon, QAction, QCloseEvent
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QSystemTrayIcon, QMenu, QStackedWidget, QFrame, QLabel)
from qfluentwidgets import (SegmentedWidget, LargeTitleLabel, PrimaryPushButton, 
                            PushButton, setTheme, Theme, CompactSpinBox, TitleLabel, 
                            CaptionLabel, ToolButton, SmoothScrollArea,
                            TransparentToolButton, FluentIcon as FIF, InfoBar, InfoBarPosition, LineEdit)

class FocusableLineEdit(LineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

    def focusOutEvent(self, e):
        super().focusOutEvent(e)
        # Khi click ra ngoài, tự động bỏ trạng thái focus để mất viền xanh
        self.clearFocus()

class WorldClockWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.vbox = QVBoxLayout(self)
        self.vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.time_label = LargeTitleLabel("00:00:00", self)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.date_label = TitleLabel("Đang tải...", self)
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.vbox.addWidget(self.time_label)
        self.vbox.addWidget(self.date_label)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.update_time()

    def update_time(self):
        current_time = QTime.currentTime().toString("hh:mm:ss AP")
        current_date = QTime.currentTime().addSecs(0) # Thủ thuật nhỏ, dùng QDateTime thực tế tốt hơn
        from PyQt6.QtCore import QDateTime
        current_date = QDateTime.currentDateTime().toString("dd/MM/yyyy")
        self.time_label.setText(current_time)
        self.date_label.setText(current_date)

class SavedTimerItem(QFrame):
    def __init__(self, seconds, parent_widget):
        super().__init__()
        self.seconds = seconds
        self.parent_widget = parent_widget
        self.setObjectName("SavedTimerItem")
        
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(8, 8, 8, 8)
        
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        
        self.time_lbl = QLabel(f"{h:02d}:{m:02d}:{s:02d}")
        font = self.time_lbl.font()
        font.setPixelSize(14) 
        font.setBold(True)
        self.time_lbl.setFont(font)
        self.time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.addWidget(self.time_lbl)
        
        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        
        self.play_btn = ToolButton(FIF.PLAY, self)
        self.del_btn = ToolButton(FIF.DELETE, self)
        
        self.play_btn.clicked.connect(lambda: self.parent_widget.start_timer_from_saved(self.seconds))
        self.del_btn.clicked.connect(lambda: self.parent_widget.delete_saved_timer(self, self.seconds))
        
        hbox.addWidget(self.play_btn)
        hbox.addWidget(self.del_btn)
        vbox.addLayout(hbox)

    # THÊM HÀM NÀY
    def update_theme(self, text_color, border_color):
        self.setStyleSheet(f"""
            #SavedTimerItem {{
                border: 1px solid {border_color};
                border-radius: 6px;
            }}
        """)
        self.time_lbl.setStyleSheet(f"color: {text_color};")

class TimerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("UbuntuClock", "TimerSettings")
        self.saved_timers_list = []

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        # ================= TRÁI: KHU VỰC TIMER & NÚT BẤM =================
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Ô nhập liệu kiêm hiển thị thời gian
        self.time_input = FocusableLineEdit(self)
        self.time_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Bắt buộc định dạng HH:MM:SS
        self.time_input.setInputMask("00:00:00")
        self.time_input.setText("000000") # Sẽ tự hiển thị thành 00:00:00
        
        # Phóng to chữ giống Label
        font = self.time_input.font()
        font.setPixelSize(70)
        font.setBold(True)
        self.time_input.setFont(font)

        self.time_input.setFixedHeight(100) 
        self.time_input.setMinimumWidth(350)
        
        # Làm trong suốt để trông giống hệt Label (ẩn viền, ẩn nền)
        self.time_input.setStyleSheet("""
            LineEdit {
                background: transparent;
                border: 2px solid transparent;
            }
            LineEdit:hover {
                #background: rgba(128, 128, 128, 0.1);
                border-radius: 12px;
            }
            LineEdit:focus {
                background: transparent;
                border: 2px solid #009faa;
                border-radius: 12px;
            }
        """)

        self.left_layout.addWidget(self.time_input)
        self.left_layout.addSpacing(30)

        # Hàng nút điều khiển
        self.btn_layout = QHBoxLayout()
        self.btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.start_btn = PrimaryPushButton("Bắt đầu", self)
        self.stop_btn = PushButton("Tạm dừng", self)
        self.reset_btn = PushButton("Đặt lại", self)
        
        self.stop_btn.setEnabled(False) # Ban đầu chưa chạy thì ẩn Tạm dừng
        
        self.btn_layout.addWidget(self.start_btn)
        self.btn_layout.addWidget(self.stop_btn)
        self.btn_layout.addWidget(self.reset_btn)
        self.left_layout.addLayout(self.btn_layout)

        self.main_layout.addWidget(self.left_panel, stretch=1)

        # ================= PHẢI: KHU VỰC DANH SÁCH ĐÃ LƯU =================
        self.scroll_area = SmoothScrollArea(self)
        self.scroll_area.setFixedWidth(200)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: 1px solid rgba(128,128,128,0.2); border-radius: 8px; background: transparent; }")
        
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_layout.setContentsMargins(10, 10, 10, 10)
        self.scroll_layout.setSpacing(10)
        
        self.saved_title = CaptionLabel("Gần đây", self)
        self.scroll_layout.addWidget(self.saved_title)

        self.scroll_area.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll_area)

        # ================= LOGIC KẾT NỐI =================
        self.start_btn.clicked.connect(self.action_start)
        self.stop_btn.clicked.connect(self.action_pause)
        self.reset_btn.clicked.connect(self.action_reset)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.remaining_seconds = 0
        self.is_paused = False

        self.load_settings()

    # ================= CÁC HÀM XỬ LÝ ================= #
    def load_settings(self):
        saved = self.settings.value("saved_timers")
        if saved:
            if not isinstance(saved, list):
                saved = [saved]
            for s in saved:
                try:
                    secs = int(s)
                    if secs not in self.saved_timers_list:
                        self.saved_timers_list.append(secs)
                        self.add_saved_timer_ui(secs)
                except:
                    pass

    def save_settings(self):
        self.settings.setValue("saved_timers", self.saved_timers_list)

    def add_saved_timer_ui(self, seconds):
        item = SavedTimerItem(seconds, self)
        self.scroll_layout.addWidget(item)
        
        # Thêm đoạn này để tự động đổi màu khi vừa tạo mới
        is_dark = (self.window().current_theme == Theme.DARK)
        text_color = "white" if is_dark else "black"
        item_border = "rgba(255, 255, 255, 0.15)" if is_dark else "rgba(0, 0, 0, 0.15)"
        item.update_theme(text_color, item_border)

    def delete_saved_timer(self, item_widget, seconds):
        if seconds in self.saved_timers_list:
            self.saved_timers_list.remove(seconds)
            self.save_settings()
        item_widget.deleteLater()

    # Hàm chạy khi bấm Play ở cột bên phải
    def start_timer_from_saved(self, seconds):
        # Điền chuỗi số vào input, mask sẽ tự ngắt ra HH:MM:SS
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        self.time_input.setText(f"{h:02d}{m:02d}{s:02d}")
        self.action_start(force_new=True)

    def action_start(self, force_new=False):
        # Nếu đang chưa chạy (hoặc ép chạy cái mới) thì đọc thời gian mới
        if not self.timer.isActive() and not self.is_paused or force_new:
            text = self.time_input.text() # Kết quả sẽ là "01:30:00" nhờ InputMask
            parts = text.split(':')
            
            try:
                secs = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            except:
                secs = 0
                
            if secs == 0:
                InfoBar.warning("Lỗi", "Vui lòng nhập thời gian lớn hơn 0.", parent=self, duration=2000)
                return

            self.remaining_seconds = secs
            
            # Tự động lưu sang danh sách
            if secs not in self.saved_timers_list:
                self.saved_timers_list.append(secs)
                self.add_saved_timer_ui(secs)
                self.save_settings()

        # Bắt đầu chạy
        self.time_input.setReadOnly(True) # Khóa không cho người dùng sửa khi đang chạy
        self.timer.start(1000)
        self.is_paused = False
        
        # Đổi trạng thái nút
        self.start_btn.setText("Tiếp tục")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def action_pause(self):
        self.timer.stop()
        self.is_paused = True
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def action_reset(self):
        self.timer.stop()
        self.is_paused = False
        self.remaining_seconds = 0
        
        # Mở khóa và reset số về 0
        self.time_input.setReadOnly(False)
        self.time_input.setText("000000")
        
        # Cập nhật nút
        self.start_btn.setText("Bắt đầu")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def update_timer(self):
        self.remaining_seconds -= 1
        self.update_display_text()

        if self.remaining_seconds <= 0:
            self.action_reset()
            InfoBar.success(
                title='Hết giờ',
                content="Thời gian đếm ngược đã kết thúc!",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self
            )

    def update_display_text(self):
        h = self.remaining_seconds // 3600
        m = (self.remaining_seconds % 3600) // 60
        s = self.remaining_seconds % 60
        # Truyền đúng 6 số, InputMask sẽ tự chèn dấu ':' vào giữa
        self.time_input.setText(f"{h:02d}{m:02d}{s:02d}")

    def update_theme(self, is_dark):
        text_color = "white" if is_dark else "black"
        
        # FIX: Dùng màu nền thực tế thay vì transparent để khối con trỏ (Block cursor) có thể đảo màu đúng
        bg_color = "#202020" if is_dark else "#F3F3F3" 
        
        # Dùng màu hover dạng solid (đặc) thay vì rgba để tránh lỗi tương tự khi di chuột
        hover_bg = "#2A2A2A" if is_dark else "#EBEBEB" 
        
        border_color = "rgba(255, 255, 255, 0.2)" if is_dark else "rgba(0, 0, 0, 0.1)"
        item_border = "rgba(255, 255, 255, 0.15)" if is_dark else "rgba(0, 0, 0, 0.15)"
        
        # Cập nhật style cho ô nhập liệu
        self.time_input.setStyleSheet(f"""
            LineEdit {{
                color: {text_color};
                background-color: {bg_color};
                border: 2px solid {bg_color};
                selection-background-color: #009faa; 
                selection-color: white;
            }}
            LineEdit:hover {{
                background-color: {hover_bg};
                border: 2px solid {hover_bg};
                border-radius: 12px;
            }}
            LineEdit:focus {{
                background-color: {bg_color};
                border: 2px solid #009faa;
                border-radius: 12px;
            }}
        """)
        
        # Cập nhật style cho danh sách gần đây
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{ 
                border: 1px solid {border_color}; 
                border-radius: 8px; 
                background-color: transparent; 
            }}
        """)
        self.scroll_area.viewport().setStyleSheet("background-color: transparent;")
        self.scroll_content.setStyleSheet("background-color: transparent;")
        
        self.saved_title.setStyleSheet(f"color: {text_color};")
        
        # Cập nhật các item bên trong danh sách
        for i in range(self.scroll_layout.count()):
            widget = self.scroll_layout.itemAt(i).widget()
            if isinstance(widget, SavedTimerItem): # Nếu bạn vẫn đặt class là SavedTimerItem
                widget.update_theme(text_color, item_border)

class StopwatchWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.vbox = QVBoxLayout(self)
        self.vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.time_display = LargeTitleLabel("00:00:00.0", self)
        self.time_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vbox.addWidget(self.time_display)

        self.btn_layout = QHBoxLayout()
        self.start_btn = PrimaryPushButton("Bắt đầu", self)
        self.start_btn.clicked.connect(self.start_stopwatch)
        
        self.reset_btn = PushButton("Đặt lại", self)
        self.reset_btn.clicked.connect(self.reset_stopwatch)
        
        self.btn_layout.addWidget(self.start_btn)
        self.btn_layout.addWidget(self.reset_btn)
        self.vbox.addLayout(self.btn_layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_display)
        self.elapsed_time = 0  # in deciseconds (1/10s)
        self.is_running = False

    def start_stopwatch(self):
        if not self.is_running:
            self.timer.start(100)
            self.start_btn.setText("Tạm dừng")
            self.is_running = True
        else:
            self.timer.stop()
            self.start_btn.setText("Tiếp tục")
            self.is_running = False

    def reset_stopwatch(self):
        self.timer.stop()
        self.is_running = False
        self.elapsed_time = 0
        self.start_btn.setText("Bắt đầu")
        self.time_display.setText("00:00:00.0")

    def update_display(self):
        self.elapsed_time += 1
        ds = self.elapsed_time % 10
        s = (self.elapsed_time // 10) % 60
        m = (self.elapsed_time // 600) % 60
        h = (self.elapsed_time // 36000)
        self.time_display.setText(f"{h:02d}:{m:02d}:{s:02d}.{ds}")

class ClockApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ubuntu Modern Clock")
        self.resize(600, 400)
        
        # 1. Đặt Object Name và cho phép render Background
        self.setObjectName("MainWindow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.current_theme = Theme.LIGHT
        setTheme(self.current_theme)

        self.main_layout = QVBoxLayout(self)

        # -- THANH ĐIỀU HƯỚNG BÊN TRÊN --
        self.top_layout = QHBoxLayout()
        self.segmented_widget = SegmentedWidget(self)
        self.theme_btn = TransparentToolButton(FIF.CONSTRACT, self)
        self.theme_btn.clicked.connect(self.toggle_theme)

        self.top_layout.addStretch(1)
        self.top_layout.addWidget(self.segmented_widget)
        self.top_layout.addStretch(1)
        self.top_layout.addWidget(self.theme_btn)
        self.main_layout.addLayout(self.top_layout)

        # -- KHU VỰC NỘI DUNG (STACKED WIDGET) --
        self.stacked_widget = QStackedWidget(self)
        self.world_clock = WorldClockWidget(self)
        self.timer_widget = TimerWidget(self)
        self.stopwatch = StopwatchWidget(self)

        self.stacked_widget.addWidget(self.world_clock)
        self.stacked_widget.addWidget(self.timer_widget)
        self.stacked_widget.addWidget(self.stopwatch)
        self.main_layout.addWidget(self.stacked_widget)

        # Liên kết
        self.segmented_widget.addItem(routeKey='world_clock', icon=FIF.GLOBE, text='World Clock', onClick=lambda: self.stacked_widget.setCurrentIndex(0))
        self.segmented_widget.addItem(routeKey='timer', icon=FIF.ALBUM, text='Timer', onClick=lambda: self.stacked_widget.setCurrentIndex(1))
        self.segmented_widget.addItem(routeKey='stopwatch', icon=FIF.HISTORY, text='Stopwatch', onClick=lambda: self.stacked_widget.setCurrentIndex(2))
        self.segmented_widget.setCurrentItem('world_clock')

        # Khay hệ thống
        self.setup_system_tray()
        self.update_background()

    # 3. Hàm xử lý riêng phần đổi màu nền cho cửa sổ QWidget
    def update_background(self):
        is_dark = (self.current_theme == Theme.DARK)
        
        if is_dark:
            self.setStyleSheet("#MainWindow { background-color: #202020; }")
        else:
            self.setStyleSheet("#MainWindow { background-color: #F3F3F3; }")
            
        # Cập nhật màu chữ và viền cho Timer (nếu Timer đã được tạo)
        if hasattr(self, 'timer_widget'):
            self.timer_widget.update_theme(is_dark)

    def toggle_theme(self):
        if self.current_theme == Theme.LIGHT:
            self.current_theme = Theme.DARK
        else:
            self.current_theme = Theme.LIGHT
        
        # 4. Áp dụng theme mới và cập nhật lại màu nền cửa sổ
        setTheme(self.current_theme)
        self.update_background()

    def setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
        
        show_action = QAction("Hiển thị", self)
        quit_action = QAction("Thoát", self)
        
        show_action.triggered.connect(self.showNormal)
        quit_action.triggered.connect(QApplication.instance().quit)
        
        tray_menu = QMenu()
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isHidden():
                self.showNormal()
                self.activateWindow()
            else:
                self.hide()

    def closeEvent(self, event: QCloseEvent):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Đang chạy ngầm",
            "Ứng dụng đã được thu nhỏ xuống khay hệ thống.",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
if __name__ == '__main__':
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    
    # Chặn ứng dụng tự đóng khi cửa sổ cuối cùng bị ẩn
    app.setQuitOnLastWindowClosed(False)

    window = ClockApp()
    window.show()
    sys.exit(app.exec())
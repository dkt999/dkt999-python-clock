import sys
import os
import platform
import subprocess
from PyQt6.QtCore import Qt, QTimer, QTime, QDateTime, QTimeZone, QPoint, QPointF, QUrl, QSettings
from PyQt6.QtGui import QIcon, QAction, QCloseEvent, QPainter, QColor, QPen, QBrush, QIntValidator
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QSystemTrayIcon, QMenu, QStackedWidget, QFrame, QLabel, QGridLayout, QSizePolicy)
from qfluentwidgets import (FluentWindow, LargeTitleLabel, PrimaryPushButton, 
                            PushButton, setTheme, Theme, CaptionLabel, ToolButton, SmoothScrollArea,
                            TransparentToolButton, FluentIcon as FIF, InfoBar, InfoBarPosition, LineEdit,
                            NavigationItemPosition, SwitchButton, CheckBox, TitleLabel, SubtitleLabel,
                            ComboBox, CardWidget)

class CustomTimePicker(QWidget):
    def __init__(self, is_24h_format=True, parent=None):
        super().__init__(parent)
        self.is_24h = is_24h_format

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Ô nhập Giờ
        self.hour_input = LineEdit(self)
        self.hour_input.setPlaceholderText("HH")
        self.hour_input.setMaxLength(2) # Giới hạn tối đa 2 ký tự
        
        # Ô nhập Phút
        self.minute_input = LineEdit(self)
        self.minute_input.setPlaceholderText("MM")
        self.minute_input.setMaxLength(2) # Giới hạn tối đa 2 ký tự

        # Select AM / PM
        self.ampm_combo = ComboBox(self)
        self.ampm_combo.addItems(["AM", "PM"])

        layout.addWidget(self.hour_input)
        layout.addWidget(self.minute_input)
        layout.addWidget(self.ampm_combo)

        # 1. Bắt sự kiện realtime ngay khi gõ phím
        self.hour_input.textChanged.connect(self._on_hour_changed)
        self.minute_input.textChanged.connect(self._on_minute_changed)

        # 2. Bắt sự kiện khi rời ô (blur) để auto fill số 0 (ví dụ "5" -> "05")
        self.hour_input.editingFinished.connect(self._format_hour_on_finish)
        self.minute_input.editingFinished.connect(self._format_minute_on_finish)

        # Áp dụng chế độ 12h hay 24h
        self.set_format_24h(self.is_24h)

    def set_format_24h(self, is_24h: bool):
        """Cấu hình lại chế độ 12h hoặc 24h"""
        self.is_24h = is_24h
        
        if self.is_24h:
            self.ampm_combo.hide()
            self.hour_input.setFixedSize(136, 40)
            self.minute_input.setFixedSize(136, 40)
        else:
            self.ampm_combo.show()
            self.hour_input.setFixedSize(90, 40)
            self.minute_input.setFixedSize(90, 40)
            self.ampm_combo.setFixedSize(84, 40)
        
        self._format_hour_on_finish()

    def set_time(self, qtime: QTime):
        """Đặt thời gian cho Picker từ QTime"""
        h = qtime.hour()
        m = qtime.minute()

        if not self.is_24h:
            if h >= 12:
                self.ampm_combo.setCurrentText("PM")
                h = h - 12 if h > 12 else 12
            else:
                self.ampm_combo.setCurrentText("AM")
                h = 12 if h == 0 else h

        self.hour_input.setText(f"{h:02d}")
        self.minute_input.setText(f"{m:02d}")

    # --- XỬ LÝ KHỐNG CHẾ TRONG LÚC ĐANG GÕ (REAL-TIME) ---
    def _on_hour_changed(self, text):
        if not text:
            return
        
        # Nếu nhập ký tự không phải số -> xóa ngay
        if not text.isdigit():
            self.hour_input.setText("".join(filter(str.isdigit, text)))
            return

        val = int(text)
        max_val = 23 if self.is_24h else 12

        # Nếu giá trị lớn hơn max_val -> gán lại bằng max_val ngay lập tức
        if val > max_val:
            self.hour_input.setText(str(max_val))

    def _on_minute_changed(self, text):
        if not text:
            return

        if not text.isdigit():
            self.minute_input.setText("".join(filter(str.isdigit, text)))
            return

        val = int(text)
        # Phút chỉ từ 0 đến 59
        if val > 59:
            self.minute_input.setText("59")

    # --- XỬ LÝ FORMAT KHI RỜI Ô INPUT (BLUR / ENTER) ---
    def _format_hour_on_finish(self):
        text = self.hour_input.text().strip()
        min_val = 1 if not self.is_24h else 0
        max_val = 12 if not self.is_24h else 23

        if not text.isdigit():
            self.hour_input.setText(f"{min_val:02d}")
            return

        val = int(text)
        if val < min_val:
            val = min_val
        elif val > max_val:
            val = max_val

        self.hour_input.setText(f"{val:02d}")

    def _format_minute_on_finish(self):
        text = self.minute_input.text().strip()
        if not text.isdigit():
            self.minute_input.setText("00")
            return

        val = int(text)
        if val < 0 or val > 59:
            val = 0

        self.minute_input.setText(f"{val:02d}")

    def get_time_string(self) -> str:
        """Trả về thời gian dạng chuẩn HH:mm 24h để lưu Database/Báo thức"""
        h_text = self.hour_input.text().strip()
        m_text = self.minute_input.text().strip()

        h = int(h_text) if h_text.isdigit() else (1 if not self.is_24h else 0)
        m = int(m_text) if m_text.isdigit() else 0

        if not self.is_24h:
            ampm = self.ampm_combo.currentText()
            if ampm == "PM" and h < 12:
                h += 12
            elif ampm == "AM" and h == 12:
                h = 0

        return f"{h:02d}:{m:02d}"
# ==============================================================================
# 1. TAB WORLD CLOCK
# ==============================================================================
class MiniAnalogClock(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(90, 90)
        self.time = QTime.currentTime()
        self.is_dark = False
        self.show_seconds = True

    def set_time(self, qtime, show_seconds, is_dark):
        self.time = qtime
        self.show_seconds = show_seconds
        self.is_dark = is_dark
        self.update()

    def paintEvent(self, event):
        side = min(self.width(), self.height())
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(side / 100.0, side / 100.0)

        face_bg = QColor("#2C2C2C") if self.is_dark else QColor("#FFFFFF")
        border_color = QColor("#454545") if self.is_dark else QColor("#D0D0D0")
        hour_color = QColor("#FFFFFF") if self.is_dark else QColor("#1A1A1A")
        min_color = QColor("#CCCCCC") if self.is_dark else QColor("#4D4D4D")
        sec_color = QColor("#009FAA")
        ticks_color = QColor("#888888")

        painter.setPen(QPen(border_color, 1.5))
        painter.setBrush(QBrush(face_bg))
        painter.drawEllipse(-46, -46, 92, 92)

        for i in range(12):
            painter.setPen(QPen(ticks_color, 1.2))
            painter.drawLine(0, -42, 0, -37)
            painter.rotate(30.0)

        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(hour_color))
        painter.rotate(30.0 * (self.time.hour() + self.time.minute() / 60.0))
        painter.drawConvexPolygon([QPointF(-2, 0), QPointF(0, -25), QPointF(2, 0), QPointF(0, 5)])
        painter.restore()

        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(min_color))
        painter.rotate(6.0 * (self.time.minute() + self.time.second() / 60.0))
        painter.drawConvexPolygon([QPointF(-1.5, 0), QPointF(0, -35), QPointF(1.5, 0), QPointF(0, 6)])
        painter.restore()

        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(sec_color))
        painter.rotate(6.0 * self.time.second())
        painter.drawConvexPolygon([QPointF(-1, 0), QPointF(0, -38), QPointF(1, 0), QPointF(0, 8)])
        painter.drawEllipse(-2, -2, 4, 4)
        painter.restore()


class TimeZoneGridItem(QFrame):
    def __init__(self, tz_id, country_name, parent_widget):
        super().__init__()
        self.tz_id = tz_id
        self.country_name = country_name
        self.parent_widget = parent_widget
        self.setObjectName("TimeZoneGridItem")
        self.setMaximumWidth(360)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 16, 10)
        main_layout.setSpacing(12)

        self.analog_clock = MiniAnalogClock(self)
        main_layout.addWidget(self.analog_clock, 0, Qt.AlignmentFlag.AlignVCenter)

        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.country_lbl = QLabel(country_name)
        font = self.country_lbl.font()
        font.setPixelSize(15)
        font.setBold(True)
        self.country_lbl.setFont(font)

        self.tz_lbl = CaptionLabel(tz_id.replace("_", " "))
        
        self.digital_lbl = TitleLabel("00:00:00")
        digital_font = self.digital_lbl.font()
        digital_font.setPixelSize(22)
        digital_font.setBold(True)
        self.digital_lbl.setFont(digital_font)

        info_layout.addWidget(self.country_lbl)
        info_layout.addWidget(self.tz_lbl)
        info_layout.addWidget(self.digital_lbl)

        main_layout.addLayout(info_layout, stretch=1)

    def update_time(self, is_24h, show_seconds, is_dark):
        now = QDateTime.currentDateTime().toTimeZone(QTimeZone(self.tz_id.encode('utf-8')))
        self.analog_clock.set_time(now.time(), show_seconds, is_dark)

        if show_seconds:
            fmt = "hh:mm:ss" if is_24h else "hh:mm:ss AP"
        else:
            fmt = "hh:mm" if is_24h else "hh:mm AP"
            
        self.digital_lbl.setText(now.toString(fmt))

        text_color = "white" if is_dark else "black"
        border_color = "rgba(255,255,255,0.15)" if is_dark else "rgba(0,0,0,0.1)"
        bg_color = "rgba(255,255,255,0.04)" if is_dark else "rgba(0,0,0,0.02)"

        self.setStyleSheet(f"""
            #TimeZoneGridItem {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
        """)
        self.country_lbl.setStyleSheet(f"color: {text_color};")
        self.digital_lbl.setStyleSheet(f"color: {text_color};")


class WorldClockWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("worldClockWidget")
        self.settings = QSettings("UbuntuClock", "WorldClockSettings")

        self.all_cities = [
            ("Asia/Ho_Chi_Minh", "Việt Nam (Hà Nội)"),
            ("Asia/Tokyo", "Nhật Bản (Tokyo)"),
            ("Asia/Seoul", "Hàn Quốc (Seoul)"),
            ("Europe/London", "Anh (London)"),
            ("Europe/Paris", "Pháp (Paris)"),
            ("America/New_York", "Mỹ (New York)"),
            ("America/Los_Angeles", "Mỹ (Los Angeles)"),
            ("Australia/Sydney", "Úc (Sydney)"),
        ]

        self.is_24h_format = self.settings.value("is_24h_format", True, type=bool)
        self.show_seconds = self.settings.value("show_seconds", True, type=bool)
        
        saved_tzs = self.settings.value("enabled_tzs")
        if saved_tzs and isinstance(saved_tzs, list):
            self.enabled_tzs = saved_tzs
        else:
            self.enabled_tzs = [c[0] for c in self.all_cities]

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)

        self.top_bar = QHBoxLayout()
        
        self.format_switch = SwitchButton(self)
        self.format_switch.setOnText("24 Giờ")
        self.format_switch.setOffText("12 Giờ")
        self.format_switch.setChecked(self.is_24h_format)
        self.format_switch.checkedChanged.connect(self.toggle_format)

        self.sec_switch = SwitchButton(self)
        self.sec_switch.setOnText("Hiện giây")
        self.sec_switch.setOffText("Ẩn giây")
        self.sec_switch.setChecked(self.show_seconds)
        self.sec_switch.checkedChanged.connect(self.toggle_seconds)

        self.config_btn = PushButton("Cài đặt múi giờ", self, FIF.SETTING)
        self.config_btn.clicked.connect(self.toggle_settings_panel)

        self.top_bar.addWidget(QLabel("Định dạng:"))
        self.top_bar.addWidget(self.format_switch)
        self.top_bar.addSpacing(15)
        self.top_bar.addWidget(self.sec_switch)
        self.top_bar.addStretch(1)
        self.top_bar.addWidget(self.config_btn)

        self.main_layout.addLayout(self.top_bar)

        self.content_stack = QStackedWidget(self)

        self.grid_scroll = SmoothScrollArea(self)
        self.grid_scroll.setWidgetResizable(True)
        self.grid_scroll_content = QWidget()
        self.grid_layout = QGridLayout(self.grid_scroll_content)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.grid_layout.setSpacing(12)
        self.grid_scroll.setWidget(self.grid_scroll_content)

        self.settings_scroll = SmoothScrollArea(self)
        self.settings_scroll.setWidgetResizable(True)
        self.settings_content = QWidget()
        self.settings_layout = QVBoxLayout(self.settings_content)
        self.settings_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.settings_layout.setSpacing(10)
        
        self.settings_title = SubtitleLabel("Chọn các múi giờ muốn hiển thị:")
        self.settings_layout.addWidget(self.settings_title)
        
        self.checkboxes = {}
        for tz_id, country in self.all_cities:
            cb = CheckBox(f"{country} ({tz_id})")
            cb.setChecked(tz_id in self.enabled_tzs)
            cb.stateChanged.connect(self.save_tz_selection)
            self.settings_layout.addWidget(cb)
            self.checkboxes[tz_id] = cb

        self.back_btn = PrimaryPushButton("Xong", self)
        self.back_btn.clicked.connect(self.toggle_settings_panel)
        self.settings_layout.addSpacing(10)
        self.settings_layout.addWidget(self.back_btn)

        self.settings_scroll.setWidget(self.settings_content)

        self.content_stack.addWidget(self.grid_scroll)
        self.content_stack.addWidget(self.settings_scroll)

        self.main_layout.addWidget(self.content_stack)

        self.card_widgets = {}
        self.rebuild_grid()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_clocks)
        self.timer.start(1000)

    def save_tz_selection(self):
        self.enabled_tzs = [tz_id for tz_id, cb in self.checkboxes.items() if cb.isChecked()]
        self.settings.setValue("enabled_tzs", self.enabled_tzs)
        self.rebuild_grid()

    def toggle_settings_panel(self):
        if self.content_stack.currentIndex() == 0:
            self.content_stack.setCurrentIndex(1)
            self.config_btn.setText("Quay lại")
        else:
            self.content_stack.setCurrentIndex(0)
            self.config_btn.setText("Cài đặt múi giờ")

    def toggle_format(self, checked):
        self.is_24h_format = checked
        self.settings.setValue("is_24h_format", self.is_24h_format)
        self.update_clocks()

    def toggle_seconds(self, checked):
        self.show_seconds = checked
        self.settings.setValue("show_seconds", self.show_seconds)
        self.update_clocks()

    def rebuild_grid(self):
        for i in reversed(range(self.grid_layout.count())): 
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)
        self.card_widgets.clear()

        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        available_width = self.grid_scroll.width() if self.grid_scroll.width() > 0 else 600
        max_cols = max(1, available_width // 320) 

        row = 0
        col = 0
        for tz_id, country in self.all_cities:
            if tz_id in self.enabled_tzs:
                card = TimeZoneGridItem(tz_id, country, self)
                self.grid_layout.addWidget(card, row, col)
                self.card_widgets[tz_id] = card
                
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1
                    
        self.update_clocks()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'resize_timer'):
            self.resize_timer.stop()
        else:
            self.resize_timer = QTimer(self)
            self.resize_timer.setSingleShot(True)
            self.resize_timer.timeout.connect(self.rebuild_grid)
        self.resize_timer.start(100)

    def update_clocks(self):
        is_dark = (self.window().current_theme == Theme.DARK) if self.window() else False
        self.grid_scroll.setStyleSheet(f"QScrollArea, QScrollArea * {{ background: transparent; }} QScrollArea {{ border: none; }}")
        self.settings_scroll.setStyleSheet(f"QScrollArea, QScrollArea * {{ background: transparent; }} QScrollArea {{ border: none; }}")

        for card in self.card_widgets.values():
            card.update_time(self.is_24h_format, self.show_seconds, is_dark)


# ==============================================================================
# 2. TAB ALARM (HẸN GIỜ MỚI)
# ==============================================================================
class AlarmGridItem(QFrame):
    def __init__(self, time_str, label_text, is_enabled, alarm_id, parent_widget):
        super().__init__()
        self.alarm_id = alarm_id
        self.time_str = time_str
        self.label_text = label_text
        self.is_enabled = is_enabled
        self.parent_widget = parent_widget
        self.setObjectName("AlarmGridItem")
        self.setMaximumWidth(360)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(12)

        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        self.time_lbl = TitleLabel(time_str)
        t_font = self.time_lbl.font()
        t_font.setPixelSize(28)
        t_font.setBold(True)
        self.time_lbl.setFont(t_font)

        self.tag_lbl = CaptionLabel(label_text if label_text else "Báo thức")

        info_layout.addWidget(self.time_lbl)
        info_layout.addWidget(self.tag_lbl)

        main_layout.addLayout(info_layout, stretch=1)

        self.switch_btn = SwitchButton(self)
        self.switch_btn.setChecked(is_enabled)
        self.switch_btn.checkedChanged.connect(self.on_switch_toggled)

        self.del_btn = ToolButton(FIF.DELETE, self)
        self.del_btn.clicked.connect(lambda: self.parent_widget.delete_alarm(self.alarm_id))

        main_layout.addWidget(self.switch_btn)
        main_layout.addWidget(self.del_btn)

    def on_switch_toggled(self, checked):
        self.is_enabled = checked
        self.parent_widget.toggle_alarm_state(self.alarm_id, checked)

    def update_theme(self, is_dark):
        text_color = "white" if is_dark else "black"
        border_color = "rgba(255,255,255,0.15)" if is_dark else "rgba(0,0,0,0.1)"
        bg_color = "rgba(255,255,255,0.04)" if is_dark else "rgba(0,0,0,0.02)"

        self.setStyleSheet(f"""
            #AlarmGridItem {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
        """)
        self.time_lbl.setStyleSheet(f"color: {text_color}; opacity: {1.0 if self.is_enabled else 0.4};")
        self.tag_lbl.setStyleSheet(f"color: {text_color}; opacity: {0.7 if self.is_enabled else 0.3};")


class AlarmWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("alarmWidget")
        self.settings = QSettings("UbuntuClock", "AlarmSettings")
        self.world_settings = QSettings("UbuntuClock", "WorldClockSettings") # Đọc chung cấu hình 12h/24h
        self.alarms = []
        self.current_infobar = None

        self.alarm_sound = QSoundEffect(self)
        sound_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ring.wav")
        if os.path.exists(sound_path):
            self.alarm_sound.setSource(QUrl.fromLocalFile(sound_path))
            self.alarm_sound.setVolume(0.8)
            self.alarm_sound.setLoopCount(-2)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)

        top_bar = QHBoxLayout()
        self.add_btn = PrimaryPushButton("Thêm báo thức", self, FIF.ADD)
        self.add_btn.clicked.connect(self.show_add_panel)
        top_bar.addStretch(1)
        top_bar.addWidget(self.add_btn)
        self.main_layout.addLayout(top_bar)

        self.content_stack = QStackedWidget(self)

        # PAGE 1: Lưới danh sách
        self.grid_scroll = SmoothScrollArea(self)
        self.grid_scroll.setWidgetResizable(True)
        self.grid_scroll_content = QWidget()
        self.grid_layout = QGridLayout(self.grid_scroll_content)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.grid_layout.setSpacing(12)
        self.grid_scroll.setWidget(self.grid_scroll_content)

        # PAGE 2: Form Thêm báo thức mới
        self.add_panel = QWidget()
        add_layout = QVBoxLayout(self.add_panel)
        add_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        add_layout.setSpacing(15)

        # Đọc định dạng 12h/24h trực tiếp từ Cài đặt
        is_24h_config = self.world_settings.value("is_24h_format", True, type=bool)
        
        self.time_picker = CustomTimePicker(is_24h_format=is_24h_config, parent=self)
        self.time_picker.setFixedSize(280, 40)

        self.label_input = LineEdit(self)
        self.label_input.setPlaceholderText("Ghi chú báo thức (Ví dụ: Thức dậy, Học bài...)")
        self.label_input.setFixedSize(280, 40)

        btn_row = QHBoxLayout()
        self.save_btn = PrimaryPushButton("Lưu", self)
        self.cancel_btn = PushButton("Hủy", self)
        self.save_btn.clicked.connect(self.save_new_alarm)
        self.cancel_btn.clicked.connect(self.hide_add_panel)
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.cancel_btn)

        add_layout.addWidget(SubtitleLabel("Chọn thời gian hẹn giờ:"))
        add_layout.addWidget(self.time_picker)
        add_layout.addWidget(self.label_input)
        add_layout.addLayout(btn_row)

        self.content_stack.addWidget(self.grid_scroll)
        self.content_stack.addWidget(self.add_panel)

        self.main_layout.addWidget(self.content_stack)

        self.card_widgets = []
        self.load_alarms()

        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self.check_alarms)
        self.check_timer.start(1000)

    def show_add_panel(self):
        # Cập nhật định dạng 12h/24h mới nhất mỗi khi mở form
        is_24h_config = self.world_settings.value("is_24h_format", True, type=bool)
        self.time_picker.set_format_24h(is_24h_config)
        self.time_picker.set_time(QTime.currentTime())
        
        self.content_stack.setCurrentIndex(1)
        self.add_btn.setVisible(False)

    def hide_add_panel(self):
        self.content_stack.setCurrentIndex(0)
        self.add_btn.setVisible(True)

    def save_new_alarm(self):
        # Đã sửa: Lấy chuỗi thời gian HH:mm 24h chuẩn từ time_picker
        time_str = self.time_picker.get_time_string()
        label_text = self.label_input.text().strip()
        alarm_id = str(QDateTime.currentMSecsSinceEpoch())

        new_alarm = {
            "id": alarm_id,
            "time": time_str,
            "label": label_text,
            "enabled": True
        }
        self.alarms.append(new_alarm)
        self.save_alarms_to_settings()
        self.rebuild_grid()
        self.hide_add_panel()

    def toggle_alarm_state(self, alarm_id, enabled):
        for alarm in self.alarms:
            if alarm["id"] == alarm_id:
                alarm["enabled"] = enabled
                break
        self.save_alarms_to_settings()
        self.update_theme()

    def delete_alarm(self, alarm_id):
        self.alarms = [a for a in self.alarms if a["id"] != alarm_id]
        self.save_alarms_to_settings()
        self.rebuild_grid()

    def load_alarms(self):
        saved = self.settings.value("alarm_list")
        if saved and isinstance(saved, list):
            self.alarms = saved
        self.rebuild_grid()

    def save_alarms_to_settings(self):
        self.settings.setValue("alarm_list", self.alarms)

    def stop_alarm_sound(self):
        if self.alarm_sound.isPlaying():
            self.alarm_sound.stop()
        if self.current_infobar:
            self.current_infobar.close()
            self.current_infobar = None

    def check_alarms(self):
        now_str = QTime.currentTime().toString("hh:mm")
        sec = QTime.currentTime().second()

        if sec == 0:
            for alarm in self.alarms:
                if alarm["enabled"] and alarm["time"] == now_str:
                    if self.alarm_sound.source().isValid():
                        self.alarm_sound.play()

                    self.current_infobar = InfoBar.success(
                        title='BÁO THỨC!',
                        content=f"Đã đến giờ: {alarm['time']} ({alarm['label']})",
                        orient=Qt.Orientation.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=0,
                        parent=self
                    )
                    self.current_infobar.closedSignal.connect(self.stop_alarm_sound)

    def rebuild_grid(self):
        for i in reversed(range(self.grid_layout.count())): 
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)
        self.card_widgets.clear()

        available_width = self.grid_scroll.width() if self.grid_scroll.width() > 0 else 600
        max_cols = max(1, available_width // 320)

        row = 0
        col = 0
        for alarm in self.alarms:
            card = AlarmGridItem(alarm["time"], alarm["label"], alarm["enabled"], alarm["id"], self)
            self.grid_layout.addWidget(card, row, col)
            self.card_widgets.append(card)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        self.update_theme()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'resize_timer'):
            self.resize_timer.stop()
        else:
            self.resize_timer = QTimer(self)
            self.resize_timer.setSingleShot(True)
            self.resize_timer.timeout.connect(self.rebuild_grid)
        self.resize_timer.start(100)

    def update_theme(self):
        is_dark = (self.window().current_theme == Theme.DARK) if self.window() else False
        self.grid_scroll.setStyleSheet(f"QScrollArea, QScrollArea * {{ background: transparent; }} QScrollArea {{ border: none; }}")
        for card in self.card_widgets:
            card.update_theme(is_dark)


# ==============================================================================
# 3. TAB TIMER & STOPWATCH
# ==============================================================================
class FocusableLineEdit(LineEdit):
    def focusOutEvent(self, e):
        super().focusOutEvent(e)
        self.clearFocus()

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

    def update_theme(self, text_color, border_color):
        self.setStyleSheet(f"#SavedTimerItem {{ border: 1px solid {border_color}; border-radius: 6px; }}")
        self.time_lbl.setStyleSheet(f"color: {text_color};")

class TimerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("timerWidget")
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.current_infobar = None
        
        self.settings = QSettings("UbuntuClock", "TimerSettings")
        self.saved_timers_list = []

        self.alarm_sound = QSoundEffect(self)
        sound_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ring.wav")
        if os.path.exists(sound_path):
            self.alarm_sound.setSource(QUrl.fromLocalFile(sound_path))
            self.alarm_sound.setVolume(0.8)
            self.alarm_sound.setLoopCount(-2)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.time_input = FocusableLineEdit(self)
        self.time_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_input.setInputMask("00:00:00")
        self.time_input.setText("000000") 
        font = self.time_input.font()
        font.setPixelSize(70)
        font.setBold(True)
        self.time_input.setFont(font)
        self.time_input.setFixedHeight(100) 
        self.time_input.setMinimumWidth(350)
        
        self.left_layout.addWidget(self.time_input)
        self.left_layout.addSpacing(30)

        self.btn_layout = QHBoxLayout()
        self.btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.start_btn = PrimaryPushButton("Bắt đầu", self)
        self.stop_btn = PushButton("Tạm dừng", self)
        self.reset_btn = PushButton("Đặt lại", self)
        self.stop_btn.setEnabled(False) 
        
        self.btn_layout.addWidget(self.start_btn)
        self.btn_layout.addWidget(self.stop_btn)
        self.btn_layout.addWidget(self.reset_btn)
        self.left_layout.addLayout(self.btn_layout)

        self.main_layout.addWidget(self.left_panel, stretch=1)

        self.scroll_area = SmoothScrollArea(self)
        self.scroll_area.setFixedWidth(200)
        self.scroll_area.setWidgetResizable(True)
        
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_layout.setContentsMargins(10, 10, 10, 10)
        self.scroll_layout.setSpacing(10)
        

        self.scroll_area.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll_area)

        self.start_btn.clicked.connect(self.action_start)
        self.stop_btn.clicked.connect(self.action_pause)
        self.reset_btn.clicked.connect(self.action_reset)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.remaining_seconds = 0
        self.is_paused = False

        self.load_settings()
        self.update_theme(False)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.time_input.clearFocus()

    def stop_alarm(self):
        if self.alarm_sound.isPlaying():
            self.alarm_sound.stop()
        if self.current_infobar:
            self.current_infobar.close()
            self.current_infobar = None

    def check_empty_state(self):
        has_items = len(self.saved_timers_list) > 0


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
        self.check_empty_state()

    def save_settings(self):
        self.settings.setValue("saved_timers", self.saved_timers_list)

    def add_saved_timer_ui(self, seconds):
        item = SavedTimerItem(seconds, self)
        self.scroll_layout.addWidget(item)
        is_dark = (self.window().current_theme == Theme.DARK) if self.window() else False
        text_color = "white" if is_dark else "black"
        item_border = "rgba(255, 255, 255, 0.15)" if is_dark else "rgba(0, 0, 0, 0.15)"
        item.update_theme(text_color, item_border)
        self.check_empty_state()

    def delete_saved_timer(self, item_widget, seconds):
        if seconds in self.saved_timers_list:
            self.saved_timers_list.remove(seconds)
            self.save_settings()
        item_widget.deleteLater()
        QTimer.singleShot(50, self.check_empty_state)

    def start_timer_from_saved(self, seconds):
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        self.time_input.setText(f"{h:02d}{m:02d}{s:02d}")
        self.action_start(force_new=True)

    def action_start(self, force_new=False):
        self.stop_alarm()
        if not self.timer.isActive() and not self.is_paused or force_new:
            text = self.time_input.text() 
            parts = text.split(':')
            try:
                secs = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            except:
                secs = 0
                
            if secs == 0:
                InfoBar.warning("Lỗi", "Vui lòng nhập thời gian lớn hơn 0.", parent=self, duration=2000)
                return

            self.remaining_seconds = secs
            if secs not in self.saved_timers_list:
                self.saved_timers_list.append(secs)
                self.add_saved_timer_ui(secs)
                self.save_settings()

        self.time_input.setReadOnly(True) 
        self.timer.start(1000)
        self.is_paused = False
        self.start_btn.setText("Tiếp tục")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def action_pause(self):
        self.stop_alarm()
        self.timer.stop()
        self.is_paused = True
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def action_reset(self):
        self.stop_alarm()
        self.timer.stop()
        self.is_paused = False
        self.remaining_seconds = 0
        self.time_input.setReadOnly(False)
        self.time_input.setText("000000")
        self.start_btn.setText("Bắt đầu")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def update_timer(self):
        self.remaining_seconds -= 1
        self.update_display_text()

        if self.remaining_seconds <= 0:
            self.action_reset()
            if self.alarm_sound.source().isValid():
                self.alarm_sound.play()

            self.current_infobar = InfoBar.success(
                title='Hết giờ',
                content="Thời gian đếm ngược đã kết thúc!",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=0,
                parent=self
            )
            self.current_infobar.closedSignal.connect(self.stop_alarm)

    def update_display_text(self):
        h = self.remaining_seconds // 3600
        m = (self.remaining_seconds % 3600) // 60
        s = self.remaining_seconds % 60
        self.time_input.setText(f"{h:02d}{m:02d}{s:02d}")

    def update_theme(self, is_dark):
        text_color = "white" if is_dark else "black"
        bg_color = "#202020" if is_dark else "#F3F3F3" 
        hover_bg = "#2A2A2A" if is_dark else "#EBEBEB" 
        border_color = "rgba(255, 255, 255, 0.2)" if is_dark else "rgba(0, 0, 0, 0.1)"
        item_border = "rgba(255, 255, 255, 0.15)" if is_dark else "rgba(0, 0, 0, 0.15)"
        
        self.time_input.setStyleSheet(f"""
            LineEdit {{ color: {text_color}; background-color: {bg_color}; border: none; selection-background-color: #009faa; selection-color: white; }}
            LineEdit:hover {{ background-color: {hover_bg}; border: none; border-radius: 12px; }}
            LineEdit:focus {{ background-color: {bg_color}; border: none; }}
        """)
        
        self.scroll_area.setStyleSheet(f"QScrollArea, QScrollArea * {{ background: transparent; }} QScrollArea {{ border: 1px solid {border_color}; border-radius: 8px; }}")
        
        for i in range(self.scroll_layout.count()):
            widget = self.scroll_layout.itemAt(i).widget()
            if isinstance(widget, SavedTimerItem):
                widget.update_theme(text_color, item_border)

class LapItem(QFrame):
    def __init__(self, lap_num, time_str, parent=None):
        super().__init__(parent)
        self.setObjectName("LapItem")
        hbox = QHBoxLayout(self)
        hbox.setContentsMargins(10, 8, 10, 8)
        
        self.icon_btn = ToolButton(FIF.HISTORY, self)
        self.icon_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.icon_btn.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        self.lap_lbl = CaptionLabel(f"Lap {lap_num}", self)
        self.time_lbl = QLabel(time_str, self)
        font = self.time_lbl.font()
        font.setPixelSize(14)
        font.setBold(True)
        self.time_lbl.setFont(font)

        hbox.addWidget(self.icon_btn)
        hbox.addWidget(self.lap_lbl)
        hbox.addStretch(1)
        hbox.addWidget(self.time_lbl)

    def update_theme(self, text_color, border_color):
        self.setStyleSheet(f"#LapItem {{ border: 1px solid {border_color}; border-radius: 6px; background-color: transparent; }}")
        self.lap_lbl.setStyleSheet(f"color: {text_color}; opacity: 0.7;")
        self.time_lbl.setStyleSheet(f"color: {text_color};")

class StopwatchWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("stopwatchWidget")
        self.lap_count = 0

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.time_display = LargeTitleLabel("00:00:00.00", self)
        self.time_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.left_layout.addWidget(self.time_display)
        self.left_layout.addSpacing(20)

        self.btn_layout = QHBoxLayout()
        self.btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.start_btn = PrimaryPushButton("Bắt đầu", self)
        self.lap_btn = PushButton("Đánh dấu", self)
        self.reset_btn = PushButton("Đặt lại", self)
        self.lap_btn.setEnabled(False)
        
        self.btn_layout.addWidget(self.start_btn)
        self.btn_layout.addWidget(self.lap_btn)
        self.btn_layout.addWidget(self.reset_btn)
        self.left_layout.addLayout(self.btn_layout)

        self.main_layout.addWidget(self.left_panel, stretch=1)

        self.scroll_area = SmoothScrollArea(self)
        self.scroll_area.setFixedWidth(220)
        self.scroll_area.setWidgetResizable(True)
        
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_layout.setContentsMargins(10, 10, 10, 10)
        self.scroll_layout.setSpacing(8)

        self.scroll_area.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll_area)

        self.start_btn.clicked.connect(self.start_stopwatch)
        self.lap_btn.clicked.connect(self.record_lap)
        self.reset_btn.clicked.connect(self.reset_stopwatch)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_display)
        self.elapsed_time = 0
        self.is_running = False
        self.update_theme(False)

    def start_stopwatch(self):
        if not self.is_running:
            self.timer.start(10)
            self.start_btn.setText("Tạm dừng")
            self.lap_btn.setEnabled(True)
            self.is_running = True
        else:
            self.timer.stop()
            self.start_btn.setText("Tiếp tục")
            self.lap_btn.setEnabled(False)
            self.is_running = False

    def record_lap(self):
        if not self.is_running:
            return
            
        self.lap_count += 1
        time_str = self.time_display.text()
        
        
        item = LapItem(self.lap_count, time_str, self)
        self.scroll_layout.insertWidget(0, item)
        
        is_dark = (self.window().current_theme == Theme.DARK) if self.window() else False
        text_color = "white" if is_dark else "black"
        border_color = "rgba(255, 255, 255, 0.15)" if is_dark else "rgba(0, 0, 0, 0.15)"
        item.update_theme(text_color, border_color)

    def reset_stopwatch(self):
        self.timer.stop()
        self.is_running = False
        self.elapsed_time = 0
        self.lap_count = 0
        
        self.start_btn.setText("Bắt đầu")
        self.time_display.setText("00:00:00.00")
        self.lap_btn.setEnabled(False)

        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if isinstance(widget, LapItem):
                widget.deleteLater()

    def update_display(self):
        self.elapsed_time += 1
        cs = self.elapsed_time % 100
        s = (self.elapsed_time // 100) % 60
        m = (self.elapsed_time // 6000) % 60
        h = (self.elapsed_time // 360000)
        self.time_display.setText(f"{h:02d}:{m:02d}:{s:02d}.{cs:02d}")

    def update_theme(self, is_dark):
        text_color = "white" if is_dark else "black"
        border_color = "rgba(255, 255, 255, 0.2)" if is_dark else "rgba(0, 0, 0, 0.1)"
        item_border = "rgba(255, 255, 255, 0.15)" if is_dark else "rgba(0, 0, 0, 0.15)"

        self.scroll_area.setStyleSheet(f"QScrollArea, QScrollArea * {{ background: transparent; }} QScrollArea {{ border: 1px solid {border_color}; border-radius: 8px; }}")

        for i in range(self.scroll_layout.count()):
            widget = self.scroll_layout.itemAt(i).widget()
            if isinstance(widget, LapItem):
                widget.update_theme(text_color, item_border)


# ==============================================================================
# 4. TAB SETTINGS (HỆ THỐNG MỚI)
# ==============================================================================
class SettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsWidget")
        self.settings = QSettings("UbuntuClock", "AppSettings")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = TitleLabel("Cài đặt hệ thống", self)
        layout.addWidget(title)

        # Card 1: Khởi động cùng PC
        autostart_card = CardWidget(self)
        a_layout = QHBoxLayout(autostart_card)
        a_layout.setContentsMargins(16, 16, 16, 16)
        
        a_info = QVBoxLayout()
        a_info.addWidget(SubtitleLabel("Khởi động cùng máy tính"))
        a_info.addWidget(CaptionLabel("Tự động chạy ứng dụng Ubuntu Clock khi đăng nhập PC (Windows/macOS/Linux)"))
        
        self.autostart_switch = SwitchButton(self)
        is_autostart = self.settings.value("autostart", False, type=bool)
        self.autostart_switch.setChecked(is_autostart)
        self.autostart_switch.checkedChanged.connect(self.toggle_autostart)

        a_layout.addLayout(a_info, stretch=1)
        a_layout.addWidget(self.autostart_switch)
        layout.addWidget(autostart_card)

        # Card 2: Chạy ngầm khi bấm X
        tray_card = CardWidget(self)
        t_layout = QHBoxLayout(tray_card)
        t_layout.setContentsMargins(16, 16, 16, 16)

        t_info = QVBoxLayout()
        t_info.addWidget(SubtitleLabel("Chạy ngầm ở khay hệ thống"))
        t_info.addWidget(CaptionLabel("Khi bật: Bấm nút 'X' sẽ thu nhỏ app xuống Tray bar. Khi tắt: Bấm nút 'X' sẽ thoát hẳn."))

        self.tray_switch = SwitchButton(self)
        is_minimize_tray = self.settings.value("minimize_to_tray", True, type=bool)
        self.tray_switch.setChecked(is_minimize_tray)
        self.tray_switch.checkedChanged.connect(self.toggle_tray_behavior)

        t_layout.addLayout(t_info, stretch=1)
        t_layout.addWidget(self.tray_switch)
        layout.addWidget(tray_card)

    def toggle_tray_behavior(self, checked):
        self.settings.setValue("minimize_to_tray", checked)

    def toggle_autostart(self, checked):
        self.settings.setValue("autostart", checked)
        system_name = platform.system()

        try:
            if system_name == "Windows":
                import winreg
                key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
                app_path = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
                if checked:
                    winreg.SetValueEx(key, "UbuntuClock", 0, winreg.REG_SZ, app_path)
                else:
                    try:
                        winreg.DeleteValue(key, "UbuntuClock")
                    except FileNotFoundError:
                        pass
                winreg.CloseKey(key)

            elif system_name == "Linux":
                autostart_dir = os.path.expanduser("~/.config/autostart")
                os.makedirs(autostart_dir, exist_ok=True)
                desktop_file = os.path.join(autostart_dir, "ubuntu_clock.desktop")
                
                if checked:
                    exec_cmd = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
                    content = f"[Desktop Entry]\nType=Application\nName=Ubuntu Clock\nExec={exec_cmd}\nHidden=false\nNoDisplay=false\nX-GNOME-Autostart-enabled=true\n"
                    with open(desktop_file, "w") as f:
                        f.write(content)
                else:
                    if os.path.exists(desktop_file):
                        os.remove(desktop_file)

            elif system_name == "Darwin": # macOS
                plist_dir = os.path.expanduser("~/Library/LaunchAgents")
                os.makedirs(plist_dir, exist_ok=True)
                plist_file = os.path.join(plist_dir, "com.ubuntu.clock.plist")

                if checked:
                    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key> <string>com.ubuntu.clock</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{os.path.abspath(sys.argv[0])}</string>
    </array>
    <key>RunAtLoad</key> <true/>
</dict>
</plist>"""
                    with open(plist_file, "w") as f:
                        f.write(content)
                else:
                    if os.path.exists(plist_file):
                        os.remove(plist_file)

        except Exception as e:
            InfoBar.error("Lỗi", f"Không thể thiết lập khởi động cùng hệ thống: {str(e)}", parent=self)


# ==============================================================================
# 5. KHUNG CỬA SỔ CHÍNH (CLOCK APP)
# ==============================================================================
class ClockApp(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ubuntu Modern Clock")
        self.resize(750, 480)
        
        self.settings = QSettings("UbuntuClock", "AppSettings")
        self.navigationInterface.setAcrylicEnabled(False)

        saved_theme = self.settings.value("theme", "LIGHT")
        if saved_theme == "DARK":
            self.current_theme = Theme.DARK
        else:
            self.current_theme = Theme.LIGHT
            
        setTheme(self.current_theme)

        # Tạo các Tab
        self.world_clock = WorldClockWidget(self)
        self.alarm_widget = AlarmWidget(self) # Tab Báo Thức Mới
        self.timer_widget = TimerWidget(self)
        self.stopwatch = StopwatchWidget(self)
        self.settings_widget = SettingsWidget(self) # Tab Cài Đặt Mới

        # Tích hợp Navigation
        self.addSubInterface(self.world_clock, icon=FIF.GLOBE, text='World Clock')
        self.addSubInterface(self.alarm_widget, icon=FIF.HISTORY, text='Alarm')
        self.addSubInterface(self.timer_widget, icon=FIF.ALBUM, text='Timer')
        self.addSubInterface(self.stopwatch, icon=FIF.HISTORY, text='Stopwatch')
        self.addSubInterface(self.settings_widget, icon=FIF.SETTING, text='Settings', position=NavigationItemPosition.BOTTOM)

        # Nút đổi theme
        self.navigationInterface.addItem(
            routeKey='theme_toggle',
            icon=FIF.CONSTRACT,
            text='Đổi giao diện',
            onClick=self.toggle_theme,
            selectable=False,
            position=NavigationItemPosition.BOTTOM
        )

        base_dir = os.path.dirname(os.path.abspath(__file__))
        app_icon_path = os.path.join(base_dir, "assets", "icon.ico" if platform.system() == "Windows" else "icon.png")
        if os.path.exists(app_icon_path):
            self.setWindowIcon(QIcon(app_icon_path))

        self.setup_system_tray()
        
        is_dark = (self.current_theme == Theme.DARK)
        self.timer_widget.update_theme(is_dark)
        self.stopwatch.update_theme(is_dark)

    def toggle_theme(self):
        if self.current_theme == Theme.LIGHT:
            self.current_theme = Theme.DARK
            self.settings.setValue("theme", "DARK")
        else:
            self.current_theme = Theme.LIGHT
            self.settings.setValue("theme", "LIGHT")
        
        setTheme(self.current_theme)
        
        is_dark = (self.current_theme == Theme.DARK)
        if hasattr(self, 'timer_widget'):
            self.timer_widget.update_theme(is_dark)
        if hasattr(self, 'world_clock'):
            self.world_clock.update_clocks()
        if hasattr(self, 'stopwatch'):
            self.stopwatch.update_theme(is_dark)
        if hasattr(self, 'alarm_widget'):
            self.alarm_widget.update_theme()

    def setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        sys_name = platform.system()

        # Chọn file theo hệ điều hành: Windows dùng .ico, Linux/Mac dùng .png
        if sys_name == "Windows":
            icon_path = os.path.join(base_dir, "assets", "icon.ico")
        else:
            icon_path = os.path.join(base_dir, "assets", "icon.png")

        # Fallback phòng trường hợp file .ico hoặc .png bị thiếu
        if not os.path.exists(icon_path):
            icon_path = os.path.join(base_dir, "assets", "icon.png")

        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            # Nếu lỡ quên chép cả 2 file vào assets thì lấy icon mặc định của hệ thống
            self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))

        # Tạo menu khi click chuột phải vào khay
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
        # Đọc cấu hình xem có cho phép chạy ngầm khi bấm X không
        minimize_to_tray = self.settings.value("minimize_to_tray", True, type=bool)
        
        if minimize_to_tray:
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Đang chạy ngầm",
                "Ứng dụng vẫn đang chạy ngầm ở khay hệ thống.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
        else:
            event.accept()
            QApplication.instance().quit()


if __name__ == '__main__':
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    window = ClockApp()
    window.show()
    sys.exit(app.exec())
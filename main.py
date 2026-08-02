import sys
import os
import platform
import subprocess
import shutil
from PyQt6.QtCore import Qt, QTimer, QTime, QDateTime, QTimeZone, QPoint, QPointF, QUrl, QSettings
from PyQt6.QtGui import QIcon, QAction, QCloseEvent, QPainter, QColor, QPen, QBrush, QIntValidator, QPixmap
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QSystemTrayIcon, QMenu, QStackedWidget, QFrame, QLabel, QGridLayout, QSizePolicy)
from qfluentwidgets import (FluentWindow, LargeTitleLabel, PrimaryPushButton, 
                            PushButton, setTheme, Theme, CaptionLabel, ToolButton, SmoothScrollArea,
                            FluentIconBase, FluentIcon as FIF, InfoBar, InfoBarPosition, LineEdit,
                            NavigationItemPosition, SwitchButton, CheckBox, TitleLabel, SubtitleLabel,
                            ComboBox, CardWidget, isDarkTheme, ColorSettingCard, setThemeColor, ColorConfigItem, BodyLabel)
import tempfile

class CustomSVGIcon(FluentIconBase):
    def __init__(self, relative_path: str, size: int = 28, extra: int = 4):
        super().__init__()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.full_path = os.path.join(base_dir, relative_path)
        self.icon_size = size
        self.extra = extra   # số pixel phóng to thêm mỗi cạnh
        self._cache = {}

    def path(self, theme=Theme.AUTO) -> str:
        is_dark = (theme == Theme.DARK) or (theme == Theme.AUTO and isDarkTheme())
        key = "dark" if is_dark else "light"

        if key in self._cache and os.path.exists(self._cache[key]):
            return self._cache[key]

        with open(self.full_path, "r", encoding="utf-8") as f:
            svg_content = f.read()

        target_color = "#FFFFFF" if is_dark else "#1A1A1A"
        svg_content = svg_content.replace('stroke="#000000"', f'stroke="{target_color}"')
        svg_content = svg_content.replace('fill="#000000"', f'fill="{target_color}"')

        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".svg", delete=False, encoding="utf-8")
        tmp.write(svg_content)
        tmp.close()

        self._cache[key] = tmp.name
        return tmp.name

    def render(self, painter, rect, **kwargs):
        # Nới rect ra để icon to hơn khung mặc định của nav bar
        enlarged_rect = rect.adjusted(-self.extra, -self.extra, self.extra, self.extra)
        super().render(painter, enlarged_rect, **kwargs)
    
def send_linux_notification(title, content, app_name="DK Clock"):
    """Gửi thông báo Pop-up Banner chuẩn Linux/Ubuntu thông qua notify-send"""
    if platform.system() == "Linux":
        notify_path = shutil.which("notify-send")
        if notify_path:
            try:
                # Tham số -u critical giúp banner ưu tiên nổi lên màn hình và giữ lâu hơn
                subprocess.Popen([
                    notify_path,
                    "-u", "critical",          # Mức độ ưu tiên cao
                    "-a", app_name,            # Tên ứng dụng
                    "-i", "alarm-symbolic",    # Biểu tượng thông báo OS
                    title,
                    content
                ])
            except Exception as e:
                print(f"Failed to send native notification: {e}")

class CustomTimePicker(QWidget):
    def __init__(self, is_24h_format=True, parent=None):
        super().__init__(parent)
        self.is_24h = is_24h_format

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Hour input
        self.hour_input = LineEdit(self)
        self.hour_input.setPlaceholderText("HH")
        self.hour_input.setMaxLength(2)
        
        # Minute input
        self.minute_input = LineEdit(self)
        self.minute_input.setPlaceholderText("MM")
        self.minute_input.setMaxLength(2)

        # Select AM / PM
        self.ampm_combo = ComboBox(self)
        self.ampm_combo.addItems(["AM", "PM"])

        layout.addWidget(self.hour_input)
        layout.addWidget(self.minute_input)
        layout.addWidget(self.ampm_combo)

        # Realtime input validation
        self.hour_input.textChanged.connect(self._on_hour_changed)
        self.minute_input.textChanged.connect(self._on_minute_changed)

        # Format on blur / enter
        self.hour_input.editingFinished.connect(self._format_hour_on_finish)
        self.minute_input.editingFinished.connect(self._format_minute_on_finish)

        # Apply 12h or 24h mode
        self.set_format_24h(self.is_24h)

    def set_format_24h(self, is_24h: bool):
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

    def _on_hour_changed(self, text):
        if not text:
            return
        if not text.isdigit():
            self.hour_input.setText("".join(filter(str.isdigit, text)))
            return

        val = int(text)
        max_val = 23 if self.is_24h else 12

        if val > max_val:
            self.hour_input.setText(str(max_val))

    def _on_minute_changed(self, text):
        if not text:
            return

        if not text.isdigit():
            self.minute_input.setText("".join(filter(str.isdigit, text)))
            return

        val = int(text)
        if val > 59:
            self.minute_input.setText("59")

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
        self.settings = QSettings("DKClock", "WorldClockSettings")

        self.all_cities = [
            # --- ASIA / PACIFIC ---
            ("Asia/Ho_Chi_Minh", "Vietnam (Hanoi)"),
            ("Asia/Tokyo", "Japan (Tokyo)"),
            ("Asia/Seoul", "South Korea (Seoul)"),
            ("Asia/Bangkok", "Thailand (Bangkok)"),
            ("Asia/Singapore", "Singapore"),
            ("Asia/Jakarta", "Indonesia (Jakarta)"),
            ("Asia/Shanghai", "China (Beijing/Shanghai)"),
            ("Asia/Hong_Kong", "Hong Kong"),
            ("Asia/Taipei", "Taiwan (Taipei)"),
            ("Asia/Manila", "Philippines (Manila)"),
            ("Asia/Kolkata", "India (New Delhi)"),
            ("Asia/Dubai", "UAE (Dubai)"),
            ("Asia/Riyadh", "Saudi Arabia (Riyadh)"),
            
            # --- EUROPE ---
            ("Europe/London", "UK (London)"),
            ("Europe/Paris", "France (Paris)"),
            ("Europe/Berlin", "Germany (Berlin)"),
            ("Europe/Rome", "Italy (Rome)"),
            ("Europe/Madrid", "Spain (Madrid)"),
            ("Europe/Moscow", "Russia (Moscow)"),
            ("Europe/Athens", "Greece (Athens)"),
            ("Europe/Amsterdam", "Netherlands (Amsterdam)"),

            # --- AMERICAS ---
            ("America/New_York", "USA (New York - Eastern)"),
            ("America/Chicago", "USA (Chicago - Central)"),
            ("America/Denver", "USA (Denver - Mountain)"),
            ("America/Los_Angeles", "USA (Los Angeles - Pacific)"),
            ("America/Toronto", "Canada (Toronto)"),
            ("America/Vancouver", "Canada (Vancouver)"),
            ("America/Mexico_City", "Mexico (Mexico City)"),
            ("America/Sao_Paulo", "Brazil (São Paulo)"),
            ("America/Argentina/Buenos_Aires", "Argentina (Buenos Aires)"),

            # --- AUSTRALIA & OCEANIA ---
            ("Australia/Sydney", "Australia (Sydney)"),
            ("Australia/Melbourne", "Australia (Melbourne)"),
            ("Australia/Perth", "Australia (Perth)"),
            ("Pacific/Auckland", "New Zealand (Auckland)"),

            # --- AFRICA ---
            ("Africa/Cairo", "Egypt (Cairo)"),
            ("Africa/Johannesburg", "South Africa (Johannesburg)"),
            ("Africa/Lagos", "Nigeria (Lagos)"),
        ]

        default_tzs = [
            "Asia/Ho_Chi_Minh", # Việt Nam (Hà Nội)
            "Asia/Tokyo",       # Nhật Bản (Tokyo)
            "Asia/Shanghai",    # Trung Quốc (Beijing/Shanghai)
            "America/New_York"  # Mỹ (New York)
        ]
        self.is_24h_format = self.settings.value("is_24h_format", True, type=bool)
        self.show_seconds = self.settings.value("show_seconds", True, type=bool)
        
        saved_tzs = self.settings.value("enabled_tzs")
        if saved_tzs and isinstance(saved_tzs, list):
            self.enabled_tzs = saved_tzs
        else:
            self.enabled_tzs = default_tzs

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)

        self.top_bar = QHBoxLayout()

        self.format_switch = SwitchButton(self)
        self.format_switch.setOnText("24-Hour")
        self.format_switch.setOffText("12-Hour")
        self.format_switch.setChecked(self.is_24h_format)
        self.format_switch.checkedChanged.connect(self.toggle_format)

        self.sec_switch = SwitchButton(self)
        self.sec_switch.setOnText("Show Seconds")
        self.sec_switch.setOffText("Hide Seconds")
        self.sec_switch.setChecked(self.show_seconds)
        self.sec_switch.checkedChanged.connect(self.toggle_seconds)

        self.config_btn = PushButton("Timezone Settings", self, FIF.SETTING)
        self.config_btn.clicked.connect(self.toggle_settings_panel)

        # Thêm BodyLabel chuẩn không kèm parent self
        self.top_bar.addWidget(BodyLabel("Format:"))
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

        # --- BẢNG SETTINGS MÚI GIỜ (ĐÃ CHỈNH NÚT DONE RA NGOÀI SCROLL) ---
        self.settings_panel = QWidget()
        settings_main_layout = QVBoxLayout(self.settings_panel)
        settings_main_layout.setContentsMargins(0, 0, 0, 0)
        settings_main_layout.setSpacing(10)

        # Title cố định phía trên
        self.settings_title = SubtitleLabel("Select timezones to display:")
        settings_main_layout.addWidget(self.settings_title)

        # Scroll Area chỉ chứa danh sách Checkbox
        self.settings_scroll = SmoothScrollArea(self)
        self.settings_scroll.setWidgetResizable(True)
        self.settings_content = QWidget()
        self.settings_layout = QVBoxLayout(self.settings_content)
        self.settings_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.settings_layout.setSpacing(10)
        
        self.checkboxes = {}
        for tz_id, country in self.all_cities:
            cb = CheckBox(f"{country} ({tz_id})")
            cb.setChecked(tz_id in self.enabled_tzs)
            cb.stateChanged.connect(self.save_tz_selection)
            self.settings_layout.addWidget(cb)
            self.checkboxes[tz_id] = cb

        self.settings_scroll.setWidget(self.settings_content)
        settings_main_layout.addWidget(self.settings_scroll, stretch=1)

        # Nút Done CỐ ĐỊNH ở phía dưới cùng (ngoài Scroll)
        self.back_btn = PrimaryPushButton("Done", self)
        self.back_btn.clicked.connect(self.toggle_settings_panel)
        settings_main_layout.addWidget(self.back_btn)

        # Thêm vào content stack
        self.content_stack.addWidget(self.grid_scroll)
        self.content_stack.addWidget(self.settings_panel) # Dùng settings_panel mới thay cho settings_scroll

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
            self.config_btn.setText("Back")
        else:
            self.content_stack.setCurrentIndex(0)
            self.config_btn.setText("Timezone Settings")

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
# 2. TAB ALARM
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
        main_layout.setSpacing(10)

        # Thông tin giờ và nhãn
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        self.time_lbl = TitleLabel(time_str)
        t_font = self.time_lbl.font()
        t_font.setPixelSize(28)
        t_font.setBold(True)
        self.time_lbl.setFont(t_font)

        self.tag_lbl = CaptionLabel(label_text if label_text else "Alarm")

        info_layout.addWidget(self.time_lbl)
        info_layout.addWidget(self.tag_lbl)

        main_layout.addLayout(info_layout, stretch=1)

        # Switch Bật/Tắt
        self.switch_btn = SwitchButton(self)
        self.switch_btn.setChecked(is_enabled)
        self.switch_btn.checkedChanged.connect(self.on_switch_toggled)

        # Nút STOP (Nằm gọn gàng cạnh nút Delete)
        self.stop_btn = PrimaryPushButton("Stop", self)
        self.stop_btn.setFixedSize(60, 32)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                border: none;
                color: white;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
        """)
        self.stop_btn.clicked.connect(self.parent_widget.stop_alarm_sound)
        self.stop_btn.hide()

        # Nút Delete
        self.del_btn = ToolButton(FIF.DELETE, self)
        self.del_btn.clicked.connect(lambda: self.parent_widget.delete_alarm(self.alarm_id))

        # Add theo đúng thứ tự: [Switch] -> [Stop] -> [Delete]
        main_layout.addWidget(self.switch_btn)
        main_layout.addWidget(self.stop_btn)
        main_layout.addWidget(self.del_btn)

    def show_stop_button(self, show: bool):
        if show:
            self.stop_btn.show()
            self.switch_btn.hide()
        else:
            self.stop_btn.hide()
            self.switch_btn.show()

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
        self.settings = QSettings("DKClock", "AlarmSettings")
        self.world_settings = QSettings("DKClock", "WorldClockSettings")
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
        self.add_btn = PrimaryPushButton("Add Alarm", self, FIF.ADD)
        self.add_btn.clicked.connect(self.show_add_panel)
        top_bar.addStretch(1)
        top_bar.addWidget(self.add_btn)
        self.main_layout.addLayout(top_bar)

        self.content_stack = QStackedWidget(self)

        # PAGE 1: Alarm list grid
        self.grid_scroll = SmoothScrollArea(self)
        self.grid_scroll.setWidgetResizable(True)
        self.grid_scroll_content = QWidget()
        self.grid_layout = QGridLayout(self.grid_scroll_content)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.grid_layout.setSpacing(12)
        self.grid_scroll.setWidget(self.grid_scroll_content)

        # PAGE 2: Add alarm form
        self.add_panel = QWidget()
        add_layout = QVBoxLayout(self.add_panel)
        add_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        add_layout.setSpacing(15)

        is_24h_config = self.world_settings.value("is_24h_format", True, type=bool)
        
        self.time_picker = CustomTimePicker(is_24h_format=is_24h_config, parent=self)
        self.time_picker.setFixedSize(280, 40)

        self.label_input = LineEdit(self)
        self.label_input.setPlaceholderText("Alarm note (e.g. Wake up, Study...)")
        self.label_input.setFixedSize(280, 40)

        btn_row = QHBoxLayout()
        self.save_btn = PrimaryPushButton("Save", self)
        self.cancel_btn = PushButton("Cancel", self)
        self.save_btn.clicked.connect(self.save_new_alarm)
        self.cancel_btn.clicked.connect(self.hide_add_panel)
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.cancel_btn)

        add_layout.addWidget(SubtitleLabel("Select Alarm Time:"))
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
        is_24h_config = self.world_settings.value("is_24h_format", True, type=bool)
        self.time_picker.set_format_24h(is_24h_config)
        self.time_picker.set_time(QTime.currentTime())
        
        self.content_stack.setCurrentIndex(1)
        self.add_btn.setVisible(False)

    def hide_add_panel(self):
        self.content_stack.setCurrentIndex(0)
        self.add_btn.setVisible(True)

    def save_new_alarm(self):
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
        if hasattr(self, 'alarm_sound') and self.alarm_sound.isPlaying():
            self.alarm_sound.stop()

        if getattr(self, 'current_infobar', None) is not None:
            try:
                self.current_infobar.close()
            except RuntimeError:
                pass
            finally:
                self.current_infobar = None

        if hasattr(self, 'card_widgets'):
            for card in self.card_widgets:
                card.show_stop_button(False)

    def check_alarms(self):
        now_str = QTime.currentTime().toString("hh:mm")
        sec = QTime.currentTime().second()

        if sec == 0:
            for alarm in self.alarms:
                if alarm["enabled"] and alarm["time"] == now_str:
                    if self.alarm_sound.source().isValid():
                        self.alarm_sound.play()

                    # CHỈ HIỆN NÚT STOP TRÊN THẺ CÓ ALARM_ID TRÙNG KHỚP
                    for card in self.card_widgets:
                        if card.alarm_id == alarm["id"]:
                            card.show_stop_button(True)

                    self.current_infobar = InfoBar.success(
                        title='ALARM!',
                        content=f"Time's up: {alarm['time']} ({alarm['label']})",
                        orient=Qt.Orientation.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=0,
                        parent=self
                    )

                    send_linux_notification(
                        "ALARM!",
                        f"Time's up: {alarm['time']} ({alarm['label']})"
                    )

                    main_window = self.window()
                    if hasattr(main_window, 'tray_icon'):
                        try:
                            main_window.tray_icon.messageClicked.disconnect()
                        except:
                            pass

                        main_window.tray_icon.messageClicked.connect(
                            lambda: main_window.switch_to_tab(1)
                        )

                        main_window.tray_icon.showMessage(
                            "ALARM!",
                            f"Time's up: {alarm['time']} ({alarm['label']})",
                            QSystemTrayIcon.MessageIcon.Information,
                            10000
                        )

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
        self.settings = QSettings("DKClock", "TimerSettings")
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
        
        self.start_btn = PrimaryPushButton("Start", self)
        #self.start_btn.setFixedWidth(60)

        self.stop_btn = PushButton("Pause", self)
        self.reset_btn = PushButton("Stop", self)
        self.reset_btn.setStyleSheet("""
            PushButton {
                background-color: #E74C3C;
                border: 1px solid #E74C3C;
                color: white;
                border-radius: 5px;
                padding: 5px;
                width:50px;
            }
            PushButton:hover {
                background-color: #C0392B;
                border: 1px solid #C0392B;
            }
            PushButton:pressed {
                background-color: #A93226;
                border: 1px solid #A93226;
            }
        """)
        self.stop_btn.setEnabled(False) 
        self.reset_btn.setEnabled(False)
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
        """Tắt âm chuông Timer an toàn (chống crash RuntimeError)"""
        
        if hasattr(self, 'alarm_sound') and self.alarm_sound.isPlaying():
            self.alarm_sound.stop()

        if getattr(self, 'current_infobar', None) is not None:
            try:
                self.current_infobar.close()
            except RuntimeError:
                pass
            finally:
                self.current_infobar = None

    def check_empty_state(self):
        has_items = len(self.saved_timers_list) > 0

    def load_settings(self):
        saved = self.settings.value("saved_timers")
        
        if not saved:
            default_timers = [300, 600]
            for secs in default_timers:
                self.saved_timers_list.append(secs)
                self.add_saved_timer_ui(secs)
            self.save_settings()
        else:
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
        self.reset_btn.setEnabled(True)

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
                InfoBar.warning("Error", "Please enter a duration greater than 0.", parent=self, duration=2000)
                return

            self.remaining_seconds = secs
            if secs not in self.saved_timers_list:
                self.saved_timers_list.append(secs)
                self.add_saved_timer_ui(secs)
                self.save_settings()

        self.time_input.setReadOnly(True) 
        self.timer.start(1000)
        self.is_paused = False
        self.start_btn.setText("Resume")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.reset_btn.setEnabled(True)

    def action_pause(self):
        self.stop_alarm()
        self.timer.stop()
        self.is_paused = True
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
    def on_timer_finished(self):
        """Xử lý khi đếm ngược kết thúc: Dừng đếm nhưng giữ nút Reset để người dùng bấm tắt chuông"""
        self.timer.stop()
        self.is_paused = False
        self.remaining_seconds = 0
        self.time_input.setReadOnly(False)
        self.start_btn.setText("Start")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.reset_btn.setEnabled(True)

    def action_reset(self):
        self.stop_alarm()
        self.timer.stop()
        self.is_paused = False
        self.remaining_seconds = 0
        self.time_input.setReadOnly(False)
        self.time_input.setText("000000")
        self.start_btn.setText("Start")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)

    def update_timer(self):
        self.remaining_seconds -= 1
        self.update_display_text()

        if self.remaining_seconds <= 0:
            self.on_timer_finished()
            if self.alarm_sound.source().isValid():
                self.alarm_sound.play()

            # 1. InfoBar giao diện (Click dấu X tự đóng thì ngắt kết nối an toàn)
            self.current_infobar = InfoBar.success(
                title="Time's Up",
                content="The countdown timer has finished!",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=0,
                parent=self
            )
            
            # 2. Linux Native Notification
            send_linux_notification(
                "Timer Finished!",
                "The countdown timer has finished!"
            )

            # 3. Notification Khay hệ thống OS (Click chỉ chuyển Tab Timer, KHÔNG ngắt âm)
            main_window = self.window()
            if hasattr(main_window, 'tray_icon'):
                try:
                    main_window.tray_icon.messageClicked.disconnect()
                except:
                    pass

                # Bấm notification -> Chỉ hiển thị ứng dụng và chuyển Tab Timer (Index = 2)
                main_window.tray_icon.messageClicked.connect(
                    lambda: main_window.switch_to_tab(2)
                )

                main_window.tray_icon.showMessage(
                    "Timer Finished!",
                    "The countdown timer has finished!",
                    QSystemTrayIcon.MessageIcon.Information,
                    10000
                )

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

        if hasattr(self, "reset_btn"):
            disabled_bg = "#2A2A2A" if is_dark else "#E5E5E5"
            disabled_text = "#666666" if is_dark else "#A0A0A0"

            self.reset_btn.setStyleSheet(f"""
                    PushButton {{
                        background-color: #E74C3C;
                        border: 1px solid #E74C3C;
                        color: white;
                        border-radius: 5px;
                        font-weight: bold;
                        padding:5px;
                        width:50px;
                    }}
                    PushButton:hover {{
                        background-color: #C0392B;
                        border: 1px solid #C0392B;
                    }}
                    PushButton:pressed {{
                        background-color: #A93226;
                        border: 1px solid #A93226;
                    }}
                    PushButton:disabled {{
                        background-color: {disabled_bg};
                        border: 1px solid {disabled_bg};
                        color: {disabled_text};
                    }}
                """)

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
        self.time_display.setFixedWidth(220)
        self.time_display.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.left_layout.addWidget(self.time_display)
        self.left_layout.addSpacing(20)

        self.btn_layout = QHBoxLayout()
        self.btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.start_btn = PrimaryPushButton("Start", self)
        self.lap_btn = PushButton("Lap", self)
        self.reset_btn = PushButton("Reset", self)
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
            self.start_btn.setText("Pause")
            self.lap_btn.setEnabled(True)
            self.is_running = True
        else:
            self.timer.stop()
            self.start_btn.setText("Resume")
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
        
        self.start_btn.setText("Start")
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
# 4. TAB SETTINGS
# ==============================================================================
accentColorConfig = ColorConfigItem("Style", "AccentColor", "#113260")
class SettingsWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsWidget")
        self.settings = QSettings("DKClock", "AppSettings")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = TitleLabel("Settings", self)
        layout.addWidget(title)

        # Card 1: Run at startup
        autostart_card = CardWidget(self)
        a_layout = QHBoxLayout(autostart_card)
        a_layout.setContentsMargins(16, 16, 16, 16)

        a_info = QVBoxLayout()
        a_info.addWidget(SubtitleLabel("Run at system startup"))
        a_info.addWidget(
            CaptionLabel(
                "Automatically launch DK Clock on system login"
                " (Windows/macOS/Linux)"
            )
        )

        self.autostart_switch = SwitchButton(self)
        is_autostart = self.settings.value("autostart", False, type=bool)
        self.autostart_switch.setChecked(is_autostart)
        self.autostart_switch.checkedChanged.connect(self.toggle_autostart)

        a_layout.addLayout(a_info, stretch=1)
        a_layout.addWidget(self.autostart_switch)
        layout.addWidget(autostart_card)

        # Card 2: Minimize to tray on close
        tray_card = CardWidget(self)
        t_layout = QHBoxLayout(tray_card)
        t_layout.setContentsMargins(16, 16, 16, 16)

        t_info = QVBoxLayout()
        t_info.addWidget(SubtitleLabel("Minimize to system tray on close"))
        t_info.addWidget(
            CaptionLabel(
                "When enabled: Clicking [Close] minimizes app to tray. When"
                " disabled: Clicking [Close] exits app."
            )
        )

        self.tray_switch = SwitchButton(self)
        is_minimize_tray = self.settings.value("minimize_to_tray", False, type=bool)
        self.tray_switch.setChecked(is_minimize_tray)
        self.tray_switch.checkedChanged.connect(self.toggle_tray_behavior)

        t_layout.addLayout(t_info, stretch=1)
        t_layout.addWidget(self.tray_switch)
        layout.addWidget(tray_card)

        # --- CARD 3: ACCENT COLOR (Mới thêm) ---
        self.color_card = ColorSettingCard(
            configItem=accentColorConfig,
            icon=FIF.PALETTE,
            title="Accent color",
            content="Change the primary theme accent color of application",
            parent=self,
        )
        self.color_card.colorChanged.connect(self.on_color_changed)
        layout.addWidget(self.color_card)

    def on_color_changed(self, color: QColor):
        color_hex = color.name()
        self.settings.setValue("accent_color", color_hex)
        setThemeColor(color)  # Cập nhật màu Accent toàn ứng dụng

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
                    winreg.SetValueEx(key, "DKClock", 0, winreg.REG_SZ, app_path)
                else:
                    try:
                        winreg.DeleteValue(key, "DKClock")
                    except FileNotFoundError:
                        pass
                winreg.CloseKey(key)

            elif system_name == "Linux":
                autostart_dir = os.path.expanduser("~/.config/autostart")
                os.makedirs(autostart_dir, exist_ok=True)
                desktop_file = os.path.join(autostart_dir, "dk_clock.desktop")
                
                if checked:
                    exec_cmd = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
                    content = f"[Desktop Entry]\nType=Application\nName=DK Clock\nExec={exec_cmd}\nHidden=false\nNoDisplay=false\nX-GNOME-Autostart-enabled=true\n"
                    with open(desktop_file, "w") as f:
                        f.write(content)
                else:
                    if os.path.exists(desktop_file):
                        os.remove(desktop_file)

            elif system_name == "Darwin": # macOS
                plist_dir = os.path.expanduser("~/Library/LaunchAgents")
                os.makedirs(plist_dir, exist_ok=True)
                plist_file = os.path.join(plist_dir, "com.dk.clock.plist")

                if checked:
                    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key> <string>com.dk.clock</string>
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
            InfoBar.error("Error", f"Failed to set system startup: {str(e)}", parent=self)


# ==============================================================================
# 5. MAIN WINDOW (CLOCK APP)
# ==============================================================================
class ClockApp(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DK Clock v1.0")
        self.resize(750, 480)
        
        self.settings = QSettings("DKClock", "AppSettings")
        self.navigationInterface.setAcrylicEnabled(False)
        
        saved_color = self.settings.value("accent_color", "#113260", type=str)
        setThemeColor(QColor(saved_color))

        saved_theme = self.settings.value("theme", "LIGHT")
        if saved_theme == "DARK":
            self.current_theme = Theme.DARK
        else:
            self.current_theme = Theme.LIGHT
            
        setTheme(self.current_theme)

        # Tab initialization
        self.world_clock = WorldClockWidget(self)
        self.alarm_widget = AlarmWidget(self)
        self.timer_widget = TimerWidget(self)
        self.stopwatch = StopwatchWidget(self)
        self.settings_widget = SettingsWidget(self)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        img_dir = os.path.join(base_dir, "assets", "image")
        ICON_SIZE = 20
        world_icon = CustomSVGIcon("assets/image/worldclock.svg", size=ICON_SIZE)
        alarm_icon = CustomSVGIcon("assets/image/alarm.svg", size=ICON_SIZE)
        timer_icon = CustomSVGIcon("assets/image/timer.svg", size=ICON_SIZE)
        stopwatch_icon = CustomSVGIcon("assets/image/stopwatch.svg", size=ICON_SIZE)

        # Navigation integration
        self.addSubInterface(self.world_clock, icon=world_icon, text='World Clock')
        self.addSubInterface(self.alarm_widget, icon=alarm_icon, text='Alarm')
        self.addSubInterface(self.timer_widget, icon=timer_icon, text='Timer')
        self.addSubInterface(self.stopwatch, icon=stopwatch_icon, text='Stopwatch')
        self.addSubInterface(self.settings_widget, icon=FIF.SETTING, text='Settings', position=NavigationItemPosition.BOTTOM)
        self.enlarge_navigation_icons(size=30)
        # Theme toggle button
        self.navigationInterface.addItem(
            routeKey='theme_toggle',
            icon=FIF.CONSTRACT,
            text='Toggle Theme',
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

    def enlarge_navigation_icons(self, size: int = 28):
        from PyQt6.QtCore import QSize

        # Ép kích thước icon chuẩn của Navigation Interface
        if hasattr(self.navigationInterface, 'setIconSize'):
            self.navigationInterface.setIconSize(QSize(size, size))

        # Ép kích thước cho tất cả các button con trên Menu
        for btn in self.navigationInterface.findChildren(QWidget):
            if hasattr(btn, 'setIconSize'):
                btn.setIconSize(QSize(size, size))
    def switch_to_tab(self, index: int):
        """Hiển thị lại ứng dụng và chuyển sang tab tương ứng (1: Alarm, 2: Timer)"""
        if self.isHidden() or self.isMinimized():
            self.showNormal()
            self.activateWindow()
        
        # Chuyển tab trong FluentWindow
        self.stackedWidget.setCurrentIndex(index)


    def toggle_theme(self):
        if self.current_theme == Theme.LIGHT:
            self.current_theme = Theme.DARK
            self.settings.setValue("theme", "DARK")
        else:
            self.current_theme = Theme.LIGHT
            self.settings.setValue("theme", "LIGHT")

        setTheme(self.current_theme)

        # --- TÙY CHỈNH MÀU NỀN CHO CỬA SỔ CHÍNH ---
        is_dark = self.current_theme == Theme.DARK
        if not is_dark:
            # Mã màu #E5E5E5 sẽ tối & dịu mắt hơn nhiều so với màu trắng xám mặc định (#F3F3F3)
            self.setStyleSheet("ClockApp { background-color: #E5E5E5; }")
        else:
            self.setStyleSheet("")  # Trả lại mặc định cho Dark Mode

        if hasattr(self, "navigationInterface"):
            self.navigationInterface.update()
        if hasattr(self, "timer_widget"):
            self.timer_widget.update_theme(is_dark)
        if hasattr(self, "world_clock"):
            self.world_clock.update_clocks()
        if hasattr(self, "stopwatch"):
            self.stopwatch.update_theme(is_dark)
        if hasattr(self, "alarm_widget"):
            self.alarm_widget.update_theme()

    def setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        sys_name = platform.system()

        if sys_name == "Windows":
            icon_path = os.path.join(base_dir, "assets", "icon.ico")
        else:
            icon_path = os.path.join(base_dir, "assets", "icon.png")

        if not os.path.exists(icon_path):
            icon_path = os.path.join(base_dir, "assets", "icon.png")

        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))

        show_action = QAction("Restore Window", self)
        quit_action = QAction("Exit", self)
        
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
        minimize_to_tray = self.settings.value("minimize_to_tray", False, type=bool)
        
        if minimize_to_tray:
            event.ignore()
            self.hide()
        else:
            event.accept()
            QApplication.instance().quit()

if __name__ == '__main__':
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Tên ID duy nhất nhận diện Instance của ứng dụng
    SOCKET_KEY = "DKClock_Unique_SingleInstance_ServerKey"

    # 1. Thử kết nối tới Server của Instance đã chạy trước đó
    socket = QLocalSocket()
    socket.connectToServer(SOCKET_KEY)

    # Nếu kết nối thành công -> Đã có 1 instance đang chạy!
    if socket.waitForConnected(500):
        # Gửi tín hiệu báo instance cũ hiện cửa sổ lên, rồi thoát instance mới này
        socket.write(b"SHOW_WINDOW")
        socket.waitForBytesWritten(1000)
        socket.disconnectFromServer()
        sys.exit(0)

    # 2. Nếu chưa có instance nào -> Lắng nghe tín hiệu từ các lần mở sau
    local_server = QLocalServer()
    # Dọn dẹp socket cũ rác nếu app từng bị crash đột ngột
    QLocalServer.removeServer(SOCKET_KEY)
    local_server.listen(SOCKET_KEY)

    # Khai báo cửa sổ chính
    window = ClockApp()

    # Xử lý khi có instance thứ 2 kết nối tới
    def handle_new_connection():
        client_socket = local_server.nextPendingConnection()
        if client_socket:
            client_socket.waitForReadyRead(500)
            msg = client_socket.readAll().data().decode('utf-8')
            if msg == "SHOW_WINDOW":
                # Kích hoạt lại cửa sổ chính nổi lên trên
                if window.isHidden() or window.isMinimized():
                    window.showNormal()
                window.activateWindow()
                window.raise_()
            client_socket.disconnectFromServer()

    local_server.newConnection.connect(handle_new_connection)

    window.show()
    sys.exit(app.exec())
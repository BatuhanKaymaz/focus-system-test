import sys
import re
import time
from pathlib import Path

import pyqtgraph as pg

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from hardware.serial import ConnectionManager
from database import FocusDatabase


# =========================================================
# RENKLER - SIYAH TEMA
# =========================================================

BACKGROUND = "#000000"
PANEL = "#080808"
BORDER = "#292929"

TEXT = "#F5F5F5"
TEXT_SECONDARY = "#A3A3A3"

RED = "#F87171"
RED_HOVER = "#EF4444"
RED_DARK = "#7F1D1D"

GREEN = "#4ADE80"
GREEN_DARK = "#166534"

YELLOW = "#FBBF24"
YELLOW_DARK = "#92400E"

BLUE = "#38BDF8"


def resource_path(relative_path):
    """Kaynak dosyaların yolunu belirler."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent.parent

    return base_path / relative_path


LOGO_PATH = resource_path("assets/focus_logo.png")


# =========================================================
# ANA PENCERE
# =========================================================

class MainWindow(QMainWindow):
    back_requested = Signal()
    test_saved = Signal(str, int)

    def __init__(self, database=None):
        super().__init__()

        self.setWindowTitle("Focus Test System")
        # Pencere boyutunu sabitleme; farklı ekranlara ve gömülü sayfaya uyum sağla.
        self.resize(1200, 760)
        self.setMinimumSize(0, 0)

        self.database = database or FocusDatabase()
        self.active_serial = None
        self.connection_manager = ConnectionManager()
        self.device_connected = False
        self.device_port = ""

        self.current_mode = "onoff"
        self.measuring = False
        self.actuator_running = False
        self.stopped = False
        self.start_time = None
        self.elapsed_seconds = 0
        self.last_command_status = ""

        # Varsayılan metinler (sıfırlama için)
        self.default_values = {
            "torque": "0.00",
            "current": "0.00",
            "voltage": "0.0",
            "temperature": "0.0",
            "speed": "0",
        }

        # Ölçüm kartlarındaki QLabel nesneleri
        self.value_labels = {}

        self.graphs = {}
        self.graph_curves = {}
        self.graph_data = {}
        self._ui_scale = 1.0

        self.setup_ui()
        self._fit_layout_to_window()
        self.set_measurement_color(False)

        self.measurement_timer = QTimer(self)
        self.measurement_timer.setInterval(100)
        self.measurement_timer.timeout.connect(
            self.update_elapsed_time
        )

        self.connection_timer = QTimer(self)
        self.connection_timer.setInterval(1500)
        self.connection_timer.timeout.connect(
            self.check_hardware_connection
        )
        self.connection_timer.start()

        self.check_hardware_connection()

    # =====================================================
    # ARAYÜZ KURULUMU
    # =====================================================

    def setup_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        self.main_layout = main_layout
        main_layout.setContentsMargins(16, 12, 16, 14)
        main_layout.setSpacing(10)

        main_layout.addLayout(self.create_header())
        main_layout.addLayout(self.create_measurement_cards())

        bottom_layout = QHBoxLayout()
        self.bottom_layout = bottom_layout
        bottom_layout.setSpacing(14)

        self.graph_panel = self.create_graph_panel()
        self.control_panel = self.create_control_panel()

        bottom_layout.addWidget(self.graph_panel, 6)
        bottom_layout.addWidget(self.control_panel, 5)

        main_layout.addLayout(bottom_layout, 1)

        self.select_mode("onoff")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_layout_to_window()

    def _fit_layout_to_window(self):
        """Ölçekler arayüzü; kart ve panel yerleşimini değiştirmez."""
        if not hasattr(self, "main_layout"):
            return

        scale = min(self.width() / 1366, self.height() / 768)
        scale = max(0.10, min(scale, 4.0))
        if abs(scale - self._ui_scale) < 0.015:
            return
        self._ui_scale = scale

        horizontal_margin = self._scaled(16)
        vertical_margin = self._scaled(12)
        self.main_layout.setContentsMargins(
            horizontal_margin, vertical_margin, horizontal_margin,
            self._scaled(14),
        )
        self.main_layout.setSpacing(self._scaled(10))

        if hasattr(self, "bottom_layout"):
            self.bottom_layout.setSpacing(self._scaled(14))
        if hasattr(self, "graph_layout"):
            margin = self._scaled(14)
            self.graph_layout.setContentsMargins(margin, margin, margin, margin)
            self.graph_layout.setSpacing(self._scaled(10))
        if hasattr(self, "control_layout"):
            horizontal = self._scaled(12)
            vertical = self._scaled(8)
            self.control_layout.setContentsMargins(
                horizontal, vertical, horizontal, vertical
            )
            self.control_layout.setSpacing(self._scaled(6))

        if hasattr(self, "header_logo"):
            logo_width = self._scaled(64)
            logo_height = self._scaled(58)
            self.header_logo.setFixedSize(logo_width, logo_height)
            self.load_logo(self.header_logo, logo_width, logo_height)
        if hasattr(self, "header_title"):
            self.header_title.setFont(
                QFont("Arial", self._scaled(20), QFont.Weight.Bold)
            )

        for card in getattr(self, "measurement_cards", []):
            card.setMinimumHeight(self._scaled(100))
        for plot in self.graphs.values():
            plot.setMinimumHeight(self._scaled(170))
        for name in ("open_button", "close_button", "stop_button"):
            button = getattr(self, name, None)
            if button is not None:
                button.setMinimumHeight(self._scaled(38))

        if hasattr(self, "current_spinbox"):
            self.current_spinbox.setMinimumHeight(self._scaled(32))
        if hasattr(self, "send_current_button"):
            self.send_current_button.setMinimumHeight(self._scaled(34))
        if hasattr(self, "save_button"):
            self.save_button.setMinimumHeight(self._scaled(34))
        if hasattr(self, "reset_button"):
            self.reset_button.setMinimumHeight(self._scaled(34))

        self.apply_styles()
        self.set_measurement_color(self.measuring)

    def _scaled(self, value):
        return max(1, round(value * self._ui_scale))

    def _scale_stylesheet(self, stylesheet):
        return re.sub(
            r"(?<![\w.])(\d+(?:\.\d+)?)(px|pt)\b",
            lambda match: f"{max(1, round(float(match.group(1)) * max(self._ui_scale, 0.1)))}{match.group(2)}",
            stylesheet,
        )

    # =====================================================
    # ÜST BAŞLIK
    # =====================================================

    def create_header(self):
        header = QHBoxLayout()
        header.setSpacing(12)

        self.header_logo = QLabel()
        self.header_logo.setMinimumSize(0, 0)
        self.header_logo.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.load_logo(self.header_logo, 64, 58)
        header.addWidget(self.header_logo)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(3)

        title = QLabel("FOCUS TEST SYSTEM")
        self.header_title = title
        title.setObjectName("headerTitle")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))

        subtitle = QLabel("AKTÜATÖR PERFORMANS TESTİ")
        subtitle.setObjectName("headerSubtitle")

        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        header.addLayout(title_layout)

        header.addStretch()

        self.save_button = QPushButton("TESTİ KAYDET")
        self.save_button.setObjectName("secondaryButton")
        self.save_button.setMinimumHeight(0)
        self.save_button.setMinimumWidth(0)
        self.save_button.clicked.connect(self.open_save_dialog)
        header.addWidget(self.save_button)

        self.back_button = QPushButton("← Ana Sayfa")
        self.back_button.setMinimumHeight(0)
        self.back_button.setMinimumWidth(0)
        self.back_button.clicked.connect(
            self.back_requested.emit
        )
        header.addWidget(self.back_button)

        self.connection_status = QLabel(
            "● BAĞLANTI KONTROL EDİLİYOR"
        )
        self.connection_status.setObjectName("connectionStatus")
        self.connection_status.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.connection_status.setMinimumWidth(0)
        self.connection_status.setWordWrap(True)
        header.addWidget(self.connection_status)

        self.check_connection_button = QPushButton(
            "BAĞLANTIYI KONTROL ET"
        )
        self.check_connection_button.setObjectName(
            "connectionButton"
        )
        self.check_connection_button.clicked.connect(
            self.manual_connection_check
        )
        header.addWidget(self.check_connection_button)

        return header

    # =====================================================
    # ÖLÇÜM KARTLARI
    # =====================================================

    def create_measurement_cards(self):
        layout = QGridLayout()
        layout.setSpacing(10)

        measurements = [
            ("ANLIK TORK", "Nm", "torque"),
            ("MOTOR AKIMI", "A", "current"),
            ("MOTOR GERİLİMİ", "V", "voltage"),
            ("MOTOR SICAKLIĞI", "°C", "temperature"),
            ("DÖNÜŞ HIZI", "RPM", "speed"),
        ]

        for column, (name, unit, key) in enumerate(measurements):
            layout.addWidget(
                self.create_measurement_card(name, unit, key),
                0,
                column,
            )

        return layout

    def create_measurement_card(self, name, unit, key):
        card = QFrame()
        card.setObjectName("measurementCard")
        card.setMinimumHeight(0)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 10, 8, 10)
        layout.setSpacing(5)

        title = QLabel(name)
        title.setObjectName("measurementTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)

        value = QLabel(self.default_values[key])
        value.setObjectName("measurementValue")
        value.setAlignment(Qt.AlignmentFlag.AlignCenter)

        unit_label = QLabel(unit)
        unit_label.setObjectName("measurementUnit")
        unit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(value)
        layout.addWidget(unit_label)
        layout.addStretch()

        self.value_labels[key] = value

        return card

    # =====================================================
    # GRAFİK PANELİ
    # =====================================================

    def create_graph_panel(self):
        graph_card = QFrame()
        graph_card.setObjectName("panelCard")
        graph_card.setMinimumWidth(0)
        graph_card.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(graph_card)
        self.graph_layout = layout
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()

        title = QLabel("GERÇEK ZAMANLI ÖLÇÜMLER")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch()

        self.graph_status = QLabel("● ÖLÇÜM YAPILMIYOR")
        self.graph_status.setObjectName("graphStatus")
        header.addWidget(self.graph_status)

        layout.addLayout(header)

        # Renkli sekme butonları + grafik yığını
        self.graph_tab_buttons = []
        self.graph_stack = QStackedWidget()

        tab_row = QHBoxLayout()
        tab_row.setSpacing(6)

        graph_settings = {
            "torque": ("Tork", "Nm", "#FB7185", "#080808"),
            "current": ("Motor Akımı", "A", "#38BDF8", "#080808"),
            "voltage": ("Motor Gerilimi", "V", "#FBBF24", "#080808"),
            "temperature": ("Motor Sıcaklığı", "°C", "#FB923C", "#080808"),
            "speed": ("Dönüş Hızı", "RPM", "#4ADE80", "#080808"),
        }

        for key, (
            name, unit, color, graph_background
        ) in graph_settings.items():

            plot = pg.PlotWidget()
            plot.setBackground(graph_background)
            plot.showGrid(x=True, y=True, alpha=0.25)
            plot.setMinimumHeight(100)

            plot.setTitle(
                f"{name} Grafiği",
                color=color,
                size="13pt",
            )

            plot.setLabel("left", name, units=unit, color=color)
            plot.setLabel(
                "bottom",
                "Zaman",
                units="s",
                color=TEXT_SECONDARY,
            )

            plot.getAxis("left").setTextPen(TEXT_SECONDARY)
            plot.getAxis("bottom").setTextPen(TEXT_SECONDARY)

            curve = plot.plot(
                [],
                [],
                pen=pg.mkPen(color=color, width=2),
            )

            self.graphs[key] = plot
            self.graph_curves[key] = curve
            self.graph_data[key] = {
                "time": [],
                "values": [],
            }

            index = self.graph_stack.addWidget(plot)

            button = QPushButton(name)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(self.graph_tab_style(color))
            button.clicked.connect(
                lambda checked=False, i=index: self.select_graph_tab(i)
            )
            button.setMinimumWidth(0)
            button.setSizePolicy(
                QSizePolicy.Policy.Ignored,
                QSizePolicy.Policy.Fixed,
            )
            tab_row.addWidget(button, 1)
            self.graph_tab_buttons.append(button)

        tab_row.addStretch()

        layout.addLayout(tab_row)
        layout.addWidget(self.graph_stack, 1)

        self.select_graph_tab(0)

        return graph_card

    # =====================================================
    # KONTROL PANELİ
    # =====================================================

    def create_control_panel(self):
        outer_card = QFrame()
        outer_card.setObjectName("panelCard")
        outer_card.setMinimumWidth(0)
        outer_card.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)

        outer_layout = QVBoxLayout(outer_card)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        content = QWidget()
        content.setObjectName("controlContent")

        control_layout = QVBoxLayout(content)
        self.control_layout = control_layout
        control_layout.setContentsMargins(12, 8, 12, 8)
        control_layout.setSpacing(6)

        # Başlık ortalandı
        title = QLabel("AKTÜATÖR KONTROLÜ")
        title.setObjectName("sectionTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        control_layout.addWidget(title)

        control_layout.addWidget(self.create_status_card())
        control_layout.addWidget(self.create_mode_selector())

        self.onoff_panel = self.create_onoff_panel()
        self.proportional_panel = self.create_proportional_panel()

        control_layout.addWidget(self.onoff_panel)
        control_layout.addWidget(self.proportional_panel)
        control_layout.addLayout(self.create_test_details())

        control_layout.addStretch()

        self.reset_button = QPushButton("ÖLÇÜMLERİ SIFIRLA")
        self.reset_button.setObjectName("secondaryButton")
        self.reset_button.setMinimumHeight(0)
        self.reset_button.clicked.connect(self.reset_measurements)
        control_layout.addWidget(self.reset_button)

        outer_layout.addWidget(content)

        return outer_card

    def open_save_dialog(self):
        """Show a themed prompt for the card serial before saving a test."""
        dialog = QDialog(self, Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        dialog.setObjectName("saveTestDialog")
        dialog.setWindowTitle("Test Kaydını Kaydet")
        dialog.setModal(True)
        dialog.setMinimumWidth(self._scaled(390))
        dialog.setStyleSheet(self._scale_stylesheet("""
            QDialog#saveTestDialog {
                background-color: #080808;
                color: #F5F5F5;
                border: 1px solid #383838;
                border-radius: 12px;
            }
            QLabel { color: #F5F5F5; background: transparent; border: none; }
            QLabel#saveDialogTitle { font-size: 16px; font-weight: 800; }
            QLabel#saveDialogPrompt { color: #A3A3A3; font-size: 12px; }
            QLineEdit {
                background-color: #101010;
                color: #F5F5F5;
                border: 1px solid #404040;
                border-radius: 7px;
                padding: 9px 11px;
                selection-background-color: #164E63;
                font-size: 13px;
            }
            QLineEdit:focus { border: 1px solid #38BDF8; }
            QPushButton {
                background-color: #202020;
                color: #F5F5F5;
                border: 1px solid #404040;
                border-radius: 7px;
                padding: 9px 13px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #303030; border-color: #737373; }
            QPushButton#generateSerialButton {
                background-color: #10232B;
                border-color: #155E75;
                color: #7DD3FC;
            }
            QPushButton#generateSerialButton:hover { background-color: #123744; }
            QPushButton#saveConfirmButton {
                background-color: #7F1D1D;
                border-color: #B91C1C;
                color: #FFFFFF;
            }
            QPushButton#saveConfirmButton:hover { background-color: #991B1B; }
            QPushButton#dialogCloseButton {
                border: none;
                background: transparent;
                color: #A3A3A3;
                font-size: 17px;
                padding: 2px;
            }
            QPushButton#dialogCloseButton:hover { color: #FFFFFF; background: #292929; }
        """))

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(self._scaled(18), self._scaled(14), self._scaled(18), self._scaled(16))
        layout.setSpacing(self._scaled(14))

        title_row = QHBoxLayout()
        title_row.setSpacing(self._scaled(8))
        title = QLabel("TEST KAYDINI KAYDET")
        title.setObjectName("saveDialogTitle")
        title_row.addWidget(title)
        title_row.addStretch(1)
        close_button = QPushButton("×")
        close_button.setObjectName("dialogCloseButton")
        close_button.setFixedSize(self._scaled(28), self._scaled(28))
        close_button.clicked.connect(dialog.reject)
        title_row.addWidget(close_button)
        layout.addLayout(title_row)

        prompt = QLabel(
            "Seri numarasını girin ya da yeni bir numara oluşturun. "
            "Test bu karta kaydedilir."
        )
        prompt.setObjectName("saveDialogPrompt")
        prompt.setWordWrap(True)
        layout.addWidget(prompt)

        serial_row = QHBoxLayout()
        serial_row.setSpacing(self._scaled(8))
        serial_input = QLineEdit()
        serial_input.setPlaceholderText("Kart seri numarası")
        serial_input.setText(self.active_serial or "")
        serial_row.addWidget(serial_input, 1)
        generate_button = QPushButton("Seri Numarası Oluştur")
        generate_button.setObjectName("generateSerialButton")
        generate_button.clicked.connect(
            lambda: serial_input.setText(self.database.generate_serial_number())
        )
        serial_row.addWidget(generate_button)
        layout.addLayout(serial_row)

        actions = QHBoxLayout()
        actions.setSpacing(self._scaled(8))
        actions.addStretch(1)
        cancel_button = QPushButton("Vazgeç")
        save_button = QPushButton("Kaydet")
        save_button.setObjectName("saveConfirmButton")
        actions.addWidget(cancel_button)
        actions.addWidget(save_button)
        layout.addLayout(actions)

        cancel_button.clicked.connect(dialog.reject)
        save_button.clicked.connect(
            lambda: self._save_test_for_serial(serial_input.text(), dialog)
        )
        serial_input.returnPressed.connect(
            lambda: self._save_test_for_serial(serial_input.text(), dialog)
        )
        serial_input.setFocus()
        dialog.exec()

    def _save_test_for_serial(self, serial_number, dialog):
        serial = str(serial_number).strip()
        if not serial:
            QMessageBox.warning(
                dialog,
                "Seri Numarası Gerekli",
                "Seri numarası girin veya yeni bir numara oluşturun.",
            )
            return

        try:
            device = self.database.get_device(serial)
            if device is None:
                self.database.create_device(serial)
                device = self.database.get_device(serial)

            measurements = {}
            for key, label in self.value_labels.items():
                try:
                    measurements[key] = float(label.text().strip())
                except (TypeError, ValueError):
                    measurements[key] = None

            try:
                measurements["actuator_position"] = float(
                    self.position_value.text().replace("%", "").strip()
                )
            except (TypeError, ValueError):
                measurements["actuator_position"] = None

            duration = self.elapsed_seconds
            if self.measuring and self.start_time is not None:
                duration = time.monotonic() - self.start_time

            test_id = self.database.save_test(
                device["serial_number"],
                measurements,
                test_mode=("ON/OFF" if self.current_mode == "onoff" else "ORANSAL"),
                duration_seconds=duration,
                result=self.test_result.text(),
                samples=self._collect_graph_samples(),
            )
        except Exception as error:
            QMessageBox.critical(dialog, "Kayıt Yapılamadı", str(error))
            return

        self.active_serial = device["serial_number"]
        self.test_saved.emit(self.active_serial, test_id)
        self._show_save_success(dialog, self.active_serial, test_id)
        dialog.accept()

    def _show_save_success(self, parent, serial_number, test_id):
        success = QDialog(
            parent,
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint,
        )
        success.setObjectName("testSavedDialog")
        success.setWindowTitle("Test kaydedildi")
        success.setModal(True)
        success.setMinimumWidth(self._scaled(430))
        success.setStyleSheet(self._scale_stylesheet("""
            QDialog#testSavedDialog {
                background-color: #080808;
                color: #F5F5F5;
                border: 1px solid #383838;
                border-radius: 12px;
            }
            QLabel { color: #F5F5F5; background: transparent; border: none; }
            QLabel#successTitle { color: #4ADE80; font-size: 17px; font-weight: 800; }
            QLabel#successSubtitle { color: #A3A3A3; font-size: 12px; }
            QFrame#successCard { background: #101713; border: 1px solid #24543A; border-radius: 9px; }
            QLabel#detailCaption { color: #A3A3A3; font-size: 11px; font-weight: 700; }
            QLabel#detailValue { color: #FFFFFF; font-size: 13px; font-weight: 800; }
            QPushButton#successClose { background: #166534; color: #FFFFFF; border: 1px solid #4ADE80; border-radius: 7px; padding: 9px 20px; font-size: 12px; font-weight: 800; }
            QPushButton#successClose:hover { background: #15803D; border-color: #86EFAC; }
            QPushButton#successClose:pressed { background: #14532D; }
        """))

        layout = QVBoxLayout(success)
        layout.setContentsMargins(self._scaled(20), self._scaled(18), self._scaled(20), self._scaled(18))
        layout.setSpacing(self._scaled(12))

        heading = QHBoxLayout()
        check = QLabel("✓")
        check.setStyleSheet(
            f"color: #4ADE80; font-size: {self._scaled(25)}px; font-weight: 900;"
        )
        heading.addWidget(check)
        title = QLabel("TEST KAYDI TAMAMLANDI")
        title.setObjectName("successTitle")
        heading.addWidget(title)
        heading.addStretch(1)
        layout.addLayout(heading)

        subtitle = QLabel("Ölçüm sonuçları kartın kayıt geçmişine eklendi.")
        subtitle.setObjectName("successSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        details = QFrame()
        details.setObjectName("successCard")
        details_layout = QVBoxLayout(details)
        details_layout.setContentsMargins(self._scaled(14), self._scaled(12), self._scaled(14), self._scaled(12))
        details_layout.setSpacing(self._scaled(9))
        values = (
            ("KART SERİ NUMARASI", serial_number),
            ("KAYIT NUMARASI", str(test_id)),
            ("TEST MODU", "ON/OFF" if self.current_mode == "onoff" else "ORANSAL"),
            ("TEST SONUCU", self.test_result.text().strip() or "Kaydedildi"),
        )
        for caption_text, value_text in values:
            row = QHBoxLayout()
            caption = QLabel(caption_text)
            caption.setObjectName("detailCaption")
            value = QLabel(str(value_text))
            value.setObjectName("detailValue")
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            value.setWordWrap(True)
            row.addWidget(caption)
            row.addStretch(1)
            row.addWidget(value)
            details_layout.addLayout(row)
        layout.addWidget(details)

        actions = QHBoxLayout()
        actions.addStretch(1)
        close_button = QPushButton("TAMAM")
        close_button.setObjectName("successClose")
        close_button.clicked.connect(success.accept)
        actions.addWidget(close_button)
        layout.addLayout(actions)
        success.exec()

    def _collect_graph_samples(self):
        """Combine graph data into rows for storage with the test summary."""
        sample_count = max(
            (len(series["time"]) for series in self.graph_data.values()),
            default=0,
        )
        samples = []
        for index in range(sample_count):
            elapsed_values = [
                series["time"][index]
                for series in self.graph_data.values()
                if index < len(series["time"])
            ]
            sample = {"elapsed_seconds": max(elapsed_values)}
            for key, series in self.graph_data.items():
                sample[key] = (
                    series["values"][index]
                    if index < len(series["values"])
                    else None
                )
            samples.append(sample)
        return samples

    # =====================================================
    # SİSTEM DURUMU
    # =====================================================

    def create_status_card(self):
        card = QFrame()
        card.setObjectName("statusCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        caption = QLabel("SİSTEM DURUMU")
        caption.setObjectName("fieldCaption")

        self.test_status = QLabel("● BAĞLANTI KONTROL EDİLİYOR")
        self.test_status.setObjectName("testStatus")
        self.test_status.setWordWrap(True)

        self.test_type = QLabel("ON/OFF")
        self.test_type.setObjectName("testType")
        self.test_type.setWordWrap(True)

        layout.addWidget(caption)
        layout.addWidget(self.test_status)
        layout.addWidget(self.test_type)

        return card

    def update_system_status(self):
        mode_text = (
            "ON/OFF"
            if self.current_mode == "onoff"
            else "ORANSAL"
        )

        if not self.device_connected:
            self.test_status.setText("● CİHAZ BAĞLI DEĞİL")
            self.test_status.setStyleSheet(
                f"color: {YELLOW}; font-weight: 700;"
            )

            self.set_test_type(
                f"{mode_text} modu seçildi — cihaz bağlı değil",
                YELLOW,
            )
            return

        if self.stopped and not self.measuring:
            self.test_status.setText("● DURDURULDU")
            self.test_status.setStyleSheet(
                f"color: {YELLOW}; font-weight: 700;"
            )
            self.set_test_type(
                f"{mode_text} — DURDUR komutu verildi",
                YELLOW,
            )
            return

        if self.measuring:
            status_text = "● ÖLÇÜM DEVAM EDİYOR"
        elif self.actuator_running:
            status_text = "● SİSTEM ÇALIŞIYOR"
        else:
            status_text = "● SİSTEM HAZIR"

        self.test_status.setText(status_text)
        self.test_status.setStyleSheet(
            f"color: {GREEN}; font-weight: 700;"
        )

        if self.last_command_status and not self.measuring:
            self.set_test_type(
                f"{mode_text} — {self.last_command_status}",
                TEXT,
            )
        else:
            self.set_test_type(
                f"{mode_text} modu seçildi — cihaz bağlı",
                GREEN,
            )

    # =====================================================
    # MOD SEÇİMİ
    # =====================================================

    def create_mode_selector(self):
        container = QWidget()

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        caption = QLabel("ÇALIŞMA MODU")
        caption.setObjectName("fieldCaption")
        layout.addWidget(caption)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)

        self.onoff_mode_button = QPushButton("ON/OFF")
        self.onoff_mode_button.setObjectName("modeButton")
        self.onoff_mode_button.setCheckable(True)

        self.proportional_mode_button = QPushButton("ORANSAL")
        self.proportional_mode_button.setObjectName("modeButton")
        self.proportional_mode_button.setCheckable(True)

        self.onoff_mode_button.clicked.connect(
            lambda: self.select_mode("onoff")
        )
        self.proportional_mode_button.clicked.connect(
            lambda: self.select_mode("proportional")
        )

        buttons.addWidget(self.onoff_mode_button)
        buttons.addWidget(self.proportional_mode_button)
        layout.addLayout(buttons)

        return container

    def select_mode(self, mode):
        self.current_mode = (
            "onoff" if mode == "onoff" else "proportional"
        )

        is_onoff = self.current_mode == "onoff"

        self.onoff_mode_button.setChecked(is_onoff)
        self.proportional_mode_button.setChecked(not is_onoff)

        self.onoff_panel.setVisible(is_onoff)
        self.proportional_panel.setVisible(not is_onoff)

        self.update_system_status()

    # =====================================================
    # ON/OFF KONTROLÜ
    # =====================================================

    def create_onoff_panel(self):
        panel = QFrame()
        panel.setObjectName("controlSection")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        title = QLabel("ON/OFF KONTROLÜ")
        title.setObjectName("fieldCaption")
        layout.addWidget(title)

        self.open_button = QPushButton("ON")
        self.open_button.setObjectName("openButton")
        self.open_button.setMinimumHeight(0)
        self.open_button.clicked.connect(self.open_actuator)

        self.close_button = QPushButton("OFF")
        self.close_button.setObjectName("closeButton")
        self.close_button.setMinimumHeight(0)
        self.close_button.clicked.connect(self.close_actuator)

        self.stop_button = QPushButton("DURDUR")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setMinimumHeight(0)
        self.stop_button.clicked.connect(self.stop_actuator)

        layout.addWidget(self.open_button)
        layout.addWidget(self.close_button)
        layout.addWidget(self.stop_button)

        return panel

    # =====================================================
    # ORANSAL AKIM KONTROLÜ
    # =====================================================

    def create_proportional_panel(self):
        panel = QFrame()
        panel.setObjectName("controlSection")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        title = QLabel("ORANSAL AKIM KONTROLÜ")
        title.setObjectName("fieldCaption")
        layout.addWidget(title)

        current_header = QHBoxLayout()
        current_header.setSpacing(4)

        current_label = QLabel("Gönderilecek akım")
        current_label.setObjectName("normalLabel")
        current_header.addWidget(current_label)
        current_header.addStretch()

        self.current_value_label = QLabel("12.0 mA")
        self.current_value_label.setObjectName("currentValue")
        current_header.addWidget(self.current_value_label)

        layout.addLayout(current_header)

        self.current_slider = QSlider(Qt.Orientation.Horizontal)
        self.current_slider.setRange(40, 200)
        self.current_slider.setValue(120)
        self.current_slider.setMaximumHeight(18)
        self.current_slider.valueChanged.connect(
            self.update_current_value
        )
        layout.addWidget(self.current_slider)

        range_layout = QHBoxLayout()
        range_layout.setSpacing(2)
        range_layout.addWidget(QLabel("4 mA"))
        range_layout.addStretch()
        range_layout.addWidget(QLabel("20 mA"))
        layout.addLayout(range_layout)

        self.current_spinbox = QDoubleSpinBox()
        self.current_spinbox.setRange(4.0, 20.0)
        self.current_spinbox.setSingleStep(0.1)
        self.current_spinbox.setDecimals(1)
        self.current_spinbox.setValue(12.0)
        self.current_spinbox.setSuffix(" mA")
        self.current_spinbox.setMinimumHeight(0)
        self.current_spinbox.valueChanged.connect(
            self.update_current_from_spinbox
        )
        layout.addWidget(self.current_spinbox)

        self.send_current_button = QPushButton(
            "HEDEF AKIMI GÖNDER"
        )
        self.send_current_button.setObjectName("sendCurrentButton")
        self.send_current_button.setMinimumHeight(0)
        self.send_current_button.clicked.connect(
            self.send_target_current
        )
        layout.addWidget(self.send_current_button)

        position_card = QFrame()
        position_card.setObjectName("positionCard")

        position_layout = QVBoxLayout(position_card)
        position_layout.setContentsMargins(7, 4, 7, 4)
        position_layout.setSpacing(1)

        position_title = QLabel("AKTÜATÖRÜN GERÇEK POZİSYONU")
        position_title.setObjectName("fieldCaption")
        position_title.setWordWrap(True)
        position_layout.addWidget(position_title)

        self.position_value = QLabel("-- %")
        self.position_value.setObjectName("positionValue")
        self.position_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        position_layout.addWidget(self.position_value)

        position_note = QLabel("Konum göstergesi")
        position_note.setObjectName("normalLabel")
        position_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        position_layout.addWidget(position_note)

        layout.addWidget(position_card)

        panel.hide()

        return panel

    def update_current_value(self, slider_value):
        current_ma = slider_value / 10.0

        self.current_value_label.setText(
            f"{current_ma:.1f} mA"
        )

        if abs(self.current_spinbox.value() - current_ma) > 0.001:
            self.current_spinbox.blockSignals(True)
            self.current_spinbox.setValue(current_ma)
            self.current_spinbox.blockSignals(False)

    def update_current_from_spinbox(self, current_ma):
        slider_value = round(current_ma * 10)

        if self.current_slider.value() != slider_value:
            self.current_slider.blockSignals(True)
            self.current_slider.setValue(slider_value)
            self.current_slider.blockSignals(False)

        self.current_value_label.setText(
            f"{current_ma:.1f} mA"
        )

    # =====================================================
    # TEST DETAYLARI
    # =====================================================

    def create_test_details(self):
        layout = QGridLayout()
        layout.setSpacing(6)

        duration_card = QFrame()
        duration_card.setObjectName("detailCard")

        duration_layout = QVBoxLayout(duration_card)

        duration_caption = QLabel("ÖLÇÜM SÜRESİ")
        duration_caption.setObjectName("fieldCaption")

        self.test_duration = QLabel("00:00")
        self.test_duration.setObjectName("detailValue")
        self.test_duration.setAlignment(Qt.AlignmentFlag.AlignCenter)

        duration_layout.addWidget(duration_caption)
        duration_layout.addWidget(self.test_duration)

        result_card = QFrame()
        result_card.setObjectName("detailCard")

        result_layout = QVBoxLayout(result_card)

        result_caption = QLabel("DURUM")
        result_caption.setObjectName("fieldCaption")

        self.test_result = QLabel("BEKLENİYOR")
        self.test_result.setObjectName("detailValue")
        self.test_result.setWordWrap(True)
        self.test_result.setAlignment(Qt.AlignmentFlag.AlignCenter)

        result_layout.addWidget(result_caption)
        result_layout.addWidget(self.test_result)

        layout.addWidget(duration_card, 0, 0)
        layout.addWidget(result_card, 0, 1)

        return layout

    # =====================================================
    # AKTÜATÖR KOMUTLARI
    # =====================================================

    def open_actuator(self):
        if not self.device_connected:
            self.update_system_status()
            return

        self.stopped = False
        self.actuator_running = True
        self.last_command_status = (
            "ON seçildi; gerçek donanım komutu bağlı değil."
        )
        self.start_measurement()

    def close_actuator(self):
        if not self.device_connected:
            self.update_system_status()
            return

        self.stopped = False
        self.actuator_running = False
        self.last_command_status = (
            "OFF seçildi; gerçek donanım komutu bağlı değil."
        )
        self.stop_measurement()
        self.test_result.setText("KAPALI")
        self.update_system_status()

    def send_target_current(self):
        if not self.device_connected:
            self.update_system_status()
            return

        current_ma = self.current_slider.value() / 10.0

        self.stopped = False
        self.last_command_status = (
            f"{current_ma:.1f} mA seçildi; "
            "gerçek donanım komutu bağlı değil."
        )
        self.update_system_status()

    def stop_actuator(self):
        self.stopped = True

        self.stop_measurement()

        self.actuator_running = False
        self.last_command_status = ""

        self.test_result.setText("DURDURULDU")
        self.graph_status.setText("● ÖLÇÜM DURDURULDU")

        self.update_system_status()

    # =====================================================
    # ÖLÇÜM KONTROLÜ
    # =====================================================

    def start_measurement(self):
        if self.measuring:
            return

        self.stopped = False
        self.measuring = True
        self.actuator_running = True
        self.start_time = time.monotonic()
        self.elapsed_seconds = 0

        self.test_duration.setText("00:00")
        self.test_result.setText("ÖLÇÜLÜYOR")
        self.graph_status.setText("● ÖLÇÜM DEVAM EDİYOR")

        self.update_system_status()
        self.set_measurement_color(True)
        self.measurement_timer.start()

    def stop_measurement(self):
        self.measuring = False
        self.measurement_timer.stop()

        self.set_measurement_color(False)

        if hasattr(self, "graph_status"):
            self.graph_status.setText("● ÖLÇÜM DURDURULDU")

    def reset_measurements(self):
        self.stop_measurement()

        self.stopped = False
        self.start_time = None
        self.elapsed_seconds = 0
        self.actuator_running = False
        self.last_command_status = ""

        for key, value in self.default_values.items():
            self.value_labels[key].setText(value)

        self.position_value.setText("-- %")

        self.clear_graphs()

        self.test_duration.setText("00:00")
        self.test_result.setText("BEKLENİYOR")

        self.set_measurement_color(False)
        self.update_system_status()

    def update_elapsed_time(self):
        if not self.measuring or self.start_time is None:
            return

        self.elapsed_seconds = int(
            time.monotonic() - self.start_time
        )

        minutes, seconds = divmod(self.elapsed_seconds, 60)

        self.test_duration.setText(
            f"{minutes:02d}:{seconds:02d}"
        )

    # =====================================================
    # DONANIMDAN GELEN VERİLER
    # =====================================================

    def update_measurements(self, data: dict):
        """
        Donanımdan gelen verileri kartlara ve grafiklere yazar.
        Örnek:
        {"torque": 1.2, "current": 0.8, "voltage": 12.1,
         "temperature": 35, "speed": 1200}
        """
        if not self.measuring or self.start_time is None:
            return

        elapsed = time.monotonic() - self.start_time

        formats = {
            "torque": "{:.2f}",
            "current": "{:.2f}",
            "voltage": "{:.1f}",
            "temperature": "{:.1f}",
            "speed": "{:.0f}",
        }

        for key, fmt in formats.items():
            if key not in data:
                continue

            try:
                number = float(data[key])
            except (TypeError, ValueError):
                continue

            self.value_labels[key].setText(fmt.format(number))
            self.update_graph(key, number, elapsed)

    def update_actuator_position(self, percent):
        """Aktüatörün gerçek pozisyonunu (%) gösterir."""
        try:
            self.position_value.setText(f"{float(percent):.0f} %")
        except (TypeError, ValueError):
            self.position_value.setText("-- %")

    # =====================================================
    # GRAFİKLER
    # =====================================================

    def update_graph(self, key, value, elapsed_seconds):
        if key not in self.graph_curves:
            return

        try:
            value = float(value)
            elapsed_seconds = float(elapsed_seconds)
        except (TypeError, ValueError):
            return

        data = self.graph_data[key]

        data["time"].append(elapsed_seconds)
        data["values"].append(value)

        max_points = 1000

        if len(data["time"]) > max_points:
            data["time"] = data["time"][-max_points:]
            data["values"] = data["values"][-max_points:]

        self.graph_curves[key].setData(
            data["time"],
            data["values"],
        )

        self.graph_status.setText("● VERİ ALINIYOR")

    def graph_tab_style(self, color):
        c = QColor(color)
        r, g, b = c.red(), c.green(), c.blue()

        return self._scale_stylesheet(f"""
            QPushButton {{
                background-color: rgba({r}, {g}, {b}, 28);
                color: {color};
                border: 1px solid rgba({r}, {g}, {b}, 130);
                border-radius: 6px;
                padding: 10px 13px;
                font-size: 13px;
                font-weight: 700;
            }}

            QPushButton:hover {{
                background-color: rgba({r}, {g}, {b}, 70);
                border: 1px solid {color};
            }}

            QPushButton:checked {{
                background-color: {color};
                color: #000000;
                border: 1px solid {color};
                font-weight: 800;
            }}
        """)

    def select_graph_tab(self, index):
        self.graph_stack.setCurrentIndex(index)

        for i, button in enumerate(self.graph_tab_buttons):
            button.setChecked(i == index)

    def clear_graphs(self):
        for key in self.graph_data:
            self.graph_data[key]["time"].clear()
            self.graph_data[key]["values"].clear()
            self.graph_curves[key].setData([], [])

        self.graph_status.setText("● ÖLÇÜM YAPILMIYOR")

    def set_test_type(self, text, color=TEXT):
        self.test_type.setText(text)
        self.test_type.setStyleSheet(
            f"color: {color}; font-weight: 600;"
        )

    def set_measurement_color(self, measuring):
        color = GREEN if measuring else TEXT

        for label in self.value_labels.values():
            label.setStyleSheet(
                f"color: {color}; "
                f"font-size: {self._scaled(28)}px; "
                "font-weight: 800;"
            )

    # =====================================================
    # DONANIM BAĞLANTISI
    # =====================================================

    def handle_connection_lost(self):
        """Bağlantı koparsa çalışan ölçümü durdurur."""
        if self.measuring:
            self.stop_measurement()
            self.test_result.setText("BAĞLANTI KOPTU")

        self.actuator_running = False

    def check_hardware_connection(self):
        try:
            result = self.connection_manager.find_esp32()

            if result and result.get("connected"):
                self.device_connected = True
                self.device_port = result.get("port", "")

                self.set_connection_status(
                    True,
                    f"● DONANIM BAĞLI ({self.device_port})",
                )
            else:
                self.device_connected = False
                self.device_port = ""
                self.handle_connection_lost()

                self.set_connection_status(
                    False,
                    "● DONANIM BAĞLI DEĞİL",
                )

        except Exception as error:
            print(f"Bağlantı kontrolü başarısız: {error}")

            self.device_connected = False
            self.device_port = ""
            self.handle_connection_lost()

            self.set_connection_status(
                False,
                "● DONANIM BAĞLI DEĞİL",
            )

        self.update_system_status()

    def manual_connection_check(self):
        self.check_connection_button.setEnabled(False)

        self.set_connection_status(
            None,
            "● BAĞLANTI KONTROL EDİLİYOR",
        )

        QTimer.singleShot(
            250,
            self._finish_manual_check,
        )

    def _finish_manual_check(self):
        self.check_hardware_connection()
        self.check_connection_button.setEnabled(True)

    def set_connection_status(self, connected, message):
        self.connection_status.setText(message)

        if connected is True:
            color = GREEN
            background = "#101F17"
            border = "#2F855A"
        elif connected is None:
            color = YELLOW
            background = "#211B0D"
            border = "#927126"
        else:
            color = RED
            background = "#211012"
            border = "#9F3A4B"

        self.connection_status.setStyleSheet(self._scale_stylesheet(f"""
            QLabel#connectionStatus {{
                color: {color};
                background-color: {background};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 8px;
                font-size: 12px;
                font-weight: 700;
            }}
        """))

    # =====================================================
    # LOGO
    # =====================================================

    def load_logo(self, label, width, height):
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo = QPixmap(str(LOGO_PATH))

        if logo.isNull():
            label.setText("FOCUS")
            label.setStyleSheet(
                f"color: {TEXT}; "
                "font-size: 20px; "
                "font-weight: bold;"
            )
            return

        label.setPixmap(
            logo.scaled(
                width,
                height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    # =====================================================
    # STİLLER - SİYAH TEMA
    # =====================================================

    def apply_styles(self):
        self.setStyleSheet(self._scale_stylesheet(f"""
            QMainWindow {{
                background-color: {BACKGROUND};
            }}


            QWidget#centralWidget {{
                background-color: {BACKGROUND};
                color: {TEXT};
                font-family: "Segoe UI";
                font-size: 13px;
            }}

            QWidget#controlContent {{
                background-color: {PANEL};
            }}

            QLabel {{
                color: {TEXT};
                background: transparent;
                border: none;
            }}

            QLabel#headerTitle {{
                font-size: 22px;
                font-weight: 700;
                color: #FFFFFF;
            }}

            QLabel#headerSubtitle {{
                color: #A3A3A3;
                font-size: 13px;
            }}

            QFrame#measurementCard,
            QFrame#panelCard {{
                background-color: #080808;
                border: 1px solid {BORDER};
                border-radius: 10px;
            }}

            QLabel#measurementTitle {{
                color: {TEXT_SECONDARY};
                font-size: 12px;
                font-weight: 700;
            }}

            QLabel#measurementValue {{
                color: {TEXT};
                font-size: 28px;
                font-weight: 800;
            }}

            QLabel#measurementUnit {{
                color: {TEXT_SECONDARY};
                font-size: 13px;
                font-weight: 600;
            }}

            QLabel#sectionTitle {{
                color: #E5E5E5;
                font-size: 15px;
                font-weight: 700;
            }}

            QFrame#statusCard {{
                background-color: #0C0C0C;
                border: 1px solid #303030;
                border-radius: 9px;
            }}

            QFrame#controlSection {{
                background-color: #0C0C0C;
                border: 1px solid #303030;
                border-radius: 9px;
            }}

            QFrame#detailCard {{
                background-color: #101010;
                border: 1px solid #303030;
                border-radius: 9px;
            }}

            QFrame#positionCard {{
                background-color: #080808;
                border: 1px solid #164E63;
                border-radius: 9px;
            }}

            QLabel#fieldCaption {{
                color: #A3A3A3;
                font-size: 13px;
                font-weight: 700;
            }}

            QLabel#testStatus {{
                font-size: 16px;
                font-weight: 700;
            }}

            QLabel#testType {{
                color: {TEXT_SECONDARY};
                font-size: 14px;
            }}

            QLabel#positionValue {{
                color: #67E8F9;
                font-size: 32px;
                font-weight: 800;
            }}

            QLabel#currentValue {{
                color: #C4B5FD;
                font-size: 23px;
                font-weight: 800;
            }}

            QLabel#normalLabel {{
                color: #E5E5E5;
                font-size: 14px;
            }}

            QLabel#detailValue {{
                color: #F5F5F5;
                font-size: 19px;
                font-weight: 700;
                padding: 4px;
            }}

            QLabel#graphStatus {{
                color: #BAE6FD;
                background-color: #080808;
                border: 1px solid #164E63;
                border-radius: 6px;
                padding: 6px;
                font-size: 12px;
                font-weight: 700;
            }}

            QPushButton {{
                background-color: #202020;
                color: #F5F5F5;
                border: 1px solid #404040;
                border-radius: 7px;
                padding: 8px;
                font-size: 13px;
                font-weight: 600;
            }}

            QPushButton:hover {{
                background-color: #303030;
                border-color: #737373;
            }}

            QPushButton:disabled {{
                color: #666666;
                background-color: #111111;
                border-color: #262626;
            }}

            QPushButton#modeButton {{
                background-color: #151515;
                border: 1px solid #404040;
            }}

            QPushButton#modeButton:hover {{
                background-color: #292929;
            }}

            QPushButton#modeButton:checked {{
                background-color: #1D4ED8;
                border: 1px solid #60A5FA;
                color: #FFFFFF;
            }}

            QPushButton#openButton {{
                background-color: #166534;
                border: 2px solid #4ADE80;
                color: #FFFFFF;
                font-size: 15px;
                font-weight: 700;
            }}

            QPushButton#openButton:hover {{
                background-color: #15803D;
                border-color: #86EFAC;
            }}

            QPushButton#closeButton {{
                background-color: #92400E;
                border: 2px solid #FBBF24;
                color: #FFFFFF;
                font-size: 15px;
                font-weight: 700;
            }}

            QPushButton#closeButton:hover {{
                background-color: #A16207;
                border-color: #FDE68A;
            }}

            QPushButton#stopButton {{
                background-color: #7F1D1D;
                border: 2px solid #F87171;
                color: #FFFFFF;
                font-size: 15px;
                font-weight: 800;
            }}

            QPushButton#stopButton:hover {{
                background-color: #991B1B;
                border-color: #FCA5A5;
            }}

            QPushButton#sendCurrentButton {{
                background-color: #5B21B6;
                border: 1px solid #A78BFA;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 700;
            }}

            QPushButton#sendCurrentButton:hover {{
                background-color: #6D28D9;
                border-color: #C4B5FD;
            }}

            QPushButton#secondaryButton {{
                background-color: #202020;
                border: 1px solid #525252;
                color: #F5F5F5;
                font-weight: 700;
            }}

            QPushButton#secondaryButton:hover {{
                background-color: #303030;
                border-color: #A3A3A3;
            }}

            QPushButton#connectionButton {{
                background-color: #0E7490;
                color: #FFFFFF;
                border: 1px solid #22D3EE;
                font-size: 12px;
                font-weight: 700;
            }}

            QPushButton#connectionButton:hover {{
                background-color: #155E75;
                border-color: #67E8F9;
            }}

            QSlider::groove:horizontal {{
                height: 6px;
                background: #303030;
                border-radius: 3px;
            }}

            QSlider::sub-page:horizontal {{
                background: #8B5CF6;
                border-radius: 3px;
            }}

            QSlider::handle:horizontal {{
                background: #C4B5FD;
                border: 2px solid #8B5CF6;
                width: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }}

            QSlider::handle:horizontal:hover {{
                background: #E9D5FF;
            }}

            QDoubleSpinBox {{
                background-color: #101010;
                color: #F5F5F5;
                border: 1px solid #404040;
                border-radius: 6px;
                padding: 5px;
                font-size: 14px;
            }}

            QDoubleSpinBox:focus {{
                border: 1px solid #A78BFA;
            }}
        """))

    # =====================================================
    # KAPATMA
    # =====================================================

    def closeEvent(self, event):
        self.stop_measurement()
        self.connection_timer.stop()

        try:
            if hasattr(self.connection_manager, "close"):
                self.connection_manager.close()
        except Exception as error:
            print(f"Bağlantı kapatılırken hata: {error}")

        event.accept()






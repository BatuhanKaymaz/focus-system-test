
from pathlib import Path
import time

import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QFont, QPixmap, QPainter, QPen, QColor, QImage
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from hardware.serial import ConnectionManager


PURPLE = "#8058E8"
PURPLE_DARK = "#6540C4"
BACKGROUND = "#101010"
WHITE = "#1B1B1B"
TEXT_DARK = "#F0F0F0"
TEXT_SECONDARY = "#A0A0A0"
BORDER = "#333333"

WARNING = "#F2C94C"
SUCCESS = "#34D399"
ERROR = "#F87171"

LOGO_PATH = (
    Path(__file__).resolve().parent.parent
    / "assets"
    / "focus_logo.png"
)


class LoadingSpinner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.angle = 0
        self.status = "idle"

        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.rotate)

        self.setFixedSize(64, 64)

    def set_status(self, status):
        self.status = status

        if status == "running":
            if not self.timer.isActive():
                self.timer.start()
        else:
            self.timer.stop()
            self.angle = 0

        self.update()

    def start(self):
        self.set_status("running")

    def stop(self):
        self.set_status("idle")

    def rotate(self):
        self.angle = (self.angle + 4) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        rect = QRectF(8, 8, 48, 48)

        colors = {
            "idle": "#FFFFFF",
            "running": "#F2C94C",
            "completed": "#34D399",
        }

        color = QColor(
            colors.get(self.status, "#FFFFFF")
        )

        # Mor renk yerine koyu gri arka halka
        background_pen = QPen(QColor("#303030"), 4)
        painter.setPen(background_pen)
        painter.drawArc(rect, 0, 360 * 16)

        # Hafif parlama
        glow_color = QColor(color)
        glow_color.setAlpha(65)

        glow_pen = QPen(glow_color, 8)
        glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(glow_pen)

        if self.status == "running":
            painter.drawArc(
                rect,
                -self.angle * 16,
                -100 * 16,
            )
        else:
            painter.drawArc(rect, 0, 300 * 16)

        # Ana halka
        main_pen = QPen(color, 4)
        main_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(main_pen)

        if self.status == "running":
            painter.drawArc(
                rect,
                -self.angle * 16,
                -100 * 16,
            )
        else:
            painter.drawArc(rect, 0, 300 * 16)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Focus Test System")
        self.resize(1440, 900)

        self.values = {
            "torque": "0.00",
            "current": "0.00",
            "voltage": "0.0",
            "temperature": "0.0",
            "speed": "0",
        }

        self.measuring = False
        self.start_time = None
        self.elapsed_seconds = 0

        self.connection_manager = ConnectionManager()

        self.setup_ui()
        self.apply_styles()

        self.set_measurement_color(False)
        self.set_test_type("SİSTEM HAZIR", "#F0F0F0")

        self.measurement_timer = QTimer(self)
        self.measurement_timer.setInterval(100)
        self.measurement_timer.timeout.connect(
            self.update_elapsed_time
        )

        self.connection_timer = QTimer(self)
        self.connection_timer.timeout.connect(
            self.check_hardware_connection
        )
        self.connection_timer.start(1500)

        self.check_hardware_connection()

    def setup_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(28, 22, 28, 24)
        main_layout.setSpacing(20)

        # HEADER
        header = QHBoxLayout()
        header.setSpacing(18)

        self.header_logo = QLabel()
        self.header_logo.setFixedSize(78, 72)
        self.load_logo(self.header_logo, 78, 72)
        header.addWidget(self.header_logo)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)

        self.header_title = QLabel("FOCUS TEST SYSTEM")
        self.header_title.setObjectName("headerTitle")
        self.header_title.setFont(
            QFont("Arial", 30, QFont.Weight.Bold)
        )

        self.header_subtitle = QLabel(
            "AKTÜATÖR PERFORMANS TESTİ"
        )
        self.header_subtitle.setObjectName("headerSubtitle")

        title_layout.addWidget(self.header_title)
        title_layout.addWidget(self.header_subtitle)
        header.addLayout(title_layout)
        header.addStretch()

        self.connection_status = QLabel(
            "● BAĞLANTI KONTROL EDİLİYOR"
        )
        self.connection_status.setObjectName("connectionStatus")
        self.connection_status.setMinimumWidth(190)
        self.connection_status.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        header.addWidget(self.connection_status)

        self.check_connection_button = QPushButton(
            "BAĞLANTIYI KONTROL ET"
        )
        self.check_connection_button.setObjectName(
            "connectionButton"
        )
        self.check_connection_button.setMinimumHeight(42)
        self.check_connection_button.clicked.connect(
            self.manual_connection_check
        )
        header.addWidget(self.check_connection_button)

        main_layout.addLayout(header)

        # ÖLÇÜM KARTLARI
        cards_layout = QGridLayout()
        cards_layout.setSpacing(18)

        measurements = [
            ("ANLIK TORK", "Nm", "torque"),
            ("MOTOR AKIMI", "A", "current"),
            ("MOTOR GERİLİMİ", "V", "voltage"),
            ("MOTOR SICAKLIĞI", "°C", "temperature"),
            ("DÖNÜŞ HIZI", "RPM", "speed"),
        ]

        for column, (name, unit, key) in enumerate(measurements):
            card = self.create_measurement_card(
                name, unit, key
            )
            cards_layout.addWidget(card, 0, column)

        main_layout.addLayout(cards_layout)

        # ALT BÖLÜM
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(20)

        # GRAFİK PANELİ
        graph_card = QFrame()
        graph_card.setObjectName("panelCard")

        graph_layout = QVBoxLayout(graph_card)
        graph_layout.setContentsMargins(20, 18, 20, 18)
        graph_layout.setSpacing(12)

        graph_header = QHBoxLayout()

        graph_title = QLabel("GERÇEK ZAMANLI ÖLÇÜMLER")
        graph_title.setObjectName("sectionTitle")
        graph_header.addWidget(graph_title)
        graph_header.addStretch()

        self.graph_status = QLabel("● ÖLÇÜM YAPILMIYOR")
        self.graph_status.setObjectName("graphStatus")
        graph_header.addWidget(self.graph_status)

        graph_layout.addLayout(graph_header)

        self.graph_tabs = QTabWidget()
        self.graph_tabs.setObjectName("graphTabs")

        self.graphs = {}
        self.graph_curves = {}
        self.graph_data = {}

        graph_settings = {
            "torque": ("Tork", "Nm", "#EF4444"),
            "current": ("Motor Akımı", "A", "#38BDF8"),
            "voltage": ("Motor Gerilimi", "V", "#F2C94C"),
            "temperature": (
                "Motor Sıcaklığı", "°C", "#F87171"
            ),
            "speed": ("Dönüş Hızı", "RPM", "#34D399"),
        }

        for key, (title, unit, color) in graph_settings.items():
            plot = pg.PlotWidget()
            plot.setBackground("#151515")
            plot.showGrid(x=True, y=True, alpha=0.20)
            plot.setMinimumHeight(300)

            plot.setTitle(
                f"{title} Grafiği",
                color="#F0F0F0",
                size="12pt",
            )
            plot.setLabel(
                "left", title, units=unit, color="#B8B8B8"
            )
            plot.setLabel(
                "bottom", "Zaman", units="s", color="#B8B8B8"
            )

            plot.getAxis("left").setTextPen("#A0A0A0")
            plot.getAxis("bottom").setTextPen("#A0A0A0")
            plot.getAxis("left").setPen("#444444")
            plot.getAxis("bottom").setPen("#444444")

            plot.setClipToView(True)
            plot.setDownsampling(auto=True)

            curve = plot.plot(
                [],
                [],
                pen=pg.mkPen(color=color, width=2.5),
            )

            self.graphs[key] = plot
            self.graph_curves[key] = curve
            self.graph_data[key] = {
                "time": [],
                "values": [],
            }

            self.graph_tabs.addTab(plot, title)

        graph_layout.addWidget(self.graph_tabs)
        bottom_layout.addWidget(graph_card, 3)

        # TEST BİLGİLERİ PANELİ
        info_card = QFrame()
        info_card.setObjectName("panelCard")
        info_card.setMinimumWidth(300)

        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(22, 22, 22, 22)
        info_layout.setSpacing(16)

        info_title = QLabel("TEST BİLGİLERİ")
        info_title.setObjectName("sectionTitle")
        info_layout.addWidget(info_title)

        self.info_logo = QLabel()
        self.info_logo.setFixedHeight(100)
        self.load_logo(self.info_logo, 210, 100)
        info_layout.addWidget(self.info_logo)

        # MEVCUT DURUM
        status_card = QFrame()
        status_card.setObjectName("statusCard")

        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(16, 14, 16, 14)
        status_layout.setSpacing(8)

        status_caption = QLabel("MEVCUT DURUM")
        status_caption.setObjectName("fieldCaption")
        status_layout.addWidget(status_caption)

        self.test_status = QLabel("● TEST BAŞLATILMADI")
        self.test_status.setObjectName("testStatus")
        self.test_status.setWordWrap(True)
        status_layout.addWidget(self.test_status)

        info_layout.addWidget(status_card)

        # YÜKLEME ANİMASYONU
        spinner_area = QVBoxLayout()
        spinner_area.setSpacing(6)

        spinner_row = QHBoxLayout()
        spinner_row.addStretch()

        self.loading_spinner = LoadingSpinner()
        spinner_row.addWidget(self.loading_spinner)

        spinner_row.addStretch()
        spinner_area.addLayout(spinner_row)

        self.test_type = QLabel("SİSTEM HAZIR")
        self.test_type.setObjectName("testType")
        self.test_type.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        spinner_area.addWidget(self.test_type)

        info_layout.addLayout(spinner_area)

        # SÜRE VE SONUÇ
        details_layout = QGridLayout()
        details_layout.setSpacing(10)

        duration_card = QFrame()
        duration_card.setObjectName("detailCard")

        duration_layout = QVBoxLayout(duration_card)
        duration_layout.setContentsMargins(12, 14, 12, 14)
        duration_layout.setSpacing(8)

        duration_caption = QLabel("TEST SÜRESİ")
        duration_caption.setObjectName("fieldCaption")
        duration_layout.addWidget(duration_caption)

        self.test_duration = QLabel("00:00")
        self.test_duration.setObjectName("detailValue")
        self.test_duration.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        duration_layout.addWidget(self.test_duration)

        result_card = QFrame()
        result_card.setObjectName("detailCard")

        result_layout = QVBoxLayout(result_card)
        result_layout.setContentsMargins(12, 14, 12, 14)
        result_layout.setSpacing(8)

        result_caption = QLabel("TEST SONUCU")
        result_caption.setObjectName("fieldCaption")
        result_layout.addWidget(result_caption)

        self.test_result = QLabel("BEKLENİYOR")
        self.test_result.setObjectName("detailValue")
        self.test_result.setWordWrap(True)
        self.test_result.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        result_layout.addWidget(self.test_result)

        details_layout.addWidget(duration_card, 0, 0)
        details_layout.addWidget(result_card, 0, 1)

        info_layout.addLayout(details_layout)
        info_layout.addStretch()

        # TEST BUTONLARI
        self.start_button = QPushButton("TESTİ BAŞLAT")
        self.start_button.setObjectName("primaryButton")
        self.start_button.setMinimumHeight(48)
        self.start_button.clicked.connect(self.start_loading)

        self.finish_button = QPushButton("ÖLÇÜMÜ TAMAMLA")
        self.finish_button.setObjectName("finishButton")
        self.finish_button.setMinimumHeight(44)
        self.finish_button.clicked.connect(self.finish_loading)
        self.finish_button.setEnabled(False)

        self.reset_button = QPushButton("TESTİ SIFIRLA")
        self.reset_button.setObjectName("secondaryButton")
        self.reset_button.setMinimumHeight(44)
        self.reset_button.clicked.connect(self.reset_loading)

        info_layout.addWidget(self.start_button)
        info_layout.addWidget(self.finish_button)
        info_layout.addWidget(self.reset_button)

        bottom_layout.addWidget(info_card, 1)
        main_layout.addLayout(bottom_layout, 1)

    # ÖLÇÜM DEĞERLERİNİN RENGİ
    def set_measurement_color(self, measuring):
        color = SUCCESS if measuring else ERROR

        for value_label in self.values.values():
            value_label.setStyleSheet(
                f"color: {color}; font-size: 36px; font-weight: 700;"
            )

    # GRAFİK VERİSİ
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

    def clear_graphs(self):
        for key in self.graph_data:
            self.graph_data[key]["time"].clear()
            self.graph_data[key]["values"].clear()
            self.graph_curves[key].setData([], [])

        self.graph_status.setText("● ÖLÇÜM YAPILMIYOR")
        self.graph_status.setStyleSheet("")

    # TEST DURUMU YAZISI
    def set_test_type(self, text, color="#F0F0F0"):
        self.test_type.setText(text)
        self.test_type.setStyleSheet(
            f"color: {color}; font-weight: 700;"
        )

    # TESTİ BAŞLAT
    def start_loading(self):
        if self.measuring:
            return

        self.measuring = True
        self.start_time = time.monotonic()
        self.elapsed_seconds = 0
        self.test_duration.setText("00:00")

        self.loading_spinner.set_status("running")
        self.set_measurement_color(True)

        self.test_status.setText("● TEST DEVAM EDİYOR")
        self.set_test_type("ÖLÇÜM YAPILIYOR", WARNING)
        self.test_result.setText("ÖLÇÜLÜYOR")

        self.test_status.setStyleSheet(f"color: {WARNING};")
        self.test_result.setStyleSheet(f"color: {WARNING};")

        self.graph_status.setText("● ÖLÇÜM DEVAM EDİYOR")
        self.start_button.setEnabled(False)
        self.finish_button.setEnabled(True)

        self.measurement_timer.start()

    # ÖLÇÜMÜ TAMAMLA
    def finish_loading(self):
        if not self.measuring:
            return

        self.measuring = False
        self.measurement_timer.stop()

        self.loading_spinner.set_status("completed")
        self.set_measurement_color(False)

        self.test_status.setText("● ÖLÇÜM TAMAMLANDI")
        self.set_test_type("TEST TAMAMLANDI", SUCCESS)
        self.test_result.setText("TAMAMLANDI")

        self.test_status.setStyleSheet(f"color: {SUCCESS};")
        self.test_result.setStyleSheet(f"color: {SUCCESS};")

        self.graph_status.setText("● ÖLÇÜM TAMAMLANDI")

        self.start_button.setEnabled(True)
        self.finish_button.setEnabled(False)

    # TESTİ SIFIRLA
    def reset_loading(self):
        self.measuring = False
        self.measurement_timer.stop()

        self.loading_spinner.set_status("idle")

        self.start_time = None
        self.elapsed_seconds = 0

        defaults = {
            "torque": "0.00",
            "current": "0.00",
            "voltage": "0.0",
            "temperature": "0.0",
            "speed": "0",
        }

        for key, default_value in defaults.items():
            self.values[key].setText(default_value)

        self.set_measurement_color(False)
        self.clear_graphs()

        self.test_status.setText("● TEST BAŞLATILMADI")
        self.set_test_type("SİSTEM HAZIR", "#F0F0F0")

        self.test_duration.setText("00:00")
        self.test_result.setText("BEKLENİYOR")

        self.test_status.setStyleSheet(f"color: {ERROR};")
        self.test_result.setStyleSheet(f"color: {ERROR};")

        self.start_button.setEnabled(True)
        self.finish_button.setEnabled(False)

    # TEST SÜRESİ
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

    # DONANIM BAĞLANTISI
    def check_hardware_connection(self):
        try:
            result = self.connection_manager.find_esp32()

            if result and result.get("connected"):
                message = (
                    f"● DONANIM BAĞLI ({result.get('port', '')})"
                )
                self.set_connection_status("connected", message)
            else:
                self.set_connection_status(
                    "disconnected",
                    "● DONANIM BAĞLI DEĞİL",
                )

        except Exception as error:
            print(
                f"Donanım bağlantı kontrolü başarısız: {error}"
            )
            self.set_connection_status(
                "disconnected",
                "● DONANIM BAĞLI DEĞİL",
            )

    def manual_connection_check(self):
        self.set_connection_status(
            "checking",
            "● BAĞLANTI KONTROL EDİLİYOR",
        )

        QTimer.singleShot(
            250,
            self.check_hardware_connection,
        )

    def set_connection_status(self, status, message):
        self.connection_status.setText(message)

        if status == "connected":
            color = SUCCESS
            background = "#142B22"
            border = "#24543E"
        elif status == "checking":
            color = WARNING
            background = "#302718"
            border = "#5A4527"
        else:
            color = ERROR
            background = "#321B1B"
            border = "#5B2929"

        self.connection_status.setStyleSheet(f"""
            QLabel#connectionStatus {{
                color: {color};
                background-color: {background};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 12px;
                font-weight: 700;
            }}
        """)

    # ÖLÇÜM KARTLARI
    def create_measurement_card(self, name, unit, key):
        card = QFrame()
        card.setObjectName("measurementCard")
        card.setMinimumSize(150, 190)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 18, 16, 18)
        layout.setSpacing(12)

        title = QLabel(name)
        title.setObjectName("measurementTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)

        value = QLabel(self.values[key])
        value.setObjectName("measurementValue")
        value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value.setStyleSheet(
            "color: #F87171; font-size: 36px; font-weight: 700;"
        )

        unit_label = QLabel(unit)
        unit_label.setObjectName("measurementUnit")
        unit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(value)
        layout.addWidget(unit_label)
        layout.addStretch()

        self.values[key] = value
        return card

    # ŞEFFAF LOGO
    def load_logo(self, label, width, height):
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            True,
        )
        label.setStyleSheet(
            "QLabel { background-color: transparent; border: none; }"
        )

        logo = QImage(str(LOGO_PATH))

        if logo.isNull():
            label.setText("FOCUS")
            label.setStyleSheet(f"""
                QLabel {{
                    background-color: transparent;
                    border: none;
                    color: {PURPLE};
                    font-size: 22px;
                    font-weight: bold;
                }}
            """)
            print(f"Logo yüklenemedi: {LOGO_PATH}")
            return

        logo = logo.convertToFormat(
            QImage.Format.Format_ARGB32
        )

        # Siyah arka plan piksellerini şeffaf yap.
        for y in range(logo.height()):
            for x in range(logo.width()):
                pixel = logo.pixelColor(x, y)

                if (
                    pixel.red() < 20
                    and pixel.green() < 20
                    and pixel.blue() < 20
                ):
                    pixel.setAlpha(0)
                    logo.setPixelColor(x, y, pixel)

        pixmap = QPixmap.fromImage(logo)

        label.setPixmap(
            pixmap.scaled(
                width,
                height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    # ARAYÜZ STİLLERİ
    def apply_styles(self):
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {BACKGROUND};
            }}

            QWidget#centralWidget {{
                background-color: {BACKGROUND};
                color: {TEXT_DARK};
                font-family: "Segoe UI";
                font-size: 14px;
            }}

            QLabel {{
                color: {TEXT_DARK};
                background: transparent;
                border: none;
            }}

            QLabel#headerTitle {{
                font-family: "Arial";
                font-size: 30px;
                font-weight: 700;
                color: #F87171;
            }}

            QLabel#headerSubtitle {{
                color: {TEXT_SECONDARY};
                font-size: 14px;
                font-weight: 500;
            }}

            QFrame#measurementCard,
            QFrame#panelCard {{
                background-color: {WHITE};
                border: 1px solid {BORDER};
                border-radius: 14px;
            }}

            QLabel#measurementTitle {{
                color: #B8B8B8;
                font-size: 13px;
                font-weight: 600;
            }}

            QLabel#measurementValue {{
                color: {ERROR};
                font-size: 36px;
                font-weight: 700;
            }}

            QLabel#measurementUnit {{
                color: {TEXT_SECONDARY};
                font-size: 14px;
            }}

            QLabel#sectionTitle {{
                color: {TEXT_DARK};
                font-size: 18px;
                font-weight: 700;
                padding-bottom: 5px;
            }}

            QTabWidget#graphTabs::pane {{
                background-color: #151515;
                border: 1px solid #5B2929;
                border-radius: 7px;
                top: -1px;
            }}

            QTabWidget#graphTabs QTabBar::tab {{
                background-color: #241818;
                color: #F0F0F0;
                border: 1px solid #4A2626;
                padding: 10px 14px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-size: 12px;
                font-weight: 600;
            }}

            QTabWidget#graphTabs QTabBar::tab:selected {{
                background-color: #991B1B;
                color: #FFFFFF;
                border-color: #EF4444;
            }}

            QTabWidget#graphTabs QTabBar::tab:hover {{
                background-color: #7F1D1D;
                color: #FFFFFF;
                border-color: #DC2626;
            }}

            QLabel#graphStatus {{
                color: {ERROR};
                background-color: #321B1B;
                border: 1px solid #5B2929;
                border-radius: 7px;
                padding: 7px 10px;
                font-size: 11px;
                font-weight: 700;
            }}

            QFrame#statusCard {{
                background-color: #202020;
                border: 1px solid #3A3A3A;
                border-radius: 12px;
            }}

            QLabel#fieldCaption {{
                color: #A0A0A0;
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 1px;
            }}

            QLabel#testStatus {{
                color: {ERROR};
                font-size: 17px;
                font-weight: 700;
            }}

            QLabel#testType {{
                color: #F0F0F0;
                font-size: 15px;
                font-weight: 800;
                padding: 4px;
            }}

            QFrame#detailCard {{
                background-color: #202020;
                border: 1px solid #383838;
                border-radius: 11px;
            }}

            QLabel#detailValue {{
                color: #F0E9FF;
                font-size: 19px;
                font-weight: 700;
            }}

            QPushButton {{
                background-color: #292929;
                color: {TEXT_DARK};
                border: 1px solid #414141;
                border-radius: 8px;
                padding: 10px 12px;
                font-size: 13px;
                font-weight: 600;
            }}

            QPushButton#primaryButton {{
                background-color: #B91C1C;
                color: white;
                border: 1px solid #EF4444;
                border-radius: 9px;
                padding: 12px;
                font-size: 15px;
                font-weight: 800;
            }}

            QPushButton#primaryButton:hover {{
                background-color: #DC2626;
            }}

            QPushButton#primaryButton:disabled {{
                background-color: #3A2020;
                color: #A0A0A0;
                border: 1px solid #5B2929;
            }}

            QPushButton#finishButton {{
                background-color: #166534;
                color: white;
                border: 1px solid #22C55E;
                border-radius: 9px;
                padding: 11px;
                font-size: 14px;
                font-weight: 700;
            }}

            QPushButton#finishButton:hover {{
                background-color: #15803D;
            }}

            QPushButton#finishButton:disabled {{
                background-color: #202020;
                color: #777777;
                border: 1px solid #383838;
            }}

            QPushButton#secondaryButton {{
                background-color: #B91C1C;
                color: white;
                border: 1px solid #EF4444;
                border-radius: 9px;
                padding: 11px;
                font-size: 14px;
                font-weight: 700;
            }}

            QPushButton#secondaryButton:hover {{
                background-color: #DC2626;
            }}

            QPushButton#connectionButton {{
                background-color: #F0F0F0;
                color: #1B1B1B;
                border: 1px solid #D0D0D0;
                border-radius: 8px;
                padding: 10px 12px;
                font-size: 12px;
                font-weight: 700;
            }}

            QPushButton#connectionButton:hover {{
                background-color: #D9D9D9;
            }}

            QPushButton:disabled {{
                color: #777777;
            }}
        """)

    def closeEvent(self, event):
        self.connection_timer.stop()
        self.measurement_timer.stop()
        self.loading_spinner.stop()
        event.accept()

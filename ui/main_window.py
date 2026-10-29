import json

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QStackedWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
)

from ui.home_page import HomePage
from ui.focus_test_page import MainWindow as ActuatorTestWindow
from ui.fault_detection_page import FaultDetectionPage
from ui.records_page import RecordsPage
from database import FocusDatabase


class TitleBar(QFrame):
    """FOCUS özel pencere başlığı."""

    def __init__(self, window):
        super().__init__(window)

        self.window = window
        self.drag_position = None

        self.setObjectName("titleBar")
        self.setFixedHeight(48)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 6, 0)
        layout.setSpacing(10)

        # Orijinal FOCUS logosu: en solda, siyah arka plan üzerinde.
        self.logo_label = QLabel()
        self.logo_label.setObjectName("titleLogo")
        self.logo_label.setFixedSize(112, 34)
        self.logo_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter
        )

        logo_path = (
            Path(__file__).resolve().parent.parent
            / "assets"
            / "focus_logo.png"
        )

        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))

            if not pixmap.isNull():
                self.logo_label.setPixmap(
                    pixmap.scaled(
                        112,
                        34,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                self.logo_label.setText("FOCUS")
        else:
            self.logo_label.setText("FOCUS")

        layout.addWidget(self.logo_label)

        separator = QLabel("/")
        separator.setObjectName("titleSeparator")
        layout.addWidget(separator)

        app_name = QLabel("ACTUATOR SYSTEM")
        app_name.setObjectName("appName")
        layout.addWidget(app_name)

        layout.addStretch()

        self.min_button = self.make_button("—", "minButton")
        self.max_button = self.make_button("□", "maxButton")
        self.close_button = self.make_button("×", "closeButton")

        self.min_button.clicked.connect(
            self.window.showMinimized
        )
        self.max_button.clicked.connect(
            self.toggle_maximize
        )
        self.close_button.clicked.connect(
            self.window.close
        )

        layout.addWidget(self.min_button)
        layout.addWidget(self.max_button)
        layout.addWidget(self.close_button)

    def make_button(self, text, object_name):
        button = QPushButton(text)
        button.setObjectName(object_name)
        button.setFixedSize(42, 34)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return button

    def toggle_maximize(self):
        if self.window.isMaximized():
            self.window.showNormal()
            self.max_button.setText("□")
        else:
            self.window.showMaximized()
            self.max_button.setText("❐")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if not self.window.isMaximized():
                self.drag_position = (
                    event.globalPosition().toPoint()
                    - self.window.frameGeometry().topLeft()
                )
            else:
                self.drag_position = None

            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            self.drag_position is not None
            and event.buttons() & Qt.MouseButton.LeftButton
            and not self.window.isMaximized()
        ):
            self.window.move(
                event.globalPosition().toPoint()
                - self.drag_position
            )
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_position = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximize()
            event.accept()
            return

        super().mouseDoubleClickEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("FOCUS | ACTUATOR SYSTEM")
        self.resize(1440, 900)
        self.setMinimumSize(1000, 650)

        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
        )

        self.database = FocusDatabase()
        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.title_bar = TitleBar(self)
        root.addWidget(self.title_bar)

        divider = QFrame()
        divider.setObjectName("titleDivider")
        divider.setFixedHeight(1)
        root.addWidget(divider)

        self.pages = QStackedWidget()
        self.pages.setObjectName("pages")
        root.addWidget(self.pages, 1)

        self.home_page = HomePage()
        self.actuator_page = ActuatorTestWindow(database=self.database)
        self.fault_detection_page = FaultDetectionPage(database=self.database)
        self.records_page = RecordsPage(database=self.database)

        # Ana ekrandaki eski logoyu gizle.
        # Üst başlık çubuğundaki yeni logo kalır.
        old_logo = self.home_page.findChild(
            QLabel, "headerLogo"
        )

        if old_logo is not None:
            old_logo.hide()

        self.pages.addWidget(self.home_page)
        self.pages.addWidget(self.actuator_page)
        self.pages.addWidget(self.fault_detection_page)
        self.pages.addWidget(self.records_page)

        self.home_page.actuator_test_requested.connect(
            self.open_actuator_test
        )
        self.home_page.fault_detection_requested.connect(
            self.open_fault_detection
        )
        self.home_page.records_requested.connect(self.open_records)

        self.actuator_page.back_requested.connect(
            self.open_home
        )
        self.fault_detection_page.back_requested.connect(
            self.open_home
        )
        self.records_page.back_requested.connect(self.open_home)
        self.records_page.device_deleted.connect(self._handle_device_deleted)
        self.actuator_page.test_saved.connect(
            self._handle_test_saved
        )
        self.fault_detection_page.hardware_check_requested.connect(
            self.check_fault_hardware
        )
        self.actuator_page.connection_timer.timeout.connect(
            self._sync_fault_hardware_status
        )
        self.actuator_page.connection_manager.line_received.connect(
            self._handle_esp_line
        )

        self.pages.setCurrentWidget(self.home_page)

    def _handle_test_saved(self, serial_number, test_id):
        # Fault/service cases must choose their own serial explicitly.
        self.fault_detection_page.refresh_device_choices()

    def _handle_esp_line(self, line):
        """Accept ESP diagnosis frames using DIAG,{json}\n."""
        if not isinstance(line, str) or not line.startswith("DIAG,"):
            return
        try:
            payload = json.loads(line[5:])
        except (TypeError, ValueError) as error:
            print(f"ESP arıza verisi okunamadı: {error}")
            return
        self.fault_detection_page.receive_esp_diagnostic(payload)

    def _handle_device_deleted(self, serial_number):
        deleted_serial = str(serial_number).strip().casefold()
        active_test_serial = str(self.actuator_page.active_serial or "").strip().casefold()
        if active_test_serial == deleted_serial:
            self.actuator_page.active_serial = None

        active_fault_serial = str(self.fault_detection_page.active_serial or "").strip().casefold()
        if active_fault_serial == deleted_serial:
            self.fault_detection_page.set_device_serial(None)
            self.fault_detection_page.reset_diagnosis()

    def open_actuator_test(self):
        self.pages.setCurrentWidget(self.actuator_page)

    def open_fault_detection(self):
        self.fault_detection_page.set_device_serial(None)
        self._sync_fault_hardware_status()
        self.pages.setCurrentWidget(self.fault_detection_page)

    def open_records(self):
        self.records_page.refresh_devices(clear_selection=True)
        self.pages.setCurrentWidget(self.records_page)

    def check_fault_hardware(self):
        self.actuator_page.check_hardware_connection()
        self._sync_fault_hardware_status()
        self.fault_detection_page.finish_hardware_check()

    def _sync_fault_hardware_status(self):
        connected = self.actuator_page.device_connected
        port = self.actuator_page.device_port
        message = f"● DONANIM BAĞLI ({port})" if connected and port else None
        self.fault_detection_page.set_hardware_status(connected, message)

    def open_home(self):
        self.pages.setCurrentWidget(self.home_page)

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0B0B0D;
            }

            QWidget#centralWidget {
                background-color: #0B0B0D;
                border: 1px solid #29292F;
            }

            QFrame#titleBar {
                background-color: #0B0B0D;
                border: none;
            }

            QLabel#titleLogo {
                background-color: transparent;
                color: #FFFFFF;
                border: none;
                font-size: 20px;
                font-weight: 900;
                letter-spacing: 2px;
            }

            QLabel#appName {
                background-color: transparent;
                color: #F4F4F5;
                font-size: 12px;
                font-weight: 800;
                letter-spacing: 2px;
            }

            QLabel#titleSeparator {
                background-color: transparent;
                color: #E5222A;
                font-size: 16px;
                font-weight: 700;
            }

            QPushButton#minButton,
            QPushButton#maxButton,
            QPushButton#closeButton {
                background-color: transparent;
                color: #B9B9C2;
                border: none;
                border-radius: 5px;
                font-size: 17px;
            }

            QPushButton#minButton:hover,
            QPushButton#maxButton:hover {
                background-color: #29292F;
                color: #FFFFFF;
            }

            QPushButton#closeButton:hover {
                background-color: #E5222A;
                color: #FFFFFF;
            }

            QFrame#titleDivider {
                background-color: #29292F;
                border: none;
            }

            QStackedWidget#pages {
                background-color: #0B0B0D;
                border: none;
            }
        """)

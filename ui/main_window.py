
import sys
from pathlib import Path

from PySide6.QtCore import Qt
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
        self.actuator_page = ActuatorTestWindow()

        # Ana ekrandaki eski logoyu gizle.
        # Üst başlık çubuğundaki yeni logo kalır.
        old_logo = self.home_page.findChild(
            QLabel, "headerLogo"
        )

        if old_logo is not None:
            old_logo.hide()

        self.pages.addWidget(self.home_page)
        self.pages.addWidget(self.actuator_page)

        self.home_page.actuator_test_requested.connect(
            self.open_actuator_test
        )

        self.actuator_page.back_requested.connect(
            self.open_home
        )

        self.pages.setCurrentWidget(self.home_page)

    def open_actuator_test(self):
        self.pages.setCurrentWidget(self.actuator_page)

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

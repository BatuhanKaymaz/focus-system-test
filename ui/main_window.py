
from PySide6.QtWidgets import QMainWindow, QStackedWidget

from ui.home_page import HomePage
from ui.focus_test_page import MainWindow as ActuatorTestWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Focus Test System")
        self.resize(1440, 900)

        self.pages = QStackedWidget()
        self.setCentralWidget(self.pages)

        self.home_page = HomePage()
        self.actuator_page = ActuatorTestWindow()

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

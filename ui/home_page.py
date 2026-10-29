from pathlib import Path
from datetime import datetime

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap, QImage
from ui.responsive import ResponsiveScaler

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QSizePolicy,
)


BACKGROUND = "#0B0B0D"
PANEL = "#141418"
PANEL_HOVER = "#1C1C22"
BORDER = "#29292F"
TEXT = "#F4F4F5"
MUTED = "#92929B"
RED = "#E5222A"
GREEN = "#48D597"


class HomePage(QWidget):
    actuator_test_requested = Signal()
    fault_detection_requested = Signal()
    records_requested = Signal()

    def __init__(self):
        super().__init__()

        self.setObjectName("homePage")
        self.setAttribute(
            Qt.WidgetAttribute.WA_StyledBackground, True
        )

        self.logo_pixmap = self.load_logo()

        self.setup_ui()
        self.apply_styles()
        self._responsive_scaler = ResponsiveScaler(self)

        self.clock_timer = QTimer(self)
        self.clock_timer.setInterval(1000)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start()

        self.update_clock()

    # ------------------------------------------------------
    # LOGO
    # ------------------------------------------------------
    def load_logo(self):
        logo_path = (
            Path(__file__).resolve().parent.parent
            / "assets"
            / "focus_logo.png"
        )

        if not logo_path.exists():
            return QPixmap()

        pixmap = QPixmap(str(logo_path))

        if pixmap.isNull():
            return QPixmap()

        image = pixmap.toImage().convertToFormat(
            QImage.Format.Format_ARGB32
        )

        # Siyah arka planı şeffaflaştır.
        for y in range(image.height()):
            for x in range(image.width()):
                color = image.pixelColor(x, y)

                if (
                    color.red() < 25
                    and color.green() < 25
                    and color.blue() < 25
                ):
                    color.setAlpha(0)
                    image.setPixelColor(x, y, color)

        return QPixmap.fromImage(image)

    def create_logo_label(self, object_name):
        label = QLabel()
        label.setObjectName(object_name)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumSize(0, 0)
        label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        if self.logo_pixmap.isNull():
            label.setText("FOCUS")
            label.setObjectName("logoFallback")

        return label

    def resize_logo(self, label, max_width, max_height):
        if self.logo_pixmap.isNull():
            return

        available_width = max(1, min(label.width(), max_width))
        available_height = max(1, min(label.height(), max_height))

        label.setPixmap(
            self.logo_pixmap.scaled(
                available_width,
                available_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)

        if hasattr(self, "small_logo"):
            self.resize_logo(
                self.small_logo, 150, 48
            )

        if hasattr(self, "large_logo"):
            self.resize_logo(
                self.large_logo, 440, 270
            )

    # ------------------------------------------------------
    # ANA ARAYÜZ
    # ------------------------------------------------------
    def setup_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.content_widget = QWidget()
        self.content_widget.setObjectName("homeContent")
        self.content_widget.setMinimumSize(0, 0)
        outer_layout.addWidget(self.content_widget)

        main = QVBoxLayout(self.content_widget)
        main.setContentsMargins(20, 12, 20, 10)
        main.setSpacing(0)

        # HEADER
        header = QHBoxLayout()
        header.setSpacing(10)

        self.small_logo = self.create_logo_label("headerLogo")
        self.small_logo.setFixedHeight(48)
        self.small_logo.setMinimumWidth(0)
        self.small_logo.setMaximumWidth(160)
        self.small_logo.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter
        )

        header.addWidget(self.small_logo, 1)
        header.addStretch(1)

        time_layout = QVBoxLayout()
        time_layout.setSpacing(2)

        self.clock_label = QLabel("--:--:--")
        self.clock_label.setObjectName("clockLabel")
        self.clock_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )

        self.date_label = QLabel("--")
        self.date_label.setObjectName("dateLabel")
        self.date_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )

        time_layout.addWidget(self.clock_label)
        time_layout.addWidget(self.date_label)
        header.addLayout(time_layout)

        self.system_status = QLabel("● SİSTEM HAZIR")
        self.system_status.setObjectName("systemStatus")
        self.system_status.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        header.addWidget(self.system_status)

        main.addLayout(header)
        main.addSpacing(10)

        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFixedHeight(1)
        main.addWidget(separator)

        # HERO
        main.addSpacing(12)

        hero = QFrame()
        hero.setObjectName("hero")
        hero.setMinimumWidth(0)
        hero.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(12, 8, 12, 8)
        hero_layout.setSpacing(8)

        hero_left = QVBoxLayout()
        hero_left.setSpacing(0)

        eyebrow = QLabel("FOCUS  /  ACTUATOR SYSTEMS")
        eyebrow.setObjectName("eyebrow")
        eyebrow.setWordWrap(True)
        hero_left.addWidget(eyebrow)

        hero_left.addSpacing(12)

        title = QLabel("Yerli Üretim,")
        title.setObjectName("pageTitle")
        title.setWordWrap(True)
        hero_left.addWidget(title)

        title_second = QLabel("Küresel Kalite.")
        title_second.setObjectName("pageTitleAccent")
        title_second.setWordWrap(True)
        hero_left.addWidget(title_second)

        hero_left.addSpacing(10)

        subtitle = QLabel("Aktüatör Kontrol Merkezi")
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)
        hero_left.addWidget(subtitle)

        hero_left.addSpacing(8)

        description = QLabel(
            "Test süreçlerini yönet, ölçüm ekranına eriş "
            "ve aktüatör performansını tek noktadan takip et."
        )
        description.setObjectName("pageDescription")
        description.setWordWrap(True)
        description.setMaximumWidth(470)
        hero_left.addWidget(description)

        hero_left.addStretch(1)

        hero_layout.addLayout(hero_left, 3)

        self.large_logo = self.create_logo_label("largeLogo")
        self.large_logo.setMinimumWidth(0)
        self.large_logo.setMinimumHeight(140)

        hero_layout.addWidget(self.large_logo, 2)

        main.addWidget(hero)

        # KISA BİLGİ KARTLARI
        main.addSpacing(10)

        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(10)

        self.create_summary_card(
            summary_layout,
            "01",
            "TEST MODÜLÜ",
            "Aktüatör performans testi",
            "KULLANIMA HAZIR",
            GREEN,
        )

        self.create_summary_card(
            summary_layout,
            "02",
            "ARIZA TESPİTİ",
            "Röle, optokuplör ve kablolama bağlantı kontrolleri",
            "ARAYÜZ HAZIR",
            "#F2C94C",
        )

        main.addLayout(summary_layout)

        # MODÜLLER
        main.addSpacing(14)

        section_header = QHBoxLayout()
        section_header.setSpacing(8)

        section_title = QLabel("İŞLEM MODÜLLERİ")
        section_title.setObjectName("sectionTitle")
        section_header.addWidget(section_title)

        section_header.addStretch(1)

        section_count = QLabel("03 AKTİF  /  03 MODÜL")
        section_count.setObjectName("sectionCount")
        section_count.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )
        section_header.addWidget(section_count)

        main.addLayout(section_header)
        main.addSpacing(8)

        cards = QHBoxLayout()
        cards.setSpacing(12)

        self.actuator_card = self.create_module_card(
            number="01",
            title="Aktüatör Testi",
            description=(
                "Tork, akım, gerilim, sıcaklık ve dönüş hızı "
                "ölçümlerini takip et. Test ekranına geç "
                "ve ölçüm sürecini başlat."
            ),
            status="TEST MODÜLÜNÜ AÇ",
            active=True,
        )

        self.diagnostics_card = self.create_module_card(
            number="02",
            title="Arıza Tespiti",
            description=(
                "Röle, optokuplör ve kablolama "
                "bağlantılarını kontrol et."
            ),
            status="ARIZA TESPİTİNİ AÇ",
            active=True,
        )

        self.records_card = self.create_module_card(
            number="03",
            title="Kayıt Geçmişi",
            description=(
                "Kartları seri numarasına göre bul; test ve arıza "
                "kayıtlarını incele, seçtiklerini sil."
            ),
            status="KAYIT GEÇMİŞİNİ AÇ",
            active=True,
        )

        self.actuator_card.clicked.connect(
            self.actuator_test_requested.emit
        )
        self.diagnostics_card.clicked.connect(
            self.fault_detection_requested.emit
        )
        self.records_card.clicked.connect(self.records_requested.emit)

        cards.addWidget(self.actuator_card, 1)
        cards.addWidget(self.diagnostics_card, 1)
        cards.addWidget(self.records_card, 1)

        main.addLayout(cards)
        main.addStretch(1)

        # FOOTER
        main.addSpacing(12)

        footer_line = QFrame()
        footer_line.setObjectName("separator")
        footer_line.setFixedHeight(1)
        main.addWidget(footer_line)

        main.addSpacing(7)

        footer = QHBoxLayout()
        footer.setSpacing(8)

        footer_left = QLabel("FOCUS  /  ACTUATOR SYSTEMS")
        footer_left.setObjectName("footerText")
        footer.addWidget(footer_left)

        footer.addStretch(1)

        self.footer_status = QLabel("CONTROL CENTER  •  v1.0")
        self.footer_status.setObjectName("footerText")
        self.footer_status.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )
        footer.addWidget(self.footer_status)

        main.addLayout(footer)

    # ------------------------------------------------------
    # BİLGİ KARTI
    # ------------------------------------------------------
    def create_summary_card(
        self,
        parent_layout,
        number,
        title,
        description,
        status,
        status_color,
    ):
        card = QFrame()
        card.setObjectName("summaryCard")
        card.setMinimumWidth(0)
        card.setMinimumHeight(72)
        card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(3)

        top = QHBoxLayout()
        top.setSpacing(5)

        number_label = QLabel(number)
        number_label.setObjectName("summaryNumber")
        top.addWidget(number_label)

        top.addStretch(1)

        status_label = QLabel(status)
        status_label.setObjectName("summaryStatus")
        status_label.setStyleSheet(
            f"color: {status_color};"
        )
        status_label.setWordWrap(True)
        status_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )
        top.addWidget(status_label)

        layout.addLayout(top)

        title_label = QLabel(title)
        title_label.setObjectName("summaryTitle")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        description_label = QLabel(description)
        description_label.setObjectName("summaryDescription")
        description_label.setWordWrap(True)
        layout.addWidget(description_label)

        parent_layout.addWidget(card, 1)

    # ------------------------------------------------------
    # MODÜL KARTI
    # ------------------------------------------------------
    def create_module_card(
        self,
        number,
        title,
        description,
        status,
        active=True,
    ):
        card = QPushButton()
        card.setObjectName(
            "activeCard" if active else "inactiveCard"
        )

        card.setCursor(
            Qt.CursorShape.PointingHandCursor
            if active
            else Qt.CursorShape.ArrowCursor
        )
        card.setEnabled(active)
        card.setMinimumWidth(0)
        card.setMinimumHeight(110)
        card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        card.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(0)

        top = QHBoxLayout()

        number_label = QLabel(number)
        number_label.setObjectName(
            "activeNumber" if active else "inactiveNumber"
        )
        number_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )
        top.addWidget(number_label)

        top.addStretch(1)

        icon = QLabel("↗" if active else "—")
        icon.setObjectName(
            "activeIcon" if active else "inactiveIcon"
        )
        icon.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )
        top.addWidget(icon)

        layout.addLayout(top)
        layout.addSpacing(5)

        title_label = QLabel(title)
        title_label.setObjectName(
            "activeCardTitle"
            if active
            else "inactiveCardTitle"
        )
        title_label.setWordWrap(True)
        title_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )
        layout.addWidget(title_label)

        layout.addSpacing(4)

        description_label = QLabel(description)
        description_label.setObjectName(
            "activeCardDescription"
            if active
            else "inactiveCardDescription"
        )
        description_label.setWordWrap(True)
        description_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )
        layout.addWidget(description_label)

        layout.addStretch(1)

        bottom_line = QFrame()
        bottom_line.setObjectName(
            "activeCardLine"
            if active
            else "inactiveCardLine"
        )
        bottom_line.setFixedHeight(2)
        layout.addWidget(bottom_line)

        layout.addSpacing(6)

        bottom = QHBoxLayout()

        status_label = QLabel(status)
        status_label.setObjectName(
            "activeCardStatus"
            if active
            else "inactiveCardStatus"
        )
        status_label.setWordWrap(True)
        status_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )
        bottom.addWidget(status_label)

        bottom.addStretch(1)

        if active:
            dot = QLabel("●")
            dot.setObjectName("activeDot")
            dot.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents
            )
            bottom.addWidget(dot)

        layout.addLayout(bottom)

        return card

    # ------------------------------------------------------
    # CANLI SAAT
    # ------------------------------------------------------
    def update_clock(self):
        now = datetime.now()
        self.clock_label.setText(now.strftime("%H:%M:%S"))
        self.date_label.setText(now.strftime("%d.%m.%Y"))

    # ------------------------------------------------------
    # STİLLER
    # ------------------------------------------------------
    def apply_styles(self):
        self.setStyleSheet("""
            QWidget#homePage,
            QWidget#homeContent {
                background-color: #0B0B0D;
                color: #F4F4F5;
                font-family: "Segoe UI";
            }

            QScrollArea#homeScrollArea {
                background-color: #0B0B0D;
                border: none;
            }

            QLabel {
                background-color: transparent;
                border: none;
            }

            QLabel#headerLogo {
                color: #FFFFFF;
                font-size: 24px;
                font-weight: 800;
            }

            QLabel#logoFallback {
                color: #FFFFFF;
                font-size: 28px;
                font-weight: 900;
                background-color: transparent;
                border: none;
            }

            QLabel#largeLogo {
                background-color: transparent;
                border: none;
                padding: 0px;
            }

            QLabel#clockLabel {
                color: #FFFFFF;
                font-size: 20px;
                font-weight: 700;
            }

            QLabel#dateLabel {
                color: #92929B;
                font-size: 11px;
            }

            QLabel#systemStatus {
                color: #48D597;
                background-color: #12251C;
                border: 1px solid #244735;
                border-radius: 7px;
                padding: 7px 9px;
                font-size: 10px;
                font-weight: 800;
            }

            QFrame#separator {
                background-color: #29292F;
                border: none;
            }

            QFrame#hero {
                background-color: #0B0B0D;
                border: none;
            }

            QLabel#eyebrow {
                color: #F0444B;
                font-size: 10px;
                font-weight: 800;
            }

            QLabel#pageTitle {
                color: #FAFAFA;
                font-size: 36px;
                font-weight: 800;
            }

            QLabel#pageTitleAccent {
                color: #E5222A;
                font-size: 36px;
                font-weight: 800;
            }

            QLabel#pageSubtitle {
                color: #DADAE0;
                font-size: 16px;
                font-weight: 700;
            }

            QLabel#pageDescription {
                color: #92929B;
                font-size: 12px;
            }

            QFrame#summaryCard {
                background-color: #141418;
                border: 1px solid #29292F;
                border-radius: 8px;
            }

            QFrame#summaryCard:hover {
                background-color: #1C1C22;
                border: 1px solid #45454D;
            }

            QLabel#summaryNumber {
                color: #F0444B;
                font-size: 10px;
                font-weight: 800;
            }

            QLabel#summaryStatus {
                font-size: 9px;
                font-weight: 800;
            }

            QLabel#summaryTitle {
                color: #F4F4F5;
                font-size: 11px;
                font-weight: 700;
            }

            QLabel#summaryDescription {
                color: #92929B;
                font-size: 9px;
            }

            QLabel#sectionTitle {
                color: #D8D8DC;
                font-size: 10px;
                font-weight: 800;
            }

            QLabel#sectionCount {
                color: #66666E;
                font-size: 10px;
                font-weight: 700;
            }

            QPushButton#activeCard {
                text-align: left;
                background-color: #171316;
                border: 1px solid #612126;
                border-radius: 9px;
            }

            QPushButton#activeCard:hover {
                background-color: #241518;
                border: 1px solid #E5222A;
            }

            QPushButton#activeCard:pressed {
                background-color: #301417;
                border: 1px solid #FF5259;
            }

            QPushButton#activeCard:focus {
                border: 1px solid #E5222A;
            }

            QPushButton#inactiveCard {
                text-align: left;
                background-color: #111114;
                border: 1px solid #29292F;
                border-radius: 9px;
            }

            QLabel#activeNumber {
                color: #F0444B;
                font-size: 11px;
                font-weight: 800;
            }

            QLabel#inactiveNumber {
                color: #55555B;
                font-size: 11px;
                font-weight: 800;
            }

            QLabel#activeIcon {
                color: #F0444B;
                font-size: 20px;
                font-weight: 700;
            }

            QLabel#inactiveIcon {
                color: #55555B;
                font-size: 20px;
            }

            QLabel#activeCardTitle {
                color: #FFFFFF;
                font-size: 17px;
                font-weight: 750;
            }

            QLabel#inactiveCardTitle {
                color: #77777E;
                font-size: 17px;
                font-weight: 700;
            }

            QLabel#activeCardDescription {
                color: #BEB3B5;
                font-size: 10px;
            }

            QLabel#inactiveCardDescription {
                color: #77777E;
                font-size: 10px;
            }

            QFrame#activeCardLine {
                background-color: #E5222A;
                border: none;
            }

            QFrame#inactiveCardLine {
                background-color: #303035;
                border: none;
            }

            QLabel#activeCardStatus {
                color: #FFFFFF;
                font-size: 9px;
                font-weight: 800;
            }

            QLabel#inactiveCardStatus {
                color: #65656C;
                font-size: 9px;
                font-weight: 800;
            }

            QLabel#activeDot {
                color: #48D597;
                font-size: 9px;
            }

            QLabel#footerText {
                color: #626269;
                font-size: 9px;
                font-weight: 700;
            }
        """)
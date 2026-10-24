
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap, QImage
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

    def __init__(self):
        super().__init__()

        self.setObjectName("homePage")
        self.setAttribute(
            Qt.WidgetAttribute.WA_StyledBackground, True
        )

        self.setup_ui()
        self.apply_styles()

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
        # Beyaz ve kırmızı logo yazılarını koru.
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

    def create_logo_label(
        self,
        max_width,
        max_height,
        object_name,
    ):
        label = QLabel()
        label.setObjectName(object_name)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumSize(0, 0)
        label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        pixmap = self.load_logo()

        if not pixmap.isNull():
            label.setPixmap(
                pixmap.scaled(
                    max_width,
                    max_height,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            label.setText("FOCUS")
            label.setObjectName("logoFallback")

        return label

    # ------------------------------------------------------
    # ANA ARAYUZ
    # ------------------------------------------------------
    def setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(32, 20, 32, 14)
        main.setSpacing(0)

        # HEADER
        header = QHBoxLayout()
        header.setSpacing(14)

        small_logo = self.create_logo_label(
            125, 44, "headerLogo"
        )
        small_logo.setFixedSize(130, 48)
        small_logo.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter
        )

        header.addWidget(small_logo)
        header.addStretch()

        time_layout = QVBoxLayout()
        time_layout.setSpacing(2)

        self.clock_label = QLabel("--:--:--")
        self.clock_label.setObjectName("clockLabel")
        self.clock_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.date_label = QLabel("--")
        self.date_label.setObjectName("dateLabel")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        time_layout.addWidget(self.clock_label)
        time_layout.addWidget(self.date_label)
        header.addLayout(time_layout)

        self.system_status = QLabel("● SİSTEM HAZIR")
        self.system_status.setObjectName("systemStatus")
        self.system_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self.system_status)

        main.addLayout(header)
        main.addSpacing(13)

        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFixedHeight(1)
        main.addWidget(separator)

        # --------------------------------------------------
        # HERO: BUYUK SLOGAN + BUYUK LOGO
        # --------------------------------------------------
        main.addSpacing(12)

        hero = QFrame()
        hero.setObjectName("hero")
        hero.setMinimumHeight(270)

        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(14, 8, 14, 8)
        hero_layout.setSpacing(8)

        hero_left = QVBoxLayout()
        hero_left.setSpacing(0)

        eyebrow = QLabel("FOCUS  /  ACTUATOR SYSTEMS")
        eyebrow.setObjectName("eyebrow")
        hero_left.addWidget(eyebrow)

        hero_left.addSpacing(17)

        title = QLabel("Yerli Üretim,")
        title.setObjectName("pageTitle")
        hero_left.addWidget(title)

        title_second = QLabel("Küresel Kalite.")
        title_second.setObjectName("pageTitleAccent")
        hero_left.addWidget(title_second)

        hero_left.addSpacing(14)

        subtitle = QLabel("Aktüatör Kontrol Merkezi")
        subtitle.setObjectName("pageSubtitle")
        hero_left.addWidget(subtitle)

        hero_left.addSpacing(10)

        description = QLabel(
            "Test süreçlerini yönet, ölçüm ekranına eriş "
            "ve aktüatör performansını tek noktadan takip et."
        )
        description.setObjectName("pageDescription")
        description.setWordWrap(True)
        description.setMaximumWidth(470)
        hero_left.addWidget(description)

        hero_left.addStretch()

        hero_layout.addLayout(hero_left, 3)

        # Logo kendi kutusu olmadan doğrudan arka planda.
        self.large_logo = self.create_logo_label(
            440, 270, "largeLogo"
        )
        self.large_logo.setMinimumWidth(250)

        hero_layout.addWidget(self.large_logo, 2)

        main.addWidget(hero)

        # --------------------------------------------------
        # KISA BILGI KARTLARI
        # --------------------------------------------------
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
            "KART DİAGNOSTİĞİ",
            "Elektronik kart inceleme",
            "GELİŞTİRİLİYOR",
            "#F2C94C",
        )

        main.addLayout(summary_layout)

        # --------------------------------------------------
        # MODULLER
        # --------------------------------------------------
        main.addSpacing(14)

        section_header = QHBoxLayout()

        section_title = QLabel("İŞLEM MODÜLLERİ")
        section_title.setObjectName("sectionTitle")
        section_header.addWidget(section_title)

        section_header.addStretch()

        section_count = QLabel("01 AKTİF  /  02 MODÜL")
        section_count.setObjectName("sectionCount")
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
            title="Kart Diagnostiği",
            description=(
                "Elektronik kontrol kartının durumunu "
                "incelemek ve donanım arızalarını "
                "araştırmak için kullanılacak modül."
            ),
            status="YAKINDA",
            active=False,
        )

        self.actuator_card.clicked.connect(
            self.actuator_test_requested.emit
        )

        cards.addWidget(self.actuator_card, 3)
        cards.addWidget(self.diagnostics_card, 2)

        main.addLayout(cards)
        main.addStretch(1)

        # FOOTER
        footer_line = QFrame()
        footer_line.setObjectName("separator")
        footer_line.setFixedHeight(1)
        main.addWidget(footer_line)

        main.addSpacing(7)

        footer = QHBoxLayout()

        footer_left = QLabel("FOCUS  /  ACTUATOR SYSTEMS")
        footer_left.setObjectName("footerText")
        footer.addWidget(footer_left)

        footer.addStretch()

        self.footer_status = QLabel("CONTROL CENTER  •  v1.0")
        self.footer_status.setObjectName("footerText")
        footer.addWidget(self.footer_status)

        main.addLayout(footer)

    # ------------------------------------------------------
    # BILGI KARTI
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
        card.setMinimumHeight(72)
        card.setMaximumHeight(84)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(3)

        top = QHBoxLayout()

        number_label = QLabel(number)
        number_label.setObjectName("summaryNumber")
        top.addWidget(number_label)

        top.addStretch()

        status_label = QLabel(status)
        status_label.setObjectName("summaryStatus")
        status_label.setStyleSheet(
            f"color: {status_color};"
        )
        top.addWidget(status_label)

        layout.addLayout(top)

        title_label = QLabel(title)
        title_label.setObjectName("summaryTitle")
        layout.addWidget(title_label)

        description_label = QLabel(description)
        description_label.setObjectName("summaryDescription")
        description_label.setWordWrap(True)
        layout.addWidget(description_label)

        parent_layout.addWidget(card, 1)

    # ------------------------------------------------------
    # MODUL KARTI
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
        card.setMinimumHeight(125)
        card.setMaximumHeight(150)
        card.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 10, 16, 10)
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

        top.addStretch()

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

        layout.addStretch()

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
        status_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )
        bottom.addWidget(status_label)

        bottom.addStretch()

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
    # SAAT
    # ------------------------------------------------------
    def update_clock(self):
        now = datetime.now()
        self.clock_label.setText(now.strftime("%H:%M:%S"))
        self.date_label.setText(now.strftime("%d.%m.%Y"))

    # ------------------------------------------------------
    # STIL
    # ------------------------------------------------------
    def apply_styles(self):
        self.setStyleSheet("""
            QWidget#homePage {
                background-color: #0B0B0D;
                color: #F4F4F5;
                font-family: "Segoe UI";
            }

            QLabel {
                background-color: transparent;
                border: none;
            }

            QLabel#headerLogo {
                color: #FFFFFF;
                font-size: 24px;
                font-weight: 800;
                letter-spacing: 2px;
            }

            QLabel#logoFallback {
                color: #FFFFFF;
                font-size: 32px;
                font-weight: 900;
                letter-spacing: 3px;
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
                padding: 8px 11px;
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
                border-radius: 0px;
            }

            QLabel#eyebrow {
                color: #F0444B;
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 2px;
            }

            QLabel#pageTitle {
                color: #FAFAFA;
                font-size: 44px;
                font-weight: 800;
            }

            QLabel#pageTitleAccent {
                color: #E5222A;
                font-size: 44px;
                font-weight: 800;
            }

            QLabel#pageSubtitle {
                color: #DADAE0;
                font-size: 18px;
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
                letter-spacing: 2px;
            }

            QLabel#sectionCount {
                color: #66666E;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1px;
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
                letter-spacing: 2px;
            }

            QLabel#inactiveNumber {
                color: #55555B;
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 2px;
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
                letter-spacing: 1px;
            }

            QLabel#inactiveCardStatus {
                color: #65656C;
                font-size: 9px;
                font-weight: 800;
                letter-spacing: 1px;
            }

            QLabel#activeDot {
                color: #48D597;
                font-size: 9px;
            }

            QLabel#footerText {
                color: #626269;
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 1px;
            }
        """)

import json
import re
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from database import FocusDatabase


BG = "#0B0B0D"
PANEL = "#141418"
BORDER = "#29292F"
TEXT = "#F4F4F5"
MUTED = "#92929B"
RED = "#E5222A"
GREEN = "#48D597"
YELLOW = "#F2C94C"
BLUE = "#67C9F3"


def resource_path(relative_path):
    """Resolve an asset path in both source and PyInstaller builds."""
    base_path = getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)
    return Path(base_path) / relative_path


class FaultDetectionPage(QWidget):
    """Guided fault-troubleshooting page with database-backed service records."""

    back_requested = Signal()
    hardware_check_requested = Signal()

    def __init__(self, database=None, parent=None):
        super().__init__(parent)
        self.database = database or FocusDatabase()
        self.active_serial = None
        self.current_diagnosis = None
        self.component_results = {}
        self.hardware_connected = None
        self._ui_scale = 1.0
        self._scale_layouts = []
        self.setObjectName("faultDetectionPage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._build_ui()
        self._apply_styles()
        self.refresh_device_choices()

    def _build_ui(self):
        root = QVBoxLayout(self)
        self.root_layout = root
        root.setContentsMargins(20, 14, 20, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(12)
        self._scale_layouts.append((header, 0, 12))
        self.logo_label = QLabel()
        self.logo_label.setObjectName("pageLogo")
        self.logo_label.setFixedSize(112, 46)
        logo_path = resource_path("assets/focus_logo.png")
        pixmap = QPixmap(str(logo_path))
        if not pixmap.isNull():
            self.logo_label.setPixmap(pixmap.scaled(
                112, 46, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
        else:
            self.logo_label.setText("FOCUS")
        header.addWidget(self.logo_label)

        title_wrap = QVBoxLayout()
        title_wrap.setSpacing(2)
        title = QLabel("ARIZA TESPİTİ")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Kablo, röle ve B17 optokuplör kontrolleri")
        subtitle.setObjectName("mutedLabel")
        title_wrap.addWidget(title)
        title_wrap.addWidget(subtitle)
        header.addLayout(title_wrap)
        header.addStretch(1)

        self.connection_badge = QLabel("● DONANIM BAĞLI DEĞİL")
        self.connection_badge.setObjectName("connectionBadge")
        self.connection_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.connection_badge.setWordWrap(True)
        header.addWidget(self.connection_badge)
        self.check_hardware_button = QPushButton("BAĞLANTIYI KONTROL ET")
        self.check_hardware_button.setObjectName("connectionButton")
        self.check_hardware_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.check_hardware_button.clicked.connect(self.request_hardware_check)
        header.addWidget(self.check_hardware_button)
        back_button = QPushButton("← ANA SAYFA")
        back_button.setObjectName("secondaryButton")
        back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        back_button.clicked.connect(self.back_requested.emit)
        header.addWidget(back_button)
        root.addLayout(header)

        serial_row = QHBoxLayout()
        serial_row.setSpacing(9)
        serial_caption = QLabel("SERİ NO")
        serial_caption.setObjectName("activeSerial")
        serial_row.addWidget(serial_caption)
        self.select_serial_button = QPushButton("SERİ NO SEÇ")
        self.select_serial_button.setObjectName("secondaryButton")
        self.select_serial_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_serial_button.setMinimumWidth(150)
        self.select_serial_button.setMaximumWidth(230)
        self.select_serial_button.clicked.connect(self.open_serial_selector)
        serial_row.addWidget(self.select_serial_button)
        self.active_device_label = QLabel("Kart seçilmedi")
        self.active_device_label.setObjectName("mutedLabel")
        serial_row.addWidget(self.active_device_label, 1)
        root.addLayout(serial_row)

        summary = QHBoxLayout()
        summary.setSpacing(10)
        self.status_card, self.status_value = self._summary_card("DURUM", "VERİ BEKLENİYOR", YELLOW)
        self.error_card, self.error_value = self._summary_card("HATA KODU", "—", TEXT)
        self.source_card, self.source_value = self._summary_card("OLASI KAYNAK", "—", BLUE)
        summary.addWidget(self.status_card, 1)
        summary.addWidget(self.error_card, 1)
        summary.addWidget(self.source_card, 1)
        root.addLayout(summary)

        diagnosis_panel = QFrame()
        diagnosis_panel.setObjectName("panel")
        diagnosis_layout = QVBoxLayout(diagnosis_panel)
        diagnosis_layout.setContentsMargins(16, 14, 16, 14)
        diagnosis_layout.setSpacing(7)
        diagnosis_title = QLabel("ÖN TANI")
        diagnosis_title.setObjectName("sectionTitle")
        diagnosis_layout.addWidget(diagnosis_title)
        self.diagnosis_text = QLabel(
            "ESP/Modbus hata bilgisi bağlandığında olası kaynak ve önerilen kontrol burada gösterilecek."
        )
        self.diagnosis_text.setObjectName("diagnosisText")
        self.diagnosis_text.setWordWrap(True)
        diagnosis_layout.addWidget(self.diagnosis_text)
        self.diagnosis_detail = QLabel("Henüz bir arıza kodu veya durum bilgisi alınmadı.")
        self.diagnosis_detail.setObjectName("mutedLabel")
        self.diagnosis_detail.setWordWrap(True)
        diagnosis_layout.addWidget(self.diagnosis_detail)
        modbus_title = QLabel("İŞLEMCİ / MODBUS VERİLERİ")
        modbus_title.setObjectName("sectionTitle")
        diagnosis_layout.addWidget(modbus_title)
        self.modbus_data_label = QLabel("Henüz Modbus verisi alınmadı.")
        self.modbus_data_label.setObjectName("modbusData")
        self.modbus_data_label.setWordWrap(True)
        diagnosis_layout.addWidget(self.modbus_data_label)
        root.addWidget(diagnosis_panel)

        checks_title = QLabel("ESP KONTROL SONUÇLARI")
        checks_title.setObjectName("sectionTitle")
        root.addWidget(checks_title)
        checks = QGridLayout()
        self.checks_layout = checks
        checks.setSpacing(10)
        self.recommendation_cards = {}
        recommendations = [
            ("cable", "KART / PIN KONNEKTÖRÜ", "Kontrol kartı çıkışları ile pin konnektöründeki kablo ve pin eşleşmesini kontrol edecek.", BLUE),
            ("relay", "HARİCİ RÖLE KARTI", "PLC konnektörüne giden röle girişini ve kontak geri bildirimini kontrol edecek.", YELLOW),
            ("b17", "HARİCİ B17 MODÜLÜ", "Kontrol kartı ile aktüatör arasındaki B17 giriş/çıkış geri bildirimini kontrol edecek.", RED),
            ("processor", "İŞLEMCİ / MODBUS", "ESP işlemci durumunu, hata kodlarını ve Modbus register verilerini değerlendirecek.", GREEN),
        ]
        self._recommendation_order = []
        for index, (key, heading, description, color) in enumerate(recommendations):
            card = self._recommendation_card(key, heading, description, color)
            self.recommendation_cards[key] = card
            self._recommendation_order.append(card["card"])
            checks.addWidget(card["card"], 0, index)
        root.addLayout(checks, 1)

        footer = QFrame()
        footer.setObjectName("panel")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(12, 10, 12, 10)
        footer_layout.setSpacing(8)
        self.manual_error_code = QLineEdit()
        self.manual_error_code.setObjectName("technicianNotes")
        self.manual_error_code.setPlaceholderText("Servis kodu")
        self.manual_error_code.setMaximumWidth(150)
        footer_layout.addWidget(self.manual_error_code)
        self.manual_source_selector = QComboBox()
        self.manual_source_selector.setObjectName("manualSourceSelector")
        self.manual_source_selector.addItems([
            "Kart / Pin Konnektörü", "Harici Röle Kartı", "Harici B17 Modülü",
            "İşlemci / Modbus", "Diğer",
        ])
        footer_layout.addWidget(self.manual_source_selector)
        self.technician_notes = QLineEdit()
        self.technician_notes.setObjectName("technicianNotes")
        self.technician_notes.setPlaceholderText("Servis bulgusu / teknisyen notu")
        footer_layout.addWidget(self.technician_notes, 1)
        self.save_diagnosis_button = QPushButton("ARIZA KAYDINI KAYDET")
        self.save_diagnosis_button.setObjectName("saveButton")
        self.save_diagnosis_button.setEnabled(False)
        self.save_diagnosis_button.clicked.connect(self.save_diagnosis)
        footer_layout.addWidget(self.save_diagnosis_button)
        root.addWidget(footer)

    def _summary_card(self, title, value, color):
        frame = QFrame()
        frame.setObjectName("summaryCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)
        caption = QLabel(title)
        caption.setObjectName("mutedLabel")
        value_label = QLabel(value)
        value_label.setObjectName("summaryValue")
        value_label.setStyleSheet(f"color: {color};")
        value_label.setWordWrap(True)
        layout.addWidget(caption)
        layout.addWidget(value_label)
        return frame, value_label

    def _recommendation_card(self, key, heading, description, color):
        frame = QFrame()
        frame.setObjectName("recommendationCard")
        frame.setProperty("recommended", False)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        title = QLabel(heading)
        title.setObjectName("recommendationTitle")
        title.setStyleSheet(f"color: {color};")
        badge = QLabel("ESP SONUCU BEKLENİYOR")
        badge.setObjectName("pendingBadge")
        layout.addWidget(title)
        layout.addWidget(badge)
        layout.addStretch(1)
        return {"card": frame, "badge": badge}

    def refresh_device_choices(self):
        self.available_serials = [
            device["serial_number"] for device in self.database.find_devices()
        ]

    def open_serial_selector(self):
        dialog = QDialog(
            self,
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint,
        )
        dialog.setObjectName("serialPickerDialog")
        dialog.setWindowTitle("Seri numarası seç")
        dialog.setModal(True)
        dialog.setMinimumWidth(420)
        dialog.setStyleSheet("""
            QDialog#serialPickerDialog { background: #0B0B0D; color: #F4F4F5; border: 1px solid #38383F; border-radius: 11px; }
            QLabel { color: #F4F4F5; background: transparent; border: none; }
            QLabel#pickerTitle { color: #FFFFFF; font-size: 16px; font-weight: 800; }
            QLabel#pickerHint { color: #92929B; font-size: 11px; }
            QLineEdit { background: #101014; color: #F4F4F5; border: 1px solid #404040; border-radius: 7px; padding: 9px; font-size: 12px; }
            QLineEdit:focus { border-color: #E5222A; }
            QListWidget { background: #101014; color: #F4F4F5; border: 1px solid #29292F; border-radius: 7px; selection-background-color: #4A171B; selection-color: #FFFFFF; }
            QListWidget::item { padding: 9px; border-bottom: 1px solid #242429; }
            QPushButton { background: #202020; color: #F5F5F5; border: 1px solid #404040; border-radius: 7px; padding: 9px 14px; font-size: 12px; font-weight: 700; }
            QPushButton:hover { background: #303030; border-color: #737373; }
            QPushButton#chooseSerialButton { background: #7F1D1D; border-color: #B91C1C; color: #FFFFFF; }
            QPushButton#chooseSerialButton:hover { background: #991B1B; border-color: #EF4444; }
            QPushButton#generateSerialButton { background: #10232B; border-color: #155E75; color: #7DD3FC; }
            QPushButton#generateSerialButton:hover { background: #123744; border-color: #38BDF8; }
        """)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        title = QLabel("KART SERİ NUMARASI")
        title.setObjectName("pickerTitle")
        layout.addWidget(title)
        hint = QLabel("Listeden kayıtlı kartı seçin veya yeni seri numarasını yazın.")
        hint.setObjectName("pickerHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        search = QLineEdit()
        search.setPlaceholderText("Ara veya seri numarası gir...")
        search.clear()
        layout.addWidget(search)
        device_list = QListWidget()
        for serial in self.available_serials:
            device_list.addItem(QListWidgetItem(serial))
        device_list.setMinimumHeight(190)
        device_list.setCurrentRow(-1)
        layout.addWidget(device_list, 1)

        def filter_serials(text):
            query = str(text).strip().casefold()
            for index in range(device_list.count()):
                item = device_list.item(index)
                item.setHidden(bool(query) and query not in item.text().casefold())

        def choose_item(item):
            if item is not None:
                search.setText(item.text())

        search.textChanged.connect(filter_serials)
        device_list.itemClicked.connect(choose_item)
        device_list.itemDoubleClicked.connect(lambda _item: dialog.accept())
        actions = QHBoxLayout()
        generate = QPushButton("YENİ SERİ NO OLUŞTUR")
        generate.setObjectName("generateSerialButton")
        cancel = QPushButton("VAZGEÇ")
        choose = QPushButton("SERİ NO'YU SEÇ")
        choose.setObjectName("chooseSerialButton")
        actions.addWidget(generate)
        actions.addStretch(1)
        actions.addWidget(cancel)
        actions.addWidget(choose)
        layout.addLayout(actions)

        def generate_and_register_serial():
            serial = None
            for _ in range(100):
                candidate = self.database.generate_serial_number()
                if self.database.get_device(candidate) is None:
                    self.database.create_device(
                        candidate,
                        notes="Servis kabulünde otomatik seri numarası oluşturuldu.",
                    )
                    serial = candidate
                    break
            if serial is None:
                QMessageBox.warning(
                    dialog,
                    "Seri Numarası Oluşturulamadı",
                    "Yeni seri numarası üretilemedi. Lütfen tekrar deneyin.",
                )
                return
            self.refresh_device_choices()
            if not any(device_list.item(i).text() == serial for i in range(device_list.count())):
                device_list.addItem(serial)
            search.setText(serial)

        generate.clicked.connect(generate_and_register_serial)
        cancel.clicked.connect(dialog.reject)
        choose.clicked.connect(dialog.accept)
        search.returnPressed.connect(dialog.accept)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        serial = search.text().strip().upper()
        if not serial and device_list.currentItem():
            serial = device_list.currentItem().text().strip().upper()
        if not serial:
            QMessageBox.warning(self, "Seri Numarası Gerekli", "Bir kart seçin veya seri numarası girin.")
            return
        self.set_device_serial(serial)

    def set_device_serial(self, serial_number):
        serial = str(serial_number).strip().upper() if serial_number else ""
        self.active_serial = serial or None
        self.select_serial_button.setText(serial or "SERİ NO SEÇ")
        self.active_device_label.setText(
            f"Seçili kart: {serial}" if serial else "Kart seçilmedi"
        )
        self.save_diagnosis_button.setEnabled(bool(self.active_serial))
        if not serial:
            self.refresh_device_choices()

    def _on_serial_changed(self, serial_number):
        # Kept as a compatibility hook for callers from older UI versions.
        self.set_device_serial(serial_number)

    def request_hardware_check(self):
        self.check_hardware_button.setEnabled(False)
        self.set_hardware_status(None, "● BAĞLANTI KONTROL EDİLİYOR")
        QTimer.singleShot(250, self.hardware_check_requested.emit)

    def finish_hardware_check(self):
        self.check_hardware_button.setEnabled(True)

    def set_hardware_status(self, connected, message=None):
        if connected is True:
            color, background, border = GREEN, "#101F17", "#2F855A"
            text = message or "● DONANIM BAĞLI"
        elif connected is None:
            color, background, border = YELLOW, "#211B0D", "#927126"
            text = message or "● BAĞLANTI KONTROL EDİLİYOR"
        else:
            color, background, border = RED, "#211012", "#9F3A4B"
            text = message or "● DONANIM BAĞLI DEĞİL"
        self.connection_badge.setText(text)
        self.connection_badge.setStyleSheet(
            f"color: {color}; background-color: {background}; border: 1px solid {border};"
        )
        if connected != self.hardware_connected:
            self.hardware_connected = connected
            state = "waiting" if connected is True else "disconnected" if connected is False else "checking"
            self.set_component_results({key: {"status": state} for key in self.recommendation_cards})

    def show_diagnosis(
        self, error_code, description, likely_source, instructions=None,
        modbus_data=None, component_results=None
    ):
        source = str(likely_source or "").strip().lower()
        selected = None
        if any(word in source for word in ("kablo", "konnektör", "pin", "wiring")):
            selected = "cable"
        elif any(word in source for word in ("röle", "role", "relay")):
            selected = "relay"
        elif any(word in source for word in ("b17", "opto", "optokuplör")):
            selected = "b17"
        elif any(word in source for word in (
            "işlemci", "processor", "cpu", "modbus", "esp", "register",
            "kontrol kartı", "firmware", "yazılım",
        )):
            selected = "processor"

        if isinstance(modbus_data, str):
            try:
                modbus_data = json.loads(modbus_data)
            except (TypeError, ValueError):
                modbus_data = {"Modbus": modbus_data}
        if not isinstance(modbus_data, (dict, list, tuple)):
            modbus_data = {}

        self.current_diagnosis = {
            "error_code": str(error_code or ""),
            "description": str(description or ""),
            "likely_source": str(likely_source or ""),
            "selected_source": selected,
            "modbus_data": modbus_data,
            "instructions": str(instructions or ""),
            "component_results": component_results or {},
        }
        self.modbus_data_label.setText(self._format_modbus_data(modbus_data))
        self.status_value.setText("ÖNERİ HAZIR")
        self.error_value.setText(str(error_code or "—"))
        self.source_value.setText(str(likely_source or "—"))
        self.diagnosis_text.setText(str(description or "Arıza açıklaması alınmadı."))
        self.diagnosis_detail.setText(
            "Önerilen bölgeyi kontrol edin. Kontrol işaretleri ve teknisyen notu servis kaydına eklenir."
        )
        for key, card in self.recommendation_cards.items():
            priority = key == selected
            card["card"].setProperty("recommended", priority)
            card["card"].style().unpolish(card["card"])
            card["card"].style().polish(card["card"])
        self.set_component_results(
            component_results if component_results is not None
            else {key: {"status": "waiting"} for key in self.recommendation_cards}
        )
        self.save_diagnosis_button.setEnabled(bool(self.active_serial))

    def set_component_results(self, results):
        """Update check cards from parsed ESP/Modbus component status data."""
        results = results if isinstance(results, dict) else {}
        aliases = {
            "ok": "healthy", "pass": "healthy", "passed": "healthy",
            "healthy": "healthy", "good": "healthy", "sağlam": "healthy",
            "fault": "fault", "fail": "fault", "failed": "fault",
            "error": "fault", "arıza": "fault",
            "warning": "warning", "warn": "warning", "uyarı": "warning",
            "unavailable": "unavailable", "not_tested": "unavailable",
            "kontrol edilemedi": "unavailable",
            "waiting": "waiting", "pending": "waiting",
            "checking": "checking", "disconnected": "disconnected",
        }
        display = {
            "healthy": ("SAĞLAM", "healthyBadge"),
            "fault": ("ARIZA TESPİT EDİLDİ", "faultBadge"),
            "warning": ("UYARI", "warningBadge"),
            "unavailable": ("KONTROL EDİLEMEDİ", "warningBadge"),
            "checking": ("ESP KONTROL EDİYOR", "warningBadge"),
            "disconnected": ("ESP BAĞLI DEĞİL", "faultBadge"),
            "waiting": ("ESP SONUCU BEKLENİYOR", "pendingBadge"),
        }
        normalized = {}
        for key, card in self.recommendation_cards.items():
            value = results.get(key, {})
            if isinstance(value, dict):
                raw_status = value.get("status", "waiting")
                detail = value.get("details") or value.get("message")
            else:
                raw_status, detail = value, None
            if isinstance(raw_status, bool):
                status = "healthy" if raw_status else "fault"
            else:
                status = aliases.get(str(raw_status).strip().casefold(), "waiting")
            label, badge_name = display[status]
            card["badge"].setText(label)
            card["badge"].setObjectName(badge_name)
            card["badge"].style().unpolish(card["badge"])
            card["badge"].style().polish(card["badge"])
            card["card"].setProperty("componentStatus", status)
            card["card"].style().unpolish(card["card"])
            card["card"].style().polish(card["card"])
            normalized[key] = {"status": status, "details": str(detail or "")}
        self.component_results = normalized
        if self.current_diagnosis is not None:
            self.current_diagnosis["component_results"] = normalized

    def receive_esp_diagnostic(self, payload):
        """Entry point for a future parsed ESP diagnostic frame."""
        if not isinstance(payload, dict):
            return False
        self.show_diagnosis(
            error_code=payload.get("error_code", payload.get("fault_code", "")),
            description=payload.get("description", payload.get("message", "")),
            likely_source=payload.get("likely_source", payload.get("source", "")),
            instructions=payload.get("instructions"),
            modbus_data=payload.get("modbus_data", payload.get("registers", {})),
            component_results=payload.get("component_results", payload.get("checks", {})),
        )
        return True

    @staticmethod
    def _format_modbus_data(data):
        if not data:
            return "Henüz Modbus verisi alınmadı."
        if isinstance(data, dict):
            parts = [f"{key}: {value}" for key, value in data.items()]
            text = "   •   ".join(parts)
        else:
            text = json.dumps(data, ensure_ascii=False, default=str)
        return text if len(text) <= 1200 else text[:1197] + "..."

    def save_diagnosis(self):
        serial = str(self.active_serial or "").strip().upper()
        if not serial:
            QMessageBox.warning(self, "Kart Seçilmedi", "Önce servis kartının seri numarasını seçin veya girin.")
            return
        self.active_serial = serial
        diagnosis = self.current_diagnosis or {}
        manual_note = self.technician_notes.text().strip()
        error_code = (
            diagnosis.get("error_code")
            or self.manual_error_code.text().strip()
            or "SERVİS"
        )
        likely_source = diagnosis.get("likely_source") or self.manual_source_selector.currentText()
        description = (
            diagnosis.get("description")
            or manual_note
            or f"{likely_source} için teknik servis kontrol kaydı."
        )
        selected = diagnosis.get("selected_source")
        selected_result = self.component_results.get(selected, {}) if selected else {}
        recommended_action = (
            diagnosis.get("instructions")
            or selected_result.get("details", "")
            or ""
        )
        checked_items = [
            {"item": key, **self.component_results.get(key, {"status": "waiting", "details": ""})}
            for key in self.recommendation_cards
        ]
        try:
            device = self.database.get_device(serial)
            if device is None:
                self.database.create_device(serial)
                device = self.database.get_device(serial)
            self.active_serial = device["serial_number"]
            record_id = self.database.save_diagnostic(
                self.active_serial,
                error_code=error_code,
                description=description,
                likely_source=likely_source,
                recommended_action=recommended_action,
                checked_items=checked_items,
                technician_notes=manual_note,
                modbus_data=diagnosis.get("modbus_data", {}),
            )
        except Exception as error:
            QMessageBox.critical(self, "Arıza Kaydı Yapılamadı", str(error))
            return
        self.refresh_device_choices()
        self.set_device_serial(self.active_serial)
        QMessageBox.information(
            self, "Arıza Kaydedildi",
            f"Arıza kaydı {self.active_serial} kartına eklendi.\nKayıt no: {record_id}",
        )

    def reset_diagnosis(self):
        self.current_diagnosis = None
        self.save_diagnosis_button.setEnabled(bool(self.active_serial))
        self.status_value.setText("VERİ BEKLENİYOR")
        self.error_value.setText("—")
        self.source_value.setText("—")
        self.diagnosis_text.setText(
            "ESP/Modbus hata bilgisi bağlandığında olası kaynak ve önerilen kontrol burada gösterilecek."
        )
        self.diagnosis_detail.setText("Henüz bir arıza kodu veya durum bilgisi alınmadı.")
        self.modbus_data_label.setText("Henüz Modbus verisi alınmadı.")
        self.set_component_results({
            key: {"status": "waiting" if self.hardware_connected else "disconnected"}
            for key in self.recommendation_cards
        })
        for card in self.recommendation_cards.values():
            card["card"].setProperty("recommended", False)
            card["card"].style().unpolish(card["card"])
            card["card"].style().polish(card["card"])

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_to_window()
        columns = 4 if self.width() >= 1200 else 2
        if getattr(self, "_recommendation_columns", None) != columns:
            for card in self._recommendation_order:
                self.checks_layout.removeWidget(card)
            for index, card in enumerate(self._recommendation_order):
                self.checks_layout.addWidget(card, index // columns, index % columns)
            self._recommendation_columns = columns

    def _fit_to_window(self):
        if self.width() <= 0 or self.height() <= 0:
            return
        scale = max(0.65, min(self.width() / 1366, self.height() / 768, 1.35))
        if abs(scale - self._ui_scale) < 0.02:
            return
        self._ui_scale = scale
        self.root_layout.setContentsMargins(
            max(8, round(20 * scale)), max(8, round(14 * scale)),
            max(8, round(20 * scale)), max(8, round(16 * scale)),
        )
        self.root_layout.setSpacing(max(6, round(12 * scale)))
        self.logo_label.setFixedSize(max(72, round(112 * scale)), max(30, round(46 * scale)))
        self._apply_styles()

    def _apply_styles(self):
        scale = max(0.65, self._ui_scale)
        def px(value):
            return max(1, round(value * scale))
        self.setStyleSheet(f"""
            QWidget#faultDetectionPage {{ background: {BG}; color: {TEXT}; }}
            QFrame#panel, QFrame#summaryCard, QFrame#recommendationCard {{
                background: {PANEL}; border: 1px solid {BORDER}; border-radius: {px(9)}px;
            }}
            QFrame#recommendationCard[recommended="true"] {{ border: 1px solid {YELLOW}; }}
            QLabel {{ color: {TEXT}; background: transparent; border: none; }}
            QLabel#pageTitle {{ font-size: {px(20)}px; font-weight: 800; }}
            QLabel#sectionTitle {{ color: #D8D8DC; font-size: {px(14)}px; font-weight: 800; }}
            QLabel#mutedLabel {{ color: {MUTED}; font-size: {px(12)}px; }}
            QLabel#activeSerial {{ color: #D4D4D8; font-size: {px(12)}px; font-weight: 700; }}
            QLabel#summaryValue {{ font-size: {px(16)}px; font-weight: 800; }}
            QLabel#diagnosisText {{ font-size: {px(15)}px; font-weight: 700; }}
            QLabel#modbusData {{ color: #A5F3FC; background: #101B1E; border: 1px solid #164E63; border-radius: 6px; padding: {px(7)}px; font-family: Consolas, monospace; font-size: {px(11)}px; }}
            QLabel#recommendationTitle {{ font-size: {px(13)}px; font-weight: 800; }}
            QLabel#recommendationText {{ color: #D4D4D8; font-size: {px(12)}px; }}
            QLabel#connectionBadge {{ color: {RED}; background: #211012; border: 1px solid #9F3A4B; border-radius: 8px; padding: {px(7)}px; font-size: {px(11)}px; font-weight: 800; }}
            QLabel#pendingBadge {{ color: {YELLOW}; background: #211B0D; border: 1px solid #927126; border-radius: 6px; padding: {px(5)}px; font-size: {px(10)}px; font-weight: 700; }}
            QLabel#warningBadge {{ color: {YELLOW}; background: #211B0D; border: 1px solid {YELLOW}; border-radius: 6px; padding: {px(5)}px; font-size: {px(10)}px; font-weight: 700; }}
            QLabel#healthyBadge {{ color: {GREEN}; background: #101F17; border: 1px solid #2F855A; border-radius: 6px; padding: {px(5)}px; font-size: {px(10)}px; font-weight: 700; }}
            QLabel#faultBadge {{ color: {RED}; background: #211012; border: 1px solid #9F3A4B; border-radius: 6px; padding: {px(5)}px; font-size: {px(10)}px; font-weight: 700; }}
            QLineEdit#technicianNotes {{ background: #101014; color: {TEXT}; border: 1px solid #35353B; border-radius: 7px; padding: {px(8)}px; font-size: {px(12)}px; }}
            QLineEdit#technicianNotes:focus {{ border-color: {RED}; }}
            QComboBox#manualSourceSelector {{ background: #101014; color: {TEXT}; border: 1px solid #404040; border-radius: 7px; padding: {px(8)}px; font-size: {px(12)}px; }}
            QComboBox#manualSourceSelector:focus {{ border-color: {RED}; }}
            QComboBox#manualSourceSelector QAbstractItemView {{ background: #141418; color: {TEXT}; selection-background-color: #4A171B; border: 1px solid #35353B; }}
            QPushButton {{ background-color: #202020; color: #F5F5F5; border: 1px solid #404040; border-radius: 7px; padding: {px(8)}px {px(12)}px; font-size: {px(13)}px; font-weight: 600; }}
            QPushButton:hover {{ background-color: #303030; border-color: #737373; }}
            QPushButton:pressed {{ background-color: #3A3A3A; border-color: #A3A3A3; padding-top: {px(9)}px; padding-bottom: {px(7)}px; }}
            QPushButton:focus {{ border-color: #737373; }}
            QPushButton:disabled {{ color: #666666; background-color: #111111; border-color: #262626; }}
            QPushButton#connectionButton {{ background-color: #0E7490; color: #FFFFFF; border: 1px solid #22D3EE; font-size: {px(12)}px; font-weight: 700; }}
            QPushButton#connectionButton:hover {{ background-color: #155E75; border-color: #67E8F9; }}
            QPushButton#connectionButton:pressed {{ background-color: #164E63; border-color: #A5F3FC; }}
            QPushButton#secondaryButton {{ background-color: #202020; border: 1px solid #525252; color: #F5F5F5; }}
            QPushButton#secondaryButton:hover {{ background-color: #303030; border-color: #A3A3A3; }}
            QPushButton#checkedButton {{ background-color: #166534; border: 1px solid #4ADE80; color: #FFFFFF; }}
            QPushButton#checkedButton:hover {{ background-color: #15803D; border-color: #86EFAC; }}
            QPushButton#checkedButton:pressed {{ background-color: #14532D; border-color: #BBF7D0; }}
            QPushButton#saveButton {{ background-color: #7F1D1D; color: #FFFFFF; border-color: #B91C1C; }}
            QPushButton#saveButton:hover {{ background-color: #991B1B; border-color: #EF4444; }}
            QPushButton#saveButton:pressed {{ background-color: #64171B; border-color: #FCA5A5; }}
        """)

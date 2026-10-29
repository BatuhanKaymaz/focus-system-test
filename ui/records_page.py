import pyqtgraph as pg

from PySide6.QtCore import Qt, Signal
from ui.responsive import ResponsiveScaler
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class RecordsPage(QWidget):
    """Search device cards and inspect or remove saved records."""

    back_requested = Signal()
    device_deleted = Signal(str)

    def __init__(self, database, parent=None):
        super().__init__(parent)
        self.database = database
        self.current_serial = None
        self.setObjectName("recordsPage")
        self.setStyleSheet("""
            QWidget#recordsPage { background: #0B0B0D; color: #F4F4F5; }
            QFrame#panel { background: #141418; border: 1px solid #29292F; border-radius: 12px; }
            QFrame#emptyState { background: #0F0F12; border: 1px dashed #35353B; border-radius: 10px; }
            QFrame#metricCard { background: #101014; border: 1px solid #29292F; border-left: 3px solid #38BDF8; border-radius: 8px; }
            QFrame#metricCard[tone="violet"] { border-left-color: #A78BFA; }
            QFrame#metricCard[tone="green"] { border-left-color: #4ADE80; }
            QFrame#metricCard[tone="amber"] { border-left-color: #FBBF24; }
            QLabel#emptyHeading { color: #38BDF8; font-size: 18px; font-weight: 800; }
            QLabel#pageTitle { color: #FFFFFF; font-size: 20px; font-weight: 800; }
            QLabel#muted { color: #92929B; font-size: 12px; }
            QLabel#cardTitle { color: #38BDF8; font-size: 14px; font-weight: 800; }
            QLabel#metricCaption { color: #92929B; font-size: 10px; font-weight: 700; }
            QLabel#metricValue { color: #F4F4F5; font-size: 19px; font-weight: 800; }
            QLabel#liveBadge { color: #67E8F9; background: #10232B; border: 1px solid #155E75; border-radius: 7px; padding: 7px 10px; font-size: 10px; font-weight: 800; }
            QPushButton { background-color: #202020; color: #F5F5F5; border: 1px solid #404040; border-radius: 7px; padding: 12px 18px; font-size: 14px; font-weight: 700; }
            QPushButton:hover { background-color: #303030; border-color: #737373; }
            QPushButton:pressed { background-color: #3A3A3A; border-color: #A3A3A3; }
            QPushButton:disabled { color: #66666E; background-color: #111114; border-color: #29292F; }
            QPushButton#deleteCardButton { background-color: #351316; border-color: #7F1D1D; color: #FCA5A5; }
            QPushButton#deleteCardButton:hover { background-color: #57191E; border-color: #E5222A; color: #FFFFFF; }
            QLineEdit { background: #101014; color: #F4F4F5; border: 1px solid #404040; border-radius: 7px; padding: 9px; font-size: 12px; }
            QLineEdit:focus { border-color: #38BDF8; }
            QComboBox { background: #101014; color: #F4F4F5; border: 1px solid #404040; border-radius: 7px; padding: 8px; font-size: 11px; }
            QComboBox:focus { border-color: #38BDF8; }
            QComboBox QAbstractItemView { background: #141418; color: #F4F4F5; selection-background-color: #164E63; border: 1px solid #35353B; }
            QListWidget, QTableWidget { background: #0F0F12; color: #E4E4E7; border: 1px solid #29292F; border-radius: 7px; gridline-color: #29292F; selection-background-color: #164E63; selection-color: #FFFFFF; alternate-background-color: #141418; }
            QListWidget::item { padding: 10px 8px; border-bottom: 1px solid #242429; }
            QListWidget::item:selected { background: #10232B; border-left: 3px solid #38BDF8; }
            QHeaderView::section { background: #19191E; color: #BEBEC5; border: none; border-bottom: 1px solid #34343B; padding: 8px; font-weight: 700; }
            QTabWidget::pane { border: 1px solid #29292F; border-radius: 7px; background: #0F0F12; }
            QTabBar::tab { background: #17171B; color: #A1A1AA; padding: 10px 20px; min-width: 150px; border: 1px solid #29292F; font-size: 12px; font-weight: 800; }
            QTabBar::tab:selected { color: #FFFFFF; background: #10232B; border-bottom: 2px solid #38BDF8; }
            QSplitter::handle { background: #29292F; }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 18)
        root.setSpacing(12)

        header = QHBoxLayout()
        back = QPushButton("← ANA SAYFA")
        back.clicked.connect(self.back_requested.emit)
        header.addWidget(back)
        title = QLabel("KART KAYIT GEÇMİŞİ")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch(1)
        self.header_badge = QLabel("YEREL VERİTABANI")
        self.header_badge.setObjectName("liveBadge")
        header.addWidget(self.header_badge)
        refresh = QPushButton("YENİLE")
        refresh.clicked.connect(self.refresh_devices)
        header.addWidget(refresh)
        root.addLayout(header)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(5)
        root.addWidget(self.splitter, 1)

        left = QFrame()
        left.setObjectName("panel")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(9)
        left_title = QLabel("KAYITLI KARTLAR")
        left_title.setObjectName("cardTitle")
        left_layout.addWidget(left_title)
        search_row = QHBoxLayout()
        search_row.setSpacing(7)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Seri numarasına göre ara...")
        self.search_input.textChanged.connect(self.refresh_devices)
        search_row.addWidget(self.search_input, 1)
        self.sort_selector = QComboBox()
        self.sort_selector.addItem("SERİ NO", "serial")
        self.sort_selector.addItem("EN YENİ", "recent")
        self.sort_selector.addItem("EN ÇOK TEST", "tests")
        self.sort_selector.currentIndexChanged.connect(self.refresh_devices)
        search_row.addWidget(self.sort_selector)
        left_layout.addLayout(search_row)
        self.device_list = QListWidget()
        self.device_list.currentItemChanged.connect(self.select_device)
        left_layout.addWidget(self.device_list, 1)
        self.delete_device_button = QPushButton("KARTI VE TÜM KAYITLARINI SİL")
        self.delete_device_button.setObjectName("deleteCardButton")
        self.delete_device_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_device_button.setEnabled(False)
        self.delete_device_button.clicked.connect(self.delete_selected_device)
        left_layout.addWidget(self.delete_device_button)
        self.device_count = QLabel("0 kart")
        self.device_count.setObjectName("muted")
        left_layout.addWidget(self.device_count)
        self.splitter.addWidget(left)

        right = QFrame()
        right.setObjectName("panel")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(14, 12, 14, 14)
        right_layout.setSpacing(9)
        self.selected_serial = QLabel("Bir kart seçin")
        self.selected_serial.setObjectName("pageTitle")
        right_layout.addWidget(self.selected_serial)
        self.device_summary = QLabel("Seçilen kartın test ve arıza geçmişi burada görünür.")
        self.device_summary.setObjectName("muted")
        right_layout.addWidget(self.device_summary)
        self.metric_values = {}
        metrics = QHBoxLayout()
        metrics.setSpacing(8)
        for key, caption, tone in (
            ("tests", "TEST KAYDI", "cyan"),
            ("faults", "ARIZA KAYDI", "violet"),
            ("last", "SON TEST", "green"),
            ("created", "KART KAYDI", "amber"),
        ):
            metric = QFrame()
            metric.setObjectName("metricCard")
            metric.setProperty("tone", tone)
            metric_layout = QVBoxLayout(metric)
            metric_layout.setContentsMargins(10, 8, 10, 8)
            metric_layout.setSpacing(3)
            caption_label = QLabel(caption)
            caption_label.setObjectName("metricCaption")
            value_label = QLabel("—")
            value_label.setObjectName("metricValue")
            value_label.setWordWrap(True)
            metric_layout.addWidget(caption_label)
            metric_layout.addWidget(value_label)
            metrics.addWidget(metric, 1)
            self.metric_values[key] = value_label
        right_layout.addLayout(metrics)

        self.tabs = QTabWidget()
        self.test_table = self._make_table(
            ["Tarih", "Mod", "Sonuç", "Tork", "Akım", "Gerilim", "Sıcaklık", "Hız", "Konum"]
        )
        self.diagnostic_table = self._make_table(
            ["Tarih", "Kod", "Olası kaynak", "Açıklama", "Önerilen kontrol", "Teknisyen notu", "Modbus / işlemci verisi"]
        )

        test_tab = QWidget()
        test_layout = QVBoxLayout(test_tab)
        test_layout.setContentsMargins(8, 8, 8, 8)
        test_layout.setSpacing(8)
        self.test_chart = pg.PlotWidget()
        self.test_chart.setBackground("#0F0F12")
        self.test_chart.showGrid(x=True, y=True, alpha=0.2)
        self.test_chart.setLabel("bottom", "Süre", units="s", color="#A1A1AA")
        self.test_chart.setLabel("left", "Ölçüm", color="#A1A1AA")
        self.test_chart.addLegend()
        self.test_chart.setMinimumHeight(160)
        self.test_chart.setMaximumHeight(220)
        test_layout.addWidget(self.test_chart)
        test_layout.addWidget(self.test_table, 1)
        self.test_table.itemSelectionChanged.connect(self.show_selected_test_chart)
        fault_tab = QWidget()
        fault_layout = QVBoxLayout(fault_tab)
        fault_layout.setContentsMargins(8, 8, 8, 8)
        fault_layout.addWidget(self.diagnostic_table, 1)
        self.tabs.addTab(test_tab, "TEST GEÇMİŞİ")
        self.tabs.addTab(fault_tab, "ARIZA GEÇMİŞİ")
        right_layout.addWidget(self.tabs, 1)

        self.empty_state = QFrame()
        self.empty_state.setObjectName("emptyState")
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setContentsMargins(24, 24, 24, 24)
        empty_layout.setSpacing(10)
        empty_layout.addStretch(1)
        self.empty_heading = QLabel("KART SEÇİN")
        self.empty_heading.setObjectName("emptyHeading")
        self.empty_heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_heading)
        self.empty_message = QLabel(
            "Test ve arıza geçmişini görüntülemek için soldaki listeden bir kart seçin."
        )
        self.empty_message.setObjectName("muted")
        self.empty_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_message.setWordWrap(True)
        empty_layout.addWidget(self.empty_message)
        empty_layout.addStretch(1)
        right_layout.addWidget(self.empty_state, 1)
        self.tabs.hide()
        self.splitter.addWidget(right)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)
        self.splitter.setSizes([300, 900])

        self.refresh_devices()
        self._show_chart_placeholder()
        self._responsive_scaler = ResponsiveScaler(self)

    @staticmethod
    def _make_delete_button(text):
        button = QPushButton(text)
        button.setObjectName("deleteButton")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    @staticmethod
    def _make_table(headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.setWordWrap(False)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(34)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        return table

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.splitter.orientation() != Qt.Orientation.Horizontal:
            self.splitter.setOrientation(Qt.Orientation.Horizontal)

    def refresh_devices(self, *_, clear_selection=False):
        previous_serial = None if clear_selection else self.current_serial
        rows = self.database.find_devices(self.search_input.text())
        sort_mode = self.sort_selector.currentData()
        if sort_mode == "recent":
            rows.sort(key=lambda row: row.get("last_tested_at") or row.get("created_at") or "", reverse=True)
        elif sort_mode == "tests":
            rows.sort(key=lambda row: (row.get("test_count", 0), row.get("last_tested_at") or ""), reverse=True)
        self.device_list.blockSignals(True)
        self.device_list.clear()
        selected_item = None
        for device in rows:
            serial = device["serial_number"]
            last = device.get("last_tested_at") or "Henüz test yok"
            label = f"{serial}\n{device.get('test_count', 0)} test  •  Son test: {last}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, serial)
            self.device_list.addItem(item)
            if serial == previous_serial:
                selected_item = item
        self.device_count.setText(f"{len(rows)} KART BULUNDU")
        self.header_badge.setText(f"{len(rows)} KART  •  YEREL VERİTABANI")
        self.device_list.setCurrentItem(selected_item)
        self.device_list.blockSignals(False)
        if selected_item:
            self.select_device(selected_item, None)
        else:
            self.current_serial = None
            self.selected_serial.setText(
                "KAYITLI KART YOK" if self.device_list.count() == 0 else "KART SEÇİLMEDİ"
            )
            self.device_summary.setText(
                "İlk testi kaydettiğinizde kart burada listelenir."
                if self.device_list.count() == 0
                else "Bir kart seçerek geçmiş kayıtları görüntüleyin."
            )
            if self.device_list.count() == 0:
                self.empty_heading.setText("HENÜZ KART KAYDI YOK")
                self.empty_message.setText("Bir test kaydedildiğinde kart geçmişi burada görünür.")
            else:
                self.empty_heading.setText("KART SEÇİN")
                self.empty_message.setText(
                    "Test ve arıza geçmişini görmek için soldaki listeden incelemek istediğiniz kartı seçin."
                )
            self.tabs.hide()
            self.empty_state.show()
            for value in self.metric_values.values():
                value.setText("—")
            self._show_chart_placeholder()
            self._fill_table(self.test_table, [])
            self._fill_table(self.diagnostic_table, [])
            self.delete_device_button.setEnabled(False)

    def select_device(self, current, _previous=None):
        if current is None:
            return
        serial = current.data(Qt.ItemDataRole.UserRole)
        self.current_serial = serial
        device = self.database.get_device(serial)
        tests = self.database.get_test_history(serial)
        diagnostics = self.database.get_diagnostic_history(serial)
        self.selected_serial.setText(serial)
        self.empty_state.hide()
        self.tabs.show()
        created = device.get("created_at", "") if device else ""
        self.device_summary.setText(
            "Kart geçmişi ve ölçüm detayları"
        )
        self.metric_values["tests"].setText(str(len(tests)))
        self.metric_values["faults"].setText(str(len(diagnostics)))
        last_test = tests[0].get("tested_at") if tests else None
        self.metric_values["last"].setText(str(last_test or "YOK"))
        self.metric_values["created"].setText(str(created or "—"))
        test_rows = [
            (r.get("id"), [r.get("tested_at"), r.get("test_mode"), r.get("result"),
             r.get("torque"), r.get("current"), r.get("voltage"), r.get("temperature"),
             r.get("speed"), r.get("actuator_position")])
            for r in tests
        ]
        diagnostic_rows = [
            (r.get("id"), [r.get("diagnosed_at"), r.get("error_code"), r.get("likely_source"),
             r.get("description"), r.get("recommended_action"), r.get("technician_notes"),
             self._format_modbus_data(r.get("modbus_data"))])
            for r in diagnostics
        ]
        self._fill_table(self.test_table, test_rows)
        self._fill_table(self.diagnostic_table, diagnostic_rows)
        self.delete_device_button.setEnabled(bool(self.current_serial))

    def _show_chart_placeholder(self):
        self.test_chart.clear()
        self.test_chart.addLegend()
        self.test_chart.setTitle("TEST ÖLÇÜM GRAFİĞİ", color="#A1A1AA", size="10pt")
        self.test_chart.setLabel("bottom", "Süre", units="s", color="#A1A1AA")
        self.test_chart.setLabel("left", "Ölçüm", color="#A1A1AA")

    def show_selected_test_chart(self):
        row = self.test_table.currentRow()
        first_item = self.test_table.item(row, 0) if row >= 0 else None
        test_id = first_item.data(Qt.ItemDataRole.UserRole) if first_item else None
        self.test_chart.clear()
        legend = self.test_chart.addLegend()
        self.test_chart.setTitle("TEST ÖLÇÜM GRAFİĞİ", color="#A1A1AA", size="10pt")
        self.test_chart.setLabel("bottom", "Süre", units="s", color="#A1A1AA")
        self.test_chart.setLabel("left", "Ölçüm", color="#A1A1AA")
        if test_id is None:
            return
        samples = self.database.get_test_samples(test_id)
        if not samples:
            self.test_chart.setTitle("BU TEST İÇİN GRAFİK ÖRNEĞİ YOK", color="#92929B", size="10pt")
            return
        elapsed = [sample.get("elapsed_seconds", 0) for sample in samples]
        series = (
            ("Tork", "torque", "#38BDF8"),
            ("Akım", "current", "#A78BFA"),
            ("Konum", "actuator_position", "#4ADE80"),
        )
        for label, key, color in series:
            values = [sample.get(key) for sample in samples]
            points = [(x, y) for x, y in zip(elapsed, values) if y is not None]
            if points:
                self.test_chart.plot(
                    [point[0] for point in points],
                    [point[1] for point in points],
                    pen=pg.mkPen(color, width=2),
                    name=label,
                )

    @staticmethod
    def _fill_table(table, rows):
        table.clearSelection()
        table.setRowCount(len(rows))
        for row_index, (record_id, values) in enumerate(rows):
            for column_index, value in enumerate(values):
                text = "—" if value is None or value == "" else str(value)
                item = QTableWidgetItem(text)
                item.setToolTip(text)
                if column_index == 0:
                    item.setData(Qt.ItemDataRole.UserRole, record_id)
                table.setItem(row_index, column_index, item)
        table.resizeRowsToContents()

    def delete_selected_device(self):
        selected_item = self.device_list.currentItem()
        serial = selected_item.data(Qt.ItemDataRole.UserRole) if selected_item else None
        if not serial:
            return
        self.current_serial = serial
        if not self._confirm_card_delete(serial):
            return
        try:
            deleted = self.database.delete_device(serial)
        except Exception as error:
            QMessageBox.critical(self, "Kart Silinemedi", str(error))
            return
        if not deleted:
            QMessageBox.warning(self, "Kart Bulunamadı", f"{serial} seri numaralı kart artık kayıtlı değil.")
            self.current_serial = None
            self.refresh_devices(clear_selection=True)
            return
        self.current_serial = None
        self.refresh_devices(clear_selection=True)
        self.device_deleted.emit(serial)

    def _confirm_card_delete(self, serial):
        dialog = QDialog(self, Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        dialog.setObjectName("deleteConfirmDialog")
        dialog.setWindowTitle("Kartı ve kayıtlarını sil")
        dialog.setModal(True)
        dialog.setMinimumWidth(420)
        dialog.setStyleSheet("""
            QDialog#deleteConfirmDialog { background: #0B0B0D; color: #F4F4F5; border: 1px solid #38383F; border-radius: 11px; }
            QLabel { color: #F4F4F5; background: transparent; border: none; }
            QLabel#dialogTitle { font-size: 16px; font-weight: 800; }
            QLabel#dialogWarning { color: #F4F4F5; font-size: 12px; }
            QPushButton { background-color: #202020; color: #F5F5F5; border: 1px solid #404040; border-radius: 7px; padding: 9px 14px; font-size: 12px; font-weight: 700; }
            QPushButton:hover { background-color: #303030; border-color: #737373; }
            QPushButton#confirmDeleteButton { background: #7F1D1D; border-color: #B91C1C; }
            QPushButton#confirmDeleteButton:hover { background: #991B1B; border-color: #EF4444; }
        """)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        title = QLabel("KARTI VE TÜM VERİLERİNİ SİL")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)
        warning = QLabel(
            f"{serial} kartı, test geçmişi, grafik örnekleri ve arıza kayıtlarıyla birlikte kalıcı olarak silinecek.\n\nBu işlem geri alınamaz."
        )
        warning.setObjectName("dialogWarning")
        warning.setWordWrap(True)
        layout.addWidget(warning)
        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel = QPushButton("VAZGEÇ")
        remove = QPushButton("KARTI SİL")
        remove.setObjectName("confirmDeleteButton")
        cancel.clicked.connect(dialog.reject)
        remove.clicked.connect(dialog.accept)
        actions.addWidget(cancel)
        actions.addWidget(remove)
        layout.addLayout(actions)
        return dialog.exec() == QDialog.DialogCode.Accepted

    @staticmethod
    def _format_modbus_data(data):
        if not data:
            return "—"
        if isinstance(data, dict):
            return "  •  ".join(f"{key}: {value}" for key, value in data.items())
        return str(data)


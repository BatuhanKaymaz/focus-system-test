import re

from PySide6.QtCore import QEvent, QObject


class ResponsiveScaler(QObject):
    """Scale existing layouts and pixel-based styles without reflowing them."""

    _STYLE_SIZE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)(px|pt)\b")

    def __init__(self, widget, reference=(1366, 768), minimum=0.52, maximum=1.5,
                 scale_stylesheet=True):
        super().__init__(widget)
        self.widget = widget
        self.reference_width, self.reference_height = reference
        self.minimum = minimum
        self.maximum = maximum
        self.scale_stylesheet = scale_stylesheet
        self._scale = None
        self._base_stylesheet = widget.styleSheet()
        self._layouts = []
        self._spacers = []
        self._widgets = []
        self._capture_widget(widget)
        widget.installEventFilter(self)
        self.apply()

    def _capture_widget(self, widget):
        self._widgets.append((
            widget,
            widget.minimumWidth(), widget.minimumHeight(),
            widget.maximumWidth(), widget.maximumHeight(),
        ))
        layout = widget.layout()
        if layout is not None:
            self._capture_layout(layout)

    def _capture_layout(self, layout):
        margins = layout.contentsMargins()
        self._layouts.append((
            layout,
            (margins.left(), margins.top(), margins.right(), margins.bottom()),
            layout.spacing(),
        ))
        for index in range(layout.count()):
            item = layout.itemAt(index)
            spacer = item.spacerItem()
            if spacer is not None:
                hint = spacer.sizeHint()
                policy = spacer.sizePolicy()
                self._spacers.append((
                    spacer, hint.width(), hint.height(),
                    policy.horizontalPolicy(), policy.verticalPolicy(),
                ))
                continue
            nested_layout = item.layout()
            if nested_layout is not None:
                self._capture_layout(nested_layout)
                continue
            child = item.widget()
            if child is not None:
                self._capture_widget(child)

    def eventFilter(self, watched, event):
        if watched is self.widget and event.type() == QEvent.Type.Resize:
            self.apply()
        return False

    def apply(self):
        width = max(1, self.widget.width())
        height = max(1, self.widget.height())
        scale = min(width / self.reference_width, height / self.reference_height)
        scale = max(self.minimum, min(self.maximum, scale))
        if self._scale is not None and abs(scale - self._scale) < 0.015:
            return
        self._scale = scale

        for layout, margins, spacing in self._layouts:
            layout.setContentsMargins(*(max(0, round(value * scale)) for value in margins))
            if spacing >= 0:
                layout.setSpacing(max(0, round(spacing * scale)))

        for spacer, width, height, horizontal, vertical in self._spacers:
            spacer.changeSize(
                max(0, round(width * scale)), max(0, round(height * scale)),
                horizontal, vertical,
            )

        for child, min_width, min_height, max_width, max_height in self._widgets:
            if child is self.widget:
                continue
            if min_width > 0:
                child.setMinimumWidth(max(1, round(min_width * scale)))
            if min_height > 0:
                child.setMinimumHeight(max(1, round(min_height * scale)))
            if max_width < 50000:
                child.setMaximumWidth(max(1, round(max_width * scale)))
            if max_height < 50000:
                child.setMaximumHeight(max(1, round(max_height * scale)))

        if self.scale_stylesheet and self._base_stylesheet:
            scaled = self._STYLE_SIZE.sub(
                lambda match: f"{max(1, round(float(match.group(1)) * scale))}{match.group(2)}",
                self._base_stylesheet,
            )
            self.widget.setStyleSheet(scaled)

        self.widget.updateGeometry()
        layout = self.widget.layout()
        if layout is not None:
            layout.invalidate()
            layout.activate()


# Advanced Cabinets Workbench - schema-driven cabinet dialog
# Target: FreeCAD 1.1.4
# CABINET CORE V1
from PySide import QtWidgets
from AdvCabinetParameters import SheetParams, parameter_raw, qty_mm, qty_int, qty_scalar
class SchemaCabinetDialog(QtWidgets.QDialog):
    def __init__(self, sheet, schema, title="Cabinet Parameters", validator=None, notes=None, derived_preview=None):
        super().__init__()
        self.sheet = sheet
        self.schema = schema
        self.validator = validator
        self.derived_preview = derived_preview
        self._validated_values = None
        self._widgets = {}
        self.setWindowTitle(title)
        self.layout = QtWidgets.QFormLayout(self)
        params = SheetParams(sheet)
        current_group = None
        for definition in schema.definitions:
            if definition.group != current_group:
                current_group = definition.group
                if current_group:
                    label = QtWidgets.QLabel("<b>{}</b>".format(current_group))
                    self.layout.addRow(label)
            raw = parameter_raw(params, definition.name, definition.default, {definition.name: definition.legacy_names})
            widget = self._make_widget(definition, raw)
            self._widgets[definition.name] = widget
            self.layout.addRow("{}:".format(definition.label), widget)
            self._connect_change(widget)
        for note_text in notes or ():
            label = QtWidgets.QLabel(str(note_text))
            label.setWordWrap(True)
            self.layout.addRow(label)
        self._preview_label = None
        if derived_preview is not None:
            self._preview_label = QtWidgets.QLabel("")
            self._preview_label.setWordWrap(True)
            self.layout.addRow("Derived:", self._preview_label)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addRow(buttons)
        self._sync_applicable_fields()
        self._update_preview()
    def _make_widget(self, definition, raw):
        if definition.kind == "text" and definition.options:
            widget = QtWidgets.QComboBox()
            widget.addItems([str(x) for x in definition.options])
            text = str(raw).strip()
            widget.setCurrentText(text if text in definition.options else str(definition.default))
        elif definition.kind == "integer":
            widget = QtWidgets.QSpinBox()
            minimum = int(definition.minimum) if definition.minimum is not None else -999999
            maximum = int(definition.maximum) if definition.maximum is not None else 999999
            widget.setRange(minimum, maximum)
            widget.setValue(qty_int(raw, int(definition.default), definition.label))
        else:
            if definition.kind == "scalar":
                value = qty_scalar(raw, float(definition.default), definition.label)
            elif definition.kind == "text":
                value = str(raw)
            else:
                value = qty_mm(raw, None, definition.label)
            widget = QtWidgets.QLineEdit(str(value))
        tooltip = definition.tooltip
        if definition.spec is not None:
            range_text = "Allowed range: {}.".format(definition.spec.limit_text())
            tooltip = "{} {}".format(tooltip, range_text).strip()
        if tooltip:
            widget.setToolTip(tooltip)
        if definition.read_only:
            widget.setEnabled(False)
        return widget
    def _connect_change(self, widget):
        if isinstance(widget, QtWidgets.QComboBox):
            widget.currentTextChanged.connect(self._on_change)
        elif isinstance(widget, QtWidgets.QSpinBox):
            widget.valueChanged.connect(self._on_change)
        elif isinstance(widget, QtWidgets.QLineEdit):
            widget.textChanged.connect(self._on_change)
    def _on_change(self, *_args):
        self._sync_applicable_fields()
        self._update_preview()
    def _sync_applicable_fields(self):
        try:
            values = self.values(validate=False)
        except Exception:
            values = {}
        for definition in self.schema.definitions:
            widget = self._widgets[definition.name]
            active = self.schema.is_active(definition.name, values)
            widget.setEnabled(active and not definition.read_only)
    def _read_widget(self, definition):
        widget = self._widgets[definition.name]
        if isinstance(widget, QtWidgets.QComboBox):
            return str(widget.currentText())
        if isinstance(widget, QtWidgets.QSpinBox):
            return int(widget.value())
        text = str(widget.text()).strip()
        if definition.kind == "text":
            return text
        if definition.kind == "scalar":
            return qty_scalar(text, None, definition.label)
        if definition.kind == "integer":
            return qty_int(text, None, definition.label)
        return qty_mm(text, None, definition.label)
    def values(self, validate=True):
        if validate and self._validated_values is not None:
            return dict(self._validated_values)
        result = {}
        provisional = {}
        for definition in self.schema.definitions:
            widget = self._widgets[definition.name]
            if isinstance(widget, QtWidgets.QComboBox):
                provisional[definition.name] = str(widget.currentText())
            elif isinstance(widget, QtWidgets.QSpinBox):
                provisional[definition.name] = int(widget.value())
            elif definition.kind == "text":
                provisional[definition.name] = str(widget.text()).strip()
        for definition in self.schema.definitions:
            active = self.schema.is_active(definition.name, provisional)
            try:
                result[definition.name] = self._read_widget(definition)
            except Exception:
                if not active:
                    if definition.kind == "integer":
                        result[definition.name] = int(definition.default)
                    elif definition.kind == "scalar":
                        result[definition.name] = float(definition.default)
                    elif definition.kind == "text":
                        result[definition.name] = str(definition.default)
                    else:
                        result[definition.name] = qty_mm(definition.default, None, definition.label)
                else:
                    raise
            provisional[definition.name] = result[definition.name]
        return result
    def _update_preview(self):
        if self._preview_label is None or self.derived_preview is None:
            return
        try:
            preview = self.derived_preview(self.values(validate=False))
            self._preview_label.setText(str(preview))
        except Exception as exc:
            self._preview_label.setText("Conflict: {}".format(exc))
    def accept(self):
        try:
            values = self.values(validate=False)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(None, "Invalid Cabinet Parameters", str(exc))
            return
        if self.validator is not None:
            result = self.validator(values)
            if result.errors:
                QtWidgets.QMessageBox.critical(None, "Invalid Cabinet Parameters", "Correct the following before creating the cabinet:\n\n{}".format(result.error_text()))
                return
            if result.warnings:
                choice = QtWidgets.QMessageBox.warning(None, "Cabinet Parameter Warning", "The cabinet is geometrically valid, but review these conditions:\n\n{}\n\nContinue?".format(result.warning_text()), QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel, QtWidgets.QMessageBox.Cancel)
                if choice != QtWidgets.QMessageBox.Ok:
                    return
        self._validated_values = dict(values)
        super().accept()

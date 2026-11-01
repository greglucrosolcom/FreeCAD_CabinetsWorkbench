# ============================================================
# MULTI-DRAWER LOWER CABINET
# SELF-CONTAINED PARAMETRIC FEATUREPYTHON PROTOTYPE
# ============================================================
# Target: FreeCAD 1.1.3
# REVISION: 0.08
#
# Based on the runtime-proven Four Drawer Lower Cabinet Rev0.14.
#
# 0.01 - Multi-drawer prototype
#        - DrawerCount supports 1 through 8 drawers
#        - eight permanent drawer-front components are created once
#        - inactive drawer fronts remain valid but hidden
#        - Drawer1 is the bottom drawer; numbering proceeds upward
#        - Drawer1Height .. Drawer8Height are independently parametric
#        - a drawer height of 0 means Auto
#        - one or more active Auto drawers divide the remaining height equally
#        - at least one active drawer must be Auto
#        - Overlay / Inset mounting retained
#        - Slab / Shaker styles retained
#        - solid recessed toe kick retained
#        - cabinet dimensions accept explicit mm or in
#        - Parameters Column B displays dimensional values in inches
#        - Column C displays nearest-1/16-inch cabinet-shop values
#        - Column D documents categorical/Auto options
#        - visible Draft origin point retained
#        - canonical DraftTools / FreeCADGui.Snapper endpoint insertion retained
#        - first non-endpoint pick warns; second non-endpoint pick uses 0,0,0
#        - no persistent Draft snap preferences are changed
#
# 0.02 - User-selected drawer-count revision
#        - DrawerCount minimum changed from 4 to 1
#        - DrawerCount maximum remains 8
#        - dialog now uses an integer spin box for DrawerCount
#        - one-drawer cabinets are supported for trash/recycling applications
#        - DrawerCount=1 automatically makes Drawer1 Auto so it fills the opening
#        - all existing Auto-height, Overlay/Inset, Slab/Shaker, toe-kick,
#          parameter-sheet, endpoint-snap and validation behavior retained
#
# 0.03 - Instruction-note layout revision
#        - adds reusable add_instruction_note() helper
#        - places instructional text inside its own padded QWidget container
#        - gives the wrapped QLabel guaranteed vertical room
#        - avoids QLabel contents margins that reduced the usable text area
#        - no cabinet geometry, drawer sizing, parameters or snap logic changed
#
# 0.04 - Instruction-note vertical-clearance refinement
#        - increases top/bottom container padding
#        - increases wrapped-label minimum height
#        - increases note-container minimum height
#        - no cabinet geometry, drawer sizing, parameters or snap logic changed
#
# 0.05 - Last-active-drawer Auto / None revision
#        - DrawerCount remains an integer from 1 through 8
#        - drawers are numbered bottom-up
#        - all active drawers below the highest active drawer are Fixed
#        - the highest active drawer is always Auto and fills remaining height
#        - drawers above DrawerCount are None / inactive
#        - Auto and None are states, not special numeric values
#        - Drawer1Height .. Drawer8Height remain numeric parameters so values
#          are preserved if DrawerCount is later changed
#        - Parameters Column D reports Fixed / Auto - calculated / None - inactive
#        - dialog displays Auto and None and disables those non-editable rows
#        - no more than eight drawers are permitted
#        - existing Overlay/Inset, Slab/Shaker, toe-kick, inch display,
#          endpoint-snap and component architecture are retained
#
# 0.06 - Recompute-loop fix
#        - execute() no longer writes to the Parameters spreadsheet
#        - removes execute-time Column-D refresh that re-touched the sheet
#          during FreeCAD recompute and left geometry objects touched
#        - Column D now documents the permanent state rule instead:
#              below DrawerCount = Fixed
#              at DrawerCount = Auto - calculated
#              above DrawerCount = None - inactive
#        - no geometry, drawer-count, Auto/None, dialog, or snap changes
#
# 0.08 - Local recompute-settle revision
#        - based directly on functional Revision 0.06; Revision 0.07 dependency
#          links are intentionally NOT used
#        - retains the Revision 0.06 cabinet body, toe-kick and Auto/None geometry
#        - caches geometry input signatures so unchanged objects are not rewritten
#          during every FeaturePython execute()
#        - only geometry whose controlling parameters actually changed is updated
#        - changed sibling features are explicitly recomputed locally after update
#          so they do not remain touched at the end of the document recompute
#        - the Parameters sheet is locally settled without writing new cell values
#        - no document-wide or nested document recompute is called from execute()
#        - no geometry dimensions, DrawerCount, Auto/None, dialog, or snap changes
#
# DEFAULT CABINET
#        Width  = 30 in
#        Depth  = 24 in
#        Height = 32 in overall, including toe kick
#        DrawerCount = 6
#        Drawer 1 / bottom = 4 in fixed
#        Drawer 2          =  4 in fixed
#        Drawer 3          =  4 in fixed
#        Drawers 4-5       = fixed default heights
#        Drawer 6          = Auto, fills remaining vertical space
#
# AUTO-HEIGHT RULE
#        Highest active drawer = DrawerCount
#        AutoHeight =
#            AvailableFrontHeight
#          - ((DrawerCount - 1) * DrawerGap)
#          - sum(all lower active fixed drawer heights)
#        Drawers above DrawerCount are None / inactive.
#
# COORDINATE SYSTEM
#        X = Cabinet Width
#        Y = Cabinet Depth
#        Z = Cabinet Height
#        Cabinet front/reference plane = Y=0
#        Cabinet extends toward +Y
#        Overlay drawer fronts extend toward -Y
#        Toe kick occupies Z=0 -> ToeKickHeight
#        Cabinet carcass begins at Z=ToeKickHeight
# ============================================================
import FreeCAD as App
import FreeCADGui as Gui
import Part
import Draft
import warnings
from PySide import QtWidgets
from pivy import coin
from draftutils import gui_utils

SHEET_NAME = "Parameters"
CONTROLLER_NAME = "CabinetController"
INSTANCE_BASENAME = "MultiDrawerLowerCabinet"
MIN_DRAWERS = 1
MAX_DRAWERS = 8
DEFAULT_DRAWER_COUNT = 6
INTEGER_PARAMETERS = {"DrawerCount"}
TEXT_PARAMETERS = {"DrawerStyle", "DrawerMount"}
DRAWER_HEIGHT_PARAMETERS = tuple("Drawer{}Height".format(i) for i in range(1, MAX_DRAWERS + 1))
DIMENSION_PARAMETERS = {
    "CabinetWidth",
    "CabinetDepth",
    "CabinetHeight",
    "BoxWallThickness",
    "DrawerThickness",
    "DrawerGap",
    "InsetSetback",
    "ToeKickDepth",
    "ToeKickHeight",
    "ToeKickThickness",
    "DrawerFrameWidth",
    "DrawerPanelThickness",
}.union(DRAWER_HEIGHT_PARAMETERS)
FRONT_STYLES = ("Slab", "Shaker")
FRONT_MOUNTS = ("Overlay", "Inset")
PARAMETER_OPTIONS = {
    "DrawerCount": "Integer 1 through 8",
    "DrawerStyle": "Slab | Shaker",
    "DrawerMount": "Overlay | Inset",
}
PARAM_DEFAULTS = [
    ("CabinetWidth",         "762 mm"),
    ("CabinetDepth",         "609.6 mm"),
    ("CabinetHeight",        "812.8 mm"),
    ("BoxWallThickness",     "19 mm"),
    ("DrawerThickness",      "19 mm"),
    ("DrawerGap",            "3 mm"),
    ("DrawerCount",          "6"),
    ("Drawer1Height",        "100 mm"),
    ("Drawer2Height",        "100 mm"),
    ("Drawer3Height",        "100 mm"),
    ("Drawer4Height",        "100 mm"),
    ("Drawer5Height",        "100 mm"),
    ("Drawer6Height",        "100 mm"),
    ("Drawer7Height",        "0 mm"),
    ("Drawer8Height",        "0 mm"),
    ("InsetSetback",         "0 mm"),
    ("DrawerStyle",          "Slab"),
    ("DrawerMount",          "Overlay"),
    ("ToeKickDepth",         "88.9 mm"),
    ("ToeKickHeight",        "88.9 mm"),
    ("ToeKickThickness",     "19.05 mm"),
    ("DrawerFrameWidth",     "25 mm"),
    ("DrawerPanelThickness", "6 mm"),
]

class SheetParams:
    def __init__(self, sheet, row_start=2, row_end=50):
        self.sheet = sheet
        self.row_start = row_start
        self.row_end = row_end
    def get_cell(self, address):
        try:
            return self.sheet.get(address)
        except Exception:
            pass
        try:
            return self.sheet.getContents(address)
        except Exception:
            pass
        try:
            return getattr(self.sheet, address)
        except Exception:
            return None
    def set_cell(self, address, value):
        self.sheet.set(address, str(value))
    def row_of(self, name):
        for row in range(self.row_start, self.row_end + 1):
            value = self.get_cell("A{}".format(row))
            if value is not None and str(value).strip() == name:
                return row
        return None
    def get(self, name, default=None):
        row = self.row_of(name)
        if row is None:
            return default
        value = self.get_cell("B{}".format(row))
        return default if value is None else value
    def set(self, name, value):
        row = self.row_of(name)
        if row is None:
            raise KeyError("Parameter '{}' was not found.".format(name))
        self.set_cell("B{}".format(row), value)

def qty_mm(value, fallback):
    try:
        if value is None:
            return float(fallback)
        text = str(value).strip()
        if not text:
            return float(fallback)
        if all(character.isdigit() or character in ".-+" for character in text):
            text += " mm"
        return float(App.Units.Quantity(text).Value)
    except Exception:
        return float(fallback)

def qty_int(value, fallback):
    try:
        if value is None:
            return int(fallback)
        text = str(value).strip()
        if not text:
            return int(fallback)
        return int(round(float(text)))
    except Exception:
        return int(fallback)

def inch_text_from_mm(mm_value):
    inches = float(mm_value) / 25.4
    text = "{:.6f}".format(inches).rstrip("0").rstrip(".")
    if text in ("", "-0"):
        text = "0"
    return "{} in".format(text)

class ParameterTable:
    @staticmethod
    def create(doc, object_name=SHEET_NAME):
        sheet = doc.addObject("Spreadsheet::Sheet", object_name)
        sheet.Label = SHEET_NAME
        sheet.set("A1", "Name")
        sheet.set("B1", "Value")
        for row, (name, default_value) in enumerate(PARAM_DEFAULTS, start=2):
            sheet.set("A{}".format(row), name)
            sheet.set("B{}".format(row), default_value)
            try:
                sheet.setAlias("B{}".format(row), name)
            except Exception:
                pass
        try:
            sheet.setColumnWidth("A", 220)
            sheet.setColumnWidth("B", 160)
        except Exception:
            pass
        ParameterTable.apply_display_units(sheet)
        ParameterTable.update_inches_column(sheet)
        ParameterTable.update_options_column(sheet)
        doc.recompute()
        return sheet
    @staticmethod
    def apply_display_units(sheet):
        for row, (name, _default_value) in enumerate(PARAM_DEFAULTS, start=2):
            if name not in DIMENSION_PARAMETERS:
                continue
            address = "B{}".format(row)
            try:
                sheet.setDisplayUnit(address, "in")
            except Exception as exc:
                raise RuntimeError(
                    "Could not set Spreadsheet display unit for {} to inches: {}"
                    .format(address, exc)
                )
    @staticmethod
    def _fractional_inch_expression(metric_address):
        inches = "({}/1in)".format(metric_address)
        sixteenths = "round(abs({})*16)".format(inches)
        whole = "floor({}/16)".format(sixteenths)
        remainder = "mod({};16)".format(sixteenths)
        sign = "({}<0?-1:1)".format(inches)
        denominator = "({r}==8?2:(mod({r};4)==0?4:(mod({r};2)==0?8:16)))".format(r=remainder)
        numerator = "({r}*{d}/16)".format(r=remainder, d=denominator)
        whole_only = "<<%g in>> % ({w}*{s})".format(w=whole, s=sign)
        fraction_only = "<<%g/%g in>> % tuple({n}*{s};{d})".format(n=numerator, s=sign, d=denominator)
        mixed_number = "<<%g %g/%g in>> % tuple({w}*{s};{n};{d})".format(w=whole, s=sign, n=numerator, d=denominator)
        return "=({r}==0?{wo}:({w}==0?{fo}:{mn}))".format(
            r=remainder, wo=whole_only, w=whole, fo=fraction_only, mn=mixed_number
        )
    @staticmethod
    def update_inches_column(sheet):
        params = SheetParams(sheet)
        sheet.set("C1", "Inches")
        try:
            sheet.setColumnWidth("C", 140)
        except Exception:
            pass
        for row, (name, _default_value) in enumerate(PARAM_DEFAULTS, start=2):
            if name not in DIMENSION_PARAMETERS:
                continue
            address = "B{}".format(row)
            value = params.get_cell(address)
            if value is None or not str(value).strip():
                continue
            sheet.set("C{}".format(row), ParameterTable._fractional_inch_expression(address))
    @staticmethod
    def update_options_column(sheet):
        sheet.set("D1", "Options / State Rule")
        try:
            sheet.setColumnWidth("D", 300)
        except Exception:
            pass
        for row, (name, _default_value) in enumerate(PARAM_DEFAULTS, start=2):
            option_text = PARAMETER_OPTIONS.get(name, "")
            if name in DRAWER_HEIGHT_PARAMETERS:
                option_text = "Below count = Fixed | At count = Auto | Above count = None"
            sheet.set("D{}".format(row), option_text)
    @staticmethod
    def update(doc, sheet, values):
        params = SheetParams(sheet)
        for name, default_value in PARAM_DEFAULTS:
            value = values.get(name, params.get(name, default_value))
            if name in INTEGER_PARAMETERS:
                text = str(int(value))
            elif name in TEXT_PARAMETERS:
                text = str(value)
            elif name in DIMENSION_PARAMETERS and name in values:
                text = "{} mm".format(value)
            else:
                text = str(value)
            params.set(name, text)
            row = params.row_of(name)
            try:
                sheet.setAlias("B{}".format(row), name)
            except Exception:
                pass
        ParameterTable.apply_display_units(sheet)
        ParameterTable.update_inches_column(sheet)
        ParameterTable.update_options_column(sheet)
        doc.recompute()
    @staticmethod
    def verify(sheet):
        params = SheetParams(sheet)
        failures = []
        for name, _default in PARAM_DEFAULTS:
            value = params.get(name)
            cell_text = "" if value is None else str(value).strip()
            if not cell_text or "#REF" in cell_text.upper():
                failures.append(name)
        if failures:
            raise RuntimeError("Parameters did not resolve: {}".format(", ".join(failures)))

def add_instruction_note(form_layout, text):
    box = QtWidgets.QWidget()
    box_layout = QtWidgets.QVBoxLayout(box)
    box_layout.setContentsMargins(10, 11, 10, 11)
    box_layout.setSpacing(0)
    label = QtWidgets.QLabel(text)
    label.setWordWrap(True)
    label.setMinimumHeight(60)
    label.setSizePolicy(
        QtWidgets.QSizePolicy.Expanding,
        QtWidgets.QSizePolicy.MinimumExpanding
    )
    box_layout.addWidget(label)
    box.setMinimumHeight(82)
    form_layout.addRow(box)
    return label

class CabinetDialog(QtWidgets.QDialog):
    def __init__(self, sheet):
        super().__init__()
        p = SheetParams(sheet)
        self.setWindowTitle("Multi-Drawer Lower Cabinet")
        layout = QtWidgets.QFormLayout(self)
        self.width = self._dimension_field(p, "CabinetWidth", 762.0)
        self.depth = self._dimension_field(p, "CabinetDepth", 609.6)
        self.height = self._dimension_field(p, "CabinetHeight", 812.8)
        self.wall = self._dimension_field(p, "BoxWallThickness", 19.0)
        self.drawer_thickness = self._dimension_field(p, "DrawerThickness", 19.0)
        self.drawer_gap = self._dimension_field(p, "DrawerGap", 3.0)
        self.drawer_count = QtWidgets.QSpinBox()
        self.drawer_count.setMinimum(MIN_DRAWERS)
        self.drawer_count.setMaximum(MAX_DRAWERS)
        self.drawer_count.setSingleStep(1)
        count = qty_int(p.get("DrawerCount"), DEFAULT_DRAWER_COUNT)
        if count < MIN_DRAWERS or count > MAX_DRAWERS:
            count = DEFAULT_DRAWER_COUNT
        self.drawer_count.setValue(count)
        self.drawer_heights = []
        self.drawer_height_labels = []
        defaults = [254.0, 203.2, 152.4, 33.1, 33.1, 33.1, 0.0, 0.0]
        for index in range(1, MAX_DRAWERS + 1):
            field = self._dimension_field(
                p,
                "Drawer{}Height".format(index),
                defaults[index - 1],
            )
            field._stored_dimension_text = field.text()
            self.drawer_heights.append(field)
        self.inset_setback = self._dimension_field(p, "InsetSetback", 0.0)
        style = str(p.get("DrawerStyle", "Slab")).strip()
        if style not in FRONT_STYLES:
            style = "Slab"
        self.drawer_style = QtWidgets.QComboBox()
        self.drawer_style.addItems(list(FRONT_STYLES))
        self.drawer_style.setCurrentText(style)
        mount = str(p.get("DrawerMount", "Overlay")).strip()
        if mount not in FRONT_MOUNTS:
            mount = "Overlay"
        self.drawer_mount = QtWidgets.QComboBox()
        self.drawer_mount.addItems(list(FRONT_MOUNTS))
        self.drawer_mount.setCurrentText(mount)
        self.toe_depth = self._dimension_field(p, "ToeKickDepth", 88.9)
        self.toe_height = self._dimension_field(p, "ToeKickHeight", 88.9)
        self.toe_thickness = self._dimension_field(p, "ToeKickThickness", 19.05)
        self.drawer_frame_width = self._dimension_field(p, "DrawerFrameWidth", 25.0)
        self.drawer_panel_thickness = self._dimension_field(p, "DrawerPanelThickness", 6.0)
        layout.addRow("Cabinet Width (in or mm):", self.width)
        layout.addRow("Cabinet Depth (in or mm):", self.depth)
        layout.addRow("Cabinet Height / Overall (in or mm):", self.height)
        layout.addRow("Box Wall Thickness (in or mm):", self.wall)
        layout.addRow("Drawer Front Thickness (in or mm):", self.drawer_thickness)
        layout.addRow("Drawer Gap (in or mm):", self.drawer_gap)
        layout.addRow("Drawer Count:", self.drawer_count)
        add_instruction_note(
            layout,
            "Drawer 1 is the bottom drawer. Enter heights for all drawers below "
            "the highest active drawer. The highest active drawer is Auto and "
            "fills the remaining vertical space. Drawers above Drawer Count are None."
        )
        for index, field in enumerate(self.drawer_heights, start=1):
            label = QtWidgets.QLabel()
            self.drawer_height_labels.append(label)
            layout.addRow(label, field)
        layout.addRow("Drawer Style:", self.drawer_style)
        layout.addRow("Drawer Mount:", self.drawer_mount)
        layout.addRow("Inset Drawer Setback / Y (in or mm):", self.inset_setback)
        layout.addRow("Drawer Frame Width (in or mm):", self.drawer_frame_width)
        layout.addRow("Drawer Panel Thickness (in or mm):", self.drawer_panel_thickness)
        layout.addRow("Toe Kick Recess Depth (in or mm):", self.toe_depth)
        layout.addRow("Toe Kick Height (in or mm):", self.toe_height)
        layout.addRow("Toe Kick Thickness (in or mm):", self.toe_thickness)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        self.drawer_count.valueChanged.connect(self._update_drawer_field_states)
        self._update_drawer_field_states()
    @staticmethod
    def _dimension_field(params, name, fallback):
        return QtWidgets.QLineEdit(inch_text_from_mm(qty_mm(params.get(name), fallback)))
    def _update_drawer_field_states(self, *_args):
        count = int(self.drawer_count.value())
        for index, field in enumerate(self.drawer_heights, start=1):
            current_text = str(field.text()).strip()
            if current_text not in ("Auto", "None"):
                field._stored_dimension_text = current_text
            label = self.drawer_height_labels[index - 1]
            bottom_text = " - Bottom" if index == 1 else ""
            if index < count:
                label.setText("Drawer {} Height{}:".format(index, bottom_text))
                field.setEnabled(True)
                stored = getattr(field, "_stored_dimension_text", "")
                if stored:
                    field.setText(stored)
            elif index == count:
                label.setText("Drawer {} Height{} - Auto:".format(index, bottom_text))
                field.setEnabled(False)
                field.setText("Auto")
            else:
                label.setText("Drawer {} Height{} - None:".format(index, bottom_text))
                field.setEnabled(False)
                field.setText("None")
    def values(self):
        values = {
            "CabinetWidth": qty_mm(self.width.text(), 762.0),
            "CabinetDepth": qty_mm(self.depth.text(), 609.6),
            "CabinetHeight": qty_mm(self.height.text(), 812.8),
            "BoxWallThickness": qty_mm(self.wall.text(), 19.0),
            "DrawerThickness": qty_mm(self.drawer_thickness.text(), 19.0),
            "DrawerGap": qty_mm(self.drawer_gap.text(), 3.0),
            "DrawerCount": int(self.drawer_count.value()),
            "InsetSetback": qty_mm(self.inset_setback.text(), 0.0),
            "DrawerStyle": str(self.drawer_style.currentText()),
            "DrawerMount": str(self.drawer_mount.currentText()),
            "ToeKickDepth": qty_mm(self.toe_depth.text(), 88.9),
            "ToeKickHeight": qty_mm(self.toe_height.text(), 88.9),
            "ToeKickThickness": qty_mm(self.toe_thickness.text(), 19.05),
            "DrawerFrameWidth": qty_mm(self.drawer_frame_width.text(), 25.0),
            "DrawerPanelThickness": qty_mm(self.drawer_panel_thickness.text(), 6.0),
        }
        defaults = [254.0, 203.2, 152.4, 33.1, 33.1, 33.1, 0.0, 0.0]
        count = values["DrawerCount"]
        for index, field in enumerate(self.drawer_heights, start=1):
            if index < count:
                source_text = field.text()
                field._stored_dimension_text = source_text
            else:
                source_text = getattr(
                    field,
                    "_stored_dimension_text",
                    inch_text_from_mm(defaults[index - 1])
                )
            values["Drawer{}Height".format(index)] = qty_mm(
                source_text,
                defaults[index - 1]
            )
        return values

class CabinetBody:
    """Reusable hollow cabinet-body component."""
    def __init__(self, body, outer, inner):
        self.body = body
        self.outer = outer
        self.inner = inner
    @classmethod
    def create(cls, doc, prefix, label="Cabinet Carcass"):
        body = doc.addObject("PartDesign::Body", "{}_CabinetBody".format(prefix))
        body.Label = label
        outer = body.newObject("PartDesign::AdditiveBox", "{}_CabinetOuter".format(prefix))
        outer.Label = "Cabinet Outer"
        inner = body.newObject("PartDesign::SubtractiveBox", "{}_CabinetInnerCut".format(prefix))
        inner.Label = "Cabinet Inner Cut"
        return cls(body, outer, inner)
    @classmethod
    def from_existing(cls, body, outer, inner):
        return cls(body, outer, inner)
    @staticmethod
    def validate_dimensions(width, depth, height, thickness):
        if width <= 0 or depth <= 0 or height <= 0:
            raise RuntimeError("CabinetBody dimensions must be greater than zero.")
        if thickness <= 0:
            raise RuntimeError("CabinetBody thickness must be greater than zero.")
        if width - 2.0 * thickness <= 0:
            raise RuntimeError("CabinetBody thickness leaves no interior width.")
        if depth - thickness <= 0:
            raise RuntimeError("CabinetBody thickness leaves no interior depth.")
        if height - 2.0 * thickness <= 0:
            raise RuntimeError("CabinetBody thickness leaves no interior height.")
    def update(self, width, depth, height, thickness, x=0.0, y=0.0, z=0.0):
        self.validate_dimensions(width, depth, height, thickness)
        self.body.Placement = App.Placement(App.Vector(x, y, z), App.Rotation())
        self.outer.Placement = App.Placement()
        self.outer.Length = width
        self.outer.Width = depth
        self.outer.Height = height
        self.inner.Length = width - 2.0 * thickness
        self.inner.Width = depth - thickness
        self.inner.Height = height - 2.0 * thickness
        self.inner.Placement.Base = App.Vector(thickness, 0.0, thickness)
    def set_visible(self, visible):
        try:
            self.body.ViewObject.Visibility = bool(visible)
        except Exception:
            pass

class CabinetDrawerFront:
    """Reusable drawer-front component supporting Slab and Shaker styles."""
    STYLE_SLAB = "Slab"
    STYLE_SHAKER = "Shaker"
    def __init__(self, body, feature, style=STYLE_SLAB):
        self.body = body
        self.feature = feature
        self.style = style
        self._validate_style()
    @classmethod
    def create(cls, doc, prefix, component_name, label, style=STYLE_SLAB):
        body = doc.addObject("PartDesign::Body", "{}_{}".format(prefix, component_name))
        body.Label = label
        feature = body.newObject("PartDesign::Feature", "{}_{}Shape".format(prefix, component_name))
        feature.Label = "{} Shape".format(label)
        return cls(body, feature, style)
    @classmethod
    def from_existing(cls, body, feature, style=STYLE_SLAB):
        return cls(body, feature, style)
    def _validate_style(self):
        if self.style not in (self.STYLE_SLAB, self.STYLE_SHAKER):
            raise ValueError("Unsupported CabinetDrawerFront style: {}".format(self.style))
    @staticmethod
    def _slab_shape(width, height, thickness):
        return Part.makeBox(width, thickness, height, App.Vector(0, -thickness, 0))
    @staticmethod
    def _frame_shape(width, height, thickness, frame_width):
        opening_width = width - 2.0 * frame_width
        left = Part.makeBox(frame_width, thickness, height, App.Vector(0, -thickness, 0))
        right = Part.makeBox(frame_width, thickness, height, App.Vector(width - frame_width, -thickness, 0))
        bottom = Part.makeBox(opening_width, thickness, frame_width, App.Vector(frame_width, -thickness, 0))
        top = Part.makeBox(opening_width, thickness, frame_width, App.Vector(frame_width, -thickness, height - frame_width))
        shape = left.fuse(right).fuse(bottom).fuse(top)
        try:
            shape = shape.removeSplitter()
        except Exception:
            pass
        return shape
    @classmethod
    def _shaker_shape(cls, width, height, thickness, frame_width, panel_thickness):
        frame = cls._frame_shape(width, height, thickness, frame_width)
        opening_width = width - 2.0 * frame_width
        opening_height = height - 2.0 * frame_width
        panel_y = -(thickness + panel_thickness) / 2.0
        panel = Part.makeBox(opening_width, panel_thickness, opening_height, App.Vector(frame_width, panel_y, frame_width))
        shape = frame.fuse(panel)
        try:
            shape = shape.removeSplitter()
        except Exception:
            pass
        return shape
    def update(self, width, height, thickness, frame_width, panel_thickness, x=0.0, z=0.0, back_y=0.0):
        if width <= 0 or height <= 0 or thickness <= 0:
            raise RuntimeError("CabinetDrawerFront dimensions must be greater than zero.")
        if self.style == self.STYLE_SHAKER:
            if frame_width <= 0:
                raise RuntimeError("DrawerFrameWidth must be greater than zero.")
            if width - 2.0 * frame_width <= 0:
                raise RuntimeError("DrawerFrameWidth leaves no center opening width.")
            if height - 2.0 * frame_width <= 0:
                raise RuntimeError("DrawerFrameWidth leaves no center opening height.")
            if panel_thickness <= 0 or panel_thickness > thickness:
                raise RuntimeError("DrawerPanelThickness must be > 0 and <= DrawerThickness.")
        self.body.Placement = App.Placement(App.Vector(x, back_y, z), App.Rotation())
        self.feature.Placement = App.Placement()
        if self.style == self.STYLE_SLAB:
            self.feature.Shape = self._slab_shape(width, height, thickness)
        else:
            self.feature.Shape = self._shaker_shape(width, height, thickness, frame_width, panel_thickness)
    def set_visible(self, visible):
        state = bool(visible)
        try:
            self.body.ViewObject.Visibility = state
        except Exception:
            pass
        try:
            self.feature.ViewObject.Visibility = state
        except Exception:
            pass

class MultiDrawerLayout:
    """Sole authority for 1-8 drawer sizing and placement in Overlay / Inset modes."""
    MOUNT_OVERLAY = "Overlay"
    MOUNT_INSET = "Inset"
    @classmethod
    def calculate(cls, p):
        width = p["width"]
        height = p["height"]
        toe_kick_height = p["toe_kick_height"]
        wall = p["wall_thickness"]
        drawer_thickness = p["drawer_thickness"]
        gap = p["drawer_gap"]
        count = p["drawer_count"]
        requested_heights = list(p["drawer_heights"])
        mount = p["drawer_mount"]
        inset_setback = p["inset_setback"]
        if width <= 0 or p["depth"] <= 0 or height <= 0:
            raise RuntimeError("Cabinet Width, Depth and Height must all be greater than zero.")
        if count < MIN_DRAWERS or count > MAX_DRAWERS:
            raise RuntimeError("DrawerCount must be an integer between {} and {}.".format(MIN_DRAWERS, MAX_DRAWERS))
        if not 0 < toe_kick_height < height:
            raise RuntimeError("ToeKickHeight must be greater than zero and less than CabinetHeight.")
        if wall <= 0:
            raise RuntimeError("BoxWallThickness must be greater than zero.")
        if drawer_thickness <= 0:
            raise RuntimeError("DrawerThickness must be greater than zero.")
        if gap < 0:
            raise RuntimeError("DrawerGap cannot be negative.")
        if inset_setback < 0:
            raise RuntimeError("InsetSetback cannot be negative.")
        if mount not in FRONT_MOUNTS:
            raise RuntimeError("DrawerMount must be Overlay or Inset.")
        if len(requested_heights) < MAX_DRAWERS:
            raise RuntimeError("Eight drawer-height parameters are required.")
        fixed_heights = requested_heights[:max(0, count - 1)]
        for index, drawer_height in enumerate(fixed_heights, start=1):
            if drawer_height <= 0:
                raise RuntimeError(
                    "Drawer{}Height is a Fixed drawer and must be greater than zero. "
                    "The highest active drawer is Auto; drawers above DrawerCount are None."
                    .format(index)
                )
        carcass_height = height - toe_kick_height
        if mount == cls.MOUNT_OVERLAY:
            front_width = width
            available_height = carcass_height
            x = 0.0
            start_z = toe_kick_height
            back_y = 0.0
        else:
            front_width = width - 2.0 * wall
            available_height = carcass_height - 2.0 * wall
            if front_width <= 0:
                raise RuntimeError("Inset mode cannot be built because BoxWallThickness leaves no usable drawer-front width.")
            if available_height <= 0:
                raise RuntimeError("Inset mode cannot be built because BoxWallThickness leaves no usable drawer-front height.")
            x = wall
            start_z = toe_kick_height + wall
            back_y = drawer_thickness + inset_setback
        total_gap_height = (count - 1) * gap
        fixed_total = sum(fixed_heights)
        auto_height = available_height - total_gap_height - fixed_total
        if auto_height <= 0:
            raise RuntimeError(
                "The specified Fixed drawer heights and required gaps leave no room "
                "for Drawer {} (Auto). The stack exceeds the available opening by "
                "{:.3f} mm. Reduce one or more Fixed drawer heights, reduce DrawerGap, "
                "reduce DrawerCount, or increase CabinetHeight."
                .format(count, abs(auto_height))
            )
        heights = list(fixed_heights) + [auto_height]
        z_positions = []
        current_z = start_z
        for index, drawer_height in enumerate(heights):
            z_positions.append(current_z)
            if index < count - 1:
                current_z += drawer_height + gap
        resolved_top = z_positions[-1] + heights[-1]
        expected_top = start_z + available_height
        if abs(resolved_top - expected_top) > 1e-6:
            raise RuntimeError("Internal layout check failed: the resolved drawer stack does not exactly fill the available height.")
        states = []
        for index in range(1, MAX_DRAWERS + 1):
            if index < count:
                states.append("Fixed")
            elif index == count:
                states.append("Auto")
            else:
                states.append("None")
        return {
            "mount": mount,
            "drawer_count": count,
            "carcass_height": carcass_height,
            "available_height": available_height,
            "front_width": front_width,
            "x": x,
            "start_z": start_z,
            "back_y": back_y,
            "fixed_total": fixed_total,
            "gap_total": total_gap_height,
            "auto_count": 1,
            "auto_height": auto_height,
            "auto_index": count - 1,
            "states": states,
            "heights": heights,
            "z_positions": z_positions,
            "resolved_top": resolved_top,
        }

class MultiDrawerCabinetFP:
    MAX_DRAWERS = MAX_DRAWERS
    @staticmethod
    def _rounded_signature(*values):
        result = []
        for value in values:
            if isinstance(value, float):
                result.append(round(value, 9))
            else:
                result.append(value)
        return tuple(result)
    def _cabinet_input_signature(self, p):
        return self._rounded_signature(
            p["width"], p["depth"], p["height"],
            p["toe_kick_height"], p["wall_thickness"],
        )
    def _toe_kick_input_signature(self, p):
        return self._rounded_signature(
            p["width"], p["depth"],
            p["toe_kick_depth"], p["toe_kick_height"],
        )
    def _drawer_input_signature(self, index, p, layout):
        count = layout["drawer_count"]
        active = index < count
        if active:
            drawer_height = layout["heights"][index]
            drawer_z = layout["z_positions"][index]
        else:
            drawer_height = max(
                layout["heights"][0],
                2.0 * p["drawer_frame_width"] + 1.0
            )
            drawer_z = layout["start_z"]
        return self._rounded_signature(
            active, p["drawer_style"], layout["front_width"],
            drawer_height, p["drawer_thickness"],
            p["drawer_frame_width"], p["drawer_panel_thickness"],
            layout["x"], drawer_z, layout["back_y"],
        )
    @staticmethod
    def _settle_object(target, recursive=False):
        if target is None:
            return
        try:
            ok = bool(target.recompute(bool(recursive)))
        except Exception:
            return
        if not ok:
            return
        try:
            if "Touched" in list(target.State):
                target.purgeTouched()
        except Exception:
            pass
    def _settle_parameter_sheet(self, sheet):
        self._settle_object(sheet, False)
    def _settle_cabinet_geometry(self, body, outer, inner):
        self._settle_object(outer, False)
        self._settle_object(inner, False)
        self._settle_object(body, False)
    def _settle_drawer_geometry(self, body, feature):
        self._settle_object(feature, False)
        self._settle_object(body, False)
    def __init__(self, obj, assembly, sheet):
        self._building = True
        self._cabinet_signature = None
        self._toe_kick_signature = None
        self._drawer_signatures = {}
        obj.Proxy = self
        obj.addProperty("App::PropertyLink", "Parameters", "Component")
        obj.addProperty("App::PropertyString", "AssemblyObjectName", "Component")
        obj.AssemblyObjectName = assembly.Name
        try:
            obj.setEditorMode("AssemblyObjectName", 1)
        except Exception:
            pass
        self._create_geometry(obj, assembly, sheet)
        obj.Parameters = sheet
        self._building = False
        obj.touch()
    def _create_geometry(self, obj, assembly, sheet):
        doc = obj.Document
        prefix = assembly.Name
        origin_point = Draft.make_point(
            X=0.0,
            Y=0.0,
            Z=0.0,
            name="{}_OriginPoint".format(prefix),
            point_size=8,
        )
        origin_point.Label = "Assembly Origin Point"
        try:
            origin_point.ViewObject.Visibility = True
        except Exception:
            pass
        p = self._read_parameters(sheet)
        layout = self._validate(p)
        self._validate_front_geometry(p, layout)
        cabinet = CabinetBody.create(doc, prefix, label="Cabinet Carcass")
        toe_kick = doc.addObject("Part::Box", "{}_ToeKick".format(prefix))
        toe_kick.Label = "Toe Kick"
        self._update_cabinet(cabinet.body, cabinet.outer, cabinet.inner, p)
        self._update_toe_kick(toe_kick, p)
        assembly.addObject(sheet)
        assembly.addObject(origin_point)
        assembly.addObject(cabinet.body)
        assembly.addObject(toe_kick)
        doc.recompute()
        drawer_components = []
        for index in range(1, self.MAX_DRAWERS + 1):
            label = "Drawer Front {}{}".format(index, " - Bottom" if index == 1 else "")
            drawer_components.append(
                CabinetDrawerFront.create(
                    doc,
                    prefix,
                    "DrawerFront_{}".format(index),
                    label,
                    style=CabinetDrawerFront.STYLE_SLAB,
                )
            )
        drawer_objects = [(component.body, component.feature) for component in drawer_components]
        self._update_drawers(drawer_objects, p, layout)
        for component in drawer_components:
            assembly.addObject(component.body)
        self._update_drawers(drawer_objects, p, layout)
        self._cabinet_signature = self._cabinet_input_signature(p)
        self._toe_kick_signature = self._toe_kick_input_signature(p)
        self._drawer_signatures = {
            index: self._drawer_input_signature(index, p, layout)
            for index in range(self.MAX_DRAWERS)
        }
        assembly.addObject(obj)
        required = [sheet, origin_point, cabinet.body, toe_kick, obj] + [
            component.body for component in drawer_components
        ]
        missing = [member.Name for member in required if member not in assembly.Group]
        if missing:
            raise RuntimeError(
                "FreeCAD did not place all cabinet members inside '{}'. Missing group members: {}"
                .format(assembly.Name, ", ".join(missing))
            )
    def onDocumentRestored(self, obj):
        obj.Proxy = self
        self._building = False
        self._cabinet_signature = None
        self._toe_kick_signature = None
        self._drawer_signatures = {}
    def _assembly(self, obj):
        for parent in obj.InList:
            if parent.TypeId == "App::Part":
                return parent
        assembly_name = ""
        try:
            assembly_name = str(obj.AssemblyObjectName).strip()
        except Exception:
            pass
        if assembly_name:
            assembly = obj.Document.getObject(assembly_name)
            if assembly is not None and assembly.TypeId == "App::Part":
                return assembly
        raise RuntimeError("Multi-Drawer Cabinet Controller cannot resolve its owning App::Part.")
    def _child_by_label(self, assembly, label, type_id=None):
        for child in assembly.Group:
            if child.Label != label:
                continue
            if type_id is None or child.TypeId == type_id:
                return child
        return None
    def _parameters(self, obj, assembly):
        sheet = obj.Parameters
        if (
            sheet is not None
            and sheet.Document == obj.Document
            and sheet in assembly.Group
        ):
            return sheet
        sheet = self._child_by_label(assembly, "Parameters", "Spreadsheet::Sheet")
        if sheet is None:
            raise RuntimeError("Parameters spreadsheet not found for '{}'.".format(assembly.Name))
        return sheet
    def _geometry(self, assembly):
        doc = assembly.Document
        prefix = assembly.Name
        body = doc.getObject("{}_CabinetBody".format(prefix))
        outer = doc.getObject("{}_CabinetOuter".format(prefix))
        inner = doc.getObject("{}_CabinetInnerCut".format(prefix))
        toe_kick = doc.getObject("{}_ToeKick".format(prefix))
        if body is None or outer is None or inner is None or toe_kick is None:
            raise RuntimeError(
                "Cabinet body/toe-kick geometry is incomplete for '{}'."
                .format(assembly.Name)
            )
        drawers = []
        for index in range(1, self.MAX_DRAWERS + 1):
            drawer_body = doc.getObject("{}_DrawerFront_{}".format(prefix, index))
            drawer_shape = doc.getObject("{}_DrawerFront_{}Shape".format(prefix, index))
            if drawer_body is None or drawer_shape is None:
                raise RuntimeError(
                    "Drawer Front {} not found for '{}'."
                    .format(index, assembly.Name)
                )
            drawers.append((drawer_body, drawer_shape))
        return body, outer, inner, toe_kick, drawers
    def _read_parameters(self, sheet):
        p = SheetParams(sheet)
        count = qty_int(p.get("DrawerCount"), DEFAULT_DRAWER_COUNT)
        defaults = [254.0, 203.2, 152.4, 33.1, 33.1, 33.1, 0.0, 0.0]
        drawer_heights = [
            qty_mm(p.get("Drawer{}Height".format(index)), defaults[index - 1])
            for index in range(1, MAX_DRAWERS + 1)
        ]
        values = {
            "width": qty_mm(p.get("CabinetWidth"), 762.0),
            "depth": qty_mm(p.get("CabinetDepth"), 609.6),
            "height": qty_mm(p.get("CabinetHeight"), 812.8),
            "wall_thickness": qty_mm(p.get("BoxWallThickness"), 19.0),
            "drawer_thickness": qty_mm(p.get("DrawerThickness"), 19.0),
            "drawer_gap": qty_mm(p.get("DrawerGap"), 3.0),
            "drawer_count": count,
            "drawer_heights": drawer_heights,
            "inset_setback": qty_mm(p.get("InsetSetback"), 0.0),
            "drawer_style": str(p.get("DrawerStyle", "Slab")).strip(),
            "drawer_mount": str(p.get("DrawerMount", "Overlay")).strip(),
            "toe_kick_depth": qty_mm(p.get("ToeKickDepth"), 88.9),
            "toe_kick_height": qty_mm(p.get("ToeKickHeight"), 88.9),
            "toe_kick_thickness": qty_mm(p.get("ToeKickThickness"), 19.05),
            "drawer_frame_width": qty_mm(p.get("DrawerFrameWidth"), 25.0),
            "drawer_panel_thickness": qty_mm(p.get("DrawerPanelThickness"), 6.0),
        }
        if values["drawer_style"] not in FRONT_STYLES:
            values["drawer_style"] = "Slab"
        if values["drawer_mount"] not in FRONT_MOUNTS:
            values["drawer_mount"] = "Overlay"
        return values
    def _validate(self, p):
        if p["toe_kick_thickness"] <= 0:
            raise RuntimeError("ToeKickThickness must be greater than zero.")
        if not 0 < p["toe_kick_depth"] < p["depth"]:
            raise RuntimeError(
                "ToeKickDepth must be greater than zero and less than CabinetDepth."
            )
        if p["drawer_style"] not in FRONT_STYLES:
            raise RuntimeError("DrawerStyle must be Slab or Shaker.")
        if p["drawer_mount"] not in FRONT_MOUNTS:
            raise RuntimeError("DrawerMount must be Overlay or Inset.")
        layout = MultiDrawerLayout.calculate(p)
        CabinetBody.validate_dimensions(
            p["width"],
            p["depth"],
            layout["carcass_height"],
            p["wall_thickness"],
        )
        if p["drawer_mount"] == MultiDrawerLayout.MOUNT_INSET:
            if p["inset_setback"] + p["drawer_thickness"] > p["depth"]:
                raise RuntimeError(
                    "InsetSetback + DrawerThickness cannot exceed CabinetDepth."
                )
        return layout
    def _validate_front_geometry(self, p, layout):
        if p["drawer_style"] != CabinetDrawerFront.STYLE_SHAKER:
            return
        frame = p["drawer_frame_width"]
        panel = p["drawer_panel_thickness"]
        if frame <= 0:
            raise RuntimeError("DrawerFrameWidth must be greater than zero.")
        if layout["front_width"] - 2.0 * frame <= 0:
            raise RuntimeError(
                "DrawerFrameWidth leaves no center opening width. "
                "Reduce DrawerFrameWidth or increase CabinetWidth."
            )
        for index, height in enumerate(layout["heights"], start=1):
            if height - 2.0 * frame <= 0:
                raise RuntimeError(
                    "Drawer {} is {:.3f} mm high, which is too short for the current Shaker frame width of {:.3f} mm. "
                    "Use Slab style, reduce DrawerFrameWidth, increase CabinetHeight, reduce DrawerCount, "
                    "or change the fixed drawer heights."
                    .format(index, height, frame)
                )
        if panel <= 0 or panel > p["drawer_thickness"]:
            raise RuntimeError(
                "DrawerPanelThickness must be greater than zero and no greater than DrawerThickness."
            )
    def _update_cabinet(self, body, outer, inner, p):
        cabinet = CabinetBody.from_existing(body, outer, inner)
        cabinet.update(
            width=p["width"],
            depth=p["depth"],
            height=p["height"] - p["toe_kick_height"],
            thickness=p["wall_thickness"],
            x=0.0,
            y=0.0,
            z=p["toe_kick_height"],
        )
    def _update_toe_kick(self, toe_kick, p):
        toe_kick.Length = p["width"]
        toe_kick.Width = p["depth"] - p["toe_kick_depth"]
        toe_kick.Height = p["toe_kick_height"]
        toe_kick.Placement.Base = App.Vector(0.0, p["toe_kick_depth"], 0.0)
    def _update_drawers(self, drawer_objects, p, layout, only_indices=None):
        style = p["drawer_style"]
        count = layout["drawer_count"]
        safe_hidden_height = max(
            layout["heights"][0],
            2.0 * p["drawer_frame_width"] + 1.0
        )
        selected = None if only_indices is None else set(only_indices)
        for index, (body, feature) in enumerate(drawer_objects):
            if selected is not None and index not in selected:
                continue
            drawer = CabinetDrawerFront.from_existing(body, feature, style)
            active = index < count
            if active:
                drawer_height = layout["heights"][index]
                drawer_z = layout["z_positions"][index]
            else:
                drawer_height = safe_hidden_height
                drawer_z = layout["start_z"]
            drawer.update(
                width=layout["front_width"],
                height=drawer_height,
                thickness=p["drawer_thickness"],
                frame_width=p["drawer_frame_width"],
                panel_thickness=p["drawer_panel_thickness"],
                x=layout["x"],
                z=drawer_z,
                back_y=layout["back_y"],
            )
            drawer.set_visible(active)
    def execute(self, obj):
        if getattr(self, "_building", False):
            return
        assembly = self._assembly(obj)
        sheet = self._parameters(obj, assembly)
        p = self._read_parameters(sheet)
        layout = self._validate(p)
        self._validate_front_geometry(p, layout)
        body, outer, inner, toe_kick, drawers = self._geometry(assembly)
        cabinet_signature = self._cabinet_input_signature(p)
        toe_kick_signature = self._toe_kick_input_signature(p)
        changed_drawers = []
        drawer_signatures = {}
        for index in range(self.MAX_DRAWERS):
            signature = self._drawer_input_signature(index, p, layout)
            drawer_signatures[index] = signature
            if self._drawer_signatures.get(index) != signature:
                changed_drawers.append(index)
        if self._cabinet_signature != cabinet_signature:
            self._update_cabinet(body, outer, inner, p)
            self._settle_cabinet_geometry(body, outer, inner)
            self._cabinet_signature = cabinet_signature
        if self._toe_kick_signature != toe_kick_signature:
            self._update_toe_kick(toe_kick, p)
            self._settle_object(toe_kick, False)
            self._toe_kick_signature = toe_kick_signature
        if changed_drawers:
            self._update_drawers(drawers, p, layout, only_indices=changed_drawers)
            for index in changed_drawers:
                drawer_body, drawer_feature = drawers[index]
                self._settle_drawer_geometry(drawer_body, drawer_feature)
                self._drawer_signatures[index] = drawer_signatures[index]
        self._settle_parameter_sheet(sheet)

def validate_dialog_values(values):
    p = {
        "width": values["CabinetWidth"],
        "depth": values["CabinetDepth"],
        "height": values["CabinetHeight"],
        "wall_thickness": values["BoxWallThickness"],
        "drawer_thickness": values["DrawerThickness"],
        "drawer_gap": values["DrawerGap"],
        "drawer_count": values["DrawerCount"],
        "drawer_heights": [
            values["Drawer{}Height".format(index)]
            for index in range(1, MAX_DRAWERS + 1)
        ],
        "inset_setback": values["InsetSetback"],
        "drawer_style": values["DrawerStyle"],
        "drawer_mount": values["DrawerMount"],
        "toe_kick_depth": values["ToeKickDepth"],
        "toe_kick_height": values["ToeKickHeight"],
        "toe_kick_thickness": values["ToeKickThickness"],
        "drawer_frame_width": values["DrawerFrameWidth"],
        "drawer_panel_thickness": values["DrawerPanelThickness"],
    }
    try:
        helper = object.__new__(MultiDrawerCabinetFP)
        layout = helper._validate(p)
        helper._validate_front_geometry(p, layout)
        return True, ""
    except Exception as exc:
        return False, str(exc)

def _sanitize_object_name(name):
    cleaned = "".join(
        character if (character.isalnum() or character == "_") else "_"
        for character in str(name).strip()
    )
    if not cleaned:
        cleaned = INSTANCE_BASENAME
    if cleaned[0].isdigit():
        cleaned = "{}_{}".format(INSTANCE_BASENAME, cleaned)
    return cleaned

def next_multi_drawer_lower_cabinet_name(document):
    if document is None:
        raise ValueError("A valid FreeCAD document is required.")
    index = 1
    while True:
        candidate = "{}{:03d}".format(INSTANCE_BASENAME, index)
        if document.getObject(candidate) is None:
            return candidate
        index += 1

class EndpointSnapPointPicker:
    """Preference-free endpoint picker with two-attempt origin fallback."""
    def __init__(self, on_accept, on_cancel):
        self.on_accept = on_accept
        self.on_cancel = on_cancel
        self.view = None
        self.snapper = None
        self.callback_move = None
        self.callback_click = None
        self.callback_key = None
        self._old_active_snaps = None
        self._last_endpoint_state = None
        self._finished = False
        self._failed_endpoint_picks = 0
    def begin(self):
        if Gui.ActiveDocument is None:
            raise RuntimeError("A FreeCAD GUI document is required to pick an insertion point.")
        self.view = Gui.ActiveDocument.ActiveView
        if self.view is None:
            raise RuntimeError("No active 3D view is available for endpoint selection.")
        self.snapper = self._ensure_snapper()
        self._old_active_snaps = list(getattr(self.snapper, "active_snaps", []))
        self.snapper.active_snaps = ["Lock", "Endpoint"]
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r"builtin type SwigPyObject has no __module__ attribute",
                category=DeprecationWarning,
            )
            self.callback_move = self.view.addEventCallbackPivy(
                coin.SoLocation2Event.getClassTypeId(),
                self._mouse_move,
            )
            self.callback_click = self.view.addEventCallbackPivy(
                coin.SoMouseButtonEvent.getClassTypeId(),
                self._mouse_click,
            )
            self.callback_key = self.view.addEventCallbackPivy(
                coin.SoKeyboardEvent.getClassTypeId(),
                self._key_press,
            )
        self._show_status(
            "Select multi-drawer cabinet insertion point: hover over an existing endpoint until the snap marker appears, then left-click. Press Esc or right-click to cancel."
        )
        try:
            Gui.updateGui()
        except Exception:
            pass
    def cancel(self):
        if self._finished:
            return
        self._finished = True
        self._cleanup()
        try:
            self.on_cancel()
        except Exception as exc:
            App.Console.PrintError("Multi-drawer cabinet endpoint-cancel callback failed: {}\n".format(exc))
    def _ensure_snapper(self):
        try:
            import DraftTools
        except Exception as exc:
            raise RuntimeError(
                "FreeCAD's Draft GUI tools could not initialize the canonical Snapper: {}"
                .format(exc)
            )
        snapper = getattr(Gui, "Snapper", None)
        if snapper is None:
            raise RuntimeError("FreeCAD's canonical Draft Snapper was not initialized.")
        return snapper
    def _mouse_move(self, event_callback):
        if self._finished:
            return
        try:
            event = event_callback.getEvent()
            self.snapper.snap(
                event.getPosition(),
                lastpoint=None,
                active=True,
                constrain=False,
                noTracker=False,
            )
            endpoint_active = str(getattr(self.snapper, "cursorMode", "") or "").lower() == "endpoint"
            if endpoint_active != self._last_endpoint_state:
                self._last_endpoint_state = endpoint_active
                if endpoint_active:
                    self._show_status("Endpoint found — left-click to place the cabinet.")
                elif self._failed_endpoint_picks == 0:
                    self._show_status("Select an existing endpoint/vertex.")
                else:
                    self._show_status("Second pick: select an endpoint. If no endpoint exists, click again to place at 0,0,0.")
        except Exception:
            pass
    def _mouse_click(self, event_callback):
        if self._finished:
            return
        try:
            event = event_callback.getEvent()
            if event.getState() != coin.SoButtonEvent.DOWN:
                return
            button = event.getButton()
            if button == coin.SoMouseButtonEvent.BUTTON2:
                event_callback.setHandled()
                self.cancel()
                return
            if button != coin.SoMouseButtonEvent.BUTTON1:
                return
            point = self.snapper.snap(
                event.getPosition(),
                lastpoint=None,
                active=True,
                constrain=False,
                noTracker=False,
            )
            snap_mode = str(getattr(self.snapper, "cursorMode", "") or "").lower()
            if point is None or snap_mode != "endpoint":
                event_callback.setHandled()
                if self._failed_endpoint_picks == 0:
                    self._failed_endpoint_picks = 1
                    self._show_status("Second pick: select an endpoint. If no endpoint exists, click again to place at 0,0,0.")
                    QtWidgets.QMessageBox.information(
                        None,
                        "Endpoint Required",
                        "An endpoint is required, please select an endpoint, if none exists on second pick cabinet will be drawn at 0,0,0.",
                    )
                    return
                self._finished = True
                accepted_point = App.Vector(0.0, 0.0, 0.0)
                App.Console.PrintMessage("No endpoint selected on second pick; placing Multi-Drawer Lower Cabinet at 0,0,0.\n")
                self._cleanup()
                try:
                    self.on_accept(accepted_point)
                except Exception as exc:
                    App.Console.PrintError("Multi-drawer cabinet insertion callback failed: {}\n".format(exc))
                return
            event_callback.setHandled()
            self._finished = True
            accepted_point = App.Vector(point)
            self._cleanup()
            try:
                self.on_accept(accepted_point)
            except Exception as exc:
                App.Console.PrintError("Multi-drawer cabinet insertion callback failed: {}\n".format(exc))
        except Exception as exc:
            App.Console.PrintError("Endpoint click handling failed: {}\n".format(exc))
            self.cancel()
    def _key_press(self, event_callback):
        if self._finished:
            return
        try:
            event = event_callback.getEvent()
            if event.getState() == coin.SoButtonEvent.DOWN and event.getKey() == coin.SoKeyboardEvent.ESCAPE:
                event_callback.setHandled()
                self.cancel()
        except Exception:
            pass
    def _cleanup(self):
        callbacks_removed = False
        if self.view is not None:
            if self.callback_move is not None:
                try:
                    self.view.removeEventCallbackPivy(
                        coin.SoLocation2Event.getClassTypeId(),
                        self.callback_move,
                    )
                    callbacks_removed = True
                except Exception:
                    pass
            if self.callback_click is not None:
                try:
                    self.view.removeEventCallbackPivy(
                        coin.SoMouseButtonEvent.getClassTypeId(),
                        self.callback_click,
                    )
                    callbacks_removed = True
                except Exception:
                    pass
            if self.callback_key is not None:
                try:
                    self.view.removeEventCallbackPivy(
                        coin.SoKeyboardEvent.getClassTypeId(),
                        self.callback_key,
                    )
                    callbacks_removed = True
                except Exception:
                    pass
        self.callback_move = None
        self.callback_click = None
        self.callback_key = None
        if callbacks_removed:
            try:
                gui_utils.end_all_events()
            except Exception:
                pass
        if self.snapper is not None:
            try:
                if self._old_active_snaps is not None:
                    self.snapper.active_snaps = list(self._old_active_snaps)
            except Exception:
                pass
            try:
                if self.snapper.tracker:
                    self.snapper.tracker.off()
            except Exception:
                pass
            try:
                self.snapper.setCursor()
            except Exception:
                pass
            try:
                self.snapper.running = False
            except Exception:
                pass
        self._clear_status()
        try:
            Gui.updateGui()
        except Exception:
            pass
    @staticmethod
    def _show_status(message):
        try:
            Gui.getMainWindow().statusBar().showMessage(message)
        except Exception:
            pass
    @staticmethod
    def _clear_status():
        try:
            Gui.getMainWindow().statusBar().clearMessage()
        except Exception:
            pass

class MultiDrawerCabinetBuilder:
    def __init__(self, document, instance_name):
        if document is None:
            raise ValueError(
                "create_multi_drawer_lower_cabinet() requires an existing FreeCAD document."
            )
        self.document = document
        self.instance_name = _sanitize_object_name(instance_name)
        if self.document.getObject(self.instance_name) is not None:
            raise ValueError(
                "An object named '{}' already exists in document '{}'."
                .format(self.instance_name, self.document.Name)
            )
        self.parameters = None
        self.assembly = None
        self.controller = None
        self.values = None
        self.insertion_point = None
        self._picker = None
        self._original_object_names = set(obj.Name for obj in self.document.Objects)
    def run(self):
        self._print_header()
        try:
            self.parameters = ParameterTable.create(
                self.document,
                "{}_Parameters".format(self.instance_name),
            )
            if not self._collect_parameters():
                self._rollback_new_objects()
                return None
            self._begin_insertion_point()
            return self
        except Exception:
            self._rollback_new_objects()
            raise
    def _collect_parameters(self):
        dialog = CabinetDialog(self.parameters)
        if not dialog.exec():
            print(
                "Multi-drawer cabinet creation cancelled. "
                "The active layout document was not changed."
            )
            return False
        self.values = dialog.values()
        valid, message = validate_dialog_values(self.values)
        if not valid:
            QtWidgets.QMessageBox.critical(
                None,
                "Invalid Multi-Drawer Cabinet Parameters",
                message,
            )
            return False
        ParameterTable.update(self.document, self.parameters, self.values)
        ParameterTable.verify(self.parameters)
        return True
    def _begin_insertion_point(self):
        self._picker = EndpointSnapPointPicker(
            on_accept=self._insertion_point_accepted,
            on_cancel=self._insertion_point_cancelled,
        )
        self._picker.begin()
    def _insertion_point_accepted(self, point):
        self.insertion_point = App.Vector(point)
        self._picker = None
        print(
            "Insertion point: X={:.3f}, Y={:.3f}, Z={:.3f} mm"
            .format(
                self.insertion_point.x,
                self.insertion_point.y,
                self.insertion_point.z,
            )
        )
        try:
            self._create_component()
            self.document.recompute()
            self._show_component()
            self._print_report()
        except Exception as exc:
            self._rollback_new_objects()
            QtWidgets.QMessageBox.critical(
                None,
                "Multi-Drawer Cabinet Creation Error",
                str(exc),
            )
            App.Console.PrintError(
                "Multi-drawer cabinet creation failed: {}\n".format(exc)
            )
    def _insertion_point_cancelled(self):
        self._picker = None
        self._rollback_new_objects()
        print(
            "Multi-drawer cabinet insertion cancelled. "
            "The active layout document was not changed."
        )
    def _create_component(self):
        self.assembly = self.document.addObject("App::Part", self.instance_name)
        self.assembly.Label = "Multi-Drawer Lower Cabinet"
        if self.insertion_point is not None:
            self.assembly.Placement.Base = App.Vector(self.insertion_point)
        self.controller = self.document.addObject(
            "Part::FeaturePython",
            "{}_Controller".format(self.instance_name),
        )
        self.controller.Label = "Multi-Drawer Cabinet Controller"
        MultiDrawerCabinetFP(
            self.controller,
            self.assembly,
            self.parameters,
        )
    def _rollback_new_objects(self):
        new_names = [
            obj.Name
            for obj in self.document.Objects
            if obj.Name not in self._original_object_names
        ]
        for name in reversed(new_names):
            try:
                self.document.removeObject(name)
            except Exception:
                pass
        try:
            self.document.recompute()
        except Exception:
            pass
    def _show_component(self):
        try:
            App.setActiveDocument(self.document.Name)
        except Exception:
            pass
        try:
            Gui.Selection.clearSelection()
            Gui.Selection.addSelection(self.assembly)
        except Exception:
            pass
        try:
            Gui.activeDocument().activeView().viewAxonometric()
            Gui.activeDocument().activeView().fitAll()
        except Exception:
            pass
    def _print_header(self):
        print("")
        print("=" * 70)
        print("MULTI-DRAWER LOWER CABINET - PROTOTYPE REVISION 0.08")
        print("Target document: {}".format(self.document.Name))
        print("Instance name:   {}".format(self.instance_name))
        print("=" * 70)
    def _print_report(self):
        p = SheetParams(self.parameters)
        helper = object.__new__(MultiDrawerCabinetFP)
        values = helper._read_parameters(self.parameters)
        layout = MultiDrawerLayout.calculate(values)
        print("")
        print("-" * 70)
        print("MULTI-DRAWER CABINET INSTANCE CREATED SUCCESSFULLY")
        print("-" * 70)
        print("Document:               ", self.document.Name)
        print("Cabinet instance:       ", self.assembly.Name)
        print("Parameters sheet:       ", self.parameters.Name)
        print("Controller:             ", self.controller.Name)
        print("Drawer count:           ", layout["drawer_count"])
        print("Drawer style:           ", values["drawer_style"])
        print("Drawer mount:           ", values["drawer_mount"])
        print("Available front height: ", inch_text_from_mm(layout["available_height"]))
        print("Total drawer gaps:      ", inch_text_from_mm(layout["gap_total"]))
        print("Fixed drawer total:     ", inch_text_from_mm(layout["fixed_total"]))
        print("Auto drawer:            ", layout["drawer_count"])
        print("Auto drawer height:     ", inch_text_from_mm(layout["auto_height"]))
        for index, drawer_height in enumerate(layout["heights"], start=1):
            source = "Auto" if index == layout["drawer_count"] else "Fixed"
            print(
                "Drawer {:d} height:       {:>12s}  ({})"
                .format(index, inch_text_from_mm(drawer_height), source)
            )
        print("Drawer visible front Y: ", inch_text_from_mm(
            layout["back_y"] - values["drawer_thickness"]
        ))
        if self.insertion_point is not None:
            print(
                "Insertion Point:         X={:.3f}, Y={:.3f}, Z={:.3f} mm"
                .format(
                    self.insertion_point.x,
                    self.insertion_point.y,
                    self.insertion_point.z,
                )
            )
        print("")

def create_multi_drawer_lower_cabinet(document, instance_name):
    builder = MultiDrawerCabinetBuilder(
        document=document,
        instance_name=instance_name,
    )
    return builder.run()

def main():
    document = App.ActiveDocument
    if document is None:
        QtWidgets.QMessageBox.warning(
            None,
            "No Active FreeCAD Document",
            "Open or create the kitchen/layout document first, then run this macro again.",
        )
        return None
    instance_name = next_multi_drawer_lower_cabinet_name(document)
    return create_multi_drawer_lower_cabinet(
        document=document,
        instance_name=instance_name,
    )

if __name__ == "__main__":
    main()

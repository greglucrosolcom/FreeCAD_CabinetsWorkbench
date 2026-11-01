# ============================================================
# PARAMETRIC 30-INCH VANITY / MIXED-FRONT BASE CABINET
# SELF-CONTAINED PARAMETRIC FEATUREPYTHON VERSION
# ============================================================
# Target: FreeCAD 1.1.3
# REVISION: 0.13
# REVISION HISTORY:
#   0.00 - Baseline 30-Inch Vanity / Mixed-Front Base Cabinet
#          - image-derived 30 in W x 21 in D x 34.5 in H defaults
#          - full-width top drawer front
#          - lower-left door
#          - upper/lower right drawer fronts and drawer boxes
#          - hollow carcass with recessed toe kick
#          - top horizontal divider and lower vertical divider
#          - per-instance Parameters spreadsheet
#          - nearest-1/16-inch display
#          - FeaturePython controller with build guard
#          - preference-free endpoint select-to-insert
#   0.01 - Insertion usability revision
#          - first non-endpoint pick displays an Endpoint Required dialog
#          - second pick still accepts a valid endpoint
#          - second non-endpoint pick creates the cabinet at 0,0,0
#          - Esc / right-click still cancel normally
#          - no persistent Draft snap preferences are changed
#   0.02 - Assembly origin snap-point revision
#          - adds a visible Draft Point at local component origin 0,0,0
#          - point is grouped inside the component App::Part
#          - point moves and rotates with the component parent Placement
#          - provides an Endpoint snap reference for Draft Move placement
#   0.11 - Mixed-front component-class / layout revision
#          - adds standardized CabinetBody, CabinetDoor and CabinetDrawerFront
#          - adds CabinetDrawerBox for the three functional drawer boxes
#          - adds MixedFrontLayout as sole front-size/position authority
#          - LeftDoorWidth is now calculated instead of independently entered
#          - RightColumnWidth remains the horizontal user sizing control
#          - LowerRightDrawerHeight is calculated from the remaining lower zone
#          - TopDrawerHeight and UpperRightDrawerHeight remain direct controls
#          - adds independent Slab / Shaker DoorStyle and DrawerStyle Data properties
#          - separates front offset, column gap, vertical gaps and side reveals
#          - validates all computed fronts and drawer boxes before geometry changes
#          - initializes valid geometry before App::Part grouping
#          - suppresses only the known SWIG/Pivy callback DeprecationWarning
#          - preserves the existing solid recessed toe kick and internal dividers
#   0.12 - Spreadsheet front-style authority correction
#          - adds DoorStyle and DrawerStyle directly to the Parameters sheet
#          - Parameters sheet is now the sole authority for Slab / Shaker styles
#          - changing DrawerStyle in the sheet rebuilds all drawer fronts on recompute
#          - changing DoorStyle in the sheet rebuilds the cabinet door on recompute
#          - removes competing controller-style authority from geometry updates
#          - preserves all mixed-front sizing, drawer boxes, dividers and insertion behavior
#   0.13 - Front style + Overlay / Inset parameter revision
#          - retains DoorStyle and DrawerStyle in the Parameters sheet
#          - adds FrontMount = Overlay / Inset to the Parameters sheet
#          - FrontMount controls the door and all drawer fronts as one coordinated face system
#          - adds InsetSetback for Y-only inset-front positioning
#          - initial dialog exposes DoorStyle, DrawerStyle and FrontMount
#          - Overlay preserves Revision 0.12 mixed-front sizing and placement
#          - Inset sizes the complete mixed-front layout inside the carcass front opening
#          - existing ColumnGap, TopLowerGap and RightDrawerGap remain active in both modes
#          - Parameters sheet remains the sole authority for style and mount choices
#          - drawer boxes, dividers, toe kick and insertion behavior are preserved
# ============================================================
# RESIZING CONTRACT
# ============================================================
# Horizontal:
#   FrontSideReveal and ColumnGap are fixed user dimensions.
#   RightColumnWidth is direct.
#   LeftDoorWidth is derived:
#       CabinetWidth - 2*FrontSideReveal - ColumnGap - RightColumnWidth
#
# Vertical:
#   TopDrawerHeight is direct.
#   Lower zone is derived from CabinetHeight, ToeKickHeight, TopDrawerHeight
#   and TopLowerGap.
#   Left door fills the entire lower zone.
#   UpperRightDrawerHeight is direct.
#   LowerRightDrawerHeight is derived from the lower-zone remainder.
#
# Coordinate system:
#   cabinet front/reference plane = Y=0
#   cabinet extends toward +Y
#   overlay drawer/door fronts extend toward -Y
#   inset fronts occupy +Y inside the carcass opening
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
INSTANCE_BASENAME = "VanityBaseCabinet"
FRONT_STYLES = ("Slab", "Shaker")
FRONT_MOUNTS = ("Overlay", "Inset")
TEXT_PARAMETERS = {"DoorStyle", "DrawerStyle", "FrontMount"}
PARAMETER_OPTIONS = {
    "DoorStyle": "Slab | Shaker",
    "DrawerStyle": "Slab | Shaker",
    "FrontMount": "Overlay | Inset",
}

PARAM_DEFAULTS = [
    ("CabinetWidth",              "762 mm"),
    ("CabinetDepth",              "533.4 mm"),
    ("CabinetHeight",             "876.3 mm"),
    ("BoxWallThickness",          "19.05 mm"),
    ("FrontThickness",            "19.05 mm"),
    ("FrontOffset",               "3 mm"),
    ("InsetSetback",              "0 mm"),
    ("FrontSideReveal",           "11.2 mm"),
    ("ColumnGap",                 "3 mm"),
    ("TopLowerGap",               "3 mm"),
    ("RightDrawerGap",            "3 mm"),
    ("RightColumnWidth",          "292.1 mm"),
    ("TopDrawerHeight",           "158.75 mm"),
    ("UpperRightDrawerHeight",    "292.1 mm"),
    ("DoorFrameWidth",            "50.8 mm"),
    ("DoorPanelThickness",        "6 mm"),
    ("DrawerFrameWidth",          "50.8 mm"),
    ("DrawerPanelThickness",      "6 mm"),
    ("DoorStyle",                 "Shaker"),
    ("DrawerStyle",               "Shaker"),
    ("FrontMount",                "Overlay"),
    ("ToeKickHeight",             "88.9 mm"),
    ("ToeKickSetback",            "88.9 mm"),
    ("DrawerBoxDepth",            "457.2 mm"),
    ("DrawerBoxWallThickness",    "12.7 mm"),
    ("DrawerSideClearance",       "6 mm"),
    ("DrawerVerticalClearance",   "3 mm"),
]

class SheetParams:
    def __init__(self, sheet, row_start=2, row_end=70):
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
    def row_of(self, key):
        for row in range(self.row_start, self.row_end + 1):
            value = self.get_cell("A{}".format(row))
            if value is not None and str(value).strip() == key:
                return row
        return None
    def get(self, key, default=None):
        row = self.row_of(key)
        if row is None:
            return default
        value = self.get_cell("B{}".format(row))
        return default if value is None else value
    def set(self, key, value):
        row = self.row_of(key)
        if row is None:
            raise KeyError("Parameter '{}' was not found.".format(key))
        self.sheet.set("B{}".format(row), str(value))

def qty_mm(value, fallback):
    try:
        if value is None:
            return float(fallback)
        text = str(value).strip()
        if not text:
            return float(fallback)
        if all(c.isdigit() or c in ".-+" for c in text):
            text += " mm"
        return float(App.Units.Quantity(text).Value)
    except Exception:
        return float(fallback)

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
            sheet.setColumnWidth("A", 240)
            sheet.setColumnWidth("B", 180)
        except Exception:
            pass
        ParameterTable.update_inches_column(sheet)
        ParameterTable.update_options_column(sheet)
        doc.recompute()
        return sheet
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
        for row, (_name, default_value) in enumerate(PARAM_DEFAULTS, start=2):
            if not str(default_value).strip().lower().endswith("mm"):
                continue
            metric_address = "B{}".format(row)
            value = params.get_cell(metric_address)
            if value is None or not str(value).strip():
                continue
            sheet.set("C{}".format(row), ParameterTable._fractional_inch_expression(metric_address))
    @staticmethod
    def update_options_column(sheet):
        sheet.set("D1", "Options")
        try:
            sheet.setColumnWidth("D", 180)
        except Exception:
            pass
        for row, (name, _default_value) in enumerate(PARAM_DEFAULTS, start=2):
            sheet.set("D{}".format(row), PARAMETER_OPTIONS.get(name, ""))
    @staticmethod
    def update(doc, sheet, values):
        params = SheetParams(sheet)
        for name, default_value in PARAM_DEFAULTS:
            value = values.get(name, params.get(name, default_value))
            if name in TEXT_PARAMETERS:
                text = str(value)
            elif name in values:
                text = "{} mm".format(value)
            else:
                text = str(value)
            params.set(name, text)
            row = params.row_of(name)
            try:
                sheet.setAlias("B{}".format(row), name)
            except Exception:
                pass
        ParameterTable.update_inches_column(sheet)
        ParameterTable.update_options_column(sheet)
        doc.recompute()
    @staticmethod
    def verify(sheet):
        params = SheetParams(sheet)
        bad = []
        for name, _default in PARAM_DEFAULTS:
            value = params.get(name)
            text = "" if value is None else str(value).strip()
            if not text or "#REF" in text.upper():
                bad.append(name)
        if bad:
            raise RuntimeError("Parameters did not resolve: {}".format(", ".join(bad)))

class VanityBaseCabinetDialog(QtWidgets.QDialog):
    def __init__(self, sheet):
        super().__init__()
        p = SheetParams(sheet)
        self.setWindowTitle("30-Inch Vanity / Mixed-Front Base Cabinet")
        layout = QtWidgets.QFormLayout(self)
        fields = [
            ("width", "CabinetWidth", 762.0, "Cabinet Width / X (mm):"),
            ("depth", "CabinetDepth", 533.4, "Cabinet Depth / Y (mm):"),
            ("height", "CabinetHeight", 876.3, "Cabinet Height / Z (mm):"),
            ("wall", "BoxWallThickness", 19.05, "Carcass Wall Thickness (mm):"),
            ("front_t", "FrontThickness", 19.05, "Front Thickness (mm):"),
            ("front_offset", "FrontOffset", 3.0, "Overlay Front Offset (mm):"),
            ("inset_setback", "InsetSetback", 0.0, "Inset Setback / Y (mm):"),
            ("side_reveal", "FrontSideReveal", 11.2, "Front Side Reveal (mm):"),
            ("column_gap", "ColumnGap", 3.0, "Door / Drawer Column Gap (mm):"),
            ("top_lower_gap", "TopLowerGap", 3.0, "Top Drawer / Lower Gap (mm):"),
            ("right_drawer_gap", "RightDrawerGap", 3.0, "Right Drawer Split Gap (mm):"),
            ("right_col_w", "RightColumnWidth", 292.1, "Right Drawer Column Width (mm):"),
            ("top_drawer_h", "TopDrawerHeight", 158.75, "Top Drawer Height (mm):"),
            ("upper_right_h", "UpperRightDrawerHeight", 292.1, "Upper Right Drawer Height (mm):"),
            ("door_frame_w", "DoorFrameWidth", 50.8, "Door Shaker Frame Width (mm):"),
            ("door_panel_t", "DoorPanelThickness", 6.0, "Door Center Panel Thickness (mm):"),
            ("drawer_frame_w", "DrawerFrameWidth", 50.8, "Drawer Shaker Frame Width (mm):"),
            ("drawer_panel_t", "DrawerPanelThickness", 6.0, "Drawer Center Panel Thickness (mm):"),
            ("toe_h", "ToeKickHeight", 88.9, "Toe Kick Height (mm):"),
            ("toe_setback", "ToeKickSetback", 88.9, "Toe Kick Setback (mm):"),
            ("drawer_depth", "DrawerBoxDepth", 457.2, "Drawer Box Depth (mm):"),
            ("drawer_wall", "DrawerBoxWallThickness", 12.7, "Drawer Box Wall Thickness (mm):"),
            ("drawer_clearance", "DrawerSideClearance", 6.0, "Drawer Side Clearance (mm):"),
            ("drawer_vertical_clearance", "DrawerVerticalClearance", 3.0, "Drawer Vertical Clearance (mm):"),
        ]
        self._field_specs = fields
        for attr, key, fallback, label in fields:
            widget = QtWidgets.QLineEdit(str(qty_mm(p.get(key), fallback)))
            setattr(self, attr, widget)
            layout.addRow(label, widget)
        door_style = str(p.get("DoorStyle", "Shaker")).strip()
        if door_style not in FRONT_STYLES:
            door_style = "Shaker"
        drawer_style = str(p.get("DrawerStyle", "Shaker")).strip()
        if drawer_style not in FRONT_STYLES:
            drawer_style = "Shaker"
        self.door_style = QtWidgets.QComboBox()
        self.door_style.addItems(list(FRONT_STYLES))
        self.door_style.setCurrentText(door_style)
        self.drawer_style = QtWidgets.QComboBox()
        self.drawer_style.addItems(list(FRONT_STYLES))
        self.drawer_style.setCurrentText(drawer_style)
        front_mount = str(p.get("FrontMount", "Overlay")).strip()
        if front_mount not in FRONT_MOUNTS:
            front_mount = "Overlay"
        self.front_mount = QtWidgets.QComboBox()
        self.front_mount.addItems(list(FRONT_MOUNTS))
        self.front_mount.setCurrentText(front_mount)
        layout.addRow("Door Style:", self.door_style)
        layout.addRow("Drawer Front Style:", self.drawer_style)
        layout.addRow("Front Mount (Door + Drawers):", self.front_mount)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    def values(self):
        result = {}
        for attr, key, fallback, _label in self._field_specs:
            result[key] = qty_mm(getattr(self, attr).text(), fallback)
        result["DoorStyle"] = str(self.door_style.currentText())
        result["DrawerStyle"] = str(self.drawer_style.currentText())
        result["FrontMount"] = str(self.front_mount.currentText())
        return result

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

class _StyledFrontBase:
    STYLE_SLAB = "Slab"
    STYLE_SHAKER = "Shaker"
    component_label = "Front"
    frame_parameter_name = "FrameWidth"
    panel_parameter_name = "PanelThickness"
    def __init__(self, body, feature, style=STYLE_SLAB):
        self.body = body
        self.feature = feature
        self.style = style
        if self.style not in (self.STYLE_SLAB, self.STYLE_SHAKER):
            raise ValueError("Unsupported {} style: {}".format(self.component_label, self.style))
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
        panel = Part.makeBox(
            opening_width,
            panel_thickness,
            opening_height,
            App.Vector(frame_width, panel_y, frame_width),
        )
        shape = frame.fuse(panel)
        try:
            shape = shape.removeSplitter()
        except Exception:
            pass
        return shape
    def update(self, width, height, thickness, frame_width, panel_thickness, x=0.0, z=0.0, back_y=0.0):
        if width <= 0 or height <= 0 or thickness <= 0:
            raise RuntimeError("{} dimensions must be greater than zero.".format(self.component_label))
        if self.style == self.STYLE_SHAKER:
            if frame_width <= 0:
                raise RuntimeError("{} must be greater than zero.".format(self.frame_parameter_name))
            if width - 2.0 * frame_width <= 0:
                raise RuntimeError("{} leaves no center opening width.".format(self.frame_parameter_name))
            if height - 2.0 * frame_width <= 0:
                raise RuntimeError("{} leaves no center opening height.".format(self.frame_parameter_name))
            if panel_thickness <= 0 or panel_thickness > thickness:
                raise RuntimeError("{} must be > 0 and <= FrontThickness.".format(self.panel_parameter_name))
        self.body.Placement = App.Placement(App.Vector(x, back_y, z), App.Rotation())
        self.feature.Placement = App.Placement()
        if self.style == self.STYLE_SLAB:
            self.feature.Shape = self._slab_shape(width, height, thickness)
        else:
            self.feature.Shape = self._shaker_shape(width, height, thickness, frame_width, panel_thickness)

class CabinetDoor(_StyledFrontBase):
    component_label = "CabinetDoor"
    frame_parameter_name = "DoorFrameWidth"
    panel_parameter_name = "DoorPanelThickness"
    @classmethod
    def create(cls, doc, prefix, component_name="LeftDoorFront", label="Left Door Front", style="Slab"):
        body = doc.addObject("PartDesign::Body", "{}_{}".format(prefix, component_name))
        body.Label = label
        feature = body.newObject("PartDesign::Feature", "{}_{}Shape".format(prefix, component_name))
        feature.Label = "{} Shape".format(label)
        return cls(body, feature, style)
    @classmethod
    def from_existing(cls, body, feature, style="Slab"):
        return cls(body, feature, style)

class CabinetDrawerFront(_StyledFrontBase):
    component_label = "CabinetDrawerFront"
    frame_parameter_name = "DrawerFrameWidth"
    panel_parameter_name = "DrawerPanelThickness"
    @classmethod
    def create(cls, doc, prefix, component_name, label, style="Slab"):
        body = doc.addObject("PartDesign::Body", "{}_{}".format(prefix, component_name))
        body.Label = label
        feature = body.newObject("PartDesign::Feature", "{}_{}Shape".format(prefix, component_name))
        feature.Label = "{} Shape".format(label)
        return cls(body, feature, style)
    @classmethod
    def from_existing(cls, body, feature, style="Slab"):
        return cls(body, feature, style)

class CabinetDrawerBox:
    """Reusable open-top drawer box."""
    def __init__(self, feature):
        self.feature = feature
    @classmethod
    def create(cls, doc, prefix, component_name, label):
        feature = doc.addObject("Part::Feature", "{}_{}".format(prefix, component_name))
        feature.Label = label
        return cls(feature)
    @classmethod
    def from_existing(cls, feature):
        return cls(feature)
    @staticmethod
    def _shape(width, depth, height, wall):
        if width <= 2.0 * wall or depth <= 2.0 * wall or height <= wall:
            raise RuntimeError("Drawer box wall thickness leaves no usable cavity.")
        outer = Part.makeBox(width, depth, height)
        inner = Part.makeBox(
            width - 2.0 * wall,
            depth - 2.0 * wall,
            height - wall,
            App.Vector(wall, wall, wall),
        )
        return outer.cut(inner)
    def update(self, width, depth, height, wall, x, y, z):
        self.feature.Shape = self._shape(width, depth, height, wall)
        self.feature.Placement = App.Placement(App.Vector(x, y, z), App.Rotation())

class MixedFrontLayout:
    """Sole authority for mixed-front dimensions and front positions."""
    MOUNT_OVERLAY = "Overlay"
    MOUNT_INSET = "Inset"
    @classmethod
    def calculate(cls, p):
        W = p["width"]
        H = p["height"]
        wall = p["wall"]
        reveal = p["side_reveal"]
        column_gap = p["column_gap"]
        top_gap = p["top_lower_gap"]
        right_gap = p["right_drawer_gap"]
        right_w = p["right_column_width"]
        top_h = p["top_drawer_height"]
        upper_right_h = p["upper_right_height"]
        toe_h = p["toe_height"]
        front_t = p["front_t"]
        front_offset = p["front_offset"]
        inset_setback = p["inset_setback"]
        mount = p["front_mount"]
        if mount not in FRONT_MOUNTS:
            raise RuntimeError("FrontMount must be Overlay or Inset.")
        if inset_setback < 0:
            raise RuntimeError("InsetSetback cannot be negative.")
        if mount == cls.MOUNT_OVERLAY:
            front_x = reveal
            front_width = W - 2.0 * reveal
            front_bottom = toe_h
            front_top = H
            front_back_y = -front_offset
        else:
            front_x = wall
            front_width = W - 2.0 * wall
            front_bottom = toe_h + wall
            front_top = H - wall
            front_back_y = front_t + inset_setback
            if front_width <= 0 or front_top <= front_bottom:
                raise RuntimeError("BoxWallThickness leaves no usable inset front opening.")
        left_w = front_width - column_gap - right_w
        top_z = front_top - top_h
        lower_top = top_z - top_gap
        lower_h = lower_top - front_bottom
        lower_right_h = lower_h - upper_right_h - right_gap
        left_x = front_x
        right_x = left_x + left_w + column_gap
        lower_right_z = front_bottom
        upper_right_z = lower_right_z + lower_right_h + right_gap
        partition_center_x = left_x + left_w + column_gap / 2.0
        return {
            "front_width": front_width,
            "front_x": front_x,
            "front_bottom": front_bottom,
            "front_top": front_top,
            "left_door_width": left_w,
            "right_column_width": right_w,
            "top_drawer_x": front_x,
            "top_drawer_z": top_z,
            "top_drawer_height": top_h,
            "left_door_x": left_x,
            "left_door_z": front_bottom,
            "left_door_height": lower_h,
            "right_x": right_x,
            "upper_right_z": upper_right_z,
            "upper_right_height": upper_right_h,
            "lower_right_z": lower_right_z,
            "lower_right_height": lower_right_h,
            "lower_top": lower_top,
            "partition_center_x": partition_center_x,
            "front_back_y": front_back_y,
        }

class VanityBaseCabinetFP:
    def __init__(self, obj, assembly, sheet):
        self._building = True
        obj.Proxy = self
        obj.addProperty("App::PropertyLink", "Parameters", "Component")
        obj.addProperty("App::PropertyString", "AssemblyObjectName", "Component")
        obj.AssemblyObjectName = assembly.Name
        try:
            obj.setEditorMode("AssemblyObjectName", 1)
        except Exception:
            pass
        # DoorStyle, DrawerStyle and FrontMount are stored in the Parameters sheet.
        # The controller intentionally does not maintain a competing front authority.
        self._create_geometry(obj, assembly, sheet)
        obj.Parameters = sheet
        self._building = False
        obj.touch()
    def _create_geometry(self, obj, assembly, sheet):
        doc = obj.Document
        prefix = assembly.Name
        origin_point = Draft.make_point(
            X=0.0, Y=0.0, Z=0.0,
            name="{}_OriginPoint".format(prefix),
            point_size=8,
        )
        origin_point.Label = "Assembly Origin Point"
        cabinet = CabinetBody.create(doc, prefix, label="Cabinet Carcass")
        toe = doc.addObject("Part::Box", "{}_ToeKick".format(prefix))
        toe.Label = "Toe Kick"
        top_divider = doc.addObject("Part::Box", "{}_TopDrawerDivider".format(prefix))
        top_divider.Label = "Top Drawer Divider"
        vertical_divider = doc.addObject("Part::Box", "{}_LowerVerticalDivider".format(prefix))
        vertical_divider.Label = "Lower Vertical Divider"
        door = CabinetDoor.create(
            doc, prefix, "LeftDoorFront", "Left Door Front",
            style="Shaker",
        )
        drawer_fronts = [
            CabinetDrawerFront.create(doc, prefix, "TopDrawerFront", "Top Drawer Front", style="Shaker"),
            CabinetDrawerFront.create(doc, prefix, "UpperRightDrawerFront", "Upper Right Drawer Front", style="Shaker"),
            CabinetDrawerFront.create(doc, prefix, "LowerRightDrawerFront", "Lower Right Drawer Front", style="Shaker"),
        ]
        drawer_boxes = [
            CabinetDrawerBox.create(doc, prefix, "TopDrawerBox", "Top Drawer Box"),
            CabinetDrawerBox.create(doc, prefix, "UpperRightDrawerBox", "Upper Right Drawer Box"),
            CabinetDrawerBox.create(doc, prefix, "LowerRightDrawerBox", "Lower Right Drawer Box"),
        ]
        p = self._read(sheet)
        self._validate(p)
        L = MixedFrontLayout.calculate(p)
        self._validate_layout(p, L)
        self._update_cabinet(cabinet.body, cabinet.outer, cabinet.inner, p)
        self._update_toe(toe, p)
        self._update_dividers(top_divider, vertical_divider, p, L)
        self._update_fronts(
            door.body, door.feature,
            [(front.body, front.feature) for front in drawer_fronts],
            p, L,
        )
        self._update_drawer_boxes([box.feature for box in drawer_boxes], p, L)
        assembly.addObject(sheet)
        assembly.addObject(origin_point)
        assembly.addObject(cabinet.body)
        assembly.addObject(toe)
        assembly.addObject(top_divider)
        assembly.addObject(vertical_divider)
        assembly.addObject(door.body)
        for front in drawer_fronts:
            assembly.addObject(front.body)
        for box in drawer_boxes:
            assembly.addObject(box.feature)
        assembly.addObject(obj)
        required = [
            sheet, origin_point, cabinet.body, toe, top_divider, vertical_divider,
            door.body, obj,
        ] + [front.body for front in drawer_fronts] + [box.feature for box in drawer_boxes]
        missing = [member.Name for member in required if member not in assembly.Group]
        if missing:
            raise RuntimeError(
                "FreeCAD did not place all mixed-front cabinet members inside '{}'. Missing: {}"
                .format(assembly.Name, ", ".join(missing))
            )
        try:
            origin_point.ViewObject.Visibility = True
            toe.ViewObject.ShapeColor = (0.25, 0.25, 0.25)
            top_divider.ViewObject.ShapeColor = (0.72, 0.72, 0.72)
            vertical_divider.ViewObject.ShapeColor = (0.72, 0.72, 0.72)
            for box in drawer_boxes:
                box.feature.ViewObject.ShapeColor = (0.72, 0.55, 0.35)
        except Exception:
            pass
    def onDocumentRestored(self, obj):
        obj.Proxy = self
        self._building = False
    def _assembly(self, obj):
        name = ""
        try:
            name = str(obj.AssemblyObjectName).strip()
        except Exception:
            pass
        if name:
            assembly = obj.Document.getObject(name)
            if assembly is not None and assembly.TypeId == "App::Part":
                return assembly
        for parent in obj.InList:
            if parent.TypeId == "App::Part":
                return parent
        raise RuntimeError("Cabinet controller cannot resolve its owning App::Part.")
    def _child(self, assembly, label, type_id=None):
        for child in assembly.Group:
            if child.Label == label and (type_id is None or child.TypeId == type_id):
                return child
        return None
    def _parameters(self, obj, assembly):
        sheet = obj.Parameters
        if sheet is not None and sheet.Document == obj.Document:
            return sheet
        sheet = self._child(assembly, "Parameters", "Spreadsheet::Sheet")
        if sheet is None:
            raise RuntimeError("Parameters spreadsheet not found.")
        return sheet
    def _geometry(self, assembly):
        d = assembly.Document
        pfx = assembly.Name
        names = {
            "body": "{}_CabinetBody".format(pfx),
            "outer": "{}_CabinetOuter".format(pfx),
            "inner": "{}_CabinetInnerCut".format(pfx),
            "toe": "{}_ToeKick".format(pfx),
            "top_divider": "{}_TopDrawerDivider".format(pfx),
            "vertical_divider": "{}_LowerVerticalDivider".format(pfx),
            "door_body": "{}_LeftDoorFront".format(pfx),
            "door_shape": "{}_LeftDoorFrontShape".format(pfx),
            "top_front_body": "{}_TopDrawerFront".format(pfx),
            "top_front_shape": "{}_TopDrawerFrontShape".format(pfx),
            "upper_front_body": "{}_UpperRightDrawerFront".format(pfx),
            "upper_front_shape": "{}_UpperRightDrawerFrontShape".format(pfx),
            "lower_front_body": "{}_LowerRightDrawerFront".format(pfx),
            "lower_front_shape": "{}_LowerRightDrawerFrontShape".format(pfx),
            "top_box": "{}_TopDrawerBox".format(pfx),
            "upper_box": "{}_UpperRightDrawerBox".format(pfx),
            "lower_box": "{}_LowerRightDrawerBox".format(pfx),
        }
        resolved = {key: d.getObject(name) for key, name in names.items()}
        missing = [names[key] for key, value in resolved.items() if value is None]
        if missing:
            raise RuntimeError("Cabinet geometry is incomplete. Missing: {}".format(", ".join(missing)))
        return resolved
    def _read(self, sheet):
        p = SheetParams(sheet)
        values = {
            "width": qty_mm(p.get("CabinetWidth"), 762.0),
            "depth": qty_mm(p.get("CabinetDepth"), 533.4),
            "height": qty_mm(p.get("CabinetHeight"), 876.3),
            "wall": qty_mm(p.get("BoxWallThickness"), 19.05),
            "front_t": qty_mm(p.get("FrontThickness"), 19.05),
            "front_offset": qty_mm(p.get("FrontOffset"), 3.0),
            "inset_setback": qty_mm(p.get("InsetSetback"), 0.0),
            "side_reveal": qty_mm(p.get("FrontSideReveal"), 11.2),
            "column_gap": qty_mm(p.get("ColumnGap"), 3.0),
            "top_lower_gap": qty_mm(p.get("TopLowerGap"), 3.0),
            "right_drawer_gap": qty_mm(p.get("RightDrawerGap"), 3.0),
            "right_column_width": qty_mm(p.get("RightColumnWidth"), 292.1),
            "top_drawer_height": qty_mm(p.get("TopDrawerHeight"), 158.75),
            "upper_right_height": qty_mm(p.get("UpperRightDrawerHeight"), 292.1),
            "door_frame_width": qty_mm(p.get("DoorFrameWidth"), 50.8),
            "door_panel_thickness": qty_mm(p.get("DoorPanelThickness"), 6.0),
            "drawer_frame_width": qty_mm(p.get("DrawerFrameWidth"), 50.8),
            "drawer_panel_thickness": qty_mm(p.get("DrawerPanelThickness"), 6.0),
            "toe_height": qty_mm(p.get("ToeKickHeight"), 88.9),
            "toe_setback": qty_mm(p.get("ToeKickSetback"), 88.9),
            "drawer_depth": qty_mm(p.get("DrawerBoxDepth"), 457.2),
            "drawer_wall": qty_mm(p.get("DrawerBoxWallThickness"), 12.7),
            "side_clearance": qty_mm(p.get("DrawerSideClearance"), 6.0),
            "vertical_clearance": qty_mm(p.get("DrawerVerticalClearance"), 3.0),
            "door_style": str(p.get("DoorStyle", "Shaker")).strip(),
            "drawer_style": str(p.get("DrawerStyle", "Shaker")).strip(),
            "front_mount": str(p.get("FrontMount", "Overlay")).strip(),
        }
        if values["door_style"] not in FRONT_STYLES:
            values["door_style"] = "Shaker"
        if values["drawer_style"] not in FRONT_STYLES:
            values["drawer_style"] = "Shaker"
        if values["front_mount"] not in FRONT_MOUNTS:
            values["front_mount"] = "Overlay"
        return values
    def _validate(self, p):
        if p["width"] <= 0 or p["depth"] <= 0 or p["height"] <= 0:
            raise RuntimeError("Cabinet Width, Depth and Height must be greater than zero.")
        if p["wall"] <= 0 or p["front_t"] <= 0:
            raise RuntimeError("Wall and front thickness must be greater than zero.")
        for name in ("front_offset", "inset_setback", "side_reveal", "column_gap", "top_lower_gap", "right_drawer_gap", "side_clearance", "vertical_clearance"):
            if p[name] < 0:
                raise RuntimeError("{} cannot be negative.".format(name))
        if p["front_mount"] not in FRONT_MOUNTS:
            raise RuntimeError("FrontMount must be Overlay or Inset.")
        if p["front_mount"] == "Inset" and p["front_t"] + p["inset_setback"] > p["depth"]:
            raise RuntimeError("FrontThickness + InsetSetback cannot exceed CabinetDepth.")
        if p["right_column_width"] <= 0:
            raise RuntimeError("RightColumnWidth must be greater than zero.")
        if p["top_drawer_height"] <= 0 or p["upper_right_height"] <= 0:
            raise RuntimeError("Drawer-front heights must be greater than zero.")
        if not 0 < p["toe_height"] < p["height"]:
            raise RuntimeError("ToeKickHeight must be greater than zero and less than CabinetHeight.")
        if not 0 <= p["toe_setback"] < p["depth"]:
            raise RuntimeError("ToeKickSetback must be >= 0 and less than CabinetDepth.")
        if p["drawer_depth"] <= 0 or p["drawer_wall"] <= 0:
            raise RuntimeError("Drawer-box dimensions must be greater than zero.")
        front_clearance_y = (
            p["front_t"] + p["inset_setback"]
            if p["front_mount"] == "Inset"
            else 0.0
        )
        usable_depth = p["depth"] - p["wall"] - front_clearance_y
        if usable_depth <= 0:
            raise RuntimeError("Front mounting leaves no usable cabinet interior depth.")
        if p["drawer_depth"] > usable_depth:
            raise RuntimeError(
                "DrawerBoxDepth exceeds the usable interior depth after front-mount clearance."
            )
        CabinetBody.validate_dimensions(
            p["width"], p["depth"], p["height"] - p["toe_height"], p["wall"]
        )
    def _validate_layout(self, p, L):
        if L["front_width"] <= 0:
            raise RuntimeError("FrontSideReveal leaves no usable front width.")
        if L["left_door_width"] <= 0:
            raise RuntimeError(
                "RightColumnWidth, ColumnGap and FrontSideReveal leave no usable Left Door width."
            )
        if L["left_door_height"] <= 0:
            raise RuntimeError("TopDrawerHeight and TopLowerGap leave no usable lower front height.")
        if L["lower_right_height"] <= 0:
            raise RuntimeError(
                "UpperRightDrawerHeight and RightDrawerGap leave no usable Lower Right Drawer height."
            )
        if p["door_style"] == "Shaker":
            if p["door_frame_width"] <= 0:
                raise RuntimeError("DoorFrameWidth must be greater than zero.")
            if L["left_door_width"] <= 2.0 * p["door_frame_width"] or L["left_door_height"] <= 2.0 * p["door_frame_width"]:
                raise RuntimeError("DoorFrameWidth is too large for the calculated Left Door.")
            if p["door_panel_thickness"] <= 0 or p["door_panel_thickness"] > p["front_t"]:
                raise RuntimeError("DoorPanelThickness must be > 0 and <= FrontThickness.")
        if p["drawer_style"] == "Shaker":
            if p["drawer_frame_width"] <= 0:
                raise RuntimeError("DrawerFrameWidth must be greater than zero.")
            drawer_sizes = [
                ("Top Drawer", L["front_width"], L["top_drawer_height"]),
                ("Upper Right Drawer", L["right_column_width"], L["upper_right_height"]),
                ("Lower Right Drawer", L["right_column_width"], L["lower_right_height"]),
            ]
            for label, width, height in drawer_sizes:
                if width <= 2.0 * p["drawer_frame_width"] or height <= 2.0 * p["drawer_frame_width"]:
                    raise RuntimeError("DrawerFrameWidth is too large for {}.".format(label))
            if p["drawer_panel_thickness"] <= 0 or p["drawer_panel_thickness"] > p["front_t"]:
                raise RuntimeError("DrawerPanelThickness must be > 0 and <= FrontThickness.")
        self._drawer_box_layout(p, L)
    def _drawer_box_layout(self, p, L):
        wall = p["wall"]
        side = p["side_clearance"]
        vertical = p["vertical_clearance"]
        partition_right = L["partition_center_x"] + wall / 2.0
        interior_right = p["width"] - wall
        top_box_x = wall + side
        top_box_w = p["width"] - 2.0 * wall - 2.0 * side
        right_box_x = partition_right + side
        right_box_w = interior_right - side - right_box_x
        top_box_z = L["top_drawer_z"] + vertical
        top_box_top = p["height"] - wall - vertical
        top_box_h = top_box_top - top_box_z
        lower_interior_floor = p["toe_height"] + wall
        lower_box_z = max(L["lower_right_z"] + vertical, lower_interior_floor + vertical)
        lower_box_top = L["lower_right_z"] + L["lower_right_height"] - vertical
        lower_box_h = lower_box_top - lower_box_z
        upper_box_z = L["upper_right_z"] + vertical
        upper_box_top = min(
            L["upper_right_z"] + L["upper_right_height"] - vertical,
            L["lower_top"] - vertical,
        )
        upper_box_h = upper_box_top - upper_box_z
        for label, width, height in [
            ("Top Drawer Box", top_box_w, top_box_h),
            ("Upper Right Drawer Box", right_box_w, upper_box_h),
            ("Lower Right Drawer Box", right_box_w, lower_box_h),
        ]:
            if width <= 2.0 * p["drawer_wall"]:
                raise RuntimeError("{} has no usable width after clearances.".format(label))
            if height <= p["drawer_wall"]:
                raise RuntimeError("{} has no usable height after clearances.".format(label))
        box_y = (
            p["front_t"] + p["inset_setback"]
            if p["front_mount"] == "Inset"
            else 0.0
        )
        return {
            "top": (top_box_x, box_y, top_box_z, top_box_w, top_box_h),
            "upper": (right_box_x, box_y, upper_box_z, right_box_w, upper_box_h),
            "lower": (right_box_x, box_y, lower_box_z, right_box_w, lower_box_h),
        }
    def _update_cabinet(self, body, outer, inner, p):
        CabinetBody.from_existing(body, outer, inner).update(
            width=p["width"],
            depth=p["depth"],
            height=p["height"] - p["toe_height"],
            thickness=p["wall"],
            x=0.0, y=0.0, z=p["toe_height"],
        )
    def _update_toe(self, toe, p):
        toe.Length = p["width"]
        toe.Width = p["depth"] - p["toe_setback"]
        toe.Height = p["toe_height"]
        toe.Placement.Base = App.Vector(0.0, p["toe_setback"], 0.0)
    def _update_dividers(self, top_divider, vertical_divider, p, L):
        wall = p["wall"]
        divider_y = (
            p["front_t"] + p["inset_setback"]
            if p["front_mount"] == "Inset"
            else 0.0
        )
        divider_depth = p["depth"] - wall - divider_y
        if divider_depth <= 0:
            raise RuntimeError("Front mounting leaves no usable divider depth.")
        top_divider.Length = p["width"] - 2.0 * wall
        top_divider.Width = divider_depth
        top_divider.Height = wall
        top_divider.Placement.Base = App.Vector(
            wall, divider_y, L["top_drawer_z"] - wall
        )
        partition_z = p["toe_height"] + wall
        partition_h = L["lower_top"] - partition_z
        if partition_h <= 0:
            raise RuntimeError("Computed lower vertical-divider height is invalid.")
        vertical_divider.Length = wall
        vertical_divider.Width = divider_depth
        vertical_divider.Height = partition_h
        vertical_divider.Placement.Base = App.Vector(
            L["partition_center_x"] - wall / 2.0,
            divider_y,
            partition_z,
        )
    def _update_fronts(self, door_body, door_feature, drawer_objects, p, L):
        back_y = L["front_back_y"]
        door = CabinetDoor.from_existing(door_body, door_feature, p["door_style"])
        door.update(
            width=L["left_door_width"],
            height=L["left_door_height"],
            thickness=p["front_t"],
            frame_width=p["door_frame_width"],
            panel_thickness=p["door_panel_thickness"],
            x=L["left_door_x"],
            z=L["left_door_z"],
            back_y=back_y,
        )
        drawer_specs = [
            (L["front_width"], L["top_drawer_height"], L["top_drawer_x"], L["top_drawer_z"]),
            (L["right_column_width"], L["upper_right_height"], L["right_x"], L["upper_right_z"]),
            (L["right_column_width"], L["lower_right_height"], L["right_x"], L["lower_right_z"]),
        ]
        for (body, feature), (width, height, x, z) in zip(drawer_objects, drawer_specs):
            front = CabinetDrawerFront.from_existing(body, feature, p["drawer_style"])
            front.update(
                width=width,
                height=height,
                thickness=p["front_t"],
                frame_width=p["drawer_frame_width"],
                panel_thickness=p["drawer_panel_thickness"],
                x=x,
                z=z,
                back_y=back_y,
            )
    def _update_drawer_boxes(self, drawer_features, p, L):
        boxes = self._drawer_box_layout(p, L)
        specs = [boxes["top"], boxes["upper"], boxes["lower"]]
        for feature, (x, y, z, width, height) in zip(drawer_features, specs):
            CabinetDrawerBox.from_existing(feature).update(
                width=width,
                depth=p["drawer_depth"],
                height=height,
                wall=p["drawer_wall"],
                x=x, y=y, z=z,
            )
    def execute(self, obj):
        if getattr(self, "_building", False):
            return
        assembly = self._assembly(obj)
        sheet = self._parameters(obj, assembly)
        p = self._read(sheet)
        self._validate(p)
        L = MixedFrontLayout.calculate(p)
        self._validate_layout(p, L)
        g = self._geometry(assembly)
        self._update_cabinet(g["body"], g["outer"], g["inner"], p)
        self._update_toe(g["toe"], p)
        self._update_dividers(g["top_divider"], g["vertical_divider"], p, L)
        self._update_fronts(
            g["door_body"], g["door_shape"],
            [
                (g["top_front_body"], g["top_front_shape"]),
                (g["upper_front_body"], g["upper_front_shape"]),
                (g["lower_front_body"], g["lower_front_shape"]),
            ],
            p, L,
        )
        self._update_drawer_boxes(
            [g["top_box"], g["upper_box"], g["lower_box"]],
            p, L,
        )

def validate_values(values):
    p = {
        "width": values["CabinetWidth"],
        "depth": values["CabinetDepth"],
        "height": values["CabinetHeight"],
        "wall": values["BoxWallThickness"],
        "front_t": values["FrontThickness"],
        "front_offset": values["FrontOffset"],
        "inset_setback": values["InsetSetback"],
        "side_reveal": values["FrontSideReveal"],
        "column_gap": values["ColumnGap"],
        "top_lower_gap": values["TopLowerGap"],
        "right_drawer_gap": values["RightDrawerGap"],
        "right_column_width": values["RightColumnWidth"],
        "top_drawer_height": values["TopDrawerHeight"],
        "upper_right_height": values["UpperRightDrawerHeight"],
        "door_frame_width": values["DoorFrameWidth"],
        "door_panel_thickness": values["DoorPanelThickness"],
        "drawer_frame_width": values["DrawerFrameWidth"],
        "drawer_panel_thickness": values["DrawerPanelThickness"],
        "toe_height": values["ToeKickHeight"],
        "toe_setback": values["ToeKickSetback"],
        "drawer_depth": values["DrawerBoxDepth"],
        "drawer_wall": values["DrawerBoxWallThickness"],
        "side_clearance": values["DrawerSideClearance"],
        "vertical_clearance": values["DrawerVerticalClearance"],
        "door_style": values["DoorStyle"],
        "drawer_style": values["DrawerStyle"],
        "front_mount": values["FrontMount"],
    }
    try:
        helper = object.__new__(VanityBaseCabinetFP)
        helper._validate(p)
        helper._validate_layout(p, MixedFrontLayout.calculate(p))
        return True, ""
    except Exception as exc:
        return False, str(exc)

def _sanitize_object_name(name):
    cleaned = "".join(
        c if (c.isalnum() or c == "_") else "_"
        for c in str(name).strip()
    )
    if not cleaned:
        cleaned = INSTANCE_BASENAME
    if cleaned[0].isdigit():
        cleaned = "{}_{}".format(INSTANCE_BASENAME, cleaned)
    return cleaned

def next_vanity_base_cabinet_name(document):
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
                coin.SoLocation2Event.getClassTypeId(), self._mouse_move
            )
            self.callback_click = self.view.addEventCallbackPivy(
                coin.SoMouseButtonEvent.getClassTypeId(), self._mouse_click
            )
            self.callback_key = self.view.addEventCallbackPivy(
                coin.SoKeyboardEvent.getClassTypeId(), self._key_press
            )
        self._status(
            "Select cabinet insertion point: hover over an existing endpoint until the snap marker appears, then left-click. Press Esc or right-click to cancel."
        )
        try:
            Gui.updateGui()
        except Exception:
            pass
    def _ensure_snapper(self):
        if hasattr(Gui, "Snapper"):
            return Gui.Snapper
        try:
            import Draft  # noqa: F401
        except Exception:
            pass
        if hasattr(Gui, "Snapper"):
            return Gui.Snapper
        from draftguitools.gui_snapper import Snapper
        Gui.Snapper = Snapper()
        return Gui.Snapper
    def _mouse_move(self, cb):
        if self._finished:
            return
        try:
            event = cb.getEvent()
            self.snapper.snap(
                event.getPosition(),
                lastpoint=None,
                active=True,
                constrain=False,
                noTracker=False,
            )
            endpoint = str(getattr(self.snapper, "cursorMode", "") or "").lower() == "endpoint"
            if endpoint != self._last_endpoint_state:
                self._last_endpoint_state = endpoint
                if endpoint:
                    self._status("Endpoint found — left-click to place the cabinet.")
                elif self._failed_endpoint_picks == 0:
                    self._status("Select an existing endpoint/vertex.")
                else:
                    self._status("Second pick: select an endpoint. If no endpoint exists, click again to place at 0,0,0.")
        except Exception:
            pass
    def _mouse_click(self, cb):
        if self._finished:
            return
        try:
            event = cb.getEvent()
            if event.getState() != coin.SoButtonEvent.DOWN:
                return
            button = event.getButton()
            if button == coin.SoMouseButtonEvent.BUTTON2:
                cb.setHandled()
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
            mode = str(getattr(self.snapper, "cursorMode", "") or "").lower()
            if point is None or mode != "endpoint":
                cb.setHandled()
                if self._failed_endpoint_picks == 0:
                    self._failed_endpoint_picks = 1
                    self._status("Second pick: select an endpoint. If no endpoint exists, click again to place at 0,0,0.")
                    QtWidgets.QMessageBox.information(
                        None,
                        "Endpoint Required",
                        "An endpoint is required, please select an endpoint, if none exists on second pick cabinet will be drawn at 0,0,0.",
                    )
                    return
                self._finished = True
                accepted = App.Vector(0.0, 0.0, 0.0)
                App.Console.PrintMessage(
                    "No endpoint selected on second pick; placing Vanity Base Cabinet at 0,0,0.\n"
                )
                self._cleanup()
                self.on_accept(accepted)
                return
            cb.setHandled()
            self._finished = True
            accepted = App.Vector(point)
            self._cleanup()
            self.on_accept(accepted)
        except Exception as exc:
            App.Console.PrintError("Endpoint click handling failed: {}\n".format(exc))
            self.cancel()
    def _key_press(self, cb):
        if self._finished:
            return
        try:
            event = cb.getEvent()
            if (
                event.getState() == coin.SoButtonEvent.DOWN
                and event.getKey() == coin.SoKeyboardEvent.ESCAPE
            ):
                cb.setHandled()
                self.cancel()
        except Exception:
            pass
    def cancel(self):
        if self._finished:
            return
        self._finished = True
        self._cleanup()
        self.on_cancel()
    def _cleanup(self):
        removed = False
        if self.view is not None:
            for typeid, token in [
                (coin.SoLocation2Event.getClassTypeId(), self.callback_move),
                (coin.SoMouseButtonEvent.getClassTypeId(), self.callback_click),
                (coin.SoKeyboardEvent.getClassTypeId(), self.callback_key),
            ]:
                if token is not None:
                    try:
                        self.view.removeEventCallbackPivy(typeid, token)
                        removed = True
                    except Exception:
                        pass
        self.callback_move = self.callback_click = self.callback_key = None
        if removed:
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
        try:
            Gui.getMainWindow().statusBar().clearMessage()
        except Exception:
            pass
        try:
            Gui.updateGui()
        except Exception:
            pass
    @staticmethod
    def _status(message):
        try:
            Gui.getMainWindow().statusBar().showMessage(message)
        except Exception:
            pass

class VanityBaseCabinetBuilder:
    def __init__(self, document, instance_name):
        if document is None:
            raise ValueError("create_vanity_base_cabinet() requires an existing FreeCAD document.")
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
                self.document, "{}_Parameters".format(self.instance_name)
            )
            if not self._collect_parameters():
                self._rollback()
                return None
            self._picker = EndpointSnapPointPicker(self._accepted, self._cancelled)
            self._picker.begin()
            return self
        except Exception:
            self._rollback()
            raise
    def _collect_parameters(self):
        dialog = VanityBaseCabinetDialog(self.parameters)
        if not dialog.exec():
            print("Cabinet creation cancelled. The active layout document was not changed.")
            return False
        self.values = dialog.values()
        valid, message = validate_values(self.values)
        if not valid:
            QtWidgets.QMessageBox.critical(None, "Invalid Cabinet Parameters", message)
            return False
        ParameterTable.update(self.document, self.parameters, self.values)
        ParameterTable.verify(self.parameters)
        return True
    def _accepted(self, point):
        self.insertion_point = App.Vector(point)
        self._picker = None
        try:
            self.assembly = self.document.addObject("App::Part", self.instance_name)
            self.assembly.Label = "30-Inch Vanity / Mixed-Front Base Cabinet"
            self.assembly.Placement.Base = App.Vector(self.insertion_point)
            self.controller = self.document.addObject(
                "Part::FeaturePython", "{}_Controller".format(self.instance_name)
            )
            self.controller.Label = "Vanity Base Cabinet Controller"
            VanityBaseCabinetFP(
                self.controller,
                self.assembly,
                self.parameters,
            )
            self.document.recompute()
            self._show()
            self._print_report()
        except Exception as exc:
            self._rollback()
            QtWidgets.QMessageBox.critical(
                None, "Vanity Base Cabinet Creation Error", str(exc)
            )
            App.Console.PrintError(
                "Vanity base cabinet creation failed: {}\n".format(exc)
            )
    def _cancelled(self):
        self._picker = None
        self._rollback()
        print("Cabinet insertion cancelled. The active layout document was not changed.")
    def _rollback(self):
        for name in reversed([
            obj.Name
            for obj in self.document.Objects
            if obj.Name not in self._original_object_names
        ]):
            try:
                self.document.removeObject(name)
            except Exception:
                pass
        try:
            self.document.recompute()
        except Exception:
            pass
    def _show(self):
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
        print("=" * 72)
        print("PARAMETRIC 30-INCH VANITY / MIXED-FRONT BASE CABINET")
        print("FREECAD 1.1.3 - VER0.13 STYLE + MOUNT PARAMETERS")
        print("Target document: {}".format(self.document.Name))
        print("Instance name:   {}".format(self.instance_name))
        print("=" * 72)
    def _print_report(self):
        p = {
            "width": qty_mm(SheetParams(self.parameters).get("CabinetWidth"), 762.0),
            "height": qty_mm(SheetParams(self.parameters).get("CabinetHeight"), 876.3),
            "side_reveal": qty_mm(SheetParams(self.parameters).get("FrontSideReveal"), 11.2),
            "column_gap": qty_mm(SheetParams(self.parameters).get("ColumnGap"), 3.0),
            "top_lower_gap": qty_mm(SheetParams(self.parameters).get("TopLowerGap"), 3.0),
            "right_drawer_gap": qty_mm(SheetParams(self.parameters).get("RightDrawerGap"), 3.0),
            "right_column_width": qty_mm(SheetParams(self.parameters).get("RightColumnWidth"), 292.1),
            "top_drawer_height": qty_mm(SheetParams(self.parameters).get("TopDrawerHeight"), 158.75),
            "upper_right_height": qty_mm(SheetParams(self.parameters).get("UpperRightDrawerHeight"), 292.1),
            "toe_height": qty_mm(SheetParams(self.parameters).get("ToeKickHeight"), 88.9),
            "front_offset": qty_mm(SheetParams(self.parameters).get("FrontOffset"), 3.0),
            "inset_setback": qty_mm(SheetParams(self.parameters).get("InsetSetback"), 0.0),
            "front_t": qty_mm(SheetParams(self.parameters).get("FrontThickness"), 19.05),
            "wall": qty_mm(SheetParams(self.parameters).get("BoxWallThickness"), 19.05),
            "front_mount": str(SheetParams(self.parameters).get("FrontMount", "Overlay")).strip(),
        }
        L = MixedFrontLayout.calculate(p)
        print("")
        print("-" * 72)
        print("CABINET INSTANCE CREATED SUCCESSFULLY")
        print("-" * 72)
        print("Cabinet instance:        ", self.assembly.Name)
        print("Parameters sheet:        ", self.parameters.Name)
        report_params = SheetParams(self.parameters)
        print("Door style:              ", str(report_params.get("DoorStyle", "Shaker")).strip())
        print("Drawer style:            ", str(report_params.get("DrawerStyle", "Shaker")).strip())
        print("Front mount:             ", str(report_params.get("FrontMount", "Overlay")).strip())
        print("Inset setback Y:         ", qty_mm(report_params.get("InsetSetback"), 0.0), "mm")
        print("Calculated Left Door W:  ", L["left_door_width"], "mm")
        print("Calculated Lower Right H:", L["lower_right_height"], "mm")
        print("Insertion Point:          X={:.3f}, Y={:.3f}, Z={:.3f} mm".format(
            self.insertion_point.x,
            self.insertion_point.y,
            self.insertion_point.z,
        ))
        print("")
        print("Edit '{}' to resize only this cabinet.".format(self.parameters.Name))
        print("Move/rotate '{}' with its App::Part Placement.".format(self.assembly.Name))
        print("=" * 72)
        print("")

def create_vanity_base_cabinet(document, instance_name):
    return VanityBaseCabinetBuilder(document, instance_name).run()

def main():
    document = App.ActiveDocument
    if document is None:
        QtWidgets.QMessageBox.warning(
            None,
            "No Active FreeCAD Document",
            "Open or create the kitchen/layout document first, then run this macro again.",
        )
        return None
    return create_vanity_base_cabinet(
        document,
        next_vanity_base_cabinet_name(document),
    )

main()

# ============================================================
# PARAMETRIC REFRIGERATOR / FREEZER
# SIDE-BY-SIDE + OVER-UNDER
# ============================================================
# Target: FreeCAD 1.1.3
# REVISION: 0.04
#
# Based on the proven Side-by-Side Refrigerator / Freezer Rev0.02.
#
# 0.03 - Side-by-Side + Over-Under upgrade
#        - adds RefrigeratorLayout = OverUnder / SideBySide
#        - defaults to 42 in W x 24 in D x 84 in H
#        - OverUnder front stack:
#              3 in base grille
#             21 in full-width bottom freezer slab door
#             50 in two equal French refrigerator doors
#             10 in full-width top cowling slab door
#          Default bottom freezer zone = 24 in total
#        - SideBySide preserves the original width-fraction concept
#        - all front members are permanent objects and visibility is mode-driven
#        - case/grille are established first; front objects are created last
#        - Parameters sheet follows current cabinet standard:
#              A = Name
#              B = editable quantity, displayed in inches
#              C = nearest-1/16-in cabinet-shop display
#              D = categorical Options
#        - dimensional B cells accept explicit mm or in input
#        - default dialog accepts mm or in
#        - visible Draft origin point retained
#        - proven two-attempt endpoint insertion retained
#        - canonical shared FreeCADGui.Snapper initialized through DraftTools
#        - no persistent Draft snap preferences are changed
#
# 0.04 - Standalone execution fix
#        - restores direct execution when run as a Python file / macro
#        - adds guarded main() call at end of file
#        - importing from CabinetsWorkbench.py remains safe because the
#          guarded call only runs when __name__ == "__main__"
#        - no geometry, parameters, layout, snapping or spreadsheet logic changed
#
# Coordinate system:
# X = appliance width
# Y = appliance depth
# Z = appliance height
# front/reference plane = Y=0
# appliance extends +Y
# front slabs extend toward -Y
# ============================================================
import FreeCAD as App
import FreeCADGui as Gui
import Draft
import warnings
from PySide import QtWidgets
from pivy import coin
from draftutils import gui_utils

SHEET_NAME = "Parameters"
CONTROLLER_NAME = "RefrigeratorController"
INSTANCE_BASENAME = "SideBySideRefrigerator"
LAYOUT_MODES = ("OverUnder", "SideBySide")
TEXT_PARAMETERS = {"RefrigeratorLayout"}
DIMENSIONLESS_PARAMETERS = {"FridgeWidthFraction"}
DIMENSION_PARAMETERS = {
    "ApplianceWidth",
    "ApplianceDepth",
    "ApplianceHeight",
    "DoorGap",
    "DoorThickness",
    "BaseGrilleHeight",
    "BaseGrilleSetback",
    "FreezerDoorHeight",
    "CowlingHeight",
}
PARAMETER_OPTIONS = {
    "RefrigeratorLayout": "OverUnder | SideBySide",
}
PARAM_DEFAULTS = [
    ("ApplianceWidth",       "1066.8 mm"),   # 42 in
    ("ApplianceDepth",       "609.6 mm"),    # 24 in
    ("ApplianceHeight",      "2133.6 mm"),   # 84 in
    ("RefrigeratorLayout",   "OverUnder"),
    ("FridgeWidthFraction",  "0.6"),
    ("DoorGap",              "6 mm"),
    ("DoorThickness",        "25.4 mm"),     # 1 in
    ("BaseGrilleHeight",     "76.2 mm"),     # 3 in
    ("BaseGrilleSetback",    "40 mm"),
    ("FreezerDoorHeight",    "533.4 mm"),    # 21 in
    ("CowlingHeight",        "254 mm"),      # 10 in
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

def qty_float(value, fallback):
    try:
        if value is None:
            return float(fallback)
        text = str(value).strip()
        if not text:
            return float(fallback)
        return float(text)
    except Exception:
        return float(fallback)

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
            try:
                sheet.setDisplayUnit("B{}".format(row), "in")
            except Exception as exc:
                raise RuntimeError(
                    "Could not set Spreadsheet display unit for B{} to inches: {}"
                    .format(row, exc)
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
            metric_address = "B{}".format(row)
            value = params.get_cell(metric_address)
            if value is None or not str(value).strip():
                continue
            sheet.set("C{}".format(row), ParameterTable._fractional_inch_expression(metric_address))
    @staticmethod
    def update_options_column(sheet):
        sheet.set("D1", "Options")
        try:
            sheet.setColumnWidth("D", 240)
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
            elif name in DIMENSIONLESS_PARAMETERS:
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
            text = "" if value is None else str(value).strip()
            if not text or "#REF" in text.upper():
                failures.append(name)
        if failures:
            raise RuntimeError("Parameters did not resolve: {}".format(", ".join(failures)))

class RefrigeratorDialog(QtWidgets.QDialog):
    def __init__(self, sheet):
        super().__init__()
        p = SheetParams(sheet)
        self.setWindowTitle("Parametric Refrigerator / Freezer")
        layout = QtWidgets.QFormLayout(self)
        mode = str(p.get("RefrigeratorLayout", "OverUnder")).strip()
        if mode not in LAYOUT_MODES:
            mode = "OverUnder"
        self.layout_mode = QtWidgets.QComboBox()
        self.layout_mode.addItems(list(LAYOUT_MODES))
        self.layout_mode.setCurrentText(mode)
        self.width = self._dimension_field(p, "ApplianceWidth", 1066.8)
        self.depth = self._dimension_field(p, "ApplianceDepth", 609.6)
        self.height = self._dimension_field(p, "ApplianceHeight", 2133.6)
        self.fraction = QtWidgets.QLineEdit(str(qty_float(p.get("FridgeWidthFraction"), 0.6)))
        self.door_gap = self._dimension_field(p, "DoorGap", 6.0)
        self.door_thickness = self._dimension_field(p, "DoorThickness", 25.4)
        self.grille_height = self._dimension_field(p, "BaseGrilleHeight", 76.2)
        self.grille_setback = self._dimension_field(p, "BaseGrilleSetback", 40.0)
        self.freezer_door_height = self._dimension_field(p, "FreezerDoorHeight", 533.4)
        self.cowling_height = self._dimension_field(p, "CowlingHeight", 254.0)
        layout.addRow("Layout:", self.layout_mode)
        layout.addRow("Appliance Width (in or mm):", self.width)
        layout.addRow("Appliance Depth (in or mm):", self.depth)
        layout.addRow("Appliance Height (in or mm):", self.height)
        layout.addRow("Side-by-Side Fridge Width Fraction:", self.fraction)
        layout.addRow("Door Gap (in or mm):", self.door_gap)
        layout.addRow("Door Thickness (in or mm):", self.door_thickness)
        layout.addRow("Base Grille Height (in or mm):", self.grille_height)
        layout.addRow("Base Grille Setback (in or mm):", self.grille_setback)
        layout.addRow("Bottom Freezer Door Height (in or mm):", self.freezer_door_height)
        layout.addRow("Top Cowling Height (in or mm):", self.cowling_height)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    @staticmethod
    def _dimension_field(params, name, fallback_mm):
        return QtWidgets.QLineEdit(inch_text_from_mm(qty_mm(params.get(name), fallback_mm)))
    def values(self):
        return {
            "ApplianceWidth": qty_mm(self.width.text(), 1066.8),
            "ApplianceDepth": qty_mm(self.depth.text(), 609.6),
            "ApplianceHeight": qty_mm(self.height.text(), 2133.6),
            "RefrigeratorLayout": str(self.layout_mode.currentText()),
            "FridgeWidthFraction": qty_float(self.fraction.text(), 0.6),
            "DoorGap": qty_mm(self.door_gap.text(), 6.0),
            "DoorThickness": qty_mm(self.door_thickness.text(), 25.4),
            "BaseGrilleHeight": qty_mm(self.grille_height.text(), 76.2),
            "BaseGrilleSetback": qty_mm(self.grille_setback.text(), 40.0),
            "FreezerDoorHeight": qty_mm(self.freezer_door_height.text(), 533.4),
            "CowlingHeight": qty_mm(self.cowling_height.text(), 254.0),
        }

class SlabFront:
    def __init__(self, box):
        self.box = box
    @classmethod
    def create(cls, doc, prefix, key, label):
        box = doc.addObject("Part::Box", "{}_{}".format(prefix, key))
        box.Label = label
        return cls(box)
    @classmethod
    def from_existing(cls, box):
        if box is None:
            raise RuntimeError("Slab front object was not found.")
        return cls(box)
    def update(self, width, height, thickness, x=0.0, z=0.0, back_y=0.0):
        if width <= 0 or height <= 0 or thickness <= 0:
            raise RuntimeError("Slab-front width, height and thickness must be greater than zero.")
        self.box.Length = width
        self.box.Width = thickness
        self.box.Height = height
        self.box.Placement = App.Placement(
            App.Vector(x, back_y - thickness, z),
            App.Rotation()
        )
    def set_visible(self, visible):
        try:
            self.box.ViewObject.Visibility = bool(visible)
        except Exception:
            pass

class RefrigeratorLayout:
    MODE_OVER_UNDER = "OverUnder"
    MODE_SIDE_BY_SIDE = "SideBySide"
    @classmethod
    def calculate(cls, p):
        W = p["width"]
        D = p["depth"]
        H = p["height"]
        mode = p["layout_mode"]
        fraction = p["fraction"]
        gap = p["door_gap"]
        door_t = p["door_thickness"]
        grille_h = p["grille_height"]
        grille_setback = p["grille_setback"]
        freezer_h = p["freezer_door_height"]
        cowling_h = p["cowling_height"]
        if W <= 0 or D <= 0 or H <= 0:
            raise RuntimeError("Appliance Width, Depth and Height must all be greater than zero.")
        if mode not in LAYOUT_MODES:
            raise RuntimeError("RefrigeratorLayout must be OverUnder or SideBySide.")
        if not 0.05 <= fraction <= 0.95:
            raise RuntimeError("FridgeWidthFraction must be between 0.05 and 0.95.")
        if gap < 0:
            raise RuntimeError("DoorGap cannot be negative.")
        if door_t <= 0:
            raise RuntimeError("DoorThickness must be greater than zero.")
        if grille_h < 0 or grille_h >= H:
            raise RuntimeError("BaseGrilleHeight must be >= 0 and less than ApplianceHeight.")
        if grille_setback < 0 or grille_setback >= D:
            raise RuntimeError("BaseGrilleSetback must be >= 0 and less than ApplianceDepth.")
        if freezer_h <= 0:
            raise RuntimeError("FreezerDoorHeight must be greater than zero.")
        if cowling_h <= 0:
            raise RuntimeError("CowlingHeight must be greater than zero.")
        if W - gap <= 0:
            raise RuntimeError("DoorGap is too large for ApplianceWidth.")
        side_height = H - grille_h
        if side_height <= 0:
            raise RuntimeError("BaseGrilleHeight leaves no usable SideBySide door height.")
        usable_width = W - gap
        refrigerator_width = usable_width * fraction
        freezer_width = usable_width - refrigerator_width
        if refrigerator_width <= 0 or freezer_width <= 0:
            raise RuntimeError("FridgeWidthFraction leaves no usable SideBySide door width.")
        if refrigerator_width <= freezer_width:
            refrigerator_x = 0.0
            freezer_x = refrigerator_width + gap
        else:
            freezer_x = 0.0
            refrigerator_x = freezer_width + gap
        bottom_zone_height = grille_h + freezer_h
        over_fridge_height = H - bottom_zone_height - cowling_h
        if over_fridge_height <= 0:
            raise RuntimeError(
                "BaseGrilleHeight + FreezerDoorHeight + CowlingHeight leaves no usable French-door refrigerator height."
            )
        french_width = (W - gap) / 2.0
        if french_width <= 0:
            raise RuntimeError("DoorGap leaves no usable French-door width.")
        return {
            "mode": mode,
            "case_z": grille_h,
            "case_height": H - grille_h,
            "grille_height": grille_h,
            "grille_depth": D - grille_setback,
            "side_height": side_height,
            "side_refrigerator_width": refrigerator_width,
            "side_refrigerator_x": refrigerator_x,
            "side_freezer_width": freezer_width,
            "side_freezer_x": freezer_x,
            "bottom_zone_height": bottom_zone_height,
            "freezer_door_height": freezer_h,
            "freezer_door_z": grille_h,
            "french_door_width": french_width,
            "french_door_height": over_fridge_height,
            "french_left_x": 0.0,
            "french_right_x": french_width + gap,
            "french_z": bottom_zone_height,
            "cowling_height": cowling_h,
            "cowling_z": H - cowling_h,
            "door_back_y": 0.0,
        }

class SideBySideRefrigeratorFP:
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
        self._create_geometry(obj, assembly, sheet)
        obj.Parameters = sheet
        self._building = False
        obj.touch()
    def _create_geometry(self, obj, assembly, sheet):
        doc = obj.Document
        prefix = assembly.Name
        p = self._read_parameters(sheet)
        layout = self._validate(p)
        origin_point = Draft.make_point(
            X=0.0,
            Y=0.0,
            Z=0.0,
            name="{}_OriginPoint".format(prefix),
            point_size=8
        )
        origin_point.Label = "Assembly Origin Point"
        try:
            origin_point.ViewObject.Visibility = True
        except Exception:
            pass
        case = doc.addObject("Part::Box", "{}_ApplianceCase".format(prefix))
        case.Label = "Appliance Case"
        grille = doc.addObject("Part::Box", "{}_BaseGrille".format(prefix))
        grille.Label = "Base Grille"
        self._update_case(case, p, layout)
        self._update_grille(grille, p, layout)
        assembly.addObject(sheet)
        assembly.addObject(origin_point)
        assembly.addObject(case)
        assembly.addObject(grille)
        doc.recompute()
        fronts = {
            "side_refrigerator": SlabFront.create(
                doc, prefix, "SideBySideRefrigeratorDoor", "Side-by-Side Refrigerator Door"
            ),
            "side_freezer": SlabFront.create(
                doc, prefix, "SideBySideFreezerDoor", "Side-by-Side Freezer Door"
            ),
            "cowling": SlabFront.create(
                doc, prefix, "CowlingSlab", "Top Cowling Slab"
            ),
            "french_left": SlabFront.create(
                doc, prefix, "FrenchDoorLeft", "French Refrigerator Door - Left"
            ),
            "french_right": SlabFront.create(
                doc, prefix, "FrenchDoorRight", "French Refrigerator Door - Right"
            ),
            "bottom_freezer": SlabFront.create(
                doc, prefix, "BottomFreezerDoor", "Bottom Freezer Door"
            ),
        }
        self._update_fronts(fronts, p, layout)
        for front in fronts.values():
            assembly.addObject(front.box)
        assembly.addObject(obj)
        required = [sheet, origin_point, case, grille, obj] + [front.box for front in fronts.values()]
        missing = [member.Name for member in required if member not in assembly.Group]
        if missing:
            raise RuntimeError(
                "FreeCAD did not place all refrigerator members inside '{}'. Missing: {}"
                .format(assembly.Name, ", ".join(missing))
            )
        self._apply_colors(case, grille, fronts)
        self._apply_visibility(fronts, p["layout_mode"])
    def onDocumentRestored(self, obj):
        obj.Proxy = self
        self._building = False
    def _assembly(self, obj):
        assembly_name = ""
        try:
            assembly_name = str(obj.AssemblyObjectName).strip()
        except Exception:
            pass
        if assembly_name:
            assembly = obj.Document.getObject(assembly_name)
            if assembly is not None and assembly.TypeId == "App::Part":
                return assembly
        for parent in obj.InList:
            if parent.TypeId == "App::Part":
                return parent
        raise RuntimeError("Refrigerator Controller cannot resolve its owning App::Part.")
    def _parameters(self, obj, assembly):
        sheet = obj.Parameters
        if sheet is not None and sheet.Document == obj.Document:
            return sheet
        for child in assembly.Group:
            if child.Label == "Parameters" and child.TypeId == "Spreadsheet::Sheet":
                return child
        raise RuntimeError("Parameters spreadsheet not found for '{}'.".format(assembly.Name))
    def _geometry(self, assembly):
        doc = assembly.Document
        prefix = assembly.Name
        case = doc.getObject("{}_ApplianceCase".format(prefix))
        grille = doc.getObject("{}_BaseGrille".format(prefix))
        names = {
            "side_refrigerator": "{}_SideBySideRefrigeratorDoor".format(prefix),
            "side_freezer": "{}_SideBySideFreezerDoor".format(prefix),
            "cowling": "{}_CowlingSlab".format(prefix),
            "french_left": "{}_FrenchDoorLeft".format(prefix),
            "french_right": "{}_FrenchDoorRight".format(prefix),
            "bottom_freezer": "{}_BottomFreezerDoor".format(prefix),
        }
        if case is None or grille is None:
            raise RuntimeError("Refrigerator case/base-grille geometry is incomplete.")
        fronts = {}
        missing = []
        for key, name in names.items():
            box = doc.getObject(name)
            if box is None:
                missing.append(name)
            else:
                fronts[key] = SlabFront.from_existing(box)
        if missing:
            raise RuntimeError("Refrigerator front geometry is incomplete. Missing: {}".format(", ".join(missing)))
        return case, grille, fronts
    def _read_parameters(self, sheet):
        params = SheetParams(sheet)
        mode = str(params.get("RefrigeratorLayout", "OverUnder")).strip()
        if mode not in LAYOUT_MODES:
            mode = "OverUnder"
        return {
            "width": qty_mm(params.get("ApplianceWidth"), 1066.8),
            "depth": qty_mm(params.get("ApplianceDepth"), 609.6),
            "height": qty_mm(params.get("ApplianceHeight"), 2133.6),
            "layout_mode": mode,
            "fraction": qty_float(params.get("FridgeWidthFraction"), 0.6),
            "door_gap": qty_mm(params.get("DoorGap"), 6.0),
            "door_thickness": qty_mm(params.get("DoorThickness"), 25.4),
            "grille_height": qty_mm(params.get("BaseGrilleHeight"), 76.2),
            "grille_setback": qty_mm(params.get("BaseGrilleSetback"), 40.0),
            "freezer_door_height": qty_mm(params.get("FreezerDoorHeight"), 533.4),
            "cowling_height": qty_mm(params.get("CowlingHeight"), 254.0),
        }
    def _validate(self, p):
        return RefrigeratorLayout.calculate(p)
    def _update_case(self, case, p, layout):
        case.Length = p["width"]
        case.Width = p["depth"]
        case.Height = layout["case_height"]
        case.Placement = App.Placement(
            App.Vector(0.0, 0.0, layout["case_z"]),
            App.Rotation()
        )
    def _update_grille(self, grille, p, layout):
        grille.Length = p["width"]
        grille.Width = layout["grille_depth"]
        grille.Height = layout["grille_height"]
        grille.Placement = App.Placement(
            App.Vector(0.0, p["grille_setback"], 0.0),
            App.Rotation()
        )
    def _update_fronts(self, fronts, p, layout):
        t = p["door_thickness"]
        y = layout["door_back_y"]
        fronts["side_refrigerator"].update(
            width=layout["side_refrigerator_width"],
            height=layout["side_height"],
            thickness=t,
            x=layout["side_refrigerator_x"],
            z=layout["grille_height"],
            back_y=y,
        )
        fronts["side_freezer"].update(
            width=layout["side_freezer_width"],
            height=layout["side_height"],
            thickness=t,
            x=layout["side_freezer_x"],
            z=layout["grille_height"],
            back_y=y,
        )
        fronts["cowling"].update(
            width=p["width"],
            height=layout["cowling_height"],
            thickness=t,
            x=0.0,
            z=layout["cowling_z"],
            back_y=y,
        )
        fronts["french_left"].update(
            width=layout["french_door_width"],
            height=layout["french_door_height"],
            thickness=t,
            x=layout["french_left_x"],
            z=layout["french_z"],
            back_y=y,
        )
        fronts["french_right"].update(
            width=layout["french_door_width"],
            height=layout["french_door_height"],
            thickness=t,
            x=layout["french_right_x"],
            z=layout["french_z"],
            back_y=y,
        )
        fronts["bottom_freezer"].update(
            width=p["width"],
            height=layout["freezer_door_height"],
            thickness=t,
            x=0.0,
            z=layout["freezer_door_z"],
            back_y=y,
        )
    @staticmethod
    def _apply_visibility(fronts, mode):
        side_visible = mode == RefrigeratorLayout.MODE_SIDE_BY_SIDE
        fronts["side_refrigerator"].set_visible(side_visible)
        fronts["side_freezer"].set_visible(side_visible)
        fronts["cowling"].set_visible(not side_visible)
        fronts["french_left"].set_visible(not side_visible)
        fronts["french_right"].set_visible(not side_visible)
        fronts["bottom_freezer"].set_visible(not side_visible)
    @staticmethod
    def _apply_colors(case, grille, fronts):
        try:
            case.ViewObject.ShapeColor = (0.72, 0.72, 0.72)
            grille.ViewObject.ShapeColor = (0.25, 0.25, 0.25)
            for front in fronts.values():
                front.box.ViewObject.ShapeColor = (0.85, 0.85, 0.85)
        except Exception:
            pass
    def execute(self, obj):
        if getattr(self, "_building", False):
            return
        assembly = self._assembly(obj)
        sheet = self._parameters(obj, assembly)
        p = self._read_parameters(sheet)
        layout = self._validate(p)
        case, grille, fronts = self._geometry(assembly)
        self._update_case(case, p, layout)
        self._update_grille(grille, p, layout)
        self._update_fronts(fronts, p, layout)
        self._apply_colors(case, grille, fronts)
        self._apply_visibility(fronts, p["layout_mode"])

def validate_dialog_values(values):
    p = {
        "width": values["ApplianceWidth"],
        "depth": values["ApplianceDepth"],
        "height": values["ApplianceHeight"],
        "layout_mode": values["RefrigeratorLayout"],
        "fraction": values["FridgeWidthFraction"],
        "door_gap": values["DoorGap"],
        "door_thickness": values["DoorThickness"],
        "grille_height": values["BaseGrilleHeight"],
        "grille_setback": values["BaseGrilleSetback"],
        "freezer_door_height": values["FreezerDoorHeight"],
        "cowling_height": values["CowlingHeight"],
    }
    try:
        RefrigeratorLayout.calculate(p)
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

def next_side_by_side_refrigerator_name(document):
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
            "Select refrigerator insertion point: hover over an existing endpoint until the snap marker appears, then left-click. Press Esc or right-click to cancel."
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
            App.Console.PrintError("Refrigerator endpoint-cancel callback failed: {}\n".format(exc))
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
                    self._show_status("Endpoint found — left-click to place the refrigerator.")
                elif self._failed_endpoint_picks == 0:
                    self._show_status("Select an existing endpoint/vertex.")
                else:
                    self._show_status(
                        "Second pick: select an endpoint. If no endpoint exists, click again to place at 0,0,0."
                    )
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
                    self._show_status(
                        "Second pick: select an endpoint. If no endpoint exists, click again to place at 0,0,0."
                    )
                    QtWidgets.QMessageBox.information(
                        None,
                        "Endpoint Required",
                        "An endpoint is required, please select an endpoint, if none exists on second pick refrigerator will be drawn at 0,0,0.",
                    )
                    return
                self._finished = True
                accepted_point = App.Vector(0.0, 0.0, 0.0)
                App.Console.PrintMessage(
                    "No endpoint selected on second pick; placing Refrigerator at 0,0,0.\n"
                )
                self._cleanup()
                try:
                    self.on_accept(accepted_point)
                except Exception as exc:
                    App.Console.PrintError(
                        "Refrigerator insertion callback failed: {}\n".format(exc)
                    )
                return
            event_callback.setHandled()
            self._finished = True
            accepted_point = App.Vector(point)
            self._cleanup()
            try:
                self.on_accept(accepted_point)
            except Exception as exc:
                App.Console.PrintError(
                    "Refrigerator insertion callback failed: {}\n".format(exc)
                )
        except Exception as exc:
            App.Console.PrintError("Endpoint click handling failed: {}\n".format(exc))
            self.cancel()
    def _key_press(self, event_callback):
        if self._finished:
            return
        try:
            event = event_callback.getEvent()
            if (
                event.getState() == coin.SoButtonEvent.DOWN
                and event.getKey() == coin.SoKeyboardEvent.ESCAPE
            ):
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

class RefrigeratorBuilder:
    def __init__(self, document, instance_name):
        if document is None:
            raise ValueError(
                "create_side_by_side_refrigerator() requires an existing FreeCAD document."
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
                "{}_Parameters".format(self.instance_name)
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
        dialog = RefrigeratorDialog(self.parameters)
        if not dialog.exec():
            print(
                "Refrigerator creation cancelled. The active layout document was not changed."
            )
            return False
        self.values = dialog.values()
        valid, message = validate_dialog_values(self.values)
        if not valid:
            QtWidgets.QMessageBox.critical(
                None,
                "Invalid Refrigerator Parameters",
                message
            )
            return False
        ParameterTable.update(
            self.document,
            self.parameters,
            self.values
        )
        ParameterTable.verify(self.parameters)
        return True
    def _begin_insertion_point(self):
        self._picker = EndpointSnapPointPicker(
            on_accept=self._insertion_point_accepted,
            on_cancel=self._insertion_point_cancelled
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
                self.insertion_point.z
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
                "Refrigerator Creation Error",
                str(exc)
            )
            App.Console.PrintError(
                "Refrigerator creation failed: {}\n".format(exc)
            )
    def _insertion_point_cancelled(self):
        self._picker = None
        self._rollback_new_objects()
        print(
            "Refrigerator insertion cancelled. The active layout document was not changed."
        )
    def _create_component(self):
        self.assembly = self.document.addObject("App::Part", self.instance_name)
        mode = str(self.values.get("RefrigeratorLayout", "OverUnder"))
        if mode == "OverUnder":
            self.assembly.Label = "Over-Under Refrigerator / Freezer"
        else:
            self.assembly.Label = "Side-by-Side Refrigerator / Freezer"
        if self.insertion_point is not None:
            self.assembly.Placement.Base = App.Vector(self.insertion_point)
        self.controller = self.document.addObject(
            "Part::FeaturePython",
            "{}_Controller".format(self.instance_name)
        )
        self.controller.Label = "Parametric Refrigerator Controller"
        SideBySideRefrigeratorFP(
            self.controller,
            self.assembly,
            self.parameters
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
        print("PARAMETRIC REFRIGERATOR / FREEZER - REVISION 0.03")
        print("Target document: {}".format(self.document.Name))
        print("Instance name:   {}".format(self.instance_name))
        print("=" * 70)
    def _print_report(self):
        p = SheetParams(self.parameters)
        values = {
            "width": qty_mm(p.get("ApplianceWidth"), 1066.8),
            "depth": qty_mm(p.get("ApplianceDepth"), 609.6),
            "height": qty_mm(p.get("ApplianceHeight"), 2133.6),
            "layout_mode": str(p.get("RefrigeratorLayout", "OverUnder")).strip(),
            "fraction": qty_float(p.get("FridgeWidthFraction"), 0.6),
            "door_gap": qty_mm(p.get("DoorGap"), 6.0),
            "door_thickness": qty_mm(p.get("DoorThickness"), 25.4),
            "grille_height": qty_mm(p.get("BaseGrilleHeight"), 76.2),
            "grille_setback": qty_mm(p.get("BaseGrilleSetback"), 40.0),
            "freezer_door_height": qty_mm(p.get("FreezerDoorHeight"), 533.4),
            "cowling_height": qty_mm(p.get("CowlingHeight"), 254.0),
        }
        if values["layout_mode"] not in LAYOUT_MODES:
            values["layout_mode"] = "OverUnder"
        layout = RefrigeratorLayout.calculate(values)
        print("")
        print("-" * 70)
        print("REFRIGERATOR INSTANCE CREATED SUCCESSFULLY")
        print("-" * 70)
        print("Document:               ", self.document.Name)
        print("Refrigerator instance:  ", self.assembly.Name)
        print("Parameters sheet:       ", self.parameters.Name)
        print("Controller:             ", self.controller.Name)
        print("Layout:                 ", values["layout_mode"])
        print("Appliance Width:        ", inch_text_from_mm(values["width"]))
        print("Appliance Depth:        ", inch_text_from_mm(values["depth"]))
        print("Appliance Height:       ", inch_text_from_mm(values["height"]))
        if values["layout_mode"] == "OverUnder":
            print("Bottom freezer zone:    ", inch_text_from_mm(layout["bottom_zone_height"]))
            print("Freezer door height:    ", inch_text_from_mm(layout["freezer_door_height"]))
            print("French door height:     ", inch_text_from_mm(layout["french_door_height"]))
            print("French door width:      ", inch_text_from_mm(layout["french_door_width"]), "each")
            print("Top cowling height:     ", inch_text_from_mm(layout["cowling_height"]))
        else:
            print("Fridge Width Fraction:  ", values["fraction"])
            print("Refrigerator door width:", inch_text_from_mm(layout["side_refrigerator_width"]))
            print("Freezer door width:     ", inch_text_from_mm(layout["side_freezer_width"]))
        if self.insertion_point is not None:
            print(
                "Insertion Point:         X={:.3f}, Y={:.3f}, Z={:.3f} mm"
                .format(
                    self.insertion_point.x,
                    self.insertion_point.y,
                    self.insertion_point.z
                )
            )
        print("")
        print("Edit '{}' to resize only this refrigerator.".format(self.parameters.Name))
        print("Move/rotate '{}' with its App::Part Placement.".format(self.assembly.Name))
        print("=" * 70)
        print("")

def create_side_by_side_refrigerator(document, instance_name):
    builder = RefrigeratorBuilder(
        document=document,
        instance_name=instance_name
    )
    return builder.run()

def create_refrigerator(document, instance_name):
    return create_side_by_side_refrigerator(document, instance_name)

def main():
    document = App.ActiveDocument
    if document is None:
        QtWidgets.QMessageBox.warning(
            None,
            "No Active FreeCAD Document",
            "Open or create the kitchen/layout document first, then run this command again."
        )
        return None
    instance_name = next_side_by_side_refrigerator_name(document)
    return create_side_by_side_refrigerator(
        document=document,
        instance_name=instance_name
    )

# WORKBENCH MODULE NOTE
# Importing this module from CabinetsWorkbench.py does not auto-run it.
# Direct execution as a Python script / macro does run main().
if __name__ == "__main__":
    main()

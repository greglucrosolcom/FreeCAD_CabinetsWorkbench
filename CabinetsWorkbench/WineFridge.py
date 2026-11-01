# ============================================================

# PARAMETRIC FLOOR-STANDING WINE FRIDGE

# FREECAD 1.1.3
#
# REVISION: 0.02
#
# REVISION HISTORY:
#   0.00 - Baseline Parametric Floor-Standing Wine Fridge
#          - active-document independent instance architecture
#          - per-instance Parameters spreadsheet
#          - nearest-1/16-inch display
#          - hollow carcass with recessed toe kick
#          - framed glass door with separate frame members
#          - recessed transparent glass panel
#          - FeaturePython controller with build guard
#          - preference-free endpoint select-to-insert
#
#   0.01 - Insertion usability revision
#          - first non-endpoint pick displays an Endpoint Required dialog
#          - second pick still accepts a valid endpoint
#          - second non-endpoint pick creates the wine fridge at 0,0,0
#          - Esc / right-click still cancel normally
#          - no persistent Draft snap preferences are changed
#
#   0.02 - Assembly origin snap-point revision
#          - adds a visible Draft Point at local component origin 0,0,0
#          - point is grouped inside the component App::Part
#          - point moves and rotates with the component parent Placement
#          - provides an Endpoint snap reference for Draft Move placement
#

# ============================================================

import FreeCAD as App

import FreeCADGui as Gui

import Draft

from PySide import QtGui

from pivy import coin

from draftutils import gui_utils

SHEET_NAME = "Parameters"

CONTROLLER_NAME = "WineFridgeController"

INSTANCE_BASENAME = "WineFridge"

PARAM_DEFAULTS = [

    ("CabinetLength", "381 mm"),

    ("CabinetWidth", "482.6 mm"),

    ("CabinetHeight", "609.6 mm"),

    ("BoxWallThickness", "19.5 mm"),

    ("DoorFrameThickness", "19 mm"),

    ("DoorFrameWidth", "50 mm"),

    ("GlassThickness", "6 mm"),

    ("ToeKickHeight", "88.9 mm"),

    ("ToeKickSetback", "88.9 mm"),

]

class SheetParams:

    def __init__(self, sheet, row_start=2, row_end=40):

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

        self.set_cell("B{}".format(row), value)

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

    def create(

        doc,

        object_name=SHEET_NAME

    ):

        sheet = doc.addObject(

            "Spreadsheet::Sheet",

            object_name

        )

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

            sheet.setColumnWidth("B", 180)

        except Exception:

            pass

        ParameterTable.update_inches_column(

            sheet

        )

        doc.recompute()

        return sheet

    @staticmethod

    def _fractional_inch_expression(metric_address):

        """Return a live expression rounded to the nearest 1/16 inch."""

        inches = "({}/1in)".format(metric_address)

        sixteenths = "round(abs({})*16)".format(inches)

        whole = "floor({}/16)".format(sixteenths)

        remainder = "mod({};16)".format(sixteenths)

        sign = "({}<0?-1:1)".format(inches)

        denominator = (

            "({r}==8?2:(mod({r};4)==0?4:"

            "(mod({r};2)==0?8:16)))"

        ).format(r=remainder)

        numerator = "({r}*{d}/16)".format(

            r=remainder,

            d=denominator

        )

        whole_only = "<<%g in>> % ({w}*{s})".format(

            w=whole,

            s=sign

        )

        fraction_only = "<<%g/%g in>> % tuple({n}*{s};{d})".format(

            n=numerator,

            s=sign,

            d=denominator

        )

        mixed_number = "<<%g %g/%g in>> % tuple({w}*{s};{n};{d})".format(

            w=whole,

            s=sign,

            n=numerator,

            d=denominator

        )

        return "=({r}==0?{wo}:({w}==0?{fo}:{mn}))".format(

            r=remainder,

            wo=whole_only,

            w=whole,

            fo=fraction_only,

            mn=mixed_number

        )

    @staticmethod

    def update_inches_column(sheet):

        """Populate column C with live nearest-1/16-inch displays."""

        params = SheetParams(

            sheet

        )

        sheet.set(

            "C1",

            "Inches"

        )

        try:

            sheet.setColumnWidth(

                "C",

                140

            )

        except Exception:

            pass

        for row, (

            _name,

            default_value

        ) in enumerate(

            PARAM_DEFAULTS,

            start=2

        ):

            if not str(

                default_value

            ).strip().lower().endswith(

                "mm"

            ):

                continue

            metric_address = "B{}".format(

                row

            )

            inch_address = "C{}".format(

                row

            )

            metric_value = params.get_cell(

                metric_address

            )

            metric_text = (

                ""

                if metric_value is None

                else str(

                    metric_value

                ).strip()

            )

            if not metric_text:

                continue

            sheet.set(

                inch_address,

                ParameterTable._fractional_inch_expression(

                    metric_address

                )

            )

    @staticmethod

    def update(doc, sheet, values):

        params = SheetParams(sheet)

        for name, default_value in PARAM_DEFAULTS:

            value = values.get(name, params.get(name, default_value))

            params.set(name, "{} mm".format(value))

            row = params.row_of(name)

            try:

                sheet.setAlias("B{}".format(row), name)

            except Exception:

                pass

        ParameterTable.update_inches_column(

            sheet

        )

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

            raise RuntimeError(

                "Parameters did not resolve: {}".format(", ".join(failures))

            )

class WineFridgeDialog(QtGui.QDialog):

    def __init__(self, sheet):

        super().__init__()

        params = SheetParams(sheet)

        self.setWindowTitle("Floor-Standing Wine Fridge")

        layout = QtGui.QFormLayout(self)

        self.length = self._field(params, "CabinetLength", 381.0)

        self.width = self._field(params, "CabinetWidth", 482.6)

        self.height = self._field(params, "CabinetHeight", 609.6)

        self.wall = self._field(params, "BoxWallThickness", 19.5)

        self.frame_thickness = self._field(params, "DoorFrameThickness", 19.0)

        self.frame_width = self._field(params, "DoorFrameWidth", 50.0)

        self.glass_thickness = self._field(params, "GlassThickness", 6.0)

        self.toe_height = self._field(params, "ToeKickHeight", 88.9)

        self.toe_setback = self._field(params, "ToeKickSetback", 88.9)

        layout.addRow("Cabinet Length / X (mm):", self.length)

        layout.addRow("Cabinet Width / Depth / Y (mm):", self.width)

        layout.addRow("Cabinet Height / Z (mm):", self.height)

        layout.addRow("Carcass Wall Thickness (mm):", self.wall)

        layout.addRow("Door Frame Thickness (mm):", self.frame_thickness)

        layout.addRow("Door Frame Width (mm):", self.frame_width)

        layout.addRow("Glass Thickness (mm):", self.glass_thickness)

        layout.addRow("Toe Kick Height (mm):", self.toe_height)

        layout.addRow("Toe Kick Setback (mm):", self.toe_setback)

        buttons = QtGui.QDialogButtonBox(

            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel

        )

        buttons.accepted.connect(self.accept)

        buttons.rejected.connect(self.reject)

        layout.addRow(buttons)

    @staticmethod

    def _field(params, name, fallback):

        return QtGui.QLineEdit(str(qty_mm(params.get(name), fallback)))

    def values(self):

        return {

            "CabinetLength": qty_mm(self.length.text(), 381.0),

            "CabinetWidth": qty_mm(self.width.text(), 482.6),

            "CabinetHeight": qty_mm(self.height.text(), 609.6),

            "BoxWallThickness": qty_mm(self.wall.text(), 19.5),

            "DoorFrameThickness": qty_mm(self.frame_thickness.text(), 19.0),

            "DoorFrameWidth": qty_mm(self.frame_width.text(), 50.0),

            "GlassThickness": qty_mm(self.glass_thickness.text(), 6.0),

            "ToeKickHeight": qty_mm(self.toe_height.text(), 88.9),

            "ToeKickSetback": qty_mm(self.toe_setback.text(), 88.9),

        }

class WineFridgeFP:

    def __init__(self, obj, assembly, sheet):

        # FreeCAD may call execute() while this instance is still being built

        # inside an already-active layout document.

        self._building = True

        obj.Proxy = self

        obj.addProperty(

            "App::PropertyLink",

            "Parameters",

            "Component"

        )

        obj.addProperty(

            "App::PropertyString",

            "AssemblyObjectName",

            "Component"

        )

        obj.AssemblyObjectName = assembly.Name

        try:

            obj.setEditorMode(

                "AssemblyObjectName",

                1

            )

        except Exception:

            pass

        # Build and group all geometry before activating the Parameters link.

        self._create_geometry(

            obj,

            assembly,

            sheet

        )

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

            point_size=8

        )

        origin_point.Label = (

            "Assembly Origin Point"

        )

        try:

            origin_point.ViewObject.Visibility = True

        except Exception:

            pass

        outer = doc.addObject("Part::Box", "{}_CarcassOuter".format(prefix))

        outer.Label = "Carcass Outer"

        cavity = doc.addObject("Part::Box", "{}_InteriorCavity".format(prefix))

        cavity.Label = "Interior Cavity"

        carcass = doc.addObject("Part::Cut", "{}_WineFridgeCarcass".format(prefix))

        carcass.Label = "Wine Fridge Carcass"

        carcass.Base = outer

        carcass.Tool = cavity

        toe_kick = doc.addObject("Part::Box", "{}_ToeKick".format(prefix))

        toe_kick.Label = "Toe Kick"

        frame_left = doc.addObject("Part::Box", "{}_DoorFrameLeft".format(prefix))

        frame_left.Label = "Door Frame Left"

        frame_right = doc.addObject("Part::Box", "{}_DoorFrameRight".format(prefix))

        frame_right.Label = "Door Frame Right"

        frame_bottom = doc.addObject("Part::Box", "{}_DoorFrameBottom".format(prefix))

        frame_bottom.Label = "Door Frame Bottom"

        frame_top = doc.addObject("Part::Box", "{}_DoorFrameTop".format(prefix))

        frame_top.Label = "Door Frame Top"

        glass = doc.addObject("Part::Box", "{}_DoorGlass".format(prefix))

        glass.Label = "Door Glass"

        # Add passive members first.  Add the FeaturePython controller last

        # so execute() cannot run against a half-built wine-fridge instance.

        assembly.addObject(sheet)

        assembly.addObject(origin_point)

        assembly.addObject(carcass)

        assembly.addObject(toe_kick)

        assembly.addObject(frame_left)

        assembly.addObject(frame_right)

        assembly.addObject(frame_bottom)

        assembly.addObject(frame_top)

        assembly.addObject(glass)

        assembly.addObject(obj)

        required_members = (

            sheet,

            origin_point,

            carcass,

            toe_kick,

            frame_left,

            frame_right,

            frame_bottom,

            frame_top,

            glass,

            obj

        )

        missing_members = [

            member.Name

            for member in required_members

            if member not in assembly.Group

        ]

        if missing_members:

            raise RuntimeError(

                "FreeCAD did not place all wine-fridge members inside '{}'. "

                "Missing group members: {}"

                .format(

                    assembly.Name,

                    ", ".join(

                        missing_members

                    )

                )

            )

        try:

            outer.ViewObject.Visibility = False

            cavity.ViewObject.Visibility = False

            carcass.ViewObject.ShapeColor = (0.72, 0.72, 0.72)

            toe_kick.ViewObject.ShapeColor = (0.25, 0.25, 0.25)

            for frame in (

                frame_left,

                frame_right,

                frame_bottom,

                frame_top

            ):

                frame.ViewObject.ShapeColor = (0.20, 0.20, 0.20)

            glass.ViewObject.ShapeColor = (0.60, 0.80, 0.90)

            glass.ViewObject.Transparency = 70

        except Exception:

            pass

    def onDocumentRestored(self, obj):

        obj.Proxy = self

        self._building = False

    def _assembly(self, obj):

        assembly_name = ""

        try:

            assembly_name = str(

                obj.AssemblyObjectName

            ).strip()

        except Exception:

            pass

        if assembly_name:

            assembly = obj.Document.getObject(

                assembly_name

            )

            if (

                assembly is not None

                and

                assembly.TypeId == "App::Part"

            ):

                return assembly

        # Backward-compatible fallback for an older single-instance file.

        for parent in obj.InList:

            if parent.TypeId == "App::Part":

                return parent

        raise RuntimeError(

            "Wine Fridge Controller cannot resolve its owning App::Part."

        )

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

            and

            sheet.Document == obj.Document

        ):

            return sheet

        # Backward-compatible fallback.

        sheet = self._child_by_label(

            assembly,

            "Parameters",

            "Spreadsheet::Sheet"

        )

        if sheet is None:

            raise RuntimeError(

                "Parameters spreadsheet not found for '{}'."

                .format(

                    assembly.Name

                )

            )

        return sheet

    def _geometry(self, assembly):

        doc = assembly.Document

        prefix = assembly.Name

        outer = doc.getObject(

            "{}_CarcassOuter".format(

                prefix

            )

        )

        cavity = doc.getObject(

            "{}_InteriorCavity".format(

                prefix

            )

        )

        carcass = doc.getObject(

            "{}_WineFridgeCarcass".format(

                prefix

            )

        )

        toe_kick = doc.getObject(

            "{}_ToeKick".format(

                prefix

            )

        )

        frame_left = doc.getObject(

            "{}_DoorFrameLeft".format(

                prefix

            )

        )

        frame_right = doc.getObject(

            "{}_DoorFrameRight".format(

                prefix

            )

        )

        frame_bottom = doc.getObject(

            "{}_DoorFrameBottom".format(

                prefix

            )

        )

        frame_top = doc.getObject(

            "{}_DoorFrameTop".format(

                prefix

            )

        )

        glass = doc.getObject(

            "{}_DoorGlass".format(

                prefix

            )

        )

        # Backward-compatible label fallbacks.

        if carcass is None:

            carcass = self._child_by_label(

                assembly,

                "Wine Fridge Carcass",

                "Part::Cut"

            )

        if toe_kick is None:

            toe_kick = self._child_by_label(

                assembly,

                "Toe Kick",

                "Part::Box"

            )

        if frame_left is None:

            frame_left = self._child_by_label(

                assembly,

                "Door Frame Left",

                "Part::Box"

            )

        if frame_right is None:

            frame_right = self._child_by_label(

                assembly,

                "Door Frame Right",

                "Part::Box"

            )

        if frame_bottom is None:

            frame_bottom = self._child_by_label(

                assembly,

                "Door Frame Bottom",

                "Part::Box"

            )

        if frame_top is None:

            frame_top = self._child_by_label(

                assembly,

                "Door Frame Top",

                "Part::Box"

            )

        if glass is None:

            glass = self._child_by_label(

                assembly,

                "Door Glass",

                "Part::Box"

            )

        required = {

            "Wine Fridge Carcass": carcass,

            "Toe Kick": toe_kick,

            "Door Frame Left": frame_left,

            "Door Frame Right": frame_right,

            "Door Frame Bottom": frame_bottom,

            "Door Frame Top": frame_top,

            "Door Glass": glass

        }

        missing = [

            label

            for label, geometry in required.items()

            if geometry is None

        ]

        if missing:

            raise RuntimeError(

                "Wine-fridge geometry for '{}' is incomplete. Missing: {}"

                .format(

                    assembly.Name,

                    ", ".join(

                        missing

                    )

                )

            )

        if outer is None:

            outer = carcass.Base

        if cavity is None:

            cavity = carcass.Tool

        if outer is None or cavity is None:

            raise RuntimeError(

                "Carcass dependencies are missing for '{}'."

                .format(

                    assembly.Name

                )

            )

        return (

            outer,

            cavity,

            toe_kick,

            frame_left,

            frame_right,

            frame_bottom,

            frame_top,

            glass

        )

    def _read_parameters(self, sheet):

        p = SheetParams(sheet)

        return {

            "length": qty_mm(p.get("CabinetLength"), 381.0),

            "width": qty_mm(p.get("CabinetWidth"), 482.6),

            "height": qty_mm(p.get("CabinetHeight"), 609.6),

            "wall": qty_mm(p.get("BoxWallThickness"), 19.5),

            "frame_thickness": qty_mm(p.get("DoorFrameThickness"), 19.0),

            "frame_width": qty_mm(p.get("DoorFrameWidth"), 50.0),

            "glass_thickness": qty_mm(p.get("GlassThickness"), 6.0),

            "toe_height": qty_mm(p.get("ToeKickHeight"), 88.9),

            "toe_setback": qty_mm(p.get("ToeKickSetback"), 88.9),

        }

    def _validate(self, p):

        L = p["length"]

        W = p["width"]

        H = p["height"]

        wall = p["wall"]

        frame_t = p["frame_thickness"]

        frame_w = p["frame_width"]

        glass_t = p["glass_thickness"]

        toe_h = p["toe_height"]

        toe_setback = p["toe_setback"]

        if L <= 0:

            raise RuntimeError(

                "CabinetLength must be greater than zero."

            )

        if W <= 0:

            raise RuntimeError(

                "CabinetWidth must be greater than zero."

            )

        if H <= 0:

            raise RuntimeError(

                "CabinetHeight must be greater than zero."

            )

        if wall <= 0:

            raise RuntimeError(

                "BoxWallThickness must be greater than zero."

            )

        if toe_h <= 0 or toe_h >= H:

            raise RuntimeError(

                "ToeKickHeight must be greater than zero and less than CabinetHeight."

            )

        if toe_setback < 0 or toe_setback >= W:

            raise RuntimeError(

                "ToeKickSetback must be >= 0 and less than CabinetWidth."

            )

        carcass_height = H - toe_h

        if L - 2.0 * wall <= 0:

            raise RuntimeError(

                "Wall thickness leaves no interior length."

            )

        if W - wall <= 0:

            raise RuntimeError(

                "Wall thickness leaves no interior depth."

            )

        if carcass_height - 2.0 * wall <= 0:

            raise RuntimeError(

                "Wall thickness leaves no interior height."

            )

        if frame_t <= 0:

            raise RuntimeError(

                "DoorFrameThickness must be greater than zero."

            )

        if frame_w <= 0:

            raise RuntimeError(

                "DoorFrameWidth must be greater than zero."

            )

        if glass_t <= 0:

            raise RuntimeError(

                "GlassThickness must be greater than zero."

            )

        door_height = H - toe_h

        if L - 2.0 * frame_w <= 0:

            raise RuntimeError(

                "DoorFrameWidth leaves no usable glass width."

            )

        if door_height - 2.0 * frame_w <= 0:

            raise RuntimeError(

                "DoorFrameWidth leaves no usable glass height."

            )

        if glass_t > frame_t:

            raise RuntimeError(

                "GlassThickness cannot exceed DoorFrameThickness."

            )

    def _update_carcass(self, outer, cavity, p):

        L = p["length"]

        W = p["width"]

        H = p["height"]

        wall = p["wall"]

        toe_h = p["toe_height"]

        carcass_height = H - toe_h

        outer.Length = L

        outer.Width = W

        outer.Height = carcass_height

        outer.Placement.Base = App.Vector(0, 0, toe_h)

        cavity.Length = L - 2.0 * wall

        cavity.Width = W - wall

        cavity.Height = carcass_height - 2.0 * wall

        cavity.Placement.Base = App.Vector(

            wall,

            0,

            toe_h + wall

        )

    def _update_toe_kick(self, toe_kick, p):

        L = p["length"]

        W = p["width"]

        toe_h = p["toe_height"]

        setback = p["toe_setback"]

        toe_kick.Length = L

        toe_kick.Width = W - setback

        toe_kick.Height = toe_h

        toe_kick.Placement.Base = App.Vector(

            0,

            setback,

            0

        )

    def _update_door(

        self,

        frame_left,

        frame_right,

        frame_bottom,

        frame_top,

        glass,

        p

    ):

        L = p["length"]

        H = p["height"]

        toe_h = p["toe_height"]

        frame_t = p["frame_thickness"]

        frame_w = p["frame_width"]

        glass_t = p["glass_thickness"]

        door_height = H - toe_h

        door_y = -frame_t

        frame_left.Length = frame_w

        frame_left.Width = frame_t

        frame_left.Height = door_height

        frame_left.Placement.Base = App.Vector(

            0,

            door_y,

            toe_h

        )

        frame_right.Length = frame_w

        frame_right.Width = frame_t

        frame_right.Height = door_height

        frame_right.Placement.Base = App.Vector(

            L - frame_w,

            door_y,

            toe_h

        )

        opening_width = L - 2.0 * frame_w

        opening_height = door_height - 2.0 * frame_w

        frame_bottom.Length = opening_width

        frame_bottom.Width = frame_t

        frame_bottom.Height = frame_w

        frame_bottom.Placement.Base = App.Vector(

            frame_w,

            door_y,

            toe_h

        )

        frame_top.Length = opening_width

        frame_top.Width = frame_t

        frame_top.Height = frame_w

        frame_top.Placement.Base = App.Vector(

            frame_w,

            door_y,

            H - frame_w

        )

        glass_y = -(frame_t + glass_t) / 2.0

        glass.Length = opening_width

        glass.Width = glass_t

        glass.Height = opening_height

        glass.Placement.Base = App.Vector(

            frame_w,

            glass_y,

            toe_h + frame_w

        )

    def execute(self, obj):

        if getattr(

            self,

            "_building",

            False

        ):

            return

        assembly = self._assembly(obj)

        sheet = self._parameters(

            obj,

            assembly

        )

        parameters = self._read_parameters(

            sheet

        )

        self._validate(parameters)

        (

            outer,

            cavity,

            toe_kick,

            frame_left,

            frame_right,

            frame_bottom,

            frame_top,

            glass

        ) = self._geometry(assembly)

        self._update_carcass(

            outer,

            cavity,

            parameters

        )

        self._update_toe_kick(

            toe_kick,

            parameters

        )

        self._update_door(

            frame_left,

            frame_right,

            frame_bottom,

            frame_top,

            glass,

            parameters

        )

def validate_values(values):

    L = values["CabinetLength"]

    W = values["CabinetWidth"]

    H = values["CabinetHeight"]

    if L <= 0:

        return (

            False,

            "Cabinet Length must be greater than zero."

        )

    if W <= 0:

        return (

            False,

            "Cabinet Width / Depth must be greater than zero."

        )

    if H <= 0:

        return (

            False,

            "Cabinet Height must be greater than zero."

        )

    if values["BoxWallThickness"] <= 0:

        return (

            False,

            "Carcass Wall Thickness must be greater than zero."

        )

    carcass_height = H - values["ToeKickHeight"]

    if L - 2.0 * values["BoxWallThickness"] <= 0:

        return (

            False,

            "Carcass Wall Thickness leaves no interior cabinet length."

        )

    if W - values["BoxWallThickness"] <= 0:

        return (

            False,

            "Carcass Wall Thickness leaves no interior cabinet depth."

        )

    if (

        values["ToeKickHeight"] > 0

        and

        carcass_height - 2.0 * values["BoxWallThickness"] <= 0

    ):

        return (

            False,

            "Carcass Wall Thickness and Toe Kick Height leave no interior cabinet height."

        )

    if values["DoorFrameThickness"] <= 0:

        return (

            False,

            "Door Frame Thickness must be greater than zero."

        )

    if values["DoorFrameWidth"] <= 0:

        return (

            False,

            "Door Frame Width must be greater than zero."

        )

    if values["GlassThickness"] <= 0:

        return (

            False,

            "Glass Thickness must be greater than zero."

        )

    if not 0 < values["ToeKickHeight"] < H:

        return (

            False,

            "Toe Kick Height must be greater than zero and less than Cabinet Height."

        )

    if not 0 <= values["ToeKickSetback"] < W:

        return (

            False,

            "Toe Kick Setback must be >= 0 and less than Cabinet Width / Depth."

        )

    door_height = H - values["ToeKickHeight"]

    if L - 2.0 * values["DoorFrameWidth"] <= 0:

        return (

            False,

            "Door Frame Width leaves no usable glass width."

        )

    if door_height - 2.0 * values["DoorFrameWidth"] <= 0:

        return (

            False,

            "Door Frame Width leaves no usable glass height."

        )

    if values["GlassThickness"] > values["DoorFrameThickness"]:

        return (

            False,

            "Glass Thickness cannot exceed Door Frame Thickness."

        )

    return True, ""

def _sanitize_object_name(name):

    """Return a FreeCAD-safe internal object name."""

    cleaned = "".join(

        character

        if (

            character.isalnum()

            or character == "_"

        )

        else "_"

        for character in str(

            name

        ).strip()

    )

    if not cleaned:

        cleaned = INSTANCE_BASENAME

    if cleaned[0].isdigit():

        cleaned = "{}_{}".format(

            INSTANCE_BASENAME,

            cleaned

        )

    return cleaned

def next_wine_fridge_name(document):

    """Return the next available WineFridge### name."""

    if document is None:

        raise ValueError(

            "A valid FreeCAD document is required."

        )

    index = 1

    while True:

        candidate = "{}{:03d}".format(

            INSTANCE_BASENAME,

            index

        )

        if document.getObject(

            candidate

        ) is None:

            return candidate

        index += 1

# ============================================================

# ENDPOINT-SNAP INSERTION POINT PICKER

# ============================================================

class EndpointSnapPointPicker:

    """

    Lightweight endpoint picker for appliance insertion.

    This picker:

      - does NOT use Gui.Snapper.getPoint()

      - does NOT use a nested Qt event loop

      - does NOT change snapModes

      - does NOT change alwaysSnap

      - does NOT write any Draft preference

    It temporarily changes only the live Gui.Snapper.active_snaps list to

    Lock + Endpoint, uses Gui.Snapper.snap(..., active=True) to calculate and

    display the endpoint marker, then restores the exact prior live snap list.

    Placement behavior:

      - first non-endpoint left-click displays an Endpoint Required dialog

      - second left-click still accepts a valid endpoint

      - second non-endpoint left-click places the wine fridge at 0,0,0

    """

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

        """Begin endpoint selection and immediately return control to FreeCAD."""

        if Gui.ActiveDocument is None:

            raise RuntimeError(

                "A FreeCAD GUI document is required to pick an insertion point."

            )

        self.view = Gui.ActiveDocument.ActiveView

        if self.view is None:

            raise RuntimeError(

                "No active 3D view is available for endpoint selection."

            )

        self.snapper = self._ensure_snapper()

        self._old_active_snaps = list(

            getattr(

                self.snapper,

                "active_snaps",

                []

            )

        )

        # TEMPORARY LIVE STATE ONLY.

        # No FreeCAD preference is written.

        self.snapper.active_snaps = [

            "Lock",

            "Endpoint"

        ]

        self.callback_move = self.view.addEventCallbackPivy(

            coin.SoLocation2Event.getClassTypeId(),

            self._mouse_move

        )

        self.callback_click = self.view.addEventCallbackPivy(

            coin.SoMouseButtonEvent.getClassTypeId(),

            self._mouse_click

        )

        self.callback_key = self.view.addEventCallbackPivy(

            coin.SoKeyboardEvent.getClassTypeId(),

            self._key_press

        )

        self._show_status(

            "Select wine-fridge insertion point: "

            "hover over an existing endpoint until the snap marker appears, "

            "then left-click. Press Esc or right-click to cancel."

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

            App.Console.PrintError(

                "Wine-fridge endpoint-cancel callback failed: {}\n".format(exc)

            )

    def _ensure_snapper(self):
        """Return FreeCAD's canonical Draft Snapper singleton."""
        if hasattr(Gui, "Snapper"):
            return Gui.Snapper
        try:
            # FreeCAD's normal Draft GUI initialization path creates
            # the shared FreeCADGui.Snapper singleton.
            import DraftTools  # noqa: F401
        except Exception as exc:
            App.Console.PrintWarning(
                "DraftTools initialization warning: {}\n".format(exc)
            )
        if hasattr(Gui, "Snapper"):
            return Gui.Snapper
        # Last-resort fallback only. DraftTools should normally create this.
        from draftguitools.gui_snapper import Snapper
        Gui.Snapper = Snapper()
        return Gui.Snapper
    def _mouse_move(self, event_callback):

        """Calculate/display the endpoint snap marker under the cursor."""

        if self._finished:

            return

        try:

            event = event_callback.getEvent()

            self.snapper.snap(

                event.getPosition(),

                lastpoint=None,

                active=True,

                constrain=False,

                noTracker=False

            )

            endpoint_active = (

                str(

                    getattr(

                        self.snapper,

                        "cursorMode",

                        ""

                    ) or ""

                ).lower()

                == "endpoint"

            )

            if endpoint_active != self._last_endpoint_state:

                self._last_endpoint_state = endpoint_active

                if endpoint_active:

                    self._show_status(

                        "Endpoint found — left-click to place the wine fridge."

                    )

                else:

                    if self._failed_endpoint_picks == 0:

                        self._show_status(

                            "Select an existing endpoint/vertex."

                        )

                    else:

                        self._show_status(

                            "Second pick: select an endpoint. "
                            "If no endpoint exists, click again to place at 0,0,0."

                        )

        except Exception:

            pass

    def _mouse_click(self, event_callback):

        """Accept only a left-click that resolves to an Endpoint snap."""

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

                noTracker=False

            )

            snap_mode = str(

                getattr(

                    self.snapper,

                    "cursorMode",

                    ""

                ) or ""

            ).lower()

            if point is None or snap_mode != "endpoint":

                event_callback.setHandled()

                if self._failed_endpoint_picks == 0:

                    self._failed_endpoint_picks = 1

                    self._show_status(

                        "Second pick: select an endpoint. "
                        "If no endpoint exists, click again to place at 0,0,0."

                    )

                    QtGui.QMessageBox.information(

                        None,

                        "Endpoint Required",

                        (
                            "An endpoint is required, please select an endpoint, "
                            "if none exists on second pick wine fridge will be "
                            "drawn at 0,0,0."
                        )

                    )

                    return

                self._finished = True

                accepted_point = App.Vector(

                    0.0,

                    0.0,

                    0.0

                )

                App.Console.PrintMessage(

                    "No endpoint selected on second pick; "
                    "placing Floor-Standing Wine Fridge at 0,0,0.\n"

                )

                self._cleanup()

                try:

                    self.on_accept(

                        accepted_point

                    )

                except Exception as exc:

                    App.Console.PrintError(

                        "Wine-fridge insertion callback failed: {}\n".format(exc)

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

                    "Wine-fridge insertion callback failed: {}\n".format(exc)

                )

        except Exception as exc:

            App.Console.PrintError(

                "Endpoint click handling failed: {}\n".format(exc)

            )

            self.cancel()

    def _key_press(self, event_callback):

        """Escape cancels insertion-point selection."""

        if self._finished:

            return

        try:

            event = event_callback.getEvent()

            if (

                event.getState() == coin.SoButtonEvent.DOWN

                and

                event.getKey() == coin.SoKeyboardEvent.ESCAPE

            ):

                event_callback.setHandled()

                self.cancel()

        except Exception:

            pass

    def _cleanup(self):

        """

        Remove only callbacks installed by this picker and restore live snaps.

        No Draft preference is read or written here.

        """

        callbacks_removed = False

        if self.view is not None:

            if self.callback_move is not None:

                try:

                    self.view.removeEventCallbackPivy(

                        coin.SoLocation2Event.getClassTypeId(),

                        self.callback_move

                    )

                    callbacks_removed = True

                except Exception:

                    pass

            if self.callback_click is not None:

                try:

                    self.view.removeEventCallbackPivy(

                        coin.SoMouseButtonEvent.getClassTypeId(),

                        self.callback_click

                    )

                    callbacks_removed = True

                except Exception:

                    pass

            if self.callback_key is not None:

                try:

                    self.view.removeEventCallbackPivy(

                        coin.SoKeyboardEvent.getClassTypeId(),

                        self.callback_key

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

                    self.snapper.active_snaps = list(

                        self._old_active_snaps

                    )

            except Exception:

                pass

            # Remove only this picker's temporary marker/tracker state.

            # Do not call Snapper.off().

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

class WineFridgeBuilder:

    """Create one independent floor-standing wine-fridge instance."""

    def __init__(

        self,

        document,

        instance_name

    ):

        if document is None:

            raise ValueError(

                "create_wine_fridge() requires an existing FreeCAD document."

            )

        self.document = document

        self.instance_name = _sanitize_object_name(

            instance_name

        )

        if self.document.getObject(

            self.instance_name

        ) is not None:

            raise ValueError(

                "An object named '{}' already exists in document '{}'."

                .format(

                    self.instance_name,

                    self.document.Name

                )

            )

        self.parameters = None

        self.assembly = None

        self.controller = None

        self.values = None

        self.insertion_point = None

        self._picker = None

        self._original_object_names = set(

            obj.Name

            for obj in self.document.Objects

        )

    def run(self):

        self._print_header()

        try:

            self.parameters = ParameterTable.create(

                self.document,

                "{}_Parameters".format(

                    self.instance_name

                )

            )

            if not self._collect_parameters():

                self._rollback_new_objects()

                return None

            self._begin_insertion_point()

            # Endpoint selection is asynchronous. Returning this builder keeps

            # the insertion alive while FreeCAD handles normal GUI events.

            return self

        except Exception:

            self._rollback_new_objects()

            raise

    def _collect_parameters(self):

        dialog = WineFridgeDialog(

            self.parameters

        )

        if not dialog.exec():

            print(

                "Wine fridge creation cancelled. "

                "The active layout document was not changed."

            )

            return False

        self.values = dialog.values()

        valid, message = validate_values(

            self.values

        )

        if not valid:

            QtGui.QMessageBox.critical(

                None,

                "Invalid Wine Fridge Parameters",

                message

            )

            return False

        ParameterTable.update(

            self.document,

            self.parameters,

            self.values

        )

        ParameterTable.verify(

            self.parameters

        )

        return True

    def _begin_insertion_point(self):

        """Begin non-blocking endpoint selection after the parameter dialog."""

        self._picker = EndpointSnapPointPicker(

            on_accept=self._insertion_point_accepted,

            on_cancel=self._insertion_point_cancelled

        )

        self._picker.begin()

    def _insertion_point_accepted(self, point):

        """Create the wine fridge after a valid endpoint is selected."""

        self.insertion_point = App.Vector(point)

        self._picker = None

        print(

            "Insertion point: X={:.3f}, Y={:.3f}, Z={:.3f} mm".format(

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

            QtGui.QMessageBox.critical(

                None,

                "Wine Fridge Creation Error",

                str(exc)

            )

            App.Console.PrintError(

                "Wine fridge creation failed: {}\n".format(exc)

            )

    def _insertion_point_cancelled(self):

        """Rollback temporary objects if insertion-point selection is cancelled."""

        self._picker = None

        self._rollback_new_objects()

        print(

            "Wine-fridge insertion cancelled. "

            "The active layout document was not changed."

        )

    def _create_component(self):

        self.assembly = self.document.addObject(

            "App::Part",

            self.instance_name

        )

        self.assembly.Label = (

            "Floor-Standing Wine Fridge"

        )

        if self.insertion_point is not None:

            self.assembly.Placement.Base = App.Vector(

                self.insertion_point

            )

        self.controller = self.document.addObject(

            "Part::FeaturePython",

            "{}_Controller".format(

                self.instance_name

            )

        )

        self.controller.Label = (

            "Wine Fridge Controller"

        )

        WineFridgeFP(

            self.controller,

            self.assembly,

            self.parameters

        )

    def _rollback_new_objects(self):

        """Remove only objects created by this insertion attempt."""

        new_names = [

            obj.Name

            for obj in self.document.Objects

            if obj.Name not in self._original_object_names

        ]

        for name in reversed(

            new_names

        ):

            try:

                self.document.removeObject(

                    name

                )

            except Exception:

                pass

        try:

            self.document.recompute()

        except Exception:

            pass

    def _show_component(self):

        try:

            App.setActiveDocument(

                self.document.Name

            )

        except Exception:

            pass

        try:

            Gui.Selection.clearSelection()

            Gui.Selection.addSelection(

                self.assembly

            )

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

        print(

            "PARAMETRIC FLOOR-STANDING WINE FRIDGE"

        )

        print(

            "ACTIVE-DOCUMENT V3 INSTANCE"

        )

        print(

            "Target document: {}".format(

                self.document.Name

            )

        )

        print(

            "Instance name:   {}".format(

                self.instance_name

            )

        )

        print("=" * 70)

    def _print_report(self):

        p = SheetParams(

            self.parameters

        )

        length = qty_mm(

            p.get(

                "CabinetLength"

            ),

            381.0

        )

        width = qty_mm(

            p.get(

                "CabinetWidth"

            ),

            482.6

        )

        height = qty_mm(

            p.get(

                "CabinetHeight"

            ),

            609.6

        )

        print("")

        print("-" * 70)

        print(

            "WINE FRIDGE INSTANCE CREATED SUCCESSFULLY"

        )

        print("-" * 70)

        print(

            "Document:               ",

            self.document.Name

        )

        print(

            "Wine-fridge instance:   ",

            self.assembly.Name

        )

        print(

            "Parameters sheet:       ",

            self.parameters.Name

        )

        print(

            "Controller:             ",

            self.controller.Name

        )

        print(

            "Cabinet Length / X:     ",

            length,

            "mm"

        )

        print(

            "Cabinet Depth / Y:      ",

            width,

            "mm"

        )

        print(

            "Cabinet Height / Z:     ",

            height,

            "mm"

        )

        if self.insertion_point is not None:

            print(

                "Insertion Point:         "

                "X={:.3f}, Y={:.3f}, Z={:.3f} mm"

                .format(

                    self.insertion_point.x,

                    self.insertion_point.y,

                    self.insertion_point.z

                )

            )

        print("")

        print(

            "Edit '{}' to resize only this wine fridge."

            .format(

                self.parameters.Name

            )

        )

        print(

            "Move/rotate '{}' with its App::Part Placement."

            .format(

                self.assembly.Name

            )

        )

        print("=" * 70)

        print("")

def create_wine_fridge(

    document,

    instance_name

):

    """Begin creation of one independent floor-standing wine fridge."""

    builder = WineFridgeBuilder(

        document=document,

        instance_name=instance_name

    )

    return builder.run()

def main():

    document = App.ActiveDocument

    if document is None:

        QtGui.QMessageBox.warning(

            None,

            "No Active FreeCAD Document",

            "Open or create the kitchen/layout document first, "

            "then run this macro again."

        )

        return None

    instance_name = next_wine_fridge_name(

        document

    )

    return create_wine_fridge(

        document=document,

        instance_name=instance_name

    )

# ============================================================
# WORKBENCH MODULE NOTE
# ============================================================
# Do not call main() automatically here.
# CabinetsWorkbench.py imports this module, calls main(), and retains the
# returned WineFridgeBuilder while endpoint selection is active.

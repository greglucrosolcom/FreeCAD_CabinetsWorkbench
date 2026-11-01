# ============================================================
# FOUR DRAWER LOWER CABINET
# FIVE-PART RABBETED CARCASS + STANDARDIZED DRAWER-FRONT LAYOUT
# ============================================================
# Target: FreeCAD 1.1.4
# REVISION: 0.16
#   0.16 - Cabinet Core v1 architecture revision
#          - shared validation, parameter, component, runtime and snap infrastructure
#          - cabinet-specific layout/geometry relationships preserved
#          - no intentional default geometry change from previous validated revision
#
# 0.14 - Supplied baseline
#        - four permanent drawer fronts
#        - independent BottomDrawerHeight
#        - upper three drawer fronts share remaining height equally
#        - Slab/Shaker fronts and Overlay/Inset mounting
#        - internal Parameters sheet with inch displays
#        - recessed solid toe kick and endpoint select-to-insert
#
# 0.15 - Cabinet-family refactor / validation standard
#        - converts hollow carcass to five manufactured rabbeted parts
#        - BoxWallThickness standardized to CabinetThickness
#        - adds RabbetDepth using the proven lower-cabinet carcass model
#        - DrawerThickness standardized to DrawerFrontThickness
#        - ToeKickDepth renamed to ToeKickSetback
#        - removes unused ToeKickThickness parameter
#        - adds optional FrontProud for Overlay fronts; default 0 preserves geometry
#        - strict quantity parsing; invalid text is never silently replaced
#        - reusable hard ranges, errors, warnings and relational validation
#        - exact min/max limits are inclusive with 1e-6 mm tolerance
#        - spreadsheet adds Options and Allowed Range columns
#        - dialog disables fields not applicable to current mount/style
#        - preserves four-drawer distribution and canonical endpoint snapping
#
# Coordinate system:
# X = cabinet width
# Y = cabinet depth
# Z = overall floor-to-top cabinet height
# cabinet front/reference plane = Y=0
# cabinet extends +Y
# overlay drawer fronts extend toward -Y
# toe kick occupies Z=0..ToeKickHeight
# five-part carcass begins at Z=ToeKickHeight
# ============================================================
import FreeCAD as App
import FreeCADGui as Gui
import Draft
import Part
import warnings
from PySide import QtWidgets
from pivy import coin
from draftutils import gui_utils

from AdvCabinetValidation import ParameterSpec, ValidationResult
from AdvCabinetParameters import SheetParams, qty_mm, ParameterTable as CoreParameterTable, schema_from_legacy, apply_schema_overrides
from AdvCabinetComponents import CabinetPanel, RabbetedSidePanel, CabinetCarcass, ToeKick, CabinetFront
from AdvCabinetSnap import EndpointSnapPointPicker
from AdvCabinetDialog import SchemaCabinetDialog
from AdvCabinetRuntime import CabinetCreationTransaction, sanitize_object_name, next_instance_name, normalized_signature
SHEET_NAME = "Parameters"
INSTANCE_BASENAME = "FourDrawerLowerCabinet"
CABINET_CORE_VERSION = 1
CABINET_SCHEMA_VERSION = 2
CABINET_TYPE = "FourDrawerLowerCabinet"
GENERATOR_REVISION = "0.16"

DRAWER_COUNT = 4
INTEGER_PARAMETERS = set()
TEXT_PARAMETERS = {"DrawerStyle", "DrawerMount"}
FRONT_STYLES = ("Slab", "Shaker")
FRONT_MOUNTS = ("Inset", "Overlay")
PARAMETER_OPTIONS = {
    "DrawerStyle": "Slab | Shaker",
    "DrawerMount": "Inset | Overlay",
    "FrontProud": "Applies to Overlay fronts",
    "InsetSetback": "Applies to Inset fronts",
    "DrawerFrameWidth": "Applies to Shaker drawer fronts",
    "DrawerPanelThickness": "Applies to Shaker drawer fronts",
}
PARAM_DEFAULTS = [
    ("CabinetWidth", "600 mm"),
    ("CabinetDepth", "560 mm"),
    ("CabinetHeight", "720 mm"),
    ("CabinetThickness", "19.5 mm"),
    ("RabbetDepth", "6.35 mm"),
    ("ToeKickHeight", "88.9 mm"),
    ("ToeKickSetback", "88.9 mm"),
    ("DrawerFrontThickness", "19 mm"),
    ("DrawerGap", "3 mm"),
    ("BottomDrawerHeight", "200 mm"),
    ("FrontProud", "0 mm"),
    ("InsetSetback", "0 mm"),
    ("DrawerStyle", "Slab"),
    ("DrawerMount", "Overlay"),
    ("DrawerFrameWidth", "25.4 mm"),
    ("DrawerPanelThickness", "6 mm"),
]
PARAM_DEFAULT_MAP = dict(PARAM_DEFAULTS)
DIMENSION_PARAMETERS = {name for name, default in PARAM_DEFAULTS if str(default).strip().lower().endswith("mm")}
LEGACY_PARAMETER_ALIASES = {
    "CabinetThickness": ("BoxWallThickness",),
    "DrawerFrontThickness": ("DrawerThickness",),
    "ToeKickSetback": ("ToeKickDepth",),
}


PARAMETER_SPECS = {
    "CabinetWidth": ParameterSpec("CabinetWidth", 304.8, 1219.2, "Cabinet Width"),
    "CabinetDepth": ParameterSpec("CabinetDepth", 304.8, 1219.2, "Cabinet Depth"),
    "CabinetHeight": ParameterSpec("CabinetHeight", 406.4, 3657.6, "Cabinet Height"),
    "CabinetThickness": ParameterSpec("CabinetThickness", 6.35, 25.4, "Cabinet Thickness"),
    "RabbetDepth": ParameterSpec("RabbetDepth", 1.5875, 12.7, "Rabbet Depth"),
    "ToeKickHeight": ParameterSpec("ToeKickHeight", 76.2, 152.4, "Toe Kick Height"),
    "ToeKickSetback": ParameterSpec("ToeKickSetback", 50.8, 152.4, "Toe Kick Setback"),
    "DrawerFrontThickness": ParameterSpec("DrawerFrontThickness", 12.7, 31.75, "Drawer Front Thickness"),
    "DrawerGap": ParameterSpec("DrawerGap", 1.0, 6.35, "Drawer Gap"),
    "BottomDrawerHeight": ParameterSpec("BottomDrawerHeight", 76.2, 609.6, "Bottom Drawer Height"),
    "FrontProud": ParameterSpec("FrontProud", 0.0, 12.7, "Front Proud"),
    "InsetSetback": ParameterSpec("InsetSetback", 0.0, 25.4, "Inset Setback"),
    "DrawerFrameWidth": ParameterSpec("DrawerFrameWidth", 25.4, 101.6, "Drawer Frame Width"),
    "DrawerPanelThickness": ParameterSpec("DrawerPanelThickness", 3.0, 19.0, "Drawer Panel Thickness"),
}


def _parameter_raw(params, name, default=None):
    value = params.get(name, None)
    if value is not None and str(value).strip():
        return value
    for legacy_name in LEGACY_PARAMETER_ALIASES.get(name, ()):
        value = params.get(legacy_name, None)
        if value is not None and str(value).strip():
            return value
    return default


def read_parameter_values(sheet):
    params = SheetParams(sheet)
    values = {}
    for name, _default in PARAM_DEFAULTS:
        raw = _parameter_raw(params, name, None)
        if raw is None or not str(raw).strip():
            raise ValueError("{} is required.".format(name))
        if name in TEXT_PARAMETERS:
            text = str(raw).strip()
            if not text:
                raise ValueError("{} is required.".format(name))
            values[name] = text
        else:
            values[name] = qty_mm(raw, None, name)
    return values







class FourDrawerLayout:
    """Sole authority for the four drawer-front sizes and positions."""
    MOUNT_OVERLAY = "Overlay"
    MOUNT_INSET = "Inset"
    @classmethod
    def calculate(cls, values):
        width = float(values["CabinetWidth"])
        height = float(values["CabinetHeight"])
        toe_h = float(values["ToeKickHeight"])
        wall = float(values["CabinetThickness"])
        front_t = float(values["DrawerFrontThickness"])
        gap = float(values["DrawerGap"])
        bottom_h = float(values["BottomDrawerHeight"])
        mount = str(values["DrawerMount"])
        inset = float(values["InsetSetback"])
        proud = float(values["FrontProud"])
        carcass_height = height - toe_h
        if mount == cls.MOUNT_OVERLAY:
            front_width = width
            available_height = carcass_height
            x = 0.0
            start_z = toe_h
            back_y = -proud
        elif mount == cls.MOUNT_INSET:
            front_width = width - 2.0 * wall
            available_height = carcass_height - 2.0 * wall
            if front_width <= 0 or available_height <= 0:
                raise RuntimeError("CabinetThickness leaves no usable inset drawer-front opening.")
            x = wall
            start_z = toe_h + wall
            back_y = front_t + inset
        else:
            raise RuntimeError("DrawerMount must be Inset or Overlay.")
        remaining_upper = available_height - bottom_h - 3.0 * gap
        if remaining_upper <= 0:
            raise RuntimeError("BottomDrawerHeight and DrawerGap leave no usable height for the upper three drawer fronts.")
        upper_h = remaining_upper / 3.0
        heights = [bottom_h, upper_h, upper_h, upper_h]
        z_positions = []
        current_z = start_z
        for index, drawer_height in enumerate(heights):
            z_positions.append(current_z)
            if index < DRAWER_COUNT - 1:
                current_z += drawer_height + gap
        resolved_top = z_positions[-1] + heights[-1]
        expected_top = start_z + available_height
        if abs(resolved_top - expected_top) > 1.0e-6:
            raise RuntimeError("FourDrawerLayout failed to resolve the drawer-front stack.")
        return {
            "carcass_height": carcass_height,
            "available_height": available_height,
            "front_width": front_width,
            "x": x,
            "start_z": start_z,
            "back_y": back_y,
            "upper_drawer_height": upper_h,
            "heights": heights,
            "z_positions": z_positions,
            "resolved_top": resolved_top,
        }

class FourDrawerValidator:
    MIN_DRAWER_FRONT_HEIGHT = 76.2
    MIN_FRAME_OPENING = 25.4
    NORMAL_FRONT_MIN = 15.0
    NORMAL_FRONT_MAX = 24.0
    RANGE_TOLERANCE_MM = 1.0e-6
    @classmethod
    def _check_range(cls, result, values, name, active=True):
        if not active:
            return
        spec = PARAMETER_SPECS[name]
        value = float(values[name])
        if value < spec.minimum - cls.RANGE_TOLERANCE_MM or value > spec.maximum + cls.RANGE_TOLERANCE_MM:
            result.add_error("{} is {:.3f} mm. Allowed range is {}.".format(spec.label, value, spec.limit_text()))
    @classmethod
    def validate(cls, values):
        result = ValidationResult()
        required = [name for name, _default in PARAM_DEFAULTS]
        missing = [name for name in required if name not in values]
        if missing:
            result.add_error("Missing parameters: {}.".format(", ".join(missing)))
            return result
        style = str(values["DrawerStyle"])
        mount = str(values["DrawerMount"])
        if style not in FRONT_STYLES:
            result.add_error("DrawerStyle must be Slab or Shaker.")
        if mount not in FRONT_MOUNTS:
            result.add_error("DrawerMount must be Inset or Overlay.")
        for name in (
            "CabinetWidth", "CabinetDepth", "CabinetHeight", "CabinetThickness", "RabbetDepth",
            "ToeKickHeight", "ToeKickSetback", "DrawerFrontThickness", "DrawerGap", "BottomDrawerHeight"
        ):
            cls._check_range(result, values, name)
        cls._check_range(result, values, "FrontProud", active=(mount == "Overlay"))
        cls._check_range(result, values, "InsetSetback", active=(mount == "Inset"))
        cls._check_range(result, values, "DrawerFrameWidth", active=(style == "Shaker"))
        cls._check_range(result, values, "DrawerPanelThickness", active=(style == "Shaker"))
        if result.errors:
            return result
        W = float(values["CabinetWidth"])
        D = float(values["CabinetDepth"])
        H = float(values["CabinetHeight"])
        T = float(values["CabinetThickness"])
        R = float(values["RabbetDepth"])
        TKH = float(values["ToeKickHeight"])
        TKS = float(values["ToeKickSetback"])
        front_t = float(values["DrawerFrontThickness"])
        if R > 0.5 * T + cls.RANGE_TOLERANCE_MM:
            result.add_error("RabbetDepth cannot exceed 50% of CabinetThickness.")
        carcass_height = H - TKH
        try:
            CabinetCarcass.validate_dimensions(W, D, carcass_height, T, R)
        except Exception as exc:
            result.add_error(str(exc))
        try:
            ToeKick.validate_dimensions(W, D, TKH, TKS)
        except Exception as exc:
            result.add_error(str(exc))
        if TKH >= H - 2.0 * T:
            result.add_error("ToeKickHeight must leave room for the carcass above it.")
        if TKS >= D - T:
            result.add_error("ToeKickSetback must be less than CabinetDepth - CabinetThickness.")
        if mount == "Inset" and float(values["InsetSetback"]) + front_t > D + cls.RANGE_TOLERANCE_MM:
            result.add_error("InsetSetback + DrawerFrontThickness cannot exceed CabinetDepth.")
        if result.errors:
            return result
        try:
            layout = FourDrawerLayout.calculate(values)
        except Exception as exc:
            result.add_error(str(exc))
            return result
        for index, height in enumerate(layout["heights"], start=1):
            if height < cls.MIN_DRAWER_FRONT_HEIGHT - cls.RANGE_TOLERANCE_MM:
                result.add_error("Drawer Front {} is {:.3f} mm high; minimum is 76.2 mm (3 in).".format(index, height))
        if style == "Shaker":
            frame = float(values["DrawerFrameWidth"])
            panel = float(values["DrawerPanelThickness"])
            if layout["front_width"] - 2.0 * frame < cls.MIN_FRAME_OPENING - cls.RANGE_TOLERANCE_MM:
                result.add_error("DrawerFrameWidth leaves less than 25.4 mm center opening width.")
            for index, height in enumerate(layout["heights"], start=1):
                if height - 2.0 * frame < cls.MIN_FRAME_OPENING - cls.RANGE_TOLERANCE_MM:
                    result.add_error("Drawer Front {} frame width leaves less than 25.4 mm center opening height.".format(index))
            if panel > front_t + cls.RANGE_TOLERANCE_MM:
                result.add_error("DrawerPanelThickness cannot exceed DrawerFrontThickness.")
        if result.errors:
            return result
        if W > 914.4:
            result.add_warning("Cabinet width exceeds 36 in; verify span, loading and drawer-slide requirements.")
        if D > 609.6:
            result.add_warning("Cabinet depth exceeds 24 in; verify drawer-slide length, access and installation clearances.")
        if H > 1066.8:
            result.add_warning("Overall lower-cabinet height exceeds 42 in; verify intended application.")
        if T < 12.7:
            result.add_warning("CabinetThickness is below 1/2 in; verify structural capacity and joinery.")
        if front_t < cls.NORMAL_FRONT_MIN or front_t > cls.NORMAL_FRONT_MAX:
            result.add_warning("DrawerFrontThickness is outside the common 15-24 mm cabinet-front range; verify selected hardware and construction.")
        if float(values["BottomDrawerHeight"]) > 304.8:
            result.add_warning("BottomDrawerHeight exceeds 12 in; verify the intended drawer-front proportion.")
        if layout["upper_drawer_height"] < 101.6:
            result.add_warning("Upper drawer fronts are under 4 in high; verify handle/pull clearance and intended proportion.")
        if mount == "Overlay" and float(values["FrontProud"]) > 6.35:
            result.add_warning("FrontProud exceeds 1/4 in; verify the intended projection from the cabinet front plane.")
        return result

PARAMETER_SCHEMA = schema_from_legacy(
    PARAM_DEFAULTS,
    parameter_specs=PARAMETER_SPECS if "PARAMETER_SPECS" in globals() else {},
    text_parameters=TEXT_PARAMETERS if "TEXT_PARAMETERS" in globals() else set(),
    integer_parameters=INTEGER_PARAMETERS if "INTEGER_PARAMETERS" in globals() else set(),
    scalar_parameters=SCALAR_PARAMETERS if "SCALAR_PARAMETERS" in globals() else set(),
    parameter_options=PARAMETER_OPTIONS if "PARAMETER_OPTIONS" in globals() else {},
    legacy_aliases=LEGACY_PARAMETER_ALIASES if "LEGACY_PARAMETER_ALIASES" in globals() else {},
    cabinet_type=CABINET_TYPE,
    version=CABINET_SCHEMA_VERSION,
    display_unit_names=DIMENSION_PARAMETERS if "DIMENSION_PARAMETERS" in globals() else (),
)
PARAMETER_SCHEMA = apply_schema_overrides(PARAMETER_SCHEMA, {'CabinetWidth': {'group': 'Cabinet'}, 'CabinetDepth': {'group': 'Cabinet'}, 'CabinetHeight': {'group': 'Cabinet'}, 'CabinetThickness': {'group': 'Cabinet'}, 'RabbetDepth': {'group': 'Cabinet'}, 'ToeKickHeight': {'group': 'Toe Kick'}, 'ToeKickSetback': {'group': 'Toe Kick'}, 'DrawerFrontThickness': {'group': 'Drawer Fronts'}, 'DrawerGap': {'group': 'Drawer Fronts'}, 'BottomDrawerHeight': {'group': 'Drawer Fronts'}, 'FrontProud': {'group': 'Drawer Fronts', 'active_when': (('DrawerMount', 'Overlay'),)}, 'InsetSetback': {'group': 'Drawer Fronts', 'active_when': (('DrawerMount', 'Inset'),)}, 'DrawerStyle': {'group': 'Drawer Fronts'}, 'DrawerMount': {'group': 'Drawer Fronts'}, 'DrawerFrameWidth': {'group': 'Front Construction', 'active_when': (('DrawerStyle', 'Shaker'),)}, 'DrawerPanelThickness': {'group': 'Front Construction', 'active_when': (('DrawerStyle', 'Shaker'),)}})
_CORE_PARAMETER_TABLE = CoreParameterTable(PARAMETER_SCHEMA)
class ParameterTable:
    @staticmethod
    def create(doc, object_name=SHEET_NAME):
        return _CORE_PARAMETER_TABLE.create(doc, object_name)
    @staticmethod
    def update(doc, sheet, values):
        return _CORE_PARAMETER_TABLE.update(doc, sheet, values)
    @staticmethod
    def verify(sheet):
        return _CORE_PARAMETER_TABLE.verify(sheet)
    _fractional_inch_expression = staticmethod(CoreParameterTable._fractional_inch_expression)
    @staticmethod
    def update_inches_column(sheet):
        return None
    @staticmethod
    def update_options_column(sheet):
        return None
    @staticmethod
    def update_limits_column(sheet):
        return None
    @staticmethod
    def update_range_column(sheet):
        return None
    @staticmethod
    def apply_display_units(sheet):
        return None

def _cabinet_derived_preview(values):
    layout = FourDrawerLayout.calculate(values)
    return "Upper drawer height: {:.3f} mm each".format(layout["upper_drawer_height"])
class CabinetDialog(SchemaCabinetDialog):
    def __init__(self, sheet):
        super().__init__(sheet, PARAMETER_SCHEMA, title='Four-Drawer Lower Cabinet Parameters', validator=FourDrawerValidator.validate, notes=('BottomDrawerHeight is a direct control. The upper three drawer fronts divide the remaining usable front height equally.',), derived_preview=_cabinet_derived_preview)

class FourDrawerCabinetFP:
    DRAWER_COUNT = DRAWER_COUNT
    def __init__(self, obj, assembly, sheet):
        self._building = True
        self._last_signature = None
        obj.Proxy = self
        obj.addProperty("App::PropertyString", "CabinetType", "Metadata", "Stable cabinet type identifier")
        obj.CabinetType = CABINET_TYPE
        obj.addProperty("App::PropertyInteger", "CabinetSchemaVersion", "Metadata", "Parameter schema version")
        obj.CabinetSchemaVersion = CABINET_SCHEMA_VERSION
        obj.addProperty("App::PropertyString", "GeneratorRevision", "Metadata", "Cabinet generator revision")
        obj.GeneratorRevision = GENERATOR_REVISION
        for _metadata_name in ("CabinetType", "CabinetSchemaVersion", "GeneratorRevision"):
            try:
                obj.setEditorMode(_metadata_name, 1)
            except Exception:
                pass
        obj.addProperty("App::PropertyLink", "Parameters", "Component")
        obj.addProperty("App::PropertyString", "AssemblyObjectName", "Component")
        obj.AssemblyObjectName = assembly.Name
        try:
            obj.setEditorMode("AssemblyObjectName", 1)
        except Exception:
            pass
        self._create_geometry(obj, assembly, sheet)
        obj.addProperty("App::PropertyLinkList", "Components", "Component", "Direct links to cabinet component objects")
        obj.Components = [child for child in assembly.Group if child is not obj]
        obj.Parameters = sheet
        self._building = False
        obj.touch()
    def _create_geometry(self, obj, assembly, sheet):
        doc = obj.Document
        prefix = assembly.Name
        origin_point = Draft.make_point(X=0.0, Y=0.0, Z=0.0, name="{}_OriginPoint".format(prefix), point_size=8)
        origin_point.Label = "Assembly Origin Point"
        try:
            origin_point.ViewObject.Visibility = True
        except Exception:
            pass
        values = read_parameter_values(sheet)
        result = FourDrawerValidator.validate(values)
        result.raise_for_errors()
        layout = FourDrawerLayout.calculate(values)
        carcass = CabinetCarcass.create(doc, prefix)
        toe_kick = ToeKick.create(doc, prefix)
        carcass.update(
            values["CabinetWidth"], values["CabinetDepth"], layout["carcass_height"],
            values["CabinetThickness"], values["RabbetDepth"], values["ToeKickHeight"]
        )
        toe_kick.update(values["CabinetWidth"], values["CabinetDepth"], values["ToeKickHeight"], values["ToeKickSetback"])
        assembly.addObject(sheet)
        assembly.addObject(origin_point)
        for body in carcass.bodies():
            assembly.addObject(body)
        assembly.addObject(toe_kick.box)
        doc.recompute()
        labels = ["Drawer Front 1 - Bottom", "Drawer Front 2", "Drawer Front 3", "Drawer Front 4"]
        fronts = []
        for index, label in enumerate(labels, start=1):
            fronts.append(CabinetFront.create(doc, prefix, "DrawerFront_{}".format(index), label, values["DrawerStyle"]))
        self._update_fronts(fronts, values, layout)
        for front in fronts:
            assembly.addObject(front.body)
        assembly.addObject(obj)
        required = [sheet, origin_point] + carcass.bodies() + [toe_kick.box] + [front.body for front in fronts] + [obj]
        missing = [member.Name for member in required if member not in assembly.Group]
        if missing:
            raise RuntimeError("FreeCAD did not place all cabinet members inside '{}'. Missing: {}".format(assembly.Name, ", ".join(missing)))
        try:
            for body in carcass.bodies():
                body.ViewObject.ShapeColor = (0.72, 0.72, 0.72)
            toe_kick.box.ViewObject.ShapeColor = (0.64, 0.64, 0.64)
        except Exception:
            pass
    def onDocumentRestored(self, obj):
        obj.Proxy = self
        self._building = False
        self._last_signature = None
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
        raise RuntimeError("Four Drawer Cabinet Controller cannot resolve its owning App::Part.")
    def _parameters(self, obj, assembly):
        sheet = obj.Parameters
        if sheet is not None and sheet.Document == obj.Document:
            return sheet
        for child in assembly.Group:
            if child.Label == "Parameters" and child.TypeId == "Spreadsheet::Sheet":
                return child
        raise RuntimeError("Parameters spreadsheet not found for '{}'.".format(assembly.Name))
    def _front(self, doc, prefix, index, style):
        component = "DrawerFront_{}".format(index)
        body = doc.getObject("{}_{}".format(prefix, component))
        feature = doc.getObject("{}_{}Shape".format(prefix, component))
        if body is None or feature is None:
            raise RuntimeError("Drawer Front {} geometry is missing for '{}'.".format(index, prefix))
        return CabinetFront.from_existing(body, feature, style)
    def _geometry(self, assembly, values):
        doc = assembly.Document
        prefix = assembly.Name
        carcass = CabinetCarcass.from_document(doc, prefix)
        toe_kick = ToeKick.from_existing(doc.getObject("{}_ToeKickRiser".format(prefix)))
        fronts = [self._front(doc, prefix, index, values["DrawerStyle"]) for index in range(1, self.DRAWER_COUNT + 1)]
        return carcass, toe_kick, fronts
    @staticmethod
    def _update_fronts(fronts, values, layout):
        for index, front in enumerate(fronts):
            front.update(
                layout["front_width"], layout["heights"][index], values["DrawerFrontThickness"],
                values["DrawerFrameWidth"], values["DrawerPanelThickness"],
                x=layout["x"], z=layout["z_positions"][index], back_y=layout["back_y"]
            )
            front.set_visible(True)
    def execute(self, obj):
        if getattr(self, "_building", False):
            return
        assembly = self._assembly(obj)
        sheet = self._parameters(obj, assembly)
        values = read_parameter_values(sheet)
        result = FourDrawerValidator.validate(values)
        result.raise_for_errors()
        signature = normalized_signature(values)
        if signature == self._last_signature:
            return
        self._last_signature = signature
        if result.warnings:
            App.Console.PrintWarning("Four drawer cabinet parameter warning:\n{}\n".format(result.warning_text()))
        layout = FourDrawerLayout.calculate(values)
        carcass, toe_kick, fronts = self._geometry(assembly, values)
        carcass.update(
            values["CabinetWidth"], values["CabinetDepth"], layout["carcass_height"],
            values["CabinetThickness"], values["RabbetDepth"], values["ToeKickHeight"]
        )
        toe_kick.update(values["CabinetWidth"], values["CabinetDepth"], values["ToeKickHeight"], values["ToeKickSetback"])
        self._update_fronts(fronts, values, layout)

def validate_dialog_values(values):
    result = FourDrawerValidator.validate(values)
    return result.valid, result.error_text()

def _sanitize_object_name(name):
    return sanitize_object_name(name, INSTANCE_BASENAME)

def next_four_drawer_lower_cabinet_name(document):
    return next_instance_name(document, INSTANCE_BASENAME)


class FourDrawerCabinetBuilder:
    def __init__(self, document, instance_name):
        if document is None:
            raise ValueError("create_four_drawer_lower_cabinet() requires an existing FreeCAD document.")
        self.document = document
        self._transaction = CabinetCreationTransaction(self.document)
        self.instance_name = _sanitize_object_name(instance_name)
        if self.document.getObject(self.instance_name) is not None:
            raise ValueError("An object named '{}' already exists in document '{}'.".format(self.instance_name, self.document.Name))
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
            self.parameters = ParameterTable.create(self.document, "{}_Parameters".format(self.instance_name))
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
        dialog = CabinetDialog(self.parameters)
        if not dialog.exec():
            print("Four drawer cabinet creation cancelled. The active layout document was not changed.")
            return False
        self.values = dialog.values()
        valid, message = validate_dialog_values(self.values)
        if not valid:
            QtWidgets.QMessageBox.critical(None, "Invalid Four Drawer Cabinet Parameters", message)
            return False
        ParameterTable.update(self.document, self.parameters, self.values)
        ParameterTable.verify(self.parameters)
        return True
    def _accepted(self, point):
        self.insertion_point = App.Vector(point)
        self._picker = None
        try:
            self.assembly = self.document.addObject("App::Part", self.instance_name)
            self.assembly.Label = "Four Drawer Lower Cabinet"
            self.assembly.Placement.Base = App.Vector(self.insertion_point)
            self.controller = self.document.addObject("Part::FeaturePython", "{}_Controller".format(self.instance_name))
            self.controller.Label = "Four Drawer Cabinet Controller"
            FourDrawerCabinetFP(self.controller, self.assembly, self.parameters)
            self.document.recompute()
            self._show()
            self._print_report()
            self._transaction.commit()
        except Exception as exc:
            self._rollback()
            QtWidgets.QMessageBox.critical(None, "Four Drawer Cabinet Creation Error", str(exc))
            App.Console.PrintError("Four drawer cabinet creation failed: {}\n".format(exc))
    def _cancelled(self):
        self._picker = None
        self._rollback()
        print("Four drawer cabinet insertion cancelled. The active layout document was not changed.")
    def _rollback(self):
        self._transaction.rollback()
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
        print("FOUR DRAWER LOWER CABINET")
        print("FREECAD 1.1.4 - REVISION 0.15")
        print("Target document: {}".format(self.document.Name))
        print("Instance name:   {}".format(self.instance_name))
        print("=" * 72)
    def _print_report(self):
        values = read_parameter_values(self.parameters)
        layout = FourDrawerLayout.calculate(values)
        d = CabinetCarcass.derived_dimensions(values["CabinetWidth"], values["CabinetDepth"], values["CabinetThickness"], values["RabbetDepth"])
        print("")
        print("-" * 72)
        print("FOUR DRAWER LOWER CABINET INSTANCE CREATED SUCCESSFULLY")
        print("-" * 72)
        print("Cabinet instance:       ", self.assembly.Name)
        print("Parameters sheet:       ", self.parameters.Name)
        print("Overall height:         ", values["CabinetHeight"], "mm")
        print("Toe kick height:        ", values["ToeKickHeight"], "mm")
        print("Carcass height:         ", layout["carcass_height"], "mm")
        print("Drawer style:           ", values["DrawerStyle"])
        print("Drawer mount:           ", values["DrawerMount"])
        print("Front width:            ", layout["front_width"], "mm")
        print("Bottom drawer height:   ", layout["heights"][0], "mm")
        print("Upper drawer height:    ", layout["upper_drawer_height"], "mm each")
        print("Carcass parts:           Left Side, Right Side, Top, Bottom, Back")
        print("Rabbet depth:           ", values["RabbetDepth"], "mm")
        print("Top/Bottom/Back width:  ", d["panel_width"], "mm")
        print("Top/Bottom depth:       ", d["panel_depth"], "mm")
        print("Drawer visible front Y: ", layout["back_y"] - values["DrawerFrontThickness"], "mm")
        print("Insertion Point:         X={:.3f}, Y={:.3f}, Z={:.3f} mm".format(self.insertion_point.x, self.insertion_point.y, self.insertion_point.z))
        print("")
        print("Edit '{}' to resize only this cabinet.".format(self.parameters.Name))
        print("Move/rotate '{}' with its App::Part Placement.".format(self.assembly.Name))
        print("=" * 72)
        print("")

def create_four_drawer_lower_cabinet(document, instance_name):
    return FourDrawerCabinetBuilder(document, instance_name).run()

def main():
    document = App.ActiveDocument
    if document is None:
        QtWidgets.QMessageBox.warning(
            None, "No Active FreeCAD Document",
            "Open or create the kitchen/layout document first, then run this cabinet command again."
        )
        return None
    instance_name = next_four_drawer_lower_cabinet_name(document)
    return create_four_drawer_lower_cabinet(document=document, instance_name=instance_name)

# WORKBENCH MODULE NOTE:
# Do not call main() automatically here. CabinetsWorkbench.py imports this module,
# calls main(), and retains the returned FourDrawerCabinetBuilder while endpoint selection is active.

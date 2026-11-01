# ============================================================
# LOWER CABINET - TOP DRAWER(S) + DOORS
# FIVE-PART RABBETED CARCASS + STANDARDIZED FRONT LAYOUT
# ============================================================
# Target: FreeCAD 1.1.4
# REVISION: 0.13
#   0.13 - Cabinet Core v1 architecture revision
#          - shared validation, parameter, component, runtime and snap infrastructure
#          - cabinet-specific layout/geometry relationships preserved
#          - no intentional default geometry change from previous validated revision
#
# 0.11 - Supplied baseline
#        - one/two top drawer fronts
#        - one/two lower doors
#        - Slab/Shaker door and drawer-front styles
#        - Overlay/Inset front mounting
#        - centralized FrontLayout
#        - recessed solid toe kick
#        - endpoint select-to-insert using the shared Draft Snapper
#
# 0.12 - Cabinet-family refactor / validation standard
#        - converts hollow carcass to five manufactured rabbeted parts
#        - CabinetHeight is now overall floor-to-top height
#        - default CabinetHeight = 808.9 mm to preserve prior physical height
#        - BoxWallThickness standardized to CabinetThickness
#        - adds RabbetDepth using the proven lower-cabinet carcass model
#        - FrontGap renamed to FrontProud because it controls Y projection
#        - DoorStyle / DrawerStyle moved into Parameters as single source of truth
#        - strict quantity parsing; invalid text is never silently replaced
#        - reusable parameter specs, errors, warnings and relational validation
#        - exact min/max limits are inclusive with 1e-6 mm tolerance
#        - spreadsheet adds Options and Allowed Range columns
#        - dialog disables fields that do not apply to the selected configuration
#        - one reusable CabinetFront class replaces duplicate door/drawer classes
#        - preserves 1/2 drawer, 1/2 door, inset/overlay and endpoint behavior
#
# Coordinate system:
# X = cabinet width
# Y = cabinet depth
# Z = overall floor-to-top cabinet height
# cabinet front/reference plane = Y=0
# cabinet extends +Y
# overlay fronts extend toward -Y
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
from AdvCabinetParameters import SheetParams, qty_mm, qty_int, qty_scalar, ParameterTable as CoreParameterTable, schema_from_legacy, apply_schema_overrides
from AdvCabinetComponents import CabinetPanel, RabbetedSidePanel, CabinetCarcass, ToeKick, CabinetFront
from AdvCabinetSnap import EndpointSnapPointPicker
from AdvCabinetDialog import SchemaCabinetDialog
from AdvCabinetRuntime import CabinetCreationTransaction, sanitize_object_name, next_instance_name, normalized_signature
SHEET_NAME = "Parameters"
INSTANCE_BASENAME = "LowerCabinetDrawersDoors"
CABINET_CORE_VERSION = 1
CABINET_SCHEMA_VERSION = 2
CABINET_TYPE = "LowerCabinetDrawersDoors"
GENERATOR_REVISION = "0.13"

INTEGER_PARAMETERS = {"TopDrawerCount", "DoorCount"}
SCALAR_PARAMETERS = {"DrawerSplitRatio"}
TEXT_PARAMETERS = {"FrontMount", "DoorStyle", "DrawerStyle"}
FRONT_STYLES = ("Slab", "Shaker")
FRONT_MOUNTS = ("Inset", "Overlay")
PARAMETER_OPTIONS = {
    "TopDrawerCount": "1 | 2",
    "DoorCount": "1 | 2",
    "FrontMount": "Inset | Overlay",
    "DoorStyle": "Slab | Shaker",
    "DrawerStyle": "Slab | Shaker",
    "DrawerSplitRatio": "Applies when TopDrawerCount = 2",
    "DrawerSplitGap": "Applies when TopDrawerCount = 2",
    "DoorSplitGap": "Applies when DoorCount = 2",
    "FrontProud": "Applies to Overlay fronts",
    "InsetSetback": "Applies to Inset fronts",
    "DoorFrameWidth": "Applies to Shaker doors",
    "DoorPanelThickness": "Applies to Shaker doors",
    "DrawerFrameWidth": "Applies to Shaker drawer fronts",
    "DrawerPanelThickness": "Applies to Shaker drawer fronts",
}
PARAM_DEFAULTS = [
    ("CabinetWidth", "600 mm"),
    ("CabinetDepth", "560 mm"),
    ("CabinetHeight", "808.9 mm"),
    ("CabinetThickness", "19.5 mm"),
    ("RabbetDepth", "6.35 mm"),
    ("ToeKickHeight", "88.9 mm"),
    ("ToeKickSetback", "88.9 mm"),
    ("TopDrawerCount", "2"),
    ("TopDrawerHeight", "180 mm"),
    ("DrawerSplitRatio", "0.50"),
    ("DrawerSplitGap", "3 mm"),
    ("DoorCount", "2"),
    ("FrontThickness", "19 mm"),
    ("FrontProud", "3 mm"),
    ("DrawerDoorGap", "3 mm"),
    ("DoorSplitGap", "2 mm"),
    ("FrontMount", "Overlay"),
    ("InsetSetback", "0 mm"),
    ("DoorStyle", "Slab"),
    ("DrawerStyle", "Slab"),
    ("DoorFrameWidth", "50 mm"),
    ("DoorPanelThickness", "6 mm"),
    ("DrawerFrameWidth", "25.4 mm"),
    ("DrawerPanelThickness", "6 mm"),
]
PARAM_DEFAULT_MAP = dict(PARAM_DEFAULTS)
LEGACY_PARAMETER_ALIASES = {
    "CabinetThickness": ("BoxWallThickness",),
    "FrontProud": ("FrontGap",),
}


PARAMETER_SPECS = {
    "CabinetWidth": ParameterSpec("CabinetWidth", 304.8, 1219.2, "Cabinet Width"),
    "CabinetDepth": ParameterSpec("CabinetDepth", 304.8, 1219.2, "Cabinet Depth"),
    "CabinetHeight": ParameterSpec("CabinetHeight", 406.4, 3657.6, "Cabinet Height"),
    "CabinetThickness": ParameterSpec("CabinetThickness", 6.35, 25.4, "Cabinet Thickness"),
    "RabbetDepth": ParameterSpec("RabbetDepth", 1.5875, 12.7, "Rabbet Depth"),
    "ToeKickHeight": ParameterSpec("ToeKickHeight", 76.2, 152.4, "Toe Kick Height"),
    "ToeKickSetback": ParameterSpec("ToeKickSetback", 50.8, 152.4, "Toe Kick Setback"),
    "TopDrawerHeight": ParameterSpec("TopDrawerHeight", 76.2, 609.6, "Top Drawer Material Height"),
    "DrawerSplitGap": ParameterSpec("DrawerSplitGap", 1.0, 6.35, "Drawer Split Gap"),
    "FrontThickness": ParameterSpec("FrontThickness", 12.7, 31.75, "Front Thickness"),
    "FrontProud": ParameterSpec("FrontProud", 0.0, 12.7, "Front Proud"),
    "DrawerDoorGap": ParameterSpec("DrawerDoorGap", 1.0, 6.35, "Drawer/Door Gap"),
    "DoorSplitGap": ParameterSpec("DoorSplitGap", 1.0, 6.35, "Door Split Gap"),
    "InsetSetback": ParameterSpec("InsetSetback", 0.0, 25.4, "Inset Setback"),
    "DoorFrameWidth": ParameterSpec("DoorFrameWidth", 25.4, 101.6, "Door Frame Width"),
    "DoorPanelThickness": ParameterSpec("DoorPanelThickness", 3.0, 19.0, "Door Panel Thickness"),
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
        if name in INTEGER_PARAMETERS:
            values[name] = qty_int(raw, None, name)
        elif name in SCALAR_PARAMETERS:
            values[name] = qty_scalar(raw, None, name)
        elif name in TEXT_PARAMETERS:
            text = str(raw).strip()
            if not text:
                raise ValueError("{} is required.".format(name))
            values[name] = text
        else:
            values[name] = qty_mm(raw, None, name)
    return values







class FrontLayout:
    """Sole authority for drawer/door front sizing, placement and visibility."""
    MOUNT_OVERLAY = "Overlay"
    MOUNT_INSET = "Inset"
    @classmethod
    def calculate(cls, values):
        W = float(values["CabinetWidth"])
        H = float(values["CabinetHeight"])
        T = float(values["CabinetThickness"])
        toe_h = float(values["ToeKickHeight"])
        front_t = float(values["FrontThickness"])
        front_proud = float(values["FrontProud"])
        drawer_count = int(values["TopDrawerCount"])
        drawer_total = float(values["TopDrawerHeight"])
        ratio = float(values["DrawerSplitRatio"])
        drawer_split_gap = float(values["DrawerSplitGap"])
        drawer_door_gap = float(values["DrawerDoorGap"])
        door_count = int(values["DoorCount"])
        door_split_gap = float(values["DoorSplitGap"])
        mount = str(values["FrontMount"])
        inset_setback = float(values["InsetSetback"])
        carcass_height = H - toe_h
        if mount == cls.MOUNT_OVERLAY:
            available_width = W
            available_height = carcass_height
            front_x = 0.0
            front_z = toe_h
            front_back_y = -front_proud
        elif mount == cls.MOUNT_INSET:
            available_width = W - 2.0 * T
            available_height = carcass_height - 2.0 * T
            if available_width <= 0 or available_height <= 0:
                raise RuntimeError("CabinetThickness leaves no usable inset front opening.")
            front_x = T
            front_z = toe_h + T
            front_back_y = front_t + inset_setback
        else:
            raise RuntimeError("FrontMount must be Overlay or Inset.")
        if drawer_count == 1:
            drawer_1_h = drawer_total
            drawer_2_h = drawer_total
            drawer_stack_h = drawer_total
            drawer_2_visible = False
        elif drawer_count == 2:
            drawer_1_h = drawer_total * ratio
            drawer_2_h = drawer_total - drawer_1_h
            drawer_stack_h = drawer_total + drawer_split_gap
            drawer_2_visible = True
        else:
            raise RuntimeError("TopDrawerCount must be 1 or 2.")
        door_h = available_height - drawer_stack_h - drawer_door_gap
        if door_h <= 0:
            raise RuntimeError("Drawer configuration leaves no usable door height.")
        drawer_1_z = front_z + door_h + drawer_door_gap
        drawer_2_z = drawer_1_z + drawer_1_h + drawer_split_gap if drawer_2_visible else drawer_1_z
        if door_count == 2:
            door_width = (available_width - door_split_gap) / 2.0
            if door_width <= 0:
                raise RuntimeError("DoorSplitGap leaves no usable door width.")
            left_door_width = door_width
            right_door_width = door_width
            left_door_x = front_x
            right_door_x = front_x + door_width + door_split_gap
            right_door_visible = True
        elif door_count == 1:
            left_door_width = available_width
            right_door_width = available_width
            left_door_x = front_x
            right_door_x = front_x
            right_door_visible = False
        else:
            raise RuntimeError("DoorCount must be 1 or 2.")
        resolved_top = drawer_2_z + drawer_2_h if drawer_2_visible else drawer_1_z + drawer_1_h
        expected_top = front_z + available_height
        if abs(resolved_top - expected_top) > 1.0e-6:
            raise RuntimeError("FrontLayout failed to resolve the door/drawer stack.")
        return {
            "carcass_height": carcass_height,
            "available_width": available_width,
            "available_height": available_height,
            "front_back_y": front_back_y,
            "door_height": door_h,
            "left_door_width": left_door_width,
            "right_door_width": right_door_width,
            "left_door_x": left_door_x,
            "right_door_x": right_door_x,
            "left_door_z": front_z,
            "right_door_z": front_z,
            "right_door_visible": right_door_visible,
            "drawer_1_width": available_width,
            "drawer_2_width": available_width,
            "drawer_1_x": front_x,
            "drawer_2_x": front_x,
            "drawer_1_height": drawer_1_h,
            "drawer_2_height": drawer_2_h,
            "drawer_1_z": drawer_1_z,
            "drawer_2_z": drawer_2_z,
            "drawer_2_visible": drawer_2_visible,
            "drawer_stack_height": drawer_stack_h,
            "resolved_top": resolved_top,
        }

class LowerDrawersDoorsValidator:
    MIN_DRAWER_FRONT_HEIGHT = 76.2
    MIN_DOOR_HEIGHT = 152.4
    MIN_FRAME_OPENING = 25.4
    NORMAL_HINGE_FRONT_MIN = 15.0
    NORMAL_HINGE_FRONT_MAX = 24.0
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
        drawer_count = values["TopDrawerCount"]
        door_count = values["DoorCount"]
        mount = str(values["FrontMount"])
        door_style = str(values["DoorStyle"])
        drawer_style = str(values["DrawerStyle"])
        if drawer_count not in (1, 2):
            result.add_error("TopDrawerCount must be 1 or 2.")
        if door_count not in (1, 2):
            result.add_error("DoorCount must be 1 or 2.")
        if mount not in FRONT_MOUNTS:
            result.add_error("FrontMount must be Inset or Overlay.")
        if door_style not in FRONT_STYLES:
            result.add_error("DoorStyle must be Slab or Shaker.")
        if drawer_style not in FRONT_STYLES:
            result.add_error("DrawerStyle must be Slab or Shaker.")
        for name in (
            "CabinetWidth", "CabinetDepth", "CabinetHeight", "CabinetThickness", "RabbetDepth",
            "ToeKickHeight", "ToeKickSetback", "TopDrawerHeight", "FrontThickness", "DrawerDoorGap"
        ):
            cls._check_range(result, values, name)
        cls._check_range(result, values, "DrawerSplitGap", active=(drawer_count == 2))
        cls._check_range(result, values, "DoorSplitGap", active=(door_count == 2))
        cls._check_range(result, values, "FrontProud", active=(mount == "Overlay"))
        cls._check_range(result, values, "InsetSetback", active=(mount == "Inset"))
        cls._check_range(result, values, "DoorFrameWidth", active=(door_style == "Shaker"))
        cls._check_range(result, values, "DoorPanelThickness", active=(door_style == "Shaker"))
        cls._check_range(result, values, "DrawerFrameWidth", active=(drawer_style == "Shaker"))
        cls._check_range(result, values, "DrawerPanelThickness", active=(drawer_style == "Shaker"))
        if drawer_count == 2:
            ratio = float(values["DrawerSplitRatio"])
            if ratio < 0.20 - 1.0e-12 or ratio > 0.80 + 1.0e-12:
                result.add_error("DrawerSplitRatio must be between 0.20 and 0.80 when two drawers are used.")
        if result.errors:
            return result
        W = float(values["CabinetWidth"])
        D = float(values["CabinetDepth"])
        H = float(values["CabinetHeight"])
        T = float(values["CabinetThickness"])
        R = float(values["RabbetDepth"])
        TKH = float(values["ToeKickHeight"])
        TKS = float(values["ToeKickSetback"])
        front_t = float(values["FrontThickness"])
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
            result.add_error("InsetSetback + FrontThickness cannot exceed CabinetDepth.")
        if result.errors:
            return result
        try:
            layout = FrontLayout.calculate(values)
        except Exception as exc:
            result.add_error(str(exc))
            return result
        drawer_heights = [layout["drawer_1_height"]]
        if layout["drawer_2_visible"]:
            drawer_heights.append(layout["drawer_2_height"])
        for index, height in enumerate(drawer_heights, start=1):
            if height < cls.MIN_DRAWER_FRONT_HEIGHT - cls.RANGE_TOLERANCE_MM:
                result.add_error("Drawer Front {} is {:.3f} mm high; minimum is 76.2 mm (3 in).".format(index, height))
        if layout["door_height"] < cls.MIN_DOOR_HEIGHT - cls.RANGE_TOLERANCE_MM:
            result.add_error("Door height is {:.3f} mm; minimum is 152.4 mm (6 in).".format(layout["door_height"]))
        if door_style == "Shaker":
            frame = float(values["DoorFrameWidth"])
            panel = float(values["DoorPanelThickness"])
            for label, width in (("Left Door", layout["left_door_width"]), ("Right Door", layout["right_door_width"])):
                if width - 2.0 * frame < cls.MIN_FRAME_OPENING - cls.RANGE_TOLERANCE_MM:
                    result.add_error("{} frame width leaves less than 25.4 mm center opening width.".format(label))
            if layout["door_height"] - 2.0 * frame < cls.MIN_FRAME_OPENING - cls.RANGE_TOLERANCE_MM:
                result.add_error("DoorFrameWidth leaves less than 25.4 mm center opening height.")
            if panel > front_t + cls.RANGE_TOLERANCE_MM:
                result.add_error("DoorPanelThickness cannot exceed FrontThickness.")
        if drawer_style == "Shaker":
            frame = float(values["DrawerFrameWidth"])
            panel = float(values["DrawerPanelThickness"])
            if layout["drawer_1_width"] - 2.0 * frame < cls.MIN_FRAME_OPENING - cls.RANGE_TOLERANCE_MM:
                result.add_error("DrawerFrameWidth leaves less than 25.4 mm center opening width.")
            for index, height in enumerate(drawer_heights, start=1):
                if height - 2.0 * frame < cls.MIN_FRAME_OPENING - cls.RANGE_TOLERANCE_MM:
                    result.add_error("Drawer Front {} frame width leaves less than 25.4 mm center opening height.".format(index))
            if panel > front_t + cls.RANGE_TOLERANCE_MM:
                result.add_error("DrawerPanelThickness cannot exceed FrontThickness.")
        if result.errors:
            return result
        if W > 914.4:
            result.add_warning("Cabinet width exceeds 36 in; verify span, loading and front hardware requirements.")
        if D > 609.6:
            result.add_warning("Cabinet depth exceeds 24 in; verify access, hardware and installation clearances.")
        if H > 1066.8:
            result.add_warning("Overall lower-cabinet height exceeds 42 in; verify intended application.")
        if T < 12.7:
            result.add_warning("CabinetThickness is below 1/2 in; verify structural capacity and joinery.")
        if front_t < cls.NORMAL_HINGE_FRONT_MIN or front_t > cls.NORMAL_HINGE_FRONT_MAX:
            result.add_warning("FrontThickness is outside the common 15-24 mm concealed-hinge range; verify selected hardware.")
        if float(values["TopDrawerHeight"]) > 304.8:
            result.add_warning("TopDrawerHeight exceeds 12 in; verify the intended drawer/door proportion.")
        if drawer_count == 2 and (float(values["DrawerSplitRatio"]) < 0.35 or float(values["DrawerSplitRatio"]) > 0.65):
            result.add_warning("DrawerSplitRatio is strongly asymmetric; verify the intended two-drawer layout.")
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
    display_unit_names=(),
)
PARAMETER_SCHEMA = apply_schema_overrides(PARAMETER_SCHEMA, {'CabinetWidth': {'group': 'Cabinet'}, 'CabinetDepth': {'group': 'Cabinet'}, 'CabinetHeight': {'group': 'Cabinet'}, 'CabinetThickness': {'group': 'Cabinet'}, 'RabbetDepth': {'group': 'Cabinet'}, 'ToeKickHeight': {'group': 'Toe Kick'}, 'ToeKickSetback': {'group': 'Toe Kick'}, 'TopDrawerCount': {'group': 'Drawer Layout', 'minimum': 1, 'maximum': 2, 'label': 'Top Drawer Count'}, 'TopDrawerHeight': {'group': 'Drawer Layout'}, 'DrawerSplitRatio': {'group': 'Drawer Layout', 'minimum': 0.05, 'maximum': 0.95, 'active_when': (('TopDrawerCount', 2),)}, 'DrawerSplitGap': {'group': 'Drawer Layout', 'active_when': (('TopDrawerCount', 2),)}, 'DoorCount': {'group': 'Door Layout', 'minimum': 1, 'maximum': 2, 'label': 'Door Count'}, 'DoorSplitGap': {'group': 'Door Layout', 'active_when': (('DoorCount', 2),)}, 'DrawerDoorGap': {'group': 'Door Layout'}, 'FrontThickness': {'group': 'Fronts'}, 'FrontProud': {'group': 'Fronts', 'active_when': (('FrontMount', 'Overlay'),)}, 'InsetSetback': {'group': 'Fronts', 'active_when': (('FrontMount', 'Inset'),)}, 'FrontMount': {'group': 'Fronts'}, 'DoorStyle': {'group': 'Fronts'}, 'DrawerStyle': {'group': 'Fronts'}, 'DoorFrameWidth': {'group': 'Front Construction', 'active_when': (('DoorStyle', 'Shaker'),)}, 'DoorPanelThickness': {'group': 'Front Construction', 'active_when': (('DoorStyle', 'Shaker'),)}, 'DrawerFrameWidth': {'group': 'Front Construction', 'active_when': (('DrawerStyle', 'Shaker'),)}, 'DrawerPanelThickness': {'group': 'Front Construction', 'active_when': (('DrawerStyle', 'Shaker'),)}})
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
    layout = FrontLayout.calculate(values)
    return "Derived door height: {:.3f} mm; drawer stack: {:.3f} mm".format(layout["door_height"], layout["drawer_stack_height"])
class CabinetDialog(SchemaCabinetDialog):
    def __init__(self, sheet):
        super().__init__(sheet, PARAMETER_SCHEMA, title='Lower Cabinet - Drawer(s) + Doors Parameters', validator=LowerDrawersDoorsValidator.validate, notes=('TopDrawerCount and DoorCount may each be one or two. FrontMount applies to both drawer fronts and doors. Derived door height is validated before geometry is changed.',), derived_preview=_cabinet_derived_preview)

class LowerCabinetDrawersDoorsFP:
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
        result = LowerDrawersDoorsValidator.validate(values)
        result.raise_for_errors()
        layout = FrontLayout.calculate(values)
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
        drawer_1 = CabinetFront.create(doc, prefix, "TopDrawerFront1", "Top Drawer Front 1", values["DrawerStyle"])
        drawer_2 = CabinetFront.create(doc, prefix, "TopDrawerFront2", "Top Drawer Front 2", values["DrawerStyle"])
        left_door = CabinetFront.create(doc, prefix, "LeftDoor", "Left Door", values["DoorStyle"])
        right_door = CabinetFront.create(doc, prefix, "RightDoor", "Right Door", values["DoorStyle"])
        self._update_fronts(drawer_1, drawer_2, left_door, right_door, values, layout)
        for front in (drawer_1, drawer_2, left_door, right_door):
            assembly.addObject(front.body)
        assembly.addObject(obj)
        required = [sheet, origin_point] + carcass.bodies() + [toe_kick.box, drawer_1.body, drawer_2.body, left_door.body, right_door.body, obj]
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
        raise RuntimeError("Lower Cabinet Controller cannot resolve its owning App::Part.")
    def _parameters(self, obj, assembly):
        sheet = obj.Parameters
        if sheet is not None and sheet.Document == obj.Document:
            return sheet
        for child in assembly.Group:
            if child.Label == "Parameters" and child.TypeId == "Spreadsheet::Sheet":
                return child
        raise RuntimeError("Parameters spreadsheet not found for '{}'.".format(assembly.Name))
    def _front(self, doc, prefix, component_name, style):
        body = doc.getObject("{}_{}".format(prefix, component_name))
        feature = doc.getObject("{}_{}Shape".format(prefix, component_name))
        if body is None or feature is None:
            raise RuntimeError("Front geometry '{}_{}' is missing.".format(prefix, component_name))
        return CabinetFront.from_existing(body, feature, style)
    def _geometry(self, assembly, values):
        doc = assembly.Document
        prefix = assembly.Name
        carcass = CabinetCarcass.from_document(doc, prefix)
        toe_box = doc.getObject("{}_ToeKickRiser".format(prefix))
        toe_kick = ToeKick.from_existing(toe_box)
        drawer_1 = self._front(doc, prefix, "TopDrawerFront1", values["DrawerStyle"])
        drawer_2 = self._front(doc, prefix, "TopDrawerFront2", values["DrawerStyle"])
        left_door = self._front(doc, prefix, "LeftDoor", values["DoorStyle"])
        right_door = self._front(doc, prefix, "RightDoor", values["DoorStyle"])
        return carcass, toe_kick, drawer_1, drawer_2, left_door, right_door
    @staticmethod
    def _update_fronts(drawer_1, drawer_2, left_door, right_door, values, layout):
        front_t = values["FrontThickness"]
        back_y = layout["front_back_y"]
        left_door.update(
            layout["left_door_width"], layout["door_height"], front_t,
            values["DoorFrameWidth"], values["DoorPanelThickness"],
            x=layout["left_door_x"], z=layout["left_door_z"], back_y=back_y
        )
        right_door.update(
            layout["right_door_width"], layout["door_height"], front_t,
            values["DoorFrameWidth"], values["DoorPanelThickness"],
            x=layout["right_door_x"], z=layout["right_door_z"], back_y=back_y
        )
        drawer_1.update(
            layout["drawer_1_width"], layout["drawer_1_height"], front_t,
            values["DrawerFrameWidth"], values["DrawerPanelThickness"],
            x=layout["drawer_1_x"], z=layout["drawer_1_z"], back_y=back_y
        )
        drawer_2.update(
            layout["drawer_2_width"], layout["drawer_2_height"], front_t,
            values["DrawerFrameWidth"], values["DrawerPanelThickness"],
            x=layout["drawer_2_x"], z=layout["drawer_2_z"], back_y=back_y
        )
        left_door.set_visible(True)
        right_door.set_visible(layout["right_door_visible"])
        drawer_1.set_visible(True)
        drawer_2.set_visible(layout["drawer_2_visible"])
    def execute(self, obj):
        if getattr(self, "_building", False):
            return
        assembly = self._assembly(obj)
        sheet = self._parameters(obj, assembly)
        values = read_parameter_values(sheet)
        result = LowerDrawersDoorsValidator.validate(values)
        result.raise_for_errors()
        signature = normalized_signature(values)
        if signature == self._last_signature:
            return
        self._last_signature = signature
        if result.warnings:
            App.Console.PrintWarning("Lower drawer/door cabinet parameter warning:\n{}\n".format(result.warning_text()))
        layout = FrontLayout.calculate(values)
        carcass, toe_kick, drawer_1, drawer_2, left_door, right_door = self._geometry(assembly, values)
        carcass.update(
            values["CabinetWidth"], values["CabinetDepth"], layout["carcass_height"],
            values["CabinetThickness"], values["RabbetDepth"], values["ToeKickHeight"]
        )
        toe_kick.update(values["CabinetWidth"], values["CabinetDepth"], values["ToeKickHeight"], values["ToeKickSetback"])
        self._update_fronts(drawer_1, drawer_2, left_door, right_door, values, layout)

def validate_dialog_values(values):
    result = LowerDrawersDoorsValidator.validate(values)
    return result.valid, result.error_text()

def _sanitize_object_name(name):
    return sanitize_object_name(name, INSTANCE_BASENAME)

def next_lower_cabinet_drawers_doors_name(document):
    return next_instance_name(document, INSTANCE_BASENAME)


class LowerCabinetBuilder:
    def __init__(self, document, instance_name):
        if document is None:
            raise ValueError("create_lower_cabinet_drawers_doors() requires an existing FreeCAD document.")
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
            print("Cabinet creation cancelled. The active layout document was not changed.")
            return False
        self.values = dialog.values()
        valid, message = validate_dialog_values(self.values)
        if not valid:
            QtWidgets.QMessageBox.critical(None, "Invalid Lower Cabinet Parameters", message)
            return False
        ParameterTable.update(self.document, self.parameters, self.values)
        ParameterTable.verify(self.parameters)
        return True
    def _accepted(self, point):
        self.insertion_point = App.Vector(point)
        self._picker = None
        try:
            self.assembly = self.document.addObject("App::Part", self.instance_name)
            self.assembly.Label = "Lower Cabinet - Drawer(s) + Doors"
            self.assembly.Placement.Base = App.Vector(self.insertion_point)
            self.controller = self.document.addObject("Part::FeaturePython", "{}_Controller".format(self.instance_name))
            self.controller.Label = "Lower Cabinet Controller"
            LowerCabinetDrawersDoorsFP(self.controller, self.assembly, self.parameters)
            self.document.recompute()
            self._show()
            self._print_report()
            self._transaction.commit()
        except Exception as exc:
            self._rollback()
            QtWidgets.QMessageBox.critical(None, "Lower Cabinet Creation Error", str(exc))
            App.Console.PrintError("Lower cabinet creation failed: {}\n".format(exc))
    def _cancelled(self):
        self._picker = None
        self._rollback()
        print("Cabinet insertion cancelled. The active layout document was not changed.")
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
        print("LOWER CABINET - TOP DRAWER(S) + DOORS")
        print("FREECAD 1.1.4 - REVISION 0.12")
        print("Target document: {}".format(self.document.Name))
        print("Instance name:   {}".format(self.instance_name))
        print("=" * 72)
    def _print_report(self):
        values = read_parameter_values(self.parameters)
        layout = FrontLayout.calculate(values)
        d = CabinetCarcass.derived_dimensions(
            values["CabinetWidth"], values["CabinetDepth"], values["CabinetThickness"], values["RabbetDepth"]
        )
        print("")
        print("-" * 72)
        print("LOWER DRAWER / DOOR CABINET INSTANCE CREATED SUCCESSFULLY")
        print("-" * 72)
        print("Cabinet instance:       ", self.assembly.Name)
        print("Parameters sheet:       ", self.parameters.Name)
        print("Overall height:         ", values["CabinetHeight"], "mm")
        print("Toe kick height:        ", values["ToeKickHeight"], "mm")
        print("Carcass height:         ", layout["carcass_height"], "mm")
        print("Top drawer count:       ", values["TopDrawerCount"])
        print("Door count:             ", values["DoorCount"])
        print("Drawer style:           ", values["DrawerStyle"])
        print("Door style:             ", values["DoorStyle"])
        print("Front mount:            ", values["FrontMount"])
        print("Drawer 1 height:        ", layout["drawer_1_height"], "mm")
        if layout["drawer_2_visible"]:
            print("Drawer 2 height:        ", layout["drawer_2_height"], "mm")
        print("Door height:            ", layout["door_height"], "mm")
        print("Carcass parts:           Left Side, Right Side, Top, Bottom, Back")
        print("Rabbet depth:           ", values["RabbetDepth"], "mm")
        print("Top/Bottom/Back width:  ", d["panel_width"], "mm")
        print("Top/Bottom depth:       ", d["panel_depth"], "mm")
        print("Insertion Point:         X={:.3f}, Y={:.3f}, Z={:.3f} mm".format(
            self.insertion_point.x, self.insertion_point.y, self.insertion_point.z
        ))
        print("")
        print("Edit '{}' to resize only this cabinet.".format(self.parameters.Name))
        print("Move/rotate '{}' with its App::Part Placement.".format(self.assembly.Name))
        print("=" * 72)
        print("")

def create_lower_cabinet_drawers_doors(document, instance_name):
    return LowerCabinetBuilder(document, instance_name).run()

def main():
    document = App.ActiveDocument
    if document is None:
        QtWidgets.QMessageBox.warning(
            None, "No Active FreeCAD Document",
            "Open or create the kitchen/layout document first, then run this cabinet command again."
        )
        return None
    instance_name = next_lower_cabinet_drawers_doors_name(document)
    return create_lower_cabinet_drawers_doors(document=document, instance_name=instance_name)

# WORKBENCH MODULE NOTE:
# Do not call main() automatically here. CabinetsWorkbench.py imports this module,
# calls main(), and retains the returned LowerCabinetBuilder while endpoint selection is active.

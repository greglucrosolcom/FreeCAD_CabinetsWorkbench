# ============================================================
# PARAMETRIC TALL PANTRY UTILITY CABINET
# FIVE-PART RABBETED CARCASS + RESOLVED MULTI-ZONE GEOMETRY
# ============================================================
# Target: FreeCAD 1.1.4
# REVISION: 0.16
#   0.16 - Cabinet Core v1 architecture revision
#          - shared validation, parameter, component, runtime and snap infrastructure
#          - cabinet-specific layout/geometry relationships preserved
#          - no intentional default geometry change from previous validated revision
#
# 0.14 - Supplied baseline
#        - paired upper doors and paired middle doors
#        - three full-width drawer fronts and functional drawer boxes
#        - configurable 0-6 upper shelves
#        - upper and middle compartment dividers
#        - TallPantryLayout controls bottom-up fixed zones
#        - UpperDoorHeight absorbs remaining cabinet height
#        - endpoint select-to-insert using FreeCAD's shared Draft Snapper
#
# 0.15 - Cabinet-family refactor / resolved-layout hardening
#        - CabinetHeight hard limit is 60-120 in, inclusive
#        - converts hollow carcass to five manufactured rabbeted parts
#        - BoxWallThickness standardized to CabinetThickness
#        - adds RabbetDepth using the proven cabinet-family carcass model
#        - FrontOffset renamed FrontProud because it controls outward Y projection
#        - adds shared FrontMount = Overlay / Inset and InsetSetback
#        - strict quantity/integer parsing; invalid text is never silently replaced
#        - exact min/max limits are inclusive with 1e-6 mm tolerance
#        - errors name the conflicting geometry/parameters rather than clamping
#        - spreadsheet adds Options and Allowed Range columns
#        - dialog disables fields that do not apply to current style/mount/shelf count
#        - one CabinetFront class handles both doors and drawer fronts
#        - front, drawer-box, divider and shelf geometry resolve through one plan
#        - validates every resolved member before geometry changes
#        - preserves default dimensions and bottom-up resizing contract
#        - preserves 0-6 shelves, three functional drawer boxes and two dividers
#        - preserves canonical endpoint snap behavior and assembly grouping
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
import DraftTools
import Part
import warnings
from PySide import QtWidgets
from pivy import coin
from draftutils import gui_utils

from AdvCabinetValidation import ParameterSpec, ValidationResult
from AdvCabinetParameters import SheetParams, qty_mm, qty_int, ParameterTable as CoreParameterTable, schema_from_legacy, apply_schema_overrides
from AdvCabinetComponents import CabinetPanel, RabbetedSidePanel, CabinetCarcass, ToeKick, CabinetFront, CabinetDrawerBox
from AdvCabinetSnap import EndpointSnapPointPicker
from AdvCabinetDialog import SchemaCabinetDialog
from AdvCabinetLayouts import ResolvedLayout
from AdvCabinetRuntime import CabinetCreationTransaction, sanitize_object_name, next_instance_name, normalized_signature
SHEET_NAME = "Parameters"
INSTANCE_BASENAME = "TallPantryUtilityCabinet"
CABINET_CORE_VERSION = 1
CABINET_SCHEMA_VERSION = 2
CABINET_TYPE = "TallPantryUtilityCabinet"
GENERATOR_REVISION = "0.16"

SHELF_MAX = 6
FRONT_STYLES = ("Slab", "Shaker")
FRONT_MOUNTS = ("Inset", "Overlay")
TEXT_PARAMETERS = {"DoorStyle", "DrawerStyle", "FrontMount"}
INTEGER_PARAMETERS = {"UpperShelfCount"}
PARAMETER_OPTIONS = {
    "DoorStyle": "Slab | Shaker",
    "DrawerStyle": "Slab | Shaker",
    "FrontMount": "Inset | Overlay",
    "FrontProud": "Applies to Overlay fronts",
    "InsetSetback": "Applies to Inset fronts",
    "DoorFrameWidth": "Applies to Shaker doors",
    "DoorPanelThickness": "Applies to Shaker doors",
    "DrawerFrameWidth": "Applies to Shaker drawer fronts",
    "DrawerPanelThickness": "Applies to Shaker drawer fronts",
    "ShelfDepth": "Active when UpperShelfCount > 0",
    "ShelfThickness": "Active when UpperShelfCount > 0",
    "UpperShelfCount": "0-6",
}
PARAM_DEFAULTS = [
    ("CabinetWidth", "914.4 mm"),
    ("CabinetDepth", "609.6 mm"),
    ("CabinetHeight", "2133.6 mm"),
    ("CabinetThickness", "19.5 mm"),
    ("RabbetDepth", "6.35 mm"),
    ("ToeKickHeight", "88.9 mm"),
    ("ToeKickSetback", "88.9 mm"),
    ("FrontThickness", "19 mm"),
    ("FrontProud", "3 mm"),
    ("InsetSetback", "0 mm"),
    ("DoorSplitGap", "3 mm"),
    ("VerticalFrontGap", "3 mm"),
    ("MiddleDoorHeight", "457.2 mm"),
    ("TopDrawerHeight", "152.4 mm"),
    ("MiddleDrawerHeight", "228.6 mm"),
    ("BottomDrawerHeight", "381.7 mm"),
    ("DoorStyle", "Shaker"),
    ("DoorFrameWidth", "50 mm"),
    ("DoorPanelThickness", "6 mm"),
    ("DrawerStyle", "Shaker"),
    ("DrawerFrameWidth", "50 mm"),
    ("DrawerPanelThickness", "6 mm"),
    ("ShelfDepth", "508 mm"),
    ("ShelfThickness", "19 mm"),
    ("UpperShelfCount", "2"),
    ("DrawerBoxDepth", "508 mm"),
    ("DrawerBoxWallThickness", "12.7 mm"),
    ("DrawerSideClearance", "6 mm"),
    ("DrawerVerticalClearance", "3 mm"),
    ("FrontMount", "Overlay"),
]
PARAM_DEFAULT_MAP = dict(PARAM_DEFAULTS)
LEGACY_PARAMETER_ALIASES = {
    "CabinetThickness": ("BoxWallThickness",),
    "FrontProud": ("FrontOffset",),
}
DIMENSION_PARAMETERS = {
    name for name, default in PARAM_DEFAULTS
    if str(default).strip().lower().endswith("mm")
}


PARAMETER_SPECS = {
    "CabinetWidth": ParameterSpec("CabinetWidth", 304.8, 1219.2, "Cabinet Width"),
    "CabinetDepth": ParameterSpec("CabinetDepth", 304.8, 1219.2, "Cabinet Depth"),
    "CabinetHeight": ParameterSpec("CabinetHeight", 1524.0, 3048.0, "Cabinet Height"),
    "CabinetThickness": ParameterSpec("CabinetThickness", 6.35, 25.4, "Cabinet Thickness"),
    "RabbetDepth": ParameterSpec("RabbetDepth", 1.5875, 12.7, "Rabbet Depth"),
    "ToeKickHeight": ParameterSpec("ToeKickHeight", 76.2, 152.4, "Toe Kick Height"),
    "ToeKickSetback": ParameterSpec("ToeKickSetback", 50.8, 152.4, "Toe Kick Setback"),
    "FrontThickness": ParameterSpec("FrontThickness", 12.7, 31.75, "Front Thickness"),
    "FrontProud": ParameterSpec("FrontProud", 0.0, 12.7, "Front Proud"),
    "InsetSetback": ParameterSpec("InsetSetback", 0.0, 25.4, "Inset Setback"),
    "DoorSplitGap": ParameterSpec("DoorSplitGap", 1.0, 6.35, "Door Split Gap"),
    "VerticalFrontGap": ParameterSpec("VerticalFrontGap", 1.0, 6.35, "Vertical Front Gap"),
    "MiddleDoorHeight": ParameterSpec("MiddleDoorHeight", 304.8, 914.4, "Middle Door Height"),
    "TopDrawerHeight": ParameterSpec("TopDrawerHeight", 76.2, 304.8, "Top Drawer Height"),
    "MiddleDrawerHeight": ParameterSpec("MiddleDrawerHeight", 76.2, 457.2, "Middle Drawer Height"),
    "BottomDrawerHeight": ParameterSpec("BottomDrawerHeight", 101.6, 609.6, "Bottom Drawer Height"),
    "DoorFrameWidth": ParameterSpec("DoorFrameWidth", 25.4, 101.6, "Door Frame Width"),
    "DoorPanelThickness": ParameterSpec("DoorPanelThickness", 3.0, 19.0, "Door Panel Thickness"),
    "DrawerFrameWidth": ParameterSpec("DrawerFrameWidth", 25.4, 101.6, "Drawer Frame Width"),
    "DrawerPanelThickness": ParameterSpec("DrawerPanelThickness", 3.0, 19.0, "Drawer Panel Thickness"),
    "ShelfDepth": ParameterSpec("ShelfDepth", 152.4, 609.6, "Shelf Depth"),
    "ShelfThickness": ParameterSpec("ShelfThickness", 6.35, 38.1, "Shelf Thickness"),
    "DrawerBoxDepth": ParameterSpec("DrawerBoxDepth", 152.4, 609.6, "Drawer Box Depth"),
    "DrawerBoxWallThickness": ParameterSpec("DrawerBoxWallThickness", 6.35, 19.05, "Drawer Box Wall Thickness"),
    "DrawerSideClearance": ParameterSpec("DrawerSideClearance", 0.0, 25.4, "Drawer Side Clearance"),
    "DrawerVerticalClearance": ParameterSpec("DrawerVerticalClearance", 0.0, 25.4, "Drawer Vertical Clearance"),
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
            values[name] = str(raw).strip()
        elif name in INTEGER_PARAMETERS:
            values[name] = qty_int(raw, None, name)
        else:
            values[name] = qty_mm(raw, None, name)
    return values








class TallPantryFrontLayout:
    MOUNT_OVERLAY = "Overlay"
    MOUNT_INSET = "Inset"
    @classmethod
    def calculate(cls, values):
        W = float(values["CabinetWidth"])
        H = float(values["CabinetHeight"])
        T = float(values["CabinetThickness"])
        toe = float(values["ToeKickHeight"])
        gap = float(values["VerticalFrontGap"])
        front_t = float(values["FrontThickness"])
        mount = str(values["FrontMount"])
        if mount == cls.MOUNT_OVERLAY:
            front_width = W
            front_x = 0.0
            front_bottom_z = toe
            front_top_z = H
            front_back_y = -float(values["FrontProud"])
            internal_front_y = 0.0
        elif mount == cls.MOUNT_INSET:
            front_width = W - 2.0 * T
            front_x = T
            front_bottom_z = toe + T
            front_top_z = H - T
            front_back_y = front_t + float(values["InsetSetback"])
            internal_front_y = front_back_y
        else:
            raise RuntimeError("FrontMount must be Inset or Overlay.")
        available_height = front_top_z - front_bottom_z
        bottom_h = float(values["BottomDrawerHeight"])
        middle_drawer_h = float(values["MiddleDrawerHeight"])
        top_drawer_h = float(values["TopDrawerHeight"])
        middle_door_h = float(values["MiddleDoorHeight"])
        fixed_zone_height = bottom_h + middle_drawer_h + top_drawer_h + middle_door_h + 4.0 * gap
        upper_door_h = available_height - fixed_zone_height
        bottom_z = front_bottom_z
        middle_drawer_z = bottom_z + bottom_h + gap
        top_drawer_z = middle_drawer_z + middle_drawer_h + gap
        middle_door_z = top_drawer_z + top_drawer_h + gap
        upper_door_z = middle_door_z + middle_door_h + gap
        split = float(values["DoorSplitGap"])
        door_width = (front_width - split) / 2.0
        return {
            "mount": mount,
            "front_width": front_width,
            "front_x": front_x,
            "front_bottom_z": front_bottom_z,
            "front_top_z": front_top_z,
            "available_height": available_height,
            "fixed_zone_height": fixed_zone_height,
            "door_width": door_width,
            "upper_door_height": upper_door_h,
            "upper_door_z": upper_door_z,
            "middle_door_height": middle_door_h,
            "middle_door_z": middle_door_z,
            "top_drawer_height": top_drawer_h,
            "top_drawer_z": top_drawer_z,
            "middle_drawer_height": middle_drawer_h,
            "middle_drawer_z": middle_drawer_z,
            "bottom_drawer_height": bottom_h,
            "bottom_drawer_z": bottom_z,
            "front_back_y": front_back_y,
            "internal_front_y": internal_front_y,
            "visible_front_y": front_back_y - front_t,
            "carcass_height": H - toe,
        }

class DividerLayout:
    @staticmethod
    def calculate(values, front):
        W = float(values["CabinetWidth"])
        D = float(values["CabinetDepth"])
        T = float(values["CabinetThickness"])
        toe = float(values["ToeKickHeight"])
        y = float(front["internal_front_y"])
        depth = D - T - y
        length = W - 2.0 * T
        lower_z = float(front["middle_door_z"]) - T / 2.0
        upper_z = float(front["upper_door_z"]) - T / 2.0
        return {
            "lower": {"x": T, "y": y, "z": lower_z, "length": length, "depth": depth, "height": T},
            "upper": {"x": T, "y": y, "z": upper_z, "length": length, "depth": depth, "height": T},
            "interior_floor": toe + T,
            "interior_top": float(values["CabinetHeight"]) - T,
            "interior_back_y": D - T,
        }

class DrawerBoxLayout:
    @staticmethod
    def calculate(values, front, dividers):
        W = float(values["CabinetWidth"])
        T = float(values["CabinetThickness"])
        side = float(values["DrawerSideClearance"])
        vertical = float(values["DrawerVerticalClearance"])
        y = float(front["internal_front_y"])
        depth = float(values["DrawerBoxDepth"])
        wall = float(values["DrawerBoxWallThickness"])
        box_width = W - 2.0 * T - 2.0 * side
        box_x = T + side
        zones = [
            ("top", "Top Drawer Box", front["top_drawer_z"], front["top_drawer_height"]),
            ("middle", "Middle Drawer Box", front["middle_drawer_z"], front["middle_drawer_height"]),
            ("bottom", "Bottom Drawer Box", front["bottom_drawer_z"], front["bottom_drawer_height"]),
        ]
        result = {}
        for key, label, zone_z, zone_h in zones:
            box_z = float(zone_z) + vertical
            if key == "bottom":
                box_z = max(box_z, float(dividers["interior_floor"]) + vertical)
            box_top = float(zone_z) + float(zone_h) - vertical
            if key == "top":
                box_top = min(box_top, float(dividers["lower"]["z"]) - vertical)
            box_h = box_top - box_z
            result[key] = {
                "label": label,
                "x": box_x,
                "y": y,
                "z": box_z,
                "width": box_width,
                "depth": depth,
                "height": box_h,
                "wall": wall,
                "rear_y": y + depth,
                "top_z": box_z + box_h,
            }
        return result

class ShelfLayout:
    @staticmethod
    def calculate(values, front, dividers):
        count = int(values["UpperShelfCount"])
        T = float(values["CabinetThickness"])
        lower_z = float(dividers["upper"]["z"]) + T
        upper_z = float(dividers["interior_top"])
        usable_h = upper_z - lower_z
        pitch = usable_h / float(count + 1) if count > 0 else 0.0
        y = float(front["internal_front_y"])
        depth = float(values["ShelfDepth"])
        thickness = float(values["ShelfThickness"])
        shelves = []
        for index in range(count):
            center_z = lower_z + pitch * float(index + 1)
            shelves.append({
                "index": index + 1,
                "x": T,
                "y": y,
                "z": center_z - thickness / 2.0,
                "length": float(values["CabinetWidth"]) - 2.0 * T,
                "depth": depth,
                "thickness": thickness,
                "rear_y": y + depth,
                "top_z": center_z + thickness / 2.0,
            })
        return {
            "count": count,
            "lower_z": lower_z,
            "upper_z": upper_z,
            "usable_height": usable_h,
            "pitch": pitch,
            "shelves": shelves,
        }

class ResolvedTallPantryLayout:
    @staticmethod
    def calculate(values):
        front = TallPantryFrontLayout.calculate(values)
        dividers = DividerLayout.calculate(values, front)
        boxes = DrawerBoxLayout.calculate(values, front, dividers)
        shelves = ShelfLayout.calculate(values, front, dividers)
        return ResolvedLayout(front=front, dividers=dividers, boxes=boxes, shelves=shelves)

class TallPantryValidator:
    RANGE_TOLERANCE_MM = 1.0e-6
    MIN_FRONT_DIMENSION = 76.2
    MIN_FRAME_OPENING = 25.4
    NORMAL_HINGE_FRONT_MIN = 15.0
    NORMAL_HINGE_FRONT_MAX = 24.0
    @classmethod
    def _range(cls, result, values, name, active=True):
        if not active or name not in PARAMETER_SPECS:
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
            result.add_error("Missing required parameters: {}.".format(", ".join(missing)))
            return result
        mount = str(values["FrontMount"])
        door_style = str(values["DoorStyle"])
        drawer_style = str(values["DrawerStyle"])
        shelf_count = values["UpperShelfCount"]
        if mount not in FRONT_MOUNTS:
            result.add_error("FrontMount must be Inset or Overlay.")
        if door_style not in FRONT_STYLES:
            result.add_error("DoorStyle must be Slab or Shaker.")
        if drawer_style not in FRONT_STYLES:
            result.add_error("DrawerStyle must be Slab or Shaker.")
        if not isinstance(shelf_count, int):
            result.add_error("UpperShelfCount must be an integer from 0 through {}.".format(SHELF_MAX))
        elif shelf_count < 0 or shelf_count > SHELF_MAX:
            result.add_error("UpperShelfCount is {}. Allowed range is 0-{}.".format(shelf_count, SHELF_MAX))
        for name in PARAMETER_SPECS:
            active = True
            if name == "FrontProud":
                active = mount == "Overlay"
            elif name == "InsetSetback":
                active = mount == "Inset"
            elif name in ("DoorFrameWidth", "DoorPanelThickness"):
                active = door_style == "Shaker"
            elif name in ("DrawerFrameWidth", "DrawerPanelThickness"):
                active = drawer_style == "Shaker"
            elif name in ("ShelfDepth", "ShelfThickness"):
                active = isinstance(shelf_count, int) and shelf_count > 0
            cls._range(result, values, name, active)
        if result.errors:
            return result
        W = float(values["CabinetWidth"])
        D = float(values["CabinetDepth"])
        H = float(values["CabinetHeight"])
        T = float(values["CabinetThickness"])
        R = float(values["RabbetDepth"])
        toe_h = float(values["ToeKickHeight"])
        toe_setback = float(values["ToeKickSetback"])
        front_t = float(values["FrontThickness"])
        if R >= T - cls.RANGE_TOLERANCE_MM:
            result.add_error("RabbetDepth ({:.3f} mm) must be less than CabinetThickness ({:.3f} mm).".format(R, T))
        if R > 0.5 * T + cls.RANGE_TOLERANCE_MM:
            result.add_error("RabbetDepth ({:.3f} mm) exceeds 50% of CabinetThickness ({:.3f} mm).".format(R, T))
        carcass_h = H - toe_h
        try:
            CabinetCarcass.validate_dimensions(W, D, carcass_h, T, R)
        except Exception as exc:
            result.add_error(str(exc))
        if toe_h >= H - 2.0 * T - cls.RANGE_TOLERANCE_MM:
            result.add_error("ToeKickHeight conflicts with CabinetHeight/CabinetThickness and leaves no usable carcass interior height.")
        if toe_setback >= D - T - cls.RANGE_TOLERANCE_MM:
            result.add_error("ToeKickSetback conflicts with CabinetDepth/CabinetThickness and leaves no positive toe-kick riser depth.")
        if mount == "Inset":
            inset_depth = front_t + float(values["InsetSetback"])
            if inset_depth >= D - T - cls.RANGE_TOLERANCE_MM:
                result.add_error("InsetSetback + FrontThickness ({:.3f} mm) conflicts with CabinetDepth/CabinetThickness and leaves no usable interior depth.".format(inset_depth))
        if float(values["DrawerBoxDepth"]) <= 2.0 * float(values["DrawerBoxWallThickness"]) + cls.RANGE_TOLERANCE_MM:
            result.add_error("DrawerBoxDepth must exceed twice DrawerBoxWallThickness to create a usable drawer cavity.")
        if result.errors:
            return result
        try:
            plan = ResolvedTallPantryLayout.calculate(values)
        except Exception as exc:
            result.add_error(str(exc))
            return result
        F = plan["front"]
        fixed_detail = (
            "BottomDrawerHeight {:.3f} + MiddleDrawerHeight {:.3f} + TopDrawerHeight {:.3f} + "
            "MiddleDoorHeight {:.3f} + four VerticalFrontGap values ({:.3f} each)"
        ).format(
            float(values["BottomDrawerHeight"]), float(values["MiddleDrawerHeight"]),
            float(values["TopDrawerHeight"]), float(values["MiddleDoorHeight"]),
            float(values["VerticalFrontGap"])
        )
        if F["available_height"] <= cls.RANGE_TOLERANCE_MM:
            result.add_error("FrontMount/CabinetThickness leaves no usable vertical front opening.")
        if F["upper_door_height"] < cls.MIN_FRONT_DIMENSION - cls.RANGE_TOLERANCE_MM:
            result.add_error(
                "Calculated Upper Door Height is {:.3f} mm, below the {:.1f} mm minimum. "
                "Conflict: available front height {:.3f} mm is consumed by {}."
                .format(F["upper_door_height"], cls.MIN_FRONT_DIMENSION, F["available_height"], fixed_detail)
            )
        if F["door_width"] < cls.MIN_FRONT_DIMENSION - cls.RANGE_TOLERANCE_MM:
            result.add_error(
                "Calculated paired Door Width is {:.3f} mm, below the {:.1f} mm minimum. "
                "Conflict: front width {:.3f} mm and DoorSplitGap {:.3f} mm."
                .format(F["door_width"], cls.MIN_FRONT_DIMENSION, F["front_width"], float(values["DoorSplitGap"]))
            )
        for label, dim in [
            ("Middle Door Height", F["middle_door_height"]),
            ("Top Drawer Height", F["top_drawer_height"]),
            ("Middle Drawer Height", F["middle_drawer_height"]),
            ("Bottom Drawer Height", F["bottom_drawer_height"]),
        ]:
            if dim < cls.MIN_FRONT_DIMENSION - cls.RANGE_TOLERANCE_MM:
                result.add_error("{} resolves to {:.3f} mm; each manufactured front dimension must be at least {:.1f} mm.".format(label, dim, cls.MIN_FRONT_DIMENSION))
        if result.errors:
            return result
        if door_style == "Shaker":
            frame = float(values["DoorFrameWidth"])
            panel = float(values["DoorPanelThickness"])
            for label, width, height in [
                ("Upper Doors", F["door_width"], F["upper_door_height"]),
                ("Middle Doors", F["door_width"], F["middle_door_height"]),
            ]:
                if width - 2.0 * frame < cls.MIN_FRAME_OPENING - cls.RANGE_TOLERANCE_MM:
                    result.add_error("DoorFrameWidth conflicts with {} width and leaves less than a 1 in center opening.".format(label))
                if height - 2.0 * frame < cls.MIN_FRAME_OPENING - cls.RANGE_TOLERANCE_MM:
                    result.add_error("DoorFrameWidth conflicts with {} height and leaves less than a 1 in center opening.".format(label))
            if panel > front_t + cls.RANGE_TOLERANCE_MM:
                result.add_error("DoorPanelThickness ({:.3f} mm) cannot exceed FrontThickness ({:.3f} mm).".format(panel, front_t))
        if drawer_style == "Shaker":
            frame = float(values["DrawerFrameWidth"])
            panel = float(values["DrawerPanelThickness"])
            for label, height in [
                ("Top Drawer", F["top_drawer_height"]),
                ("Middle Drawer", F["middle_drawer_height"]),
                ("Bottom Drawer", F["bottom_drawer_height"]),
            ]:
                if F["front_width"] - 2.0 * frame < cls.MIN_FRAME_OPENING - cls.RANGE_TOLERANCE_MM:
                    result.add_error("DrawerFrameWidth conflicts with {} width and leaves less than a 1 in center opening.".format(label))
                if height - 2.0 * frame < cls.MIN_FRAME_OPENING - cls.RANGE_TOLERANCE_MM:
                    result.add_error("DrawerFrameWidth conflicts with {} height and leaves less than a 1 in center opening.".format(label))
            if panel > front_t + cls.RANGE_TOLERANCE_MM:
                result.add_error("DrawerPanelThickness ({:.3f} mm) cannot exceed FrontThickness ({:.3f} mm).".format(panel, front_t))
        if result.errors:
            return result
        dividers = plan["dividers"]
        interior_floor = float(dividers["interior_floor"])
        interior_top = float(dividers["interior_top"])
        interior_back = float(dividers["interior_back_y"])
        for key, label in (("lower", "Middle Compartment Divider"), ("upper", "Upper Compartment Divider")):
            d = dividers[key]
            if d["length"] <= cls.RANGE_TOLERANCE_MM or d["depth"] <= cls.RANGE_TOLERANCE_MM or d["height"] <= cls.RANGE_TOLERANCE_MM:
                result.add_error("{} resolves to a non-positive manufactured dimension.".format(label))
            if d["z"] < interior_floor - cls.RANGE_TOLERANCE_MM or d["z"] + d["height"] > interior_top + cls.RANGE_TOLERANCE_MM:
                result.add_error("{} conflicts with the carcass interior vertical limits ({:.3f}-{:.3f} mm).".format(label, interior_floor, interior_top))
            if d["y"] < -cls.RANGE_TOLERANCE_MM or d["y"] + d["depth"] > interior_back + cls.RANGE_TOLERANCE_MM:
                result.add_error("{} conflicts with the available cabinet depth after the selected front mount/setback.".format(label))
        box_wall = float(values["DrawerBoxWallThickness"])
        for key in ("top", "middle", "bottom"):
            box = plan["boxes"][key]
            label = box["label"]
            if box["width"] <= 2.0 * box_wall + cls.RANGE_TOLERANCE_MM:
                result.add_error("{} conflicts with CabinetWidth/CabinetThickness/DrawerSideClearance and leaves no usable cavity width.".format(label))
            if box["height"] <= box_wall + cls.RANGE_TOLERANCE_MM:
                result.add_error("{} conflicts with its front zone, dividers, or DrawerVerticalClearance and leaves no usable cavity height.".format(label))
            if box["rear_y"] > interior_back + cls.RANGE_TOLERANCE_MM:
                result.add_error(
                    "{} rear edge {:.3f} mm exceeds the inside back-panel plane {:.3f} mm. "
                    "Reduce DrawerBoxDepth or the selected inset depth."
                    .format(label, box["rear_y"], interior_back)
                )
            if box["z"] < interior_floor - cls.RANGE_TOLERANCE_MM or box["top_z"] > interior_top + cls.RANGE_TOLERANCE_MM:
                result.add_error("{} conflicts with the carcass interior vertical limits.".format(label))
        shelf_plan = plan["shelves"]
        if shelf_count > 0:
            if shelf_plan["usable_height"] <= cls.RANGE_TOLERANCE_MM:
                result.add_error("Upper shelf region conflicts with the Upper Compartment Divider and top carcass panel; no usable shelf height remains.")
            if float(values["ShelfThickness"]) >= shelf_plan["pitch"] - cls.RANGE_TOLERANCE_MM:
                result.add_error(
                    "ShelfThickness {:.3f} mm conflicts with UpperShelfCount {}: available shelf pitch is only {:.3f} mm."
                    .format(float(values["ShelfThickness"]), shelf_count, shelf_plan["pitch"])
                )
            for shelf in shelf_plan["shelves"]:
                if shelf["rear_y"] > interior_back + cls.RANGE_TOLERANCE_MM:
                    result.add_error(
                        "ShelfDepth conflicts with the selected front mount/setback: Upper Shelf {} rear edge {:.3f} mm exceeds inside back-panel plane {:.3f} mm."
                        .format(shelf["index"], shelf["rear_y"], interior_back)
                    )
                if shelf["z"] < shelf_plan["lower_z"] - cls.RANGE_TOLERANCE_MM or shelf["top_z"] > shelf_plan["upper_z"] + cls.RANGE_TOLERANCE_MM:
                    result.add_error("Upper Shelf {} conflicts with the upper compartment vertical limits.".format(shelf["index"]))
        if W > 914.4:
            result.add_warning("CabinetWidth exceeds 36 in; verify shelf span, door hardware and installation support.")
        if D > 609.6:
            result.add_warning("CabinetDepth exceeds 24 in; verify access, drawer-slide reach and installation clearance.")
        if H > 2438.4:
            result.add_warning("CabinetHeight exceeds 96 in; verify ceiling clearance, anti-tip anchoring and installation method.")
        if T < 12.7:
            result.add_warning("CabinetThickness is below 1/2 in; verify structural capacity and joinery.")
        if front_t < cls.NORMAL_HINGE_FRONT_MIN or front_t > cls.NORMAL_HINGE_FRONT_MAX:
            result.add_warning("FrontThickness is outside the common 15-24 mm concealed-hinge range; verify selected hardware.")
        if mount == "Overlay" and float(values["FrontProud"]) > 6.35:
            result.add_warning("FrontProud exceeds 1/4 in; verify the intended front projection.")
        if F["upper_door_height"] > 1219.2:
            result.add_warning("Calculated Upper Door Height exceeds 48 in; verify hinge count, door stiffness and material stability.")
        if F["door_width"] > 609.6:
            result.add_warning("Calculated paired door width exceeds 24 in; verify hinge loading and door stability.")
        if shelf_count >= 5:
            result.add_warning("UpperShelfCount is {}. Verify practical vertical clearance between shelves.".format(shelf_count))
        if float(values["DrawerBoxDepth"]) > 558.8:
            result.add_warning("DrawerBoxDepth exceeds 22 in; verify selected slide length and cabinet clearance.")
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
PARAMETER_SCHEMA = apply_schema_overrides(PARAMETER_SCHEMA, {'CabinetWidth': {'group': 'Cabinet'}, 'CabinetDepth': {'group': 'Cabinet'}, 'CabinetHeight': {'group': 'Cabinet'}, 'CabinetThickness': {'group': 'Cabinet'}, 'RabbetDepth': {'group': 'Cabinet'}, 'ToeKickHeight': {'group': 'Toe Kick'}, 'ToeKickSetback': {'group': 'Toe Kick'}, 'FrontThickness': {'group': 'Front Layout'}, 'FrontProud': {'group': 'Front Layout', 'active_when': (('FrontMount', 'Overlay'),)}, 'InsetSetback': {'group': 'Front Layout', 'active_when': (('FrontMount', 'Inset'),)}, 'DoorSplitGap': {'group': 'Front Layout'}, 'VerticalFrontGap': {'group': 'Front Layout'}, 'MiddleDoorHeight': {'group': 'Front Layout'}, 'TopDrawerHeight': {'group': 'Front Layout'}, 'MiddleDrawerHeight': {'group': 'Front Layout'}, 'BottomDrawerHeight': {'group': 'Front Layout'}, 'FrontMount': {'group': 'Front Layout'}, 'DoorStyle': {'group': 'Front Construction'}, 'DoorFrameWidth': {'group': 'Front Construction', 'active_when': (('DoorStyle', 'Shaker'),)}, 'DoorPanelThickness': {'group': 'Front Construction', 'active_when': (('DoorStyle', 'Shaker'),)}, 'DrawerStyle': {'group': 'Front Construction'}, 'DrawerFrameWidth': {'group': 'Front Construction', 'active_when': (('DrawerStyle', 'Shaker'),)}, 'DrawerPanelThickness': {'group': 'Front Construction', 'active_when': (('DrawerStyle', 'Shaker'),)}, 'ShelfDepth': {'group': 'Upper Interior', 'active_when': (('UpperShelfCount', '>', 0),)}, 'ShelfThickness': {'group': 'Upper Interior', 'active_when': (('UpperShelfCount', '>', 0),)}, 'UpperShelfCount': {'group': 'Upper Interior', 'minimum': 0, 'maximum': 6, 'label': 'Upper Shelf Count'}, 'DrawerBoxDepth': {'group': 'Drawer Boxes'}, 'DrawerBoxWallThickness': {'group': 'Drawer Boxes'}, 'DrawerSideClearance': {'group': 'Drawer Boxes'}, 'DrawerVerticalClearance': {'group': 'Drawer Boxes'}})
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
    resolved = ResolvedTallPantryLayout.calculate(values)
    return "Calculated Upper Door Height: {:.3f} mm ({:.3f} in)".format(resolved.front["upper_door_height"], resolved.front["upper_door_height"] / 25.4)
class TallPantryDialog(SchemaCabinetDialog):
    def __init__(self, sheet):
        super().__init__(sheet, PARAMETER_SCHEMA, title='Tall Pantry Utility Cabinet Parameters', validator=TallPantryValidator.validate, notes=('CabinetHeight is limited to 60-120 in. Bottom, middle and top drawer heights plus MiddleDoorHeight are direct controls; UpperDoorHeight is derived from the remaining height. Conflicting fixed zones are rejected rather than clamped.',), derived_preview=_cabinet_derived_preview)

class TallPantryFP:
    def __init__(self, obj, assembly, sheet):
        self._building = True
        self._last_signature = None
        self._warning_signature = None
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
    def onDocumentRestored(self, obj):
        obj.Proxy = self
        self._building = False
        self._warning_signature = None
        self._last_signature = None
    def _validate_values(self, values, report_warnings=False):
        result = TallPantryValidator.validate(values)
        result.raise_for_errors()
        signature = tuple(result.warnings)
        if report_warnings and signature and signature != self._warning_signature:
            App.Console.PrintWarning("Tall pantry parameter warning(s):\\n{}\\n".format(result.warning_text()))
        self._warning_signature = signature
        return result
    def _create_geometry(self, obj, assembly, sheet):
        doc = obj.Document
        prefix = assembly.Name
        values = read_parameter_values(sheet)
        self._validate_values(values)
        plan = ResolvedTallPantryLayout.calculate(values)
        origin_point = Draft.make_point(X=0.0, Y=0.0, Z=0.0, name="{}_OriginPoint".format(prefix), point_size=8)
        origin_point.Label = "Assembly Origin Point"
        try:
            origin_point.ViewObject.Visibility = True
        except Exception:
            pass
        carcass = CabinetCarcass.create(doc, prefix)
        toe = ToeKick.create(doc, prefix)
        upper_divider = doc.addObject("Part::Box", "{}_UpperDivider".format(prefix))
        upper_divider.Label = "Upper Compartment Divider"
        lower_divider = doc.addObject("Part::Box", "{}_LowerDivider".format(prefix))
        lower_divider.Label = "Middle Compartment Divider"
        self._update_carcass(carcass, values)
        toe.update(values["CabinetWidth"], values["CabinetDepth"], values["ToeKickHeight"], values["ToeKickSetback"])
        self._update_dividers(upper_divider, lower_divider, plan)
        assembly.addObject(sheet)
        assembly.addObject(origin_point)
        for body in carcass.bodies():
            assembly.addObject(body)
        assembly.addObject(toe.box)
        assembly.addObject(upper_divider)
        assembly.addObject(lower_divider)
        doc.recompute()
        door_components = [
            CabinetFront.create(doc, prefix, "UpperDoorLeft", "Upper Door Left", values["DoorStyle"]),
            CabinetFront.create(doc, prefix, "UpperDoorRight", "Upper Door Right", values["DoorStyle"]),
            CabinetFront.create(doc, prefix, "MiddleDoorLeft", "Middle Door Left", values["DoorStyle"]),
            CabinetFront.create(doc, prefix, "MiddleDoorRight", "Middle Door Right", values["DoorStyle"]),
        ]
        drawer_fronts = [
            CabinetFront.create(doc, prefix, "DrawerFrontTop", "Drawer Front Top", values["DrawerStyle"]),
            CabinetFront.create(doc, prefix, "DrawerFrontMiddle", "Drawer Front Middle", values["DrawerStyle"]),
            CabinetFront.create(doc, prefix, "DrawerFrontBottom", "Drawer Front Bottom", values["DrawerStyle"]),
        ]
        drawer_boxes = [
            CabinetDrawerBox.create(doc, prefix, "DrawerBoxTop", "Drawer Box Top"),
            CabinetDrawerBox.create(doc, prefix, "DrawerBoxMiddle", "Drawer Box Middle"),
            CabinetDrawerBox.create(doc, prefix, "DrawerBoxBottom", "Drawer Box Bottom"),
        ]
        shelves = []
        for index in range(SHELF_MAX):
            shelf = doc.addObject("Part::Box", "{}_UpperShelf{}".format(prefix, index + 1))
            shelf.Label = "Upper Shelf {}".format(index + 1)
            shelves.append(shelf)
        self._update_fronts(
            [(c.body, c.feature) for c in door_components],
            [(c.body, c.feature) for c in drawer_fronts],
            values, plan
        )
        self._update_drawer_boxes([b.feature for b in drawer_boxes], plan)
        self._update_shelves(shelves, values, plan)
        for component in door_components + drawer_fronts:
            assembly.addObject(component.body)
        for box in drawer_boxes:
            assembly.addObject(box.feature)
        for shelf in shelves:
            assembly.addObject(shelf)
        assembly.addObject(obj)
        required = [sheet, origin_point] + carcass.bodies() + [toe.box, upper_divider, lower_divider, obj]
        required += [c.body for c in door_components + drawer_fronts]
        required += [b.feature for b in drawer_boxes] + shelves
        missing = [member.Name for member in required if member not in assembly.Group]
        if missing:
            raise RuntimeError("FreeCAD did not place all tall-pantry members inside '{}'. Missing: {}".format(assembly.Name, ", ".join(missing)))
        try:
            toe.box.ViewObject.ShapeColor = (0.25, 0.25, 0.25)
            upper_divider.ViewObject.ShapeColor = (0.72, 0.72, 0.72)
            lower_divider.ViewObject.ShapeColor = (0.72, 0.72, 0.72)
            for box in drawer_boxes:
                box.feature.ViewObject.ShapeColor = (0.72, 0.55, 0.35)
            for shelf in shelves:
                shelf.ViewObject.ShapeColor = (0.72, 0.55, 0.35)
        except Exception:
            pass
        for front in door_components + drawer_fronts:
            front.set_visible(True)
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
        raise RuntimeError("Tall Pantry Utility Controller cannot resolve its owning App::Part.")
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
        carcass = CabinetCarcass.from_document(doc, prefix)
        toe_obj = doc.getObject("{}_ToeKickRiser".format(prefix))
        upper_divider = doc.getObject("{}_UpperDivider".format(prefix))
        lower_divider = doc.getObject("{}_LowerDivider".format(prefix))
        if toe_obj is None or upper_divider is None or lower_divider is None:
            raise RuntimeError("Tall pantry toe-kick/divider geometry is incomplete.")
        front_names = [
            "UpperDoorLeft", "UpperDoorRight", "MiddleDoorLeft", "MiddleDoorRight",
            "DrawerFrontTop", "DrawerFrontMiddle", "DrawerFrontBottom"
        ]
        fronts = []
        for name in front_names:
            body = doc.getObject("{}_{}".format(prefix, name))
            shape = doc.getObject("{}_{}Shape".format(prefix, name))
            if body is None or shape is None:
                raise RuntimeError("Tall pantry front '{}_{}' is incomplete.".format(prefix, name))
            fronts.append((body, shape))
        boxes = []
        for name in ("DrawerBoxTop", "DrawerBoxMiddle", "DrawerBoxBottom"):
            feature = doc.getObject("{}_{}".format(prefix, name))
            if feature is None:
                raise RuntimeError("Tall pantry drawer box '{}_{}' was not found.".format(prefix, name))
            boxes.append(feature)
        shelves = []
        for index in range(SHELF_MAX):
            shelf = doc.getObject("{}_UpperShelf{}".format(prefix, index + 1))
            if shelf is None:
                raise RuntimeError("Upper Shelf {} not found for '{}'.".format(index + 1, assembly.Name))
            shelves.append(shelf)
        return {
            "carcass": carcass,
            "toe": ToeKick.from_existing(toe_obj),
            "upper_divider": upper_divider,
            "lower_divider": lower_divider,
            "door_fronts": fronts[:4],
            "drawer_fronts": fronts[4:],
            "boxes": boxes,
            "shelves": shelves,
        }
    def _update_carcass(self, carcass, values):
        carcass.update(
            values["CabinetWidth"], values["CabinetDepth"],
            values["CabinetHeight"] - values["ToeKickHeight"],
            values["CabinetThickness"], values["RabbetDepth"],
            base_z=values["ToeKickHeight"]
        )
    @staticmethod
    def _apply_box(box, spec):
        if min(spec["length"], spec["depth"], spec["height"]) <= 0:
            raise RuntimeError("{} resolves to a non-positive dimension.".format(box.Label))
        box.Length = spec["length"]
        box.Width = spec["depth"]
        box.Height = spec["height"]
        box.Placement = App.Placement(App.Vector(spec["x"], spec["y"], spec["z"]), App.Rotation())
    def _update_dividers(self, upper_divider, lower_divider, plan):
        self._apply_box(lower_divider, plan["dividers"]["lower"])
        self._apply_box(upper_divider, plan["dividers"]["upper"])
    def _update_fronts(self, door_objects, drawer_objects, values, plan):
        F = plan["front"]
        split = values["DoorSplitGap"]
        door_specs = [
            (F["door_width"], F["upper_door_height"], F["front_x"], F["upper_door_z"]),
            (F["door_width"], F["upper_door_height"], F["front_x"] + F["door_width"] + split, F["upper_door_z"]),
            (F["door_width"], F["middle_door_height"], F["front_x"], F["middle_door_z"]),
            (F["door_width"], F["middle_door_height"], F["front_x"] + F["door_width"] + split, F["middle_door_z"]),
        ]
        for (body, feature), (width, height, x, z) in zip(door_objects, door_specs):
            CabinetFront.from_existing(body, feature, values["DoorStyle"]).update(
                width=width, height=height, thickness=values["FrontThickness"],
                frame_width=values["DoorFrameWidth"], panel_thickness=values["DoorPanelThickness"],
                x=x, z=z, back_y=F["front_back_y"]
            )
        drawer_specs = [
            (F["top_drawer_height"], F["top_drawer_z"]),
            (F["middle_drawer_height"], F["middle_drawer_z"]),
            (F["bottom_drawer_height"], F["bottom_drawer_z"]),
        ]
        for (body, feature), (height, z) in zip(drawer_objects, drawer_specs):
            CabinetFront.from_existing(body, feature, values["DrawerStyle"]).update(
                width=F["front_width"], height=height, thickness=values["FrontThickness"],
                frame_width=values["DrawerFrameWidth"], panel_thickness=values["DrawerPanelThickness"],
                x=F["front_x"], z=z, back_y=F["front_back_y"]
            )
    def _update_drawer_boxes(self, features, plan):
        for feature, key in zip(features, ("top", "middle", "bottom")):
            spec = plan["boxes"][key]
            CabinetDrawerBox.from_existing(feature).update(
                width=spec["width"], depth=spec["depth"], height=spec["height"], wall=spec["wall"],
                x=spec["x"], y=spec["y"], z=spec["z"]
            )
    def _update_shelves(self, shelves, values, plan):
        shelf_specs = plan["shelves"]["shelves"]
        T = values["CabinetThickness"]
        hidden_z = plan["shelves"]["lower_z"]
        for index, shelf in enumerate(shelves):
            shelf.Length = values["CabinetWidth"] - 2.0 * T
            shelf.Width = values["ShelfDepth"]
            shelf.Height = values["ShelfThickness"]
            if index < len(shelf_specs):
                spec = shelf_specs[index]
                shelf.Placement = App.Placement(App.Vector(spec["x"], spec["y"], spec["z"]), App.Rotation())
                try:
                    shelf.ViewObject.Visibility = True
                except Exception:
                    pass
            else:
                shelf.Placement = App.Placement(App.Vector(T, plan["front"]["internal_front_y"], hidden_z), App.Rotation())
                try:
                    shelf.ViewObject.Visibility = False
                except Exception:
                    pass
    def execute(self, obj):
        if getattr(self, "_building", False):
            return
        assembly = self._assembly(obj)
        sheet = self._parameters(obj, assembly)
        values = read_parameter_values(sheet)
        self._validate_values(values, report_warnings=True)
        signature = normalized_signature(values)
        if signature == self._last_signature:
            return
        self._last_signature = signature
        plan = ResolvedTallPantryLayout.calculate(values)
        g = self._geometry(assembly)
        self._update_carcass(g["carcass"], values)
        g["toe"].update(values["CabinetWidth"], values["CabinetDepth"], values["ToeKickHeight"], values["ToeKickSetback"])
        self._update_dividers(g["upper_divider"], g["lower_divider"], plan)
        self._update_fronts(g["door_fronts"], g["drawer_fronts"], values, plan)
        self._update_drawer_boxes(g["boxes"], plan)
        self._update_shelves(g["shelves"], values, plan)

def validate_values(values):
    result = TallPantryValidator.validate(values)
    return result.valid, result.error_text()


def _sanitize_object_name(name):
    return sanitize_object_name(name, INSTANCE_BASENAME)

def next_tall_pantry_utility_name(document):
    return next_instance_name(document, INSTANCE_BASENAME)

class TallPantryBuilder:
    def __init__(self, document, instance_name):
        if document is None:
            raise ValueError("create_tall_pantry_utility() requires an existing FreeCAD document.")
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
                self._rollback_new_objects()
                return None
            self._begin_insertion_point()
            return self
        except Exception:
            self._rollback_new_objects()
            raise
    def _collect_parameters(self):
        dialog = TallPantryDialog(self.parameters)
        if not dialog.exec():
            print("Tall pantry creation cancelled. The active layout document was not changed.")
            return False
        self.values = dialog.values()
        result = TallPantryValidator.validate(self.values)
        if result.errors:
            QtWidgets.QMessageBox.critical(None, "Invalid Tall Pantry Parameters", result.error_text())
            return False
        ParameterTable.update(self.document, self.parameters, self.values)
        ParameterTable.verify(self.parameters)
        return True
    def _begin_insertion_point(self):
        self._picker = EndpointSnapPointPicker(on_accept=self._insertion_point_accepted, on_cancel=self._insertion_point_cancelled)
        self._picker.begin()
    def _insertion_point_accepted(self, point):
        self.insertion_point = App.Vector(point)
        self._picker = None
        print("Insertion point: X={:.3f}, Y={:.3f}, Z={:.3f} mm".format(self.insertion_point.x, self.insertion_point.y, self.insertion_point.z))
        try:
            self._create_component()
            self.document.recompute()
            self._show_component()
            self._print_report()
            self._transaction.commit()
        except Exception as exc:
            self._rollback_new_objects()
            QtWidgets.QMessageBox.critical(None, "Tall Pantry Creation Error", str(exc))
            App.Console.PrintError("Tall pantry creation failed: {}\\n".format(exc))
    def _insertion_point_cancelled(self):
        self._picker = None
        self._rollback_new_objects()
        print("Tall pantry insertion cancelled. The active layout document was not changed.")
    def _create_component(self):
        self.assembly = self.document.addObject("App::Part", self.instance_name)
        self.assembly.Label = "Tall Pantry Utility Cabinet"
        if self.insertion_point is not None:
            self.assembly.Placement.Base = App.Vector(self.insertion_point)
        self.controller = self.document.addObject("Part::FeaturePython", "{}_Controller".format(self.instance_name))
        self.controller.Label = "Tall Pantry Utility Controller"
        TallPantryFP(self.controller, self.assembly, self.parameters)
    def _rollback_new_objects(self):
        self._transaction.rollback()
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
        print("=" * 72)
        print("PARAMETRIC TALL PANTRY UTILITY CABINET")
        print("FREECAD 1.1.4 - REVISION 0.15 VALIDATED/RESOLVED-LAYOUT")
        print("Target document: {}".format(self.document.Name))
        print("Instance name:   {}".format(self.instance_name))
        print("=" * 72)
    def _print_report(self):
        values = read_parameter_values(self.parameters)
        plan = ResolvedTallPantryLayout.calculate(values)
        result = TallPantryValidator.validate(values)
        result.raise_for_errors()
        F = plan["front"]
        print("")
        print("-" * 72)
        print("TALL PANTRY INSTANCE CREATED SUCCESSFULLY")
        print("-" * 72)
        print("Pantry instance:             ", self.assembly.Name)
        print("Parameters sheet:            ", self.parameters.Name)
        print("Front mount:                 ", values["FrontMount"])
        print("Door style:                  ", values["DoorStyle"])
        print("Drawer style:                ", values["DrawerStyle"])
        print("Cabinet Height:              {:.3f} mm".format(values["CabinetHeight"]))
        print("Upper Shelves:               ", values["UpperShelfCount"])
        print("Calculated Upper Door Height:{:.3f} mm".format(F["upper_door_height"]))
        print("Paired Door Width:           {:.3f} mm".format(F["door_width"]))
        print("Bottom Drawer Height:        {:.3f} mm".format(F["bottom_drawer_height"]))
        print("Visible Front Y:             {:.3f} mm".format(F["visible_front_y"]))
        if self.insertion_point is not None:
            print("Insertion Point:             X={:.3f}, Y={:.3f}, Z={:.3f} mm".format(
                self.insertion_point.x, self.insertion_point.y, self.insertion_point.z
            ))
        if result.warnings:
            print("Warnings:")
            for warning in result.warnings:
                print("  - {}".format(warning))
        print("")
        print("Edit '{}' to resize only this pantry.".format(self.parameters.Name))
        print("Move/rotate '{}' with its App::Part Placement.".format(self.assembly.Name))
        print("=" * 72)
        print("")

def create_tall_pantry_utility(document, instance_name):
    builder = TallPantryBuilder(document=document, instance_name=instance_name)
    return builder.run()

def main():
    document = App.ActiveDocument
    if document is None:
        QtWidgets.QMessageBox.warning(
            None, "No Active FreeCAD Document",
            "Open or create the kitchen/layout document first, then run this macro again."
        )
        return None
    instance_name = next_tall_pantry_utility_name(document)
    return create_tall_pantry_utility(document=document, instance_name=instance_name)

# ============================================================
# WORKBENCH MODULE NOTE
# ============================================================
# Do not call main() automatically here.
# CabinetsWorkbench.py imports this module, calls main(), and retains the
# returned TallPantryBuilder while endpoint selection is active.

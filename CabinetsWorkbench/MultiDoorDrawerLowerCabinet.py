# ============================================================
# PARAMETRIC LOWER MULTI-DRAWER / MIXED-FRONT BASE CABINET
# FIVE-PART RABBETED CARCASS + FUNCTIONAL DRAWER BOXES
# ============================================================
# Target: FreeCAD 1.1.4
# REVISION: 0.15
#   0.15 - Cabinet Core v1 architecture revision
#          - shared validation, parameter, component, runtime and snap infrastructure
#          - cabinet-specific layout/geometry relationships preserved
#          - no intentional default geometry change from previous validated revision
#
# 0.12 - Supplied baseline
#        - image-derived 30 in W x 21 in D x 34.5 in H default envelope
#        - full-width top drawer front
#        - lower-left door
#        - upper/lower right drawer fronts and three functional drawer boxes
#        - top horizontal divider and lower vertical divider
#        - Slab/Shaker door and drawer styles
#        - Overlay/Inset shared front mounting
#        - centralized MixedFrontLayout
#        - endpoint select-to-insert using FreeCAD's shared Draft Snapper
#
# 0.13 - Cabinet-family refactor / validation standard
#        - converts hollow carcass to five manufactured rabbeted parts
#        - BoxWallThickness standardized to CabinetThickness
#        - adds RabbetDepth using the proven lower-cabinet carcass model
#        - FrontOffset renamed FrontProud because it controls outward Y projection
#        - strict quantity parsing; invalid text is never silently replaced
#        - exact min/max limits are inclusive with 1e-6 mm tolerance
#        - errors and non-blocking engineering warnings are separated
#        - spreadsheet adds Options and Allowed Range columns
#        - dialog disables fields that do not apply to current style/mount
#        - one CabinetFront class handles both doors and drawer fronts
#        - front-grid and drawer-box layouts are validated independently
#        - preserves the derived left-door/right-column resizing contract
#        - preserves three functional drawer boxes, both dividers and toe kick
#        - preserves canonical endpoint snap behavior and assembly grouping
#
# 0.14 - Resolved-layout / recompute-hardening revision
#        - adds DividerLayout as the single authority for both internal dividers
#        - adds ResolvedCabinetLayout so fronts, drawer boxes and dividers resolve together
#        - validates divider bounds and drawer-box rear clearance from resolved coordinates
#        - adds defensive geometry checks inside CabinetFront and CabinetDrawerBox
#        - creation, recompute and reporting now consume the same resolved layout plan
#        - preserves all Rev0.13 dimensions, front proportions, drawer boxes and snap behavior
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
from AdvCabinetParameters import SheetParams, qty_mm, ParameterTable as CoreParameterTable, schema_from_legacy, apply_schema_overrides
from AdvCabinetComponents import CabinetPanel, RabbetedSidePanel, CabinetCarcass, ToeKick, CabinetFront, CabinetDrawerBox
from AdvCabinetSnap import EndpointSnapPointPicker
from AdvCabinetDialog import SchemaCabinetDialog
from AdvCabinetLayouts import ResolvedLayout
from AdvCabinetRuntime import CabinetCreationTransaction, sanitize_object_name, next_instance_name, normalized_signature
SHEET_NAME = "Parameters"
INSTANCE_BASENAME = "VanityBaseCabinet"
CABINET_CORE_VERSION = 1
CABINET_SCHEMA_VERSION = 2
CABINET_TYPE = "MultiDoorDrawerLowerCabinet"
GENERATOR_REVISION = "0.15"

FRONT_STYLES = ("Slab", "Shaker")
FRONT_MOUNTS = ("Inset", "Overlay")
TEXT_PARAMETERS = {"DoorStyle", "DrawerStyle", "FrontMount"}
PARAMETER_OPTIONS = {
    "DoorStyle": "Slab | Shaker",
    "DrawerStyle": "Slab | Shaker",
    "FrontMount": "Inset | Overlay",
    "FrontProud": "Applies to Overlay fronts",
    "FrontSideReveal": "Applies to Overlay fronts",
    "InsetSetback": "Applies to Inset fronts",
    "DoorFrameWidth": "Applies to Shaker door",
    "DoorPanelThickness": "Applies to Shaker door",
    "DrawerFrameWidth": "Applies to Shaker drawer fronts",
    "DrawerPanelThickness": "Applies to Shaker drawer fronts",
    "RightColumnWidth": "Direct control; Left Door Width is derived",
    "UpperRightDrawerHeight": "Direct control; Lower Right Drawer Height is derived",
}
PARAM_DEFAULTS = [
    ("CabinetWidth", "762 mm"),
    ("CabinetDepth", "533.4 mm"),
    ("CabinetHeight", "876.3 mm"),
    ("CabinetThickness", "19.05 mm"),
    ("RabbetDepth", "6.35 mm"),
    ("ToeKickHeight", "88.9 mm"),
    ("ToeKickSetback", "88.9 mm"),
    ("FrontThickness", "19.05 mm"),
    ("FrontProud", "3 mm"),
    ("InsetSetback", "0 mm"),
    ("FrontSideReveal", "11.2 mm"),
    ("ColumnGap", "3 mm"),
    ("TopLowerGap", "3 mm"),
    ("RightDrawerGap", "3 mm"),
    ("RightColumnWidth", "292.1 mm"),
    ("TopDrawerHeight", "158.75 mm"),
    ("UpperRightDrawerHeight", "292.1 mm"),
    ("DoorStyle", "Shaker"),
    ("DoorFrameWidth", "50.8 mm"),
    ("DoorPanelThickness", "6 mm"),
    ("DrawerStyle", "Shaker"),
    ("DrawerFrameWidth", "50.8 mm"),
    ("DrawerPanelThickness", "6 mm"),
    ("FrontMount", "Overlay"),
    ("DrawerBoxDepth", "457.2 mm"),
    ("DrawerBoxWallThickness", "12.7 mm"),
    ("DrawerSideClearance", "6 mm"),
    ("DrawerVerticalClearance", "3 mm"),
]
PARAM_DEFAULT_MAP = dict(PARAM_DEFAULTS)
LEGACY_PARAMETER_ALIASES = {
    "CabinetThickness": ("BoxWallThickness",),
    "FrontProud": ("FrontOffset",),
}
DIMENSION_PARAMETERS = {name for name, default in PARAM_DEFAULTS if str(default).strip().lower().endswith("mm")}


PARAMETER_SPECS = {
    "CabinetWidth": ParameterSpec("CabinetWidth", 304.8, 1219.2, "Cabinet Width"),
    "CabinetDepth": ParameterSpec("CabinetDepth", 304.8, 1219.2, "Cabinet Depth"),
    "CabinetHeight": ParameterSpec("CabinetHeight", 406.4, 3657.6, "Cabinet Height"),
    "CabinetThickness": ParameterSpec("CabinetThickness", 6.35, 25.4, "Cabinet Thickness"),
    "RabbetDepth": ParameterSpec("RabbetDepth", 1.5875, 12.7, "Rabbet Depth"),
    "ToeKickHeight": ParameterSpec("ToeKickHeight", 76.2, 152.4, "Toe Kick Height"),
    "ToeKickSetback": ParameterSpec("ToeKickSetback", 50.8, 152.4, "Toe Kick Setback"),
    "FrontThickness": ParameterSpec("FrontThickness", 12.7, 31.75, "Front Thickness"),
    "FrontProud": ParameterSpec("FrontProud", 0.0, 12.7, "Front Proud"),
    "InsetSetback": ParameterSpec("InsetSetback", 0.0, 25.4, "Inset Setback"),
    "FrontSideReveal": ParameterSpec("FrontSideReveal", 0.0, 50.8, "Front Side Reveal"),
    "ColumnGap": ParameterSpec("ColumnGap", 1.0, 12.7, "Column Gap"),
    "TopLowerGap": ParameterSpec("TopLowerGap", 1.0, 12.7, "Top/Lower Gap"),
    "RightDrawerGap": ParameterSpec("RightDrawerGap", 1.0, 12.7, "Right Drawer Gap"),
    "RightColumnWidth": ParameterSpec("RightColumnWidth", 152.4, 609.6, "Right Column Width"),
    "TopDrawerHeight": ParameterSpec("TopDrawerHeight", 76.2, 304.8, "Top Drawer Height"),
    "UpperRightDrawerHeight": ParameterSpec("UpperRightDrawerHeight", 76.2, 609.6, "Upper Right Drawer Height"),
    "DoorFrameWidth": ParameterSpec("DoorFrameWidth", 25.4, 101.6, "Door Frame Width"),
    "DoorPanelThickness": ParameterSpec("DoorPanelThickness", 3.0, 19.0, "Door Panel Thickness"),
    "DrawerFrameWidth": ParameterSpec("DrawerFrameWidth", 25.4, 101.6, "Drawer Frame Width"),
    "DrawerPanelThickness": ParameterSpec("DrawerPanelThickness", 3.0, 19.0, "Drawer Panel Thickness"),
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
        else:
            values[name] = qty_mm(raw, None, name)
    return values








class MixedFrontLayout:
    MOUNT_OVERLAY = "Overlay"
    MOUNT_INSET = "Inset"
    @classmethod
    def calculate(cls, values):
        W = float(values["CabinetWidth"])
        H = float(values["CabinetHeight"])
        wall = float(values["CabinetThickness"])
        reveal = float(values["FrontSideReveal"])
        column_gap = float(values["ColumnGap"])
        top_gap = float(values["TopLowerGap"])
        right_gap = float(values["RightDrawerGap"])
        right_w = float(values["RightColumnWidth"])
        top_h = float(values["TopDrawerHeight"])
        upper_right_h = float(values["UpperRightDrawerHeight"])
        toe_h = float(values["ToeKickHeight"])
        mount = str(values["FrontMount"])
        front_t = float(values["FrontThickness"])
        inset = float(values["InsetSetback"])
        proud = float(values["FrontProud"])
        if mount == cls.MOUNT_OVERLAY:
            front_width = W - 2.0 * reveal
            front_x = reveal
            front_bottom_z = toe_h
            front_top_z = H
            front_back_y = -proud
            internal_front_y = 0.0
        elif mount == cls.MOUNT_INSET:
            front_width = W - 2.0 * wall
            front_x = wall
            front_bottom_z = toe_h + wall
            front_top_z = H - wall
            front_back_y = front_t + inset
            internal_front_y = front_back_y
        else:
            raise RuntimeError("FrontMount must be Inset or Overlay.")
        left_w = front_width - column_gap - right_w
        top_z = front_top_z - top_h
        lower_top = top_z - top_gap
        lower_h = lower_top - front_bottom_z
        lower_right_h = lower_h - upper_right_h - right_gap
        left_x = front_x
        right_x = left_x + left_w + column_gap
        lower_right_z = front_bottom_z
        upper_right_z = lower_right_z + lower_right_h + right_gap
        partition_center_x = left_x + left_w + column_gap / 2.0
        return {
            "front_width": front_width,
            "left_door_width": left_w,
            "right_column_width": right_w,
            "top_drawer_x": front_x,
            "top_drawer_z": top_z,
            "top_drawer_height": top_h,
            "left_door_x": left_x,
            "left_door_z": front_bottom_z,
            "left_door_height": lower_h,
            "right_x": right_x,
            "upper_right_z": upper_right_z,
            "upper_right_height": upper_right_h,
            "lower_right_z": lower_right_z,
            "lower_right_height": lower_right_h,
            "lower_top": lower_top,
            "partition_center_x": partition_center_x,
            "front_back_y": front_back_y,
            "internal_front_y": internal_front_y,
            "front_bottom_z": front_bottom_z,
            "front_top_z": front_top_z,
            "visible_front_y": front_back_y - front_t,
            "carcass_height": H - toe_h,
        }

class DrawerBoxLayout:
    @staticmethod
    def calculate(values, front_layout):
        wall = float(values["CabinetThickness"])
        side = float(values["DrawerSideClearance"])
        vertical = float(values["DrawerVerticalClearance"])
        W = float(values["CabinetWidth"])
        H = float(values["CabinetHeight"])
        toe_h = float(values["ToeKickHeight"])
        front_y = float(front_layout["internal_front_y"])
        partition_right = float(front_layout["partition_center_x"]) + wall / 2.0
        interior_right = W - wall
        top_box_x = wall + side
        top_box_w = W - 2.0 * wall - 2.0 * side
        right_box_x = partition_right + side
        right_box_w = interior_right - side - right_box_x
        top_box_z = float(front_layout["top_drawer_z"]) + vertical
        top_box_top = H - wall - vertical
        top_box_h = top_box_top - top_box_z
        lower_interior_floor = toe_h + wall
        lower_box_z = max(float(front_layout["lower_right_z"]) + vertical, lower_interior_floor + vertical)
        lower_box_top = float(front_layout["lower_right_z"]) + float(front_layout["lower_right_height"]) - vertical
        lower_box_h = lower_box_top - lower_box_z
        upper_box_z = float(front_layout["upper_right_z"]) + vertical
        upper_box_top = min(
            float(front_layout["upper_right_z"]) + float(front_layout["upper_right_height"]) - vertical,
            float(front_layout["lower_top"]) - vertical,
        )
        upper_box_h = upper_box_top - upper_box_z
        return {
            "top": {"x": top_box_x, "y": front_y, "z": top_box_z, "width": top_box_w, "height": top_box_h},
            "upper": {"x": right_box_x, "y": front_y, "z": upper_box_z, "width": right_box_w, "height": upper_box_h},
            "lower": {"x": right_box_x, "y": front_y, "z": lower_box_z, "width": right_box_w, "height": lower_box_h},
        }

class DividerLayout:
    @staticmethod
    def calculate(values, front_layout):
        wall = float(values["CabinetThickness"])
        width = float(values["CabinetWidth"])
        depth = float(values["CabinetDepth"])
        toe_h = float(values["ToeKickHeight"])
        front_y = float(front_layout["internal_front_y"])
        usable_depth = depth - wall - front_y
        partition_z = toe_h + wall
        return {
            "top": {
                "x": wall,
                "y": front_y,
                "z": float(front_layout["top_drawer_z"]) - wall,
                "length": width - 2.0 * wall,
                "depth": usable_depth,
                "height": wall,
            },
            "vertical": {
                "x": float(front_layout["partition_center_x"]) - wall / 2.0,
                "y": front_y,
                "z": partition_z,
                "length": wall,
                "depth": usable_depth,
                "height": float(front_layout["lower_top"]) - partition_z,
            },
        }

class ResolvedCabinetLayout:
    @staticmethod
    def calculate(values):
        front = MixedFrontLayout.calculate(values)
        return ResolvedLayout(
            front=front,
            drawer_boxes=DrawerBoxLayout.calculate(values, front),
            dividers=DividerLayout.calculate(values, front),
        )

class MixedFrontValidator:
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
        if mount not in FRONT_MOUNTS:
            result.add_error("FrontMount must be Inset or Overlay.")
        if door_style not in FRONT_STYLES:
            result.add_error("DoorStyle must be Slab or Shaker.")
        if drawer_style not in FRONT_STYLES:
            result.add_error("DrawerStyle must be Slab or Shaker.")
        for name in PARAMETER_SPECS:
            active = True
            if name in ("FrontProud", "FrontSideReveal"):
                active = mount == "Overlay"
            elif name == "InsetSetback":
                active = mount == "Inset"
            elif name in ("DoorFrameWidth", "DoorPanelThickness"):
                active = door_style == "Shaker"
            elif name in ("DrawerFrameWidth", "DrawerPanelThickness"):
                active = drawer_style == "Shaker"
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
            result.add_error("RabbetDepth must be less than CabinetThickness.")
        if R > 0.5 * T + cls.RANGE_TOLERANCE_MM:
            result.add_error("RabbetDepth cannot exceed 50% of CabinetThickness.")
        if toe_h >= H - 2.0 * T - cls.RANGE_TOLERANCE_MM:
            result.add_error("ToeKickHeight leaves no usable carcass interior height.")
        if toe_setback >= D - T - cls.RANGE_TOLERANCE_MM:
            result.add_error("ToeKickSetback must leave positive cabinet depth behind the toe-kick front.")
        try:
            CabinetCarcass.validate_dimensions(W, D, H - toe_h, T, R)
        except Exception as exc:
            result.add_error(str(exc))
        if mount == "Inset" and front_t + float(values["InsetSetback"]) >= D - T - cls.RANGE_TOLERANCE_MM:
            result.add_error("InsetSetback + FrontThickness leaves no usable interior depth before the cabinet back.")
        if float(values["DrawerBoxDepth"]) <= 2.0 * float(values["DrawerBoxWallThickness"]) + cls.RANGE_TOLERANCE_MM:
            result.add_error("DrawerBoxDepth must exceed twice DrawerBoxWallThickness.")
        try:
            resolved = ResolvedCabinetLayout.calculate(values)
            L = resolved["front"]
            boxes = resolved["drawer_boxes"]
            dividers = resolved["dividers"]
        except Exception as exc:
            result.add_error(str(exc))
            return result
        for label, dimension in [
            ("Front grid width", L["front_width"]),
            ("Left door width", L["left_door_width"]),
            ("Left door height", L["left_door_height"]),
            ("Top drawer height", L["top_drawer_height"]),
            ("Upper right drawer height", L["upper_right_height"]),
            ("Lower right drawer height", L["lower_right_height"]),
        ]:
            if dimension < cls.MIN_FRONT_DIMENSION - cls.RANGE_TOLERANCE_MM:
                result.add_error("{} is {:.3f} mm; each manufactured front dimension must be at least {:.1f} mm.".format(label, dimension, cls.MIN_FRONT_DIMENSION))
        if L["right_column_width"] < cls.MIN_FRONT_DIMENSION - cls.RANGE_TOLERANCE_MM:
            result.add_error("RightColumnWidth leaves no practical right drawer-front width.")
        top_divider = dividers["top"]
        vertical_divider = dividers["vertical"]
        for label, divider in (("Top Drawer Divider", top_divider), ("Lower Vertical Divider", vertical_divider)):
            if min(divider["length"], divider["depth"], divider["height"]) <= cls.RANGE_TOLERANCE_MM:
                result.add_error("{} has invalid resolved dimensions.".format(label))
            if divider["x"] < -cls.RANGE_TOLERANCE_MM or divider["y"] < -cls.RANGE_TOLERANCE_MM or divider["z"] < -cls.RANGE_TOLERANCE_MM:
                result.add_error("{} resolves outside the cabinet origin planes.".format(label))
        if vertical_divider["x"] < T - cls.RANGE_TOLERANCE_MM or vertical_divider["x"] + vertical_divider["length"] > W - T + cls.RANGE_TOLERANCE_MM:
            result.add_error("The calculated lower vertical divider falls outside the usable cabinet interior.")
        if top_divider["x"] < T - cls.RANGE_TOLERANCE_MM or top_divider["x"] + top_divider["length"] > W - T + cls.RANGE_TOLERANCE_MM:
            result.add_error("The calculated top drawer divider falls outside the usable cabinet width.")
        usable_divider_depth = top_divider["depth"]
        if usable_divider_depth <= cls.RANGE_TOLERANCE_MM:
            result.add_error("Selected front mount/setback leaves no usable divider depth.")
        drawer_depth = float(values["DrawerBoxDepth"])
        if drawer_depth > usable_divider_depth + cls.RANGE_TOLERANCE_MM:
            result.add_error("DrawerBoxDepth exceeds the usable cabinet depth for the selected front mount/setback.")
        if door_style == "Shaker":
            frame = float(values["DoorFrameWidth"])
            panel = float(values["DoorPanelThickness"])
            if L["left_door_width"] - 2.0 * frame < cls.MIN_FRAME_OPENING - cls.RANGE_TOLERANCE_MM:
                result.add_error("DoorFrameWidth leaves less than a 1 in center opening in the Left Door.")
            if L["left_door_height"] - 2.0 * frame < cls.MIN_FRAME_OPENING - cls.RANGE_TOLERANCE_MM:
                result.add_error("DoorFrameWidth leaves less than a 1 in center opening in the Left Door height.")
            if panel > front_t + cls.RANGE_TOLERANCE_MM:
                result.add_error("DoorPanelThickness cannot exceed FrontThickness.")
        if drawer_style == "Shaker":
            frame = float(values["DrawerFrameWidth"])
            panel = float(values["DrawerPanelThickness"])
            for label, width, height in [
                ("Top Drawer", L["front_width"], L["top_drawer_height"]),
                ("Upper Right Drawer", L["right_column_width"], L["upper_right_height"]),
                ("Lower Right Drawer", L["right_column_width"], L["lower_right_height"]),
            ]:
                if width - 2.0 * frame < cls.MIN_FRAME_OPENING - cls.RANGE_TOLERANCE_MM:
                    result.add_error("DrawerFrameWidth leaves less than a 1 in center opening in {} width.".format(label))
                if height - 2.0 * frame < cls.MIN_FRAME_OPENING - cls.RANGE_TOLERANCE_MM:
                    result.add_error("DrawerFrameWidth leaves less than a 1 in center opening in {} height.".format(label))
            if panel > front_t + cls.RANGE_TOLERANCE_MM:
                result.add_error("DrawerPanelThickness cannot exceed FrontThickness.")
        try:
            box_wall = float(values["DrawerBoxWallThickness"])
            box_depth = float(values["DrawerBoxDepth"])
            cabinet_back_y = D - T
            cabinet_top_z = H - T
            cabinet_floor_z = toe_h + T
            for key, label in (("top", "Top Drawer Box"), ("upper", "Upper Right Drawer Box"), ("lower", "Lower Right Drawer Box")):
                box = boxes[key]
                if box["width"] <= 2.0 * box_wall + cls.RANGE_TOLERANCE_MM:
                    result.add_error("{} has no usable width after side clearances and wall thickness.".format(label))
                if box["height"] <= box_wall + cls.RANGE_TOLERANCE_MM:
                    result.add_error("{} has no usable height after vertical clearances and wall thickness.".format(label))
                if box_depth <= 2.0 * box_wall + cls.RANGE_TOLERANCE_MM:
                    result.add_error("{} depth leaves no usable cavity.".format(label))
                if box["x"] < T - cls.RANGE_TOLERANCE_MM or box["x"] + box["width"] > W - T + cls.RANGE_TOLERANCE_MM:
                    result.add_error("{} extends outside the usable interior width.".format(label))
                if box["y"] < -cls.RANGE_TOLERANCE_MM or box["y"] + box_depth > cabinet_back_y + cls.RANGE_TOLERANCE_MM:
                    result.add_error("{} extends outside the usable interior depth.".format(label))
                if box["z"] < cabinet_floor_z - cls.RANGE_TOLERANCE_MM or box["z"] + box["height"] > cabinet_top_z + cls.RANGE_TOLERANCE_MM:
                    result.add_error("{} extends outside the usable interior height.".format(label))
        except Exception as exc:
            result.add_error(str(exc))
        if W > 914.4:
            result.add_warning("CabinetWidth exceeds 36 in; verify divider stiffness, drawer loading and installation support.")
        if D > 609.6:
            result.add_warning("CabinetDepth exceeds 24 in; verify drawer hardware reach and installation clearance.")
        if H < 762.0 or H > 1066.8:
            result.add_warning("CabinetHeight is outside the common 30-42 in base-cabinet band; verify the intended application.")
        if T < 12.7:
            result.add_warning("CabinetThickness is below 1/2 in; verify structural capacity and joinery.")
        if front_t < cls.NORMAL_HINGE_FRONT_MIN or front_t > cls.NORMAL_HINGE_FRONT_MAX:
            result.add_warning("FrontThickness is outside the common 15-24 mm concealed-hinge range; verify selected hardware.")
        if mount == "Overlay" and float(values["FrontProud"]) > 6.35:
            result.add_warning("FrontProud exceeds 1/4 in; verify the intended front projection.")
        if mount == "Overlay" and float(values["FrontSideReveal"]) > 25.4:
            result.add_warning("FrontSideReveal exceeds 1 in per side; verify the intended face-frame/reveal appearance.")
        if L["left_door_width"] < 228.6:
            result.add_warning("Calculated Left Door width is under 9 in; verify hinge and access usability.")
        if float(values["TopDrawerHeight"]) > 254.0:
            result.add_warning("TopDrawerHeight exceeds 10 in; verify the intended vanity/front proportion.")
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
PARAMETER_SCHEMA = apply_schema_overrides(PARAMETER_SCHEMA, {'CabinetWidth': {'group': 'Cabinet'}, 'CabinetDepth': {'group': 'Cabinet'}, 'CabinetHeight': {'group': 'Cabinet'}, 'CabinetThickness': {'group': 'Cabinet'}, 'RabbetDepth': {'group': 'Cabinet'}, 'ToeKickHeight': {'group': 'Toe Kick'}, 'ToeKickSetback': {'group': 'Toe Kick'}, 'FrontThickness': {'group': 'Front Grid'}, 'FrontProud': {'group': 'Front Grid', 'active_when': (('FrontMount', 'Overlay'),)}, 'InsetSetback': {'group': 'Front Grid', 'active_when': (('FrontMount', 'Inset'),)}, 'FrontSideReveal': {'group': 'Front Grid', 'active_when': (('FrontMount', 'Overlay'),)}, 'ColumnGap': {'group': 'Front Grid'}, 'TopLowerGap': {'group': 'Front Grid'}, 'RightDrawerGap': {'group': 'Front Grid'}, 'RightColumnWidth': {'group': 'Front Grid'}, 'TopDrawerHeight': {'group': 'Front Grid'}, 'UpperRightDrawerHeight': {'group': 'Front Grid'}, 'FrontMount': {'group': 'Front Grid'}, 'DoorStyle': {'group': 'Front Construction'}, 'DoorFrameWidth': {'group': 'Front Construction', 'active_when': (('DoorStyle', 'Shaker'),)}, 'DoorPanelThickness': {'group': 'Front Construction', 'active_when': (('DoorStyle', 'Shaker'),)}, 'DrawerStyle': {'group': 'Front Construction'}, 'DrawerFrameWidth': {'group': 'Front Construction', 'active_when': (('DrawerStyle', 'Shaker'),)}, 'DrawerPanelThickness': {'group': 'Front Construction', 'active_when': (('DrawerStyle', 'Shaker'),)}, 'DrawerBoxDepth': {'group': 'Drawer Boxes'}, 'DrawerBoxWallThickness': {'group': 'Drawer Boxes'}, 'DrawerSideClearance': {'group': 'Drawer Boxes'}, 'DrawerVerticalClearance': {'group': 'Drawer Boxes'}})
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
    resolved = ResolvedCabinetLayout.calculate(values)
    return "Left door: {:.3f} mm wide; lower-right drawer: {:.3f} mm high".format(resolved.front["left_door_width"], resolved.front["lower_right_height"])
class VanityBaseCabinetDialog(SchemaCabinetDialog):
    def __init__(self, sheet):
        super().__init__(sheet, PARAMETER_SCHEMA, title='Lower Multi-Door / Multi-Drawer Cabinet Parameters', validator=MixedFrontValidator.validate, notes=('RightColumnWidth and UpperRightDrawerHeight are direct controls. Left door width and Lower Right Drawer height are derived. Drawer-box and divider geometry are resolved from the same cabinet layout.',), derived_preview=_cabinet_derived_preview)

class VanityBaseCabinetFP:
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
    @staticmethod
    def _component(doc, name, label=None):
        result = doc.getObject(name)
        if result is None:
            raise RuntimeError("Cabinet geometry object '{}' was not found.".format(name))
        if label is not None and result.Label != label:
            pass
        return result
    def _validate_values(self, values, report_warnings=False):
        result = MixedFrontValidator.validate(values)
        result.raise_for_errors()
        signature = tuple(result.warnings)
        if report_warnings and signature and signature != self._warning_signature:
            App.Console.PrintWarning("Mixed-front cabinet parameter warning(s):\n{}\n".format(result.warning_text()))
        self._warning_signature = signature
        return result
    def _create_geometry(self, obj, assembly, sheet):
        doc = obj.Document
        prefix = assembly.Name
        values = read_parameter_values(sheet)
        self._validate_values(values)
        resolved = ResolvedCabinetLayout.calculate(values)
        L = resolved["front"]
        boxes = resolved["drawer_boxes"]
        dividers = resolved["dividers"]
        origin_point = Draft.make_point(X=0.0, Y=0.0, Z=0.0, name="{}_OriginPoint".format(prefix), point_size=8)
        origin_point.Label = "Assembly Origin Point"
        try:
            origin_point.ViewObject.Visibility = True
        except Exception:
            pass
        carcass = CabinetCarcass.create(doc, prefix)
        toe = ToeKick.create(doc, prefix)
        top_divider = doc.addObject("Part::Box", "{}_TopDrawerDivider".format(prefix))
        top_divider.Label = "Top Drawer Divider"
        vertical_divider = doc.addObject("Part::Box", "{}_LowerVerticalDivider".format(prefix))
        vertical_divider.Label = "Lower Vertical Divider"
        self._update_carcass(carcass, values)
        toe.update(values["CabinetWidth"], values["CabinetDepth"], values["ToeKickHeight"], values["ToeKickSetback"])
        self._update_dividers(top_divider, vertical_divider, dividers)
        assembly.addObject(sheet)
        assembly.addObject(origin_point)
        for body in carcass.bodies():
            assembly.addObject(body)
        assembly.addObject(toe.box)
        assembly.addObject(top_divider)
        assembly.addObject(vertical_divider)
        doc.recompute()
        door = CabinetFront.create(doc, prefix, "LeftDoorFront", "Left Door Front", values["DoorStyle"])
        drawer_fronts = [
            CabinetFront.create(doc, prefix, "TopDrawerFront", "Top Drawer Front", values["DrawerStyle"]),
            CabinetFront.create(doc, prefix, "UpperRightDrawerFront", "Upper Right Drawer Front", values["DrawerStyle"]),
            CabinetFront.create(doc, prefix, "LowerRightDrawerFront", "Lower Right Drawer Front", values["DrawerStyle"]),
        ]
        drawer_boxes = [
            CabinetDrawerBox.create(doc, prefix, "TopDrawerBox", "Top Drawer Box"),
            CabinetDrawerBox.create(doc, prefix, "UpperRightDrawerBox", "Upper Right Drawer Box"),
            CabinetDrawerBox.create(doc, prefix, "LowerRightDrawerBox", "Lower Right Drawer Box"),
        ]
        self._update_fronts(door.body, door.feature, [(f.body, f.feature) for f in drawer_fronts], values, L)
        self._update_drawer_boxes([b.feature for b in drawer_boxes], values, boxes)
        assembly.addObject(door.body)
        for front in drawer_fronts:
            assembly.addObject(front.body)
        for box in drawer_boxes:
            assembly.addObject(box.feature)
        assembly.addObject(obj)
        required = [sheet, origin_point] + carcass.bodies() + [toe.box, top_divider, vertical_divider, door.body, obj] + [f.body for f in drawer_fronts] + [b.feature for b in drawer_boxes]
        missing = [member.Name for member in required if member not in assembly.Group]
        if missing:
            raise RuntimeError("FreeCAD did not place all mixed-front cabinet members inside '{}'. Missing: {}".format(assembly.Name, ", ".join(missing)))
        try:
            toe.box.ViewObject.ShapeColor = (0.25, 0.25, 0.25)
            top_divider.ViewObject.ShapeColor = (0.72, 0.72, 0.72)
            vertical_divider.ViewObject.ShapeColor = (0.72, 0.72, 0.72)
            for box in drawer_boxes:
                box.feature.ViewObject.ShapeColor = (0.72, 0.55, 0.35)
        except Exception:
            pass
        for front in [door] + drawer_fronts:
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
        raise RuntimeError("Cabinet controller cannot resolve its owning App::Part.")
    def _parameters(self, obj, assembly):
        sheet = obj.Parameters
        if sheet is not None and sheet.Document == obj.Document:
            return sheet
        for child in assembly.Group:
            if child.Label == "Parameters" and child.TypeId == "Spreadsheet::Sheet":
                return child
        raise RuntimeError("Parameters spreadsheet not found.")
    def _geometry(self, assembly):
        doc = assembly.Document
        prefix = assembly.Name
        carcass = CabinetCarcass.from_document(doc, prefix)
        names = {
            "toe": "{}_ToeKickRiser".format(prefix),
            "top_divider": "{}_TopDrawerDivider".format(prefix),
            "vertical_divider": "{}_LowerVerticalDivider".format(prefix),
            "door_body": "{}_LeftDoorFront".format(prefix),
            "door_shape": "{}_LeftDoorFrontShape".format(prefix),
            "top_front_body": "{}_TopDrawerFront".format(prefix),
            "top_front_shape": "{}_TopDrawerFrontShape".format(prefix),
            "upper_front_body": "{}_UpperRightDrawerFront".format(prefix),
            "upper_front_shape": "{}_UpperRightDrawerFrontShape".format(prefix),
            "lower_front_body": "{}_LowerRightDrawerFront".format(prefix),
            "lower_front_shape": "{}_LowerRightDrawerFrontShape".format(prefix),
            "top_box": "{}_TopDrawerBox".format(prefix),
            "upper_box": "{}_UpperRightDrawerBox".format(prefix),
            "lower_box": "{}_LowerRightDrawerBox".format(prefix),
        }
        resolved = {key: doc.getObject(name) for key, name in names.items()}
        missing = [name for key, name in names.items() if resolved[key] is None]
        if missing:
            raise RuntimeError("Cabinet geometry is incomplete. Missing: {}".format(", ".join(missing)))
        resolved["carcass"] = carcass
        return resolved
    def _update_carcass(self, carcass, values):
        carcass.update(
            width=values["CabinetWidth"], depth=values["CabinetDepth"],
            height=values["CabinetHeight"] - values["ToeKickHeight"],
            thickness=values["CabinetThickness"], rabbet_depth=values["RabbetDepth"],
            base_z=values["ToeKickHeight"]
        )
    def _update_dividers(self, top_divider, vertical_divider, dividers):
        for obj, spec, label in (
            (top_divider, dividers["top"], "Top Drawer Divider"),
            (vertical_divider, dividers["vertical"], "Lower Vertical Divider"),
        ):
            if min(spec["length"], spec["depth"], spec["height"]) <= 0:
                raise RuntimeError("{} has invalid resolved geometry.".format(label))
            obj.Length = spec["length"]
            obj.Width = spec["depth"]
            obj.Height = spec["height"]
            obj.Placement.Base = App.Vector(spec["x"], spec["y"], spec["z"])
    def _update_fronts(self, door_body, door_feature, drawer_objects, values, L):
        door = CabinetFront.from_existing(door_body, door_feature, values["DoorStyle"])
        door.update(
            width=L["left_door_width"], height=L["left_door_height"], thickness=values["FrontThickness"],
            frame_width=values["DoorFrameWidth"], panel_thickness=values["DoorPanelThickness"],
            x=L["left_door_x"], z=L["left_door_z"], back_y=L["front_back_y"]
        )
        drawer_specs = [
            (L["front_width"], L["top_drawer_height"], L["top_drawer_x"], L["top_drawer_z"]),
            (L["right_column_width"], L["upper_right_height"], L["right_x"], L["upper_right_z"]),
            (L["right_column_width"], L["lower_right_height"], L["right_x"], L["lower_right_z"]),
        ]
        for (body, feature), (width, height, x, z) in zip(drawer_objects, drawer_specs):
            front = CabinetFront.from_existing(body, feature, values["DrawerStyle"])
            front.update(
                width=width, height=height, thickness=values["FrontThickness"],
                frame_width=values["DrawerFrameWidth"], panel_thickness=values["DrawerPanelThickness"],
                x=x, z=z, back_y=L["front_back_y"]
            )
    def _update_drawer_boxes(self, drawer_features, values, boxes):
        specs = [boxes["top"], boxes["upper"], boxes["lower"]]
        for feature, spec in zip(drawer_features, specs):
            CabinetDrawerBox.from_existing(feature).update(
                width=spec["width"], depth=values["DrawerBoxDepth"], height=spec["height"],
                wall=values["DrawerBoxWallThickness"], x=spec["x"], y=spec["y"], z=spec["z"]
            )
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
        resolved = ResolvedCabinetLayout.calculate(values)
        L = resolved["front"]
        boxes = resolved["drawer_boxes"]
        dividers = resolved["dividers"]
        g = self._geometry(assembly)
        self._update_carcass(g["carcass"], values)
        ToeKick.from_existing(g["toe"]).update(values["CabinetWidth"], values["CabinetDepth"], values["ToeKickHeight"], values["ToeKickSetback"])
        self._update_dividers(g["top_divider"], g["vertical_divider"], dividers)
        self._update_fronts(
            g["door_body"], g["door_shape"],
            [(g["top_front_body"], g["top_front_shape"]), (g["upper_front_body"], g["upper_front_shape"]), (g["lower_front_body"], g["lower_front_shape"])],
            values, L
        )
        self._update_drawer_boxes([g["top_box"], g["upper_box"], g["lower_box"]], values, boxes)

def validate_values(values):
    result = MixedFrontValidator.validate(values)
    return result.valid, result.error_text()

def _sanitize_object_name(name):
    return sanitize_object_name(name, INSTANCE_BASENAME)

def next_vanity_base_cabinet_name(document):
    return next_instance_name(document, INSTANCE_BASENAME)


class VanityBaseCabinetBuilder:
    def __init__(self, document, instance_name):
        if document is None:
            raise ValueError("create_vanity_base_cabinet() requires an existing FreeCAD document.")
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
        dialog = VanityBaseCabinetDialog(self.parameters)
        if not dialog.exec():
            print("Mixed-front cabinet creation cancelled. The active layout document was not changed.")
            return False
        self.values = dialog.values()
        valid, message = validate_values(self.values)
        if not valid:
            QtWidgets.QMessageBox.critical(None, "Invalid Mixed-Front Cabinet Parameters", message)
            return False
        ParameterTable.update(self.document, self.parameters, self.values)
        ParameterTable.verify(self.parameters)
        return True
    def _accepted(self, point):
        self.insertion_point = App.Vector(point)
        self._picker = None
        try:
            self.assembly = self.document.addObject("App::Part", self.instance_name)
            self.assembly.Label = "Lower Multi-Drawer / Mixed-Front Cabinet"
            self.assembly.Placement.Base = App.Vector(self.insertion_point)
            self.controller = self.document.addObject("Part::FeaturePython", "{}_Controller".format(self.instance_name))
            self.controller.Label = "Mixed-Front Lower Cabinet Controller"
            VanityBaseCabinetFP(self.controller, self.assembly, self.parameters)
            self.document.recompute()
            self._show()
            self._print_report()
            self._transaction.commit()
        except Exception as exc:
            self._rollback()
            QtWidgets.QMessageBox.critical(None, "Mixed-Front Cabinet Creation Error", str(exc))
            App.Console.PrintError("Mixed-front cabinet creation failed: {}\n".format(exc))
    def _cancelled(self):
        self._picker = None
        self._rollback()
        print("Mixed-front cabinet insertion cancelled. The active layout document was not changed.")
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
        print("LOWER MULTI-DRAWER / MIXED-FRONT BASE CABINET")
        print("FREECAD 1.1.4 - REVISION 0.14")
        print("Target document: {}".format(self.document.Name))
        print("Instance name:   {}".format(self.instance_name))
        print("=" * 72)
    def _print_report(self):
        values = read_parameter_values(self.parameters)
        resolved = ResolvedCabinetLayout.calculate(values)
        L = resolved["front"]
        boxes = resolved["drawer_boxes"]
        dividers = resolved["dividers"]
        d = CabinetCarcass.derived_dimensions(values["CabinetWidth"], values["CabinetDepth"], values["CabinetThickness"], values["RabbetDepth"])
        print("")
        print("-" * 72)
        print("MIXED-FRONT LOWER CABINET INSTANCE CREATED SUCCESSFULLY")
        print("-" * 72)
        print("Cabinet instance:        ", self.assembly.Name)
        print("Parameters sheet:        ", self.parameters.Name)
        print("Overall height:          ", values["CabinetHeight"], "mm")
        print("Carcass height:          ", L["carcass_height"], "mm")
        print("Door style:              ", values["DoorStyle"])
        print("Drawer style:            ", values["DrawerStyle"])
        print("Front mount:             ", values["FrontMount"])
        print("Calculated Left Door W:  ", L["left_door_width"], "mm")
        print("Calculated Lower Right H:", L["lower_right_height"], "mm")
        print("Front visible Y:         ", L["visible_front_y"], "mm")
        print("Rabbet depth:            ", values["RabbetDepth"], "mm")
        print("Top/Bottom/Back width:   ", d["panel_width"], "mm")
        print("Top/Bottom depth:        ", d["panel_depth"], "mm")
        print("Top drawer box W/H:      ", boxes["top"]["width"], "/", boxes["top"]["height"], "mm")
        print("Right drawer box W:      ", boxes["upper"]["width"], "mm")
        print("Drawer box depth:        ", values["DrawerBoxDepth"], "mm")
        print("Divider usable depth:   ", dividers["top"]["depth"], "mm")
        print("Vertical divider X:     ", dividers["vertical"]["x"], "mm")
        print("Insertion Point:          X={:.3f}, Y={:.3f}, Z={:.3f} mm".format(self.insertion_point.x, self.insertion_point.y, self.insertion_point.z))
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
        QtWidgets.QMessageBox.warning(None, "No Active FreeCAD Document", "Open or create the kitchen/layout document first, then run this cabinet command again.")
        return None
    return create_vanity_base_cabinet(document, next_vanity_base_cabinet_name(document))

# WORKBENCH MODULE NOTE:
# Do not call main() automatically here. CabinetsWorkbench.py imports this module,
# calls main(), and retains the returned VanityBaseCabinetBuilder while endpoint selection is active.

# ============================================================
# PARAMETRIC LOWER CABINET
# FIVE-PART RABBETED CARCASS + TOE KICK
# ============================================================
# Target: FreeCAD 1.1.4
# REVISION: 0.13
#   0.13 - Cabinet Core v1 architecture revision
#          - shared validation, parameter, component, runtime and snap infrastructure
#          - cabinet-specific layout/geometry relationships preserved
#          - no intentional default geometry change from previous validated revision
#
# 0.09 - Lower-cabinet refactor based on:
#        - proven Lower Cabinet Revision 0.08 toe-kick architecture
#        - proven Lower Cabinet Revision 0.17 carcass / door architecture
#        - five manufactured carcass parts: Left Side, Right Side, Top,
#          Bottom and Back
#        - real top, bottom and back rabbets in both side panels
#        - solid recessed toe-kick riser retained as a separate object
#        - CabinetHeight remains the overall floor-to-top cabinet height
#        - carcass base Z = ToeKickHeight
#        - carcass height = CabinetHeight - ToeKickHeight
#        - doors are created LAST after carcass + toe kick are established
#        - DoorCount, DoorStyle and DoorMount live in Parameters
#        - Options column documents valid categorical values
#        - DoorStyle = Slab / Shaker / Glass
#        - DoorMount = Inset / Overlay
#        - Overlay retains original outward (-Y) door behavior
#        - Inset doors are sized from the finished carcass front opening
#        - InsetSetback affects Y only and does not alter door width/height
#        - one/two-door geometry uses one centralized LowerDoorLayout
#        - assembly-origin Draft Point and two-attempt endpoint insertion retained
#        - canonical shared Draft GUI Snapper initialized through DraftTools
#
# 0.10 - Report-order correction
#        - initializes report_height before its first use in _print_report()
#        - no geometry, parameter, toe-kick, door, carcass or snap behavior changed
#
# 0.11 - Cabinet-family validation standard
#        - strict parsing: invalid user/spreadsheet text is never silently replaced
#        - reusable ParameterSpec / ValidationResult / LowerCabinetValidator pattern
#        - hard dimensional envelopes for cabinet, stock, toe kick and door inputs
#        - geometry-dependent relational checks remain centralized
#        - warning tier added for unusual but geometrically permitted dimensions
#        - ToeKickDepth renamed to ToeKickSetback with legacy read compatibility
#        - spreadsheet adds an Allowed Range column
#        - dialog disables style/mount fields that do not apply
#        - existing carcass, door, insertion and Draft Snapper geometry preserved
#
#
# 0.12 - Inclusive hard-range boundary patch
#        - exact minimum and maximum dimensional limits are valid
#        - adds 1e-6 mm tolerance for microscopic FreeCAD unit-conversion noise
#        - values genuinely outside the permitted range remain blocking errors
#        - no cabinet geometry, parameter ranges, warnings or snap behavior changed
#
# Coordinate system:
# X = cabinet width
# Y = cabinet depth
# Z = overall cabinet height
# cabinet front/reference plane = Y=0
# cabinet extends +Y
# overlay doors extend toward -Y
#
# Lower-cabinet vertical construction:
#   Toe Kick:
#       Z = 0 .. ToeKickHeight
#   Five-piece carcass:
#       base Z = ToeKickHeight
#       height = CabinetHeight - ToeKickHeight
#   Overlay doors:
#       Z = ToeKickHeight
#       height = carcass height
#   Inset doors:
#       Z = ToeKickHeight + CabinetThickness
#       height = carcass height - 2*CabinetThickness
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
from AdvCabinetParameters import SheetParams, qty_mm, qty_int, ParameterTable as CoreParameterTable, schema_from_legacy, apply_schema_overrides
from AdvCabinetComponents import CabinetPanel, RabbetedSidePanel, CabinetCarcass, ToeKick, CabinetDoor
from AdvCabinetSnap import EndpointSnapPointPicker
from AdvCabinetDialog import SchemaCabinetDialog
from AdvCabinetRuntime import CabinetCreationTransaction, sanitize_object_name, next_instance_name, normalized_signature
SHEET_NAME = "Parameters"
INSTANCE_BASENAME = "LowerCabinet"
CABINET_CORE_VERSION = 1
CABINET_SCHEMA_VERSION = 2
CABINET_TYPE = "LowerTwoDoorCabinet"
GENERATOR_REVISION = "0.13"

INTEGER_PARAMETERS = {"DoorCount"}
TEXT_PARAMETERS = {"DoorStyle", "DoorMount"}
DOOR_STYLES = ("Slab", "Shaker", "Glass")
DOOR_MOUNTS = ("Inset", "Overlay")
PARAMETER_OPTIONS = {
    "DoorCount": "1 | 2",
    "DoorStyle": "Slab | Shaker | Glass",
    "DoorMount": "Inset | Overlay",
    "DoorGap": "Applies when DoorCount = 2",
    "InsetSetback": "Applies to Inset doors",
    "DoorFrameWidth": "Applies to Shaker / Glass",
    "DoorPanelThickness": "Applies to Shaker",
    "GlassThickness": "Applies to Glass",
}
PARAM_DEFAULTS = [
    ("CabinetWidth",       "600 mm"),
    ("CabinetDepth",       "580 mm"),
    ("CabinetHeight",      "720 mm"),
    ("CabinetThickness",   "19.5 mm"),
    ("RabbetDepth",        "6.35 mm"),
    ("ToeKickHeight",      "88.9 mm"),
    ("ToeKickSetback",     "88.9 mm"),
    ("DoorThickness",      "19 mm"),
    ("DoorGap",            "2 mm"),
    ("InsetSetback",       "0 mm"),
    ("DoorCount",          "2"),
    ("DoorStyle",          "Slab"),
    ("DoorMount",          "Inset"),
    ("DoorFrameWidth",     "50 mm"),
    ("DoorPanelThickness", "6 mm"),
    ("GlassThickness",     "6 mm"),
]
PARAM_DEFAULT_MAP = dict(PARAM_DEFAULTS)
LEGACY_PARAMETER_ALIASES = {
    "ToeKickSetback": ("ToeKickDepth",),
}


PARAMETER_SPECS = {
    "CabinetWidth": ParameterSpec("CabinetWidth", 304.8, 1219.2, "Cabinet Width"),
    "CabinetDepth": ParameterSpec("CabinetDepth", 304.8, 1219.2, "Cabinet Depth"),
    "CabinetHeight": ParameterSpec("CabinetHeight", 406.4, 3657.6, "Cabinet Height"),
    "CabinetThickness": ParameterSpec("CabinetThickness", 6.35, 25.4, "Cabinet Thickness"),
    # This command is specifically a rabbeted carcass, so a positive rabbet is required.
    "RabbetDepth": ParameterSpec("RabbetDepth", 1.5875, 12.7, "Rabbet Depth"),
    "ToeKickHeight": ParameterSpec("ToeKickHeight", 76.2, 152.4, "Toe Kick Height"),
    "ToeKickSetback": ParameterSpec("ToeKickSetback", 50.8, 152.4, "Toe Kick Setback"),
    "DoorThickness": ParameterSpec("DoorThickness", 12.7, 31.75, "Door Thickness"),
    "DoorGap": ParameterSpec("DoorGap", 1.0, 6.35, "Door Gap"),
    "InsetSetback": ParameterSpec("InsetSetback", 0.0, 25.4, "Inset Setback"),
    "DoorFrameWidth": ParameterSpec("DoorFrameWidth", 25.4, 101.6, "Door Frame Width"),
    "DoorPanelThickness": ParameterSpec("DoorPanelThickness", 3.0, 19.0, "Door Panel Thickness"),
    "GlassThickness": ParameterSpec("GlassThickness", 3.0, 12.7, "Glass Thickness"),
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
    """Read one cabinet's Parameters sheet using canonical names and strict parsing."""
    params = SheetParams(sheet)
    values = {}
    for name, default_value in PARAM_DEFAULTS:
        raw = _parameter_raw(params, name, None)
        if raw is None or not str(raw).strip():
            raise ValueError("{} is required.".format(name))
        if name in INTEGER_PARAMETERS:
            values[name] = qty_int(raw, None, name)
        elif name in TEXT_PARAMETERS:
            text = str(raw).strip()
            if not text:
                raise ValueError("{} is required.".format(name))
            values[name] = text
        else:
            values[name] = qty_mm(raw, None, name)
    return values


class LowerCabinetValidator:
    """Reusable lower-cabinet profile: hard limits + geometry-dependent rules."""
    MIN_FRAME_OPENING = 25.4
    NORMAL_HINGE_DOOR_MIN = 15.0
    NORMAL_HINGE_DOOR_MAX = 24.0
    RANGE_TOLERANCE_MM = 1.0e-6
    @staticmethod
    def _check_range(result, values, name, active=True):
        """Accept inclusive hard limits while ignoring microscopic unit-conversion noise."""
        if not active:
            return
        spec = PARAMETER_SPECS[name]
        value = float(values[name])
        tolerance = LowerCabinetValidator.RANGE_TOLERANCE_MM
        if value < spec.minimum - tolerance or value > spec.maximum + tolerance:
            result.add_error(
                "{} is {:.3f} mm. Allowed range is {}.".format(
                    spec.label, value, spec.limit_text()
                )
            )
    @classmethod
    def validate(cls, values):
        result = ValidationResult()
        required = [name for name, _default in PARAM_DEFAULTS]
        missing = [name for name in required if name not in values]
        if missing:
            result.add_error("Missing parameters: {}.".format(", ".join(missing)))
            return result
        door_count = values["DoorCount"]
        style = str(values["DoorStyle"])
        mount = str(values["DoorMount"])
        if door_count not in (1, 2):
            result.add_error("DoorCount must be 1 or 2.")
        if style not in DOOR_STYLES:
            result.add_error("DoorStyle must be Slab, Shaker or Glass.")
        if mount not in DOOR_MOUNTS:
            result.add_error("DoorMount must be Inset or Overlay.")
        for name in (
            "CabinetWidth", "CabinetDepth", "CabinetHeight", "CabinetThickness",
            "RabbetDepth", "ToeKickHeight", "ToeKickSetback", "DoorThickness"
        ):
            cls._check_range(result, values, name)
        cls._check_range(result, values, "DoorGap", active=(door_count == 2))
        cls._check_range(result, values, "InsetSetback", active=(mount == "Inset"))
        cls._check_range(result, values, "DoorFrameWidth", active=(style in ("Shaker", "Glass")))
        cls._check_range(result, values, "DoorPanelThickness", active=(style == "Shaker"))
        cls._check_range(result, values, "GlassThickness", active=(style == "Glass"))
        if result.errors:
            return result
        W = float(values["CabinetWidth"])
        D = float(values["CabinetDepth"])
        H = float(values["CabinetHeight"])
        T = float(values["CabinetThickness"])
        R = float(values["RabbetDepth"])
        TKH = float(values["ToeKickHeight"])
        TKS = float(values["ToeKickSetback"])
        door_t = float(values["DoorThickness"])
        gap = float(values["DoorGap"])
        inset = float(values["InsetSetback"])
        frame = float(values["DoorFrameWidth"])
        panel = float(values["DoorPanelThickness"])
        glass = float(values["GlassThickness"])
        if R > 0.5 * T:
            result.add_error("RabbetDepth cannot exceed 50% of CabinetThickness.")
        if TKH >= H - 2.0 * T:
            result.add_error("ToeKickHeight leaves insufficient carcass height above the toe kick.")
        if TKS >= D - T:
            result.add_error("ToeKickSetback must be less than CabinetDepth - CabinetThickness.")
        carcass_height = H - TKH
        try:
            CabinetCarcass.validate_dimensions(W, D, carcass_height, T, R)
        except Exception as exc:
            result.add_error(str(exc))
        layout = None
        try:
            layout = LowerDoorLayout.calculate(
                width=W, height=H, toe_kick_height=TKH, cabinet_thickness=T,
                door_thickness=door_t, gap=gap, count=door_count,
                mount=mount, inset_setback=inset
            )
        except Exception as exc:
            result.add_error(str(exc))
        if mount == "Inset" and inset + door_t > D:
            result.add_error("InsetSetback + DoorThickness cannot exceed CabinetDepth.")
        if layout is not None and style in ("Shaker", "Glass"):
            center_width = layout["door_width"] - 2.0 * frame
            center_height = layout["door_height"] - 2.0 * frame
            if center_width < cls.MIN_FRAME_OPENING:
                result.add_error(
                    "DoorFrameWidth leaves less than 25.4 mm (1 in) of center opening width."
                )
            if center_height < cls.MIN_FRAME_OPENING:
                result.add_error(
                    "DoorFrameWidth leaves less than 25.4 mm (1 in) of center opening height."
                )
        if style == "Shaker" and panel > door_t:
            result.add_error("DoorPanelThickness cannot exceed DoorThickness.")
        if style == "Glass" and glass > door_t:
            result.add_error("GlassThickness cannot exceed DoorThickness.")
        if door_t < cls.NORMAL_HINGE_DOOR_MIN or door_t > cls.NORMAL_HINGE_DOOR_MAX:
            result.add_warning(
                "DoorThickness is outside the 15-24 mm normal concealed-hinge design band; verify selected hardware."
            )
        if T < 12.7:
            result.add_warning(
                "CabinetThickness is below 12.7 mm (1/2 in). Geometry is permitted, but verify material strength and joinery."
            )
        if W > 914.4:
            result.add_warning(
                "CabinetWidth exceeds 36 in. Verify door hardware, internal support and installation requirements for the intended load."
            )
        return result
    @classmethod
    def validate_internal(cls, p):
        return cls.validate({
            "CabinetWidth": p["width"],
            "CabinetDepth": p["depth"],
            "CabinetHeight": p["height"],
            "CabinetThickness": p["cabinet_thickness"],
            "RabbetDepth": p["rabbet_depth"],
            "ToeKickHeight": p["toe_kick_height"],
            "ToeKickSetback": p["toe_kick_setback"],
            "DoorThickness": p["door_thickness"],
            "DoorGap": p["door_gap"],
            "InsetSetback": p["inset_setback"],
            "DoorCount": p["door_count"],
            "DoorStyle": p["door_style"],
            "DoorMount": p["door_mount"],
            "DoorFrameWidth": p["frame_width"],
            "DoorPanelThickness": p["panel_thickness"],
            "GlassThickness": p["glass_thickness"],
        })

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
PARAMETER_SCHEMA = apply_schema_overrides(PARAMETER_SCHEMA, {'CabinetWidth': {'group': 'Cabinet'}, 'CabinetDepth': {'group': 'Cabinet'}, 'CabinetHeight': {'group': 'Cabinet'}, 'CabinetThickness': {'group': 'Cabinet'}, 'RabbetDepth': {'group': 'Cabinet'}, 'ToeKickHeight': {'group': 'Toe Kick'}, 'ToeKickSetback': {'group': 'Toe Kick'}, 'DoorThickness': {'group': 'Doors'}, 'DoorGap': {'group': 'Doors', 'active_when': (('DoorCount', 2),)}, 'InsetSetback': {'group': 'Doors', 'active_when': (('DoorMount', 'Inset'),)}, 'DoorCount': {'group': 'Doors', 'minimum': 1, 'maximum': 2, 'label': 'Door Count'}, 'DoorStyle': {'group': 'Doors'}, 'DoorMount': {'group': 'Doors'}, 'DoorFrameWidth': {'group': 'Doors', 'active_when': (('DoorStyle', ('Shaker', 'Glass')),)}, 'DoorPanelThickness': {'group': 'Doors', 'active_when': (('DoorStyle', 'Shaker'),)}, 'GlassThickness': {'group': 'Doors', 'active_when': (('DoorStyle', 'Glass'),)}})
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

class CabinetDialog(SchemaCabinetDialog):
    def __init__(self, sheet):
        super().__init__(sheet, PARAMETER_SCHEMA, title='Lower Two-Door Cabinet Parameters', validator=LowerCabinetValidator.validate, notes=('DoorCount supports one or two doors. InsetSetback applies only to Inset doors; frame/panel/glass fields follow DoorStyle.',))






class LowerDoorLayout:
    """Door sizing/placement for a lower cabinet above a toe kick."""
    MOUNT_OVERLAY = "Overlay"
    MOUNT_INSET = "Inset"
    @classmethod
    def calculate(
        cls,
        width,
        height,
        toe_kick_height,
        cabinet_thickness,
        door_thickness,
        gap,
        count,
        mount,
        inset_setback
    ):
        if width <= 0 or height <= 0:
            raise RuntimeError("Cabinet width and height must be greater than zero.")
        if toe_kick_height <= 0 or toe_kick_height >= height:
            raise RuntimeError("ToeKickHeight must be greater than zero and less than CabinetHeight.")
        if cabinet_thickness <= 0:
            raise RuntimeError("CabinetThickness must be greater than zero.")
        if door_thickness <= 0:
            raise RuntimeError("DoorThickness must be greater than zero.")
        if gap < 0:
            raise RuntimeError("DoorGap cannot be negative.")
        if inset_setback < 0:
            raise RuntimeError("InsetSetback cannot be negative.")
        if count not in (1, 2):
            raise RuntimeError("DoorCount must be 1 or 2.")
        if mount not in DOOR_MOUNTS:
            raise RuntimeError("DoorMount must be Overlay or Inset.")
        carcass_height = height - toe_kick_height
        if mount == cls.MOUNT_OVERLAY:
            door_width = width if count == 1 else (width - gap) / 2.0
            door_height = carcass_height
            left_x = 0.0
            left_z = toe_kick_height
            back_y = 0.0
        else:
            opening_width = width - 2.0 * cabinet_thickness
            opening_height = carcass_height - 2.0 * cabinet_thickness
            if opening_width <= 0 or opening_height <= 0:
                raise RuntimeError("CabinetThickness leaves no opening for inset doors.")
            available_width = opening_width
            door_height = opening_height
            if count == 2:
                available_width -= gap
            door_width = available_width if count == 1 else available_width / 2.0
            left_x = cabinet_thickness
            left_z = toe_kick_height + cabinet_thickness
            # CabinetDoor geometry runs from -DoorThickness to 0 in local Y.
            # This makes the visible front face equal to InsetSetback.
            back_y = door_thickness + inset_setback
        if door_width <= 0:
            raise RuntimeError("Door layout leaves no usable door width.")
        if door_height <= 0:
            raise RuntimeError("Door layout leaves no usable door height.")
        right_x = left_x if count == 1 else left_x + door_width + gap
        return {
            "carcass_height": carcass_height,
            "door_width": door_width,
            "door_height": door_height,
            "left_x": left_x,
            "right_x": right_x,
            "z": left_z,
            "back_y": back_y,
            "right_visible": count == 2,
        }

class LowerCabinetFP:
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
        origin_point = Draft.make_point(
            X=0.0, Y=0.0, Z=0.0,
            name="{}_OriginPoint".format(prefix),
            point_size=8
        )
        origin_point.Label = "Assembly Origin Point"
        try:
            origin_point.ViewObject.Visibility = True
        except Exception:
            pass
        # 1. Read and validate final lower-cabinet parameters.
        p = self._read_parameters(sheet)
        self._validate(p)
        # 2. Create and fully establish carcass + toe kick first.
        carcass = CabinetCarcass.create(doc, prefix)
        toe_kick = ToeKick.create(doc, prefix)
        self._update_carcass(carcass, p)
        self._update_toe_kick(toe_kick, p)
        try:
            for body in carcass.bodies():
                body.ViewObject.ShapeColor = (0.72, 0.72, 0.72)
        except Exception:
            pass
        assembly.addObject(sheet)
        assembly.addObject(origin_point)
        for body in carcass.bodies():
            assembly.addObject(body)
        assembly.addObject(toe_kick.box)
        doc.recompute()
        # 3. Create the doors LAST from the completed lower-cabinet geometry.
        left = CabinetDoor.create(
            doc, prefix, "LeftDoor", "Left Door",
            style=CabinetDoor.STYLE_SLAB
        )
        right = CabinetDoor.create(
            doc, prefix, "RightDoor", "Right Door",
            style=CabinetDoor.STYLE_SLAB
        )
        self._update_doors(
            left.body, left.feature, left.glass,
            right.body, right.feature, right.glass,
            p
        )
        assembly.addObject(left.body)
        assembly.addObject(left.glass)
        assembly.addObject(right.body)
        assembly.addObject(right.glass)
        left_current = CabinetDoor.from_existing(
            left.body, left.feature, left.glass, p["door_style"]
        )
        right_current = CabinetDoor.from_existing(
            right.body, right.feature, right.glass, p["door_style"]
        )
        left_current.set_visible(True)
        right_current.set_visible(p["door_count"] == 2)
        # Controller is deliberately grouped last.
        assembly.addObject(obj)
        required = (
            [sheet, origin_point]
            + carcass.bodies()
            + [toe_kick.box, left.body, left.glass, right.body, right.glass, obj]
        )
        missing = [
            member.Name for member in required
            if member not in assembly.Group
        ]
        if missing:
            raise RuntimeError(
                "FreeCAD did not place all lower-cabinet members inside '{}'. Missing: {}"
                .format(assembly.Name, ", ".join(missing))
            )
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
    def _child_by_label(self, assembly, label, type_id=None):
        for child in assembly.Group:
            if child.Label == label and (type_id is None or child.TypeId == type_id):
                return child
        return None
    def _parameters(self, obj, assembly):
        sheet = obj.Parameters
        if sheet is not None and sheet.Document == obj.Document:
            return sheet
        sheet = self._child_by_label(assembly, "Parameters", "Spreadsheet::Sheet")
        if sheet is None:
            raise RuntimeError("Parameters spreadsheet not found for '{}'.".format(assembly.Name))
        return sheet
    def _geometry(self, assembly):
        doc = assembly.Document
        prefix = assembly.Name
        carcass = CabinetCarcass.from_document(doc, prefix)
        toe_box = doc.getObject("{}_ToeKickRiser".format(prefix))
        if toe_box is None:
            raise RuntimeError("Toe Kick Riser geometry is missing.")
        toe_kick = ToeKick.from_existing(toe_box)
        names = {
            "left_door": "{}_LeftDoor".format(prefix),
            "left_shape": "{}_LeftDoorShape".format(prefix),
            "left_glass": "{}_LeftDoorGlass".format(prefix),
            "right_door": "{}_RightDoor".format(prefix),
            "right_shape": "{}_RightDoorShape".format(prefix),
            "right_glass": "{}_RightDoorGlass".format(prefix),
        }
        resolved = {key: doc.getObject(name) for key, name in names.items()}
        missing = [name for key, name in names.items() if resolved[key] is None]
        if missing:
            raise RuntimeError("Cabinet door geometry is incomplete. Missing: {}".format(", ".join(missing)))
        return carcass, toe_kick, resolved
    def _read_parameters(self, sheet):
        values = read_parameter_values(sheet)
        return {
            "width": values["CabinetWidth"],
            "depth": values["CabinetDepth"],
            "height": values["CabinetHeight"],
            "cabinet_thickness": values["CabinetThickness"],
            "rabbet_depth": values["RabbetDepth"],
            "toe_kick_height": values["ToeKickHeight"],
            "toe_kick_setback": values["ToeKickSetback"],
            "door_thickness": values["DoorThickness"],
            "door_gap": values["DoorGap"],
            "inset_setback": values["InsetSetback"],
            "door_count": values["DoorCount"],
            "door_style": values["DoorStyle"],
            "door_mount": values["DoorMount"],
            "frame_width": values["DoorFrameWidth"],
            "panel_thickness": values["DoorPanelThickness"],
            "glass_thickness": values["GlassThickness"],
        }
    def _validate(self, p):
        result = LowerCabinetValidator.validate_internal(p)
        result.raise_for_errors()
        warning_signature = tuple(result.warnings)
        if warning_signature != getattr(self, "_last_warning_signature", ()):
            self._last_warning_signature = warning_signature
            if warning_signature:
                App.Console.PrintWarning(
                    "Lower Cabinet parameter warning:\n{}\n".format(result.warning_text())
                )
        return result
    def _update_carcass(self, carcass, p):
        carcass.update(
            width=p["width"],
            depth=p["depth"],
            height=p["height"] - p["toe_kick_height"],
            thickness=p["cabinet_thickness"],
            rabbet_depth=p["rabbet_depth"],
            base_z=p["toe_kick_height"],
        )
    def _update_toe_kick(self, toe_kick, p):
        toe_kick.update(
            width=p["width"],
            depth=p["depth"],
            height=p["toe_kick_height"],
            setback=p["toe_kick_setback"],
        )
    def _update_doors(self, left_door, left_shape, left_glass, right_door, right_shape, right_glass, p):
        style = p["door_style"]
        left = CabinetDoor.from_existing(left_door, left_shape, left_glass, style)
        right = CabinetDoor.from_existing(right_door, right_shape, right_glass, style)
        layout = LowerDoorLayout.calculate(
            width=p["width"],
            height=p["height"],
            toe_kick_height=p["toe_kick_height"],
            cabinet_thickness=p["cabinet_thickness"],
            door_thickness=p["door_thickness"],
            gap=p["door_gap"],
            count=p["door_count"],
            mount=p["door_mount"],
            inset_setback=p["inset_setback"],
        )
        left.update(
            layout["door_width"], layout["door_height"], p["door_thickness"],
            p["frame_width"], p["panel_thickness"], p["glass_thickness"],
            x=layout["left_x"], z=layout["z"], back_y=layout["back_y"]
        )
        right.update(
            layout["door_width"], layout["door_height"], p["door_thickness"],
            p["frame_width"], p["panel_thickness"], p["glass_thickness"],
            x=layout["right_x"], z=layout["z"], back_y=layout["back_y"]
        )
        left.set_visible(True)
        right.set_visible(layout["right_visible"])
    def execute(self, obj):
        if getattr(self, "_building", False):
            return
        assembly = self._assembly(obj)
        sheet = self._parameters(obj, assembly)
        p = self._read_parameters(sheet)
        self._validate(p)
        signature = normalized_signature(p)
        if signature == self._last_signature:
            return
        self._last_signature = signature
        carcass, toe_kick, g = self._geometry(assembly)
        self._update_carcass(carcass, p)
        self._update_toe_kick(toe_kick, p)
        self._update_doors(
            g["left_door"], g["left_shape"], g["left_glass"],
            g["right_door"], g["right_shape"], g["right_glass"], p
        )

def validate_dialog_values(values):
    result = LowerCabinetValidator.validate(values)
    return result.valid, result.error_text()

def _sanitize_object_name(name):
    return sanitize_object_name(name, INSTANCE_BASENAME)

def next_lower_cabinet_name(document):
    return next_instance_name(document, INSTANCE_BASENAME)


class LowerCabinetBuilder:
    def __init__(self, document, instance_name):
        if document is None:
            raise ValueError("create_lower_cabinet() requires an existing FreeCAD document.")
        self.document = document
        self._transaction = CabinetCreationTransaction(self.document)
        self.instance_name = _sanitize_object_name(instance_name)
        if self.document.getObject(self.instance_name) is not None:
            raise ValueError("An object named '{}' already exists in document '{}'.".format(
                self.instance_name, self.document.Name
            ))
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
        dialog = CabinetDialog(self.parameters)
        if not dialog.exec():
            print("Lower cabinet creation cancelled. The active layout document was not changed.")
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
            self.assembly.Label = "Lower Cabinet"
            self.assembly.Placement.Base = App.Vector(self.insertion_point)
            self.controller = self.document.addObject(
                "Part::FeaturePython", "{}_Controller".format(self.instance_name)
            )
            self.controller.Label = "Lower Cabinet Controller"
            LowerCabinetFP(
                self.controller,
                self.assembly,
                self.parameters
            )
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
        print("Lower cabinet insertion cancelled. The active layout document was not changed.")
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
        print("PARAMETRIC LOWER CABINET - FIVE-PART RABBETED CARCASS")
        print("FREECAD 1.1.4 - REVISION 0.12")
        print("Target document: {}".format(self.document.Name))
        print("Instance name:   {}".format(self.instance_name))
        print("=" * 72)
    def _print_report(self):
        p = SheetParams(self.parameters)
        W = qty_mm(p.get("CabinetWidth"), 600.0)
        D = qty_mm(p.get("CabinetDepth"), 580.0)
        t = qty_mm(p.get("CabinetThickness"), 19.5)
        r = qty_mm(p.get("RabbetDepth"), 6.35)
        inset_setback = qty_mm(p.get("InsetSetback"), 0.0)
        toe_kick_height = qty_mm(p.get("ToeKickHeight"), 88.9)
        toe_kick_setback = qty_mm(p.get("ToeKickSetback"), 88.9)
        report_height = qty_mm(p.get("CabinetHeight"), 720.0)
        d = CabinetCarcass.derived_dimensions(W, D, t, r)
        print("")
        print("-" * 72)
        print("LOWER CABINET INSTANCE CREATED SUCCESSFULLY")
        print("-" * 72)
        print("Cabinet instance:       ", self.assembly.Name)
        print("Parameters sheet:       ", self.parameters.Name)
        report_style = str(p.get("DoorStyle", "Slab")).strip()
        if report_style not in DOOR_STYLES:
            report_style = "Slab"
        print("Door style:             ", report_style)
        report_mount = str(p.get("DoorMount", "Inset")).strip()
        if report_mount not in DOOR_MOUNTS:
            report_mount = "Inset"
        print("Door mount:             ", report_mount)
        print("Toe kick height:        ", toe_kick_height, "mm")
        print("Toe kick front setback: ", toe_kick_setback, "mm")
        print("Carcass base Z:         ", toe_kick_height, "mm")
        print("Carcass height:         ", report_height - toe_kick_height, "mm")
        print("Inset door setback Y:   ", inset_setback, "mm")
        report_count = qty_int(p.get("DoorCount"), 2)
        report_gap = qty_mm(p.get("DoorGap"), 2.0)
        report_door_t = qty_mm(p.get("DoorThickness"), 19.0)
        report_layout = LowerDoorLayout.calculate(
            width=W,
            height=report_height,
            toe_kick_height=toe_kick_height,
            cabinet_thickness=t,
            door_thickness=report_door_t,
            gap=report_gap,
            count=report_count,
            mount=report_mount,
            inset_setback=inset_setback,
        )
        print("Calculated door width:  ", report_layout["door_width"], "mm")
        print("Calculated door height: ", report_layout["door_height"], "mm")
        print("Calculated door X/Z:    ", report_layout["left_x"], "/", report_layout["z"], "mm")
        print("Door back/reference Y:  ", report_layout["back_y"], "mm")
        print("Door visible front Y:   ", report_layout["back_y"] - report_door_t, "mm")
        print("Carcass parts:           Left Side, Right Side, Top, Bottom, Back")
        print("Stock / rabbet width:   ", t, "mm")
        print("Rabbet depth:           ", r, "mm")
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

def create_lower_cabinet(document, instance_name):
    return LowerCabinetBuilder(document, instance_name).run()

def main():
    document = App.ActiveDocument
    if document is None:
        QtWidgets.QMessageBox.warning(
            None,
            "No Active FreeCAD Document",
            "Open or create the kitchen/layout document first, then run this macro again."
        )
        return None
    return create_lower_cabinet(document, next_lower_cabinet_name(document))



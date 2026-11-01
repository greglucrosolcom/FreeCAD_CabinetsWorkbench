# ============================================================
# PARAMETRIC UPPER OPEN-SHELF CABINET
# FIVE-PART RABBETED CARCASS + TWO FIXED SHELVES
# ============================================================
# Target: FreeCAD 1.1.4
# REVISION: 0.07
#   0.07 - Cabinet Core v1 architecture revision
#          - shared validation, parameter, component, runtime and snap infrastructure
#          - cabinet-specific layout/geometry relationships preserved
#          - no intentional default geometry change from previous validated revision
#
# 0.00 - Baseline Open Shelf Cabinet
#        - 30 in W x 24 in D x 24 in H defaults
#        - DoorCount = 0, 1 or 2
#        - framed-glass doors
#        - controllable DoorFrameWidth
#        - 6 mm recessed glass
#        - two fixed 19 mm shelves at 1/3 and 2/3 usable interior height
#        - active-document independent instance architecture
#        - spreadsheet parameters with fractional-inch display
#        - preference-free endpoint select-to-insert
# 0.01 - Insertion usability revision
#        - first non-endpoint pick displays an Endpoint Required dialog
#        - second pick still accepts a valid endpoint
#        - second non-endpoint pick creates the cabinet at 0,0,0
#        - Esc / right-click still cancel normally
#        - no persistent Draft snap preferences are changed
# 0.02 - Assembly origin snap-point revision
#        - adds a visible Draft Point at local component origin 0,0,0
#        - point is grouped inside the component App::Part
#        - point moves and rotates with the component parent Placement
#        - provides an Endpoint snap reference for Draft Move placement
# 0.03 - Door style / mount revision
#        - adds DoorStyle = Slab / Shaker / Glass
#        - adds DoorMount = Inset / Overlay
#        - retains 0 / 1 / 2 door count behavior
#        - Overlay preserves the original full-envelope door placement
#        - Inset sizes doors from the finished cabinet front opening
#        - adds InsetSetback and DoorPanelThickness parameters
#        - retains framed-glass behavior as the default
# 0.04 - Inset shelf-clearance revision
#        - inset shelves begin behind InsetSetback + DoorThickness
#        - shelf backs remain aligned to the inside face of the cabinet back
#        - overlay and no-door shelf geometry remains unchanged
#        - prevents inset doors from intersecting the two fixed shelves
# 0.05 - Cabinet-family validation / manufacturing-standard revision
#        - target platform updated to FreeCAD 1.1.4
#        - replaces hollow-shell carcass with five manufactured rabbeted parts
#        - adds RabbetDepth as an explicit validated construction parameter
#        - replaces fixed internal shelf thickness with ShelfThickness parameter
#        - retains two shelves centered at 1/3 and 2/3 of usable interior height
#        - reuses standardized CabinetDoor and door-layout geometry patterns
#        - adds reusable ParameterSpec / ValidationResult / validator architecture
#        - enforces cabinet-family dimensional limits and relational geometry rules
#        - distinguishes blocking errors from non-blocking design warnings
#        - uses strict quantity parsing; invalid text is never silently defaulted
#        - validates both creation-dialog input and later spreadsheet recomputes
#        - adds Allowed Range column to the Parameters sheet
#        - disables irrelevant door fields when DoorCount = 0
#        - final geometry checks prevent zero/negative manufactured dimensions
#        - preserves endpoint snapping and active-document instance architecture
# 0.06 - Inclusive hard-range boundary correction
#        - exact minimum and maximum parameter values are valid
#        - adds 0.000001 mm tolerance for floating-point unit conversion noise
#        - prevents valid values such as 12 in = 304.8 mm from being rejected
#        - values meaningfully below minimum or above maximum still fail
#        - no geometry, snapping, assembly or parameter ranges changed
#
# Coordinate system:
# X = cabinet width
# Y = cabinet depth
# Z = cabinet height
# cabinet front/reference plane = Y=0
# cabinet extends +Y
# overlay doors extend toward -Y
# inset doors occupy the finished carcass opening and can move rearward +Y
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
from AdvCabinetComponents import CabinetPanel, RabbetedSidePanel, CabinetCarcass, CabinetDoor
from AdvCabinetSnap import EndpointSnapPointPicker
from AdvCabinetDialog import SchemaCabinetDialog
from AdvCabinetRuntime import CabinetCreationTransaction, sanitize_object_name, next_instance_name, normalized_signature
SHEET_NAME = "Parameters"
CONTROLLER_NAME = "CabinetController"
INSTANCE_BASENAME = "OpenShelfCabinet"
CABINET_CORE_VERSION = 1
CABINET_SCHEMA_VERSION = 2
CABINET_TYPE = "UpperOpenShelf"
GENERATOR_REVISION = "0.07"

INTEGER_PARAMETERS = {"DoorCount"}
TEXT_PARAMETERS = {"DoorStyle", "DoorMount"}
DOOR_STYLES = ("Slab", "Shaker", "Glass")
DOOR_MOUNTS = ("Inset", "Overlay")
PARAMETER_OPTIONS = {
    "DoorCount": "0 | 1 | 2",
    "DoorStyle": "Slab | Shaker | Glass",
    "DoorMount": "Inset | Overlay",
}
PARAM_DEFAULTS = [
    ("CabinetWidth",        "762 mm"),
    ("CabinetDepth",        "609.6 mm"),
    ("CabinetHeight",       "609.6 mm"),
    ("CabinetThickness",    "20 mm"),
    ("RabbetDepth",         "6.35 mm"),
    ("ShelfThickness",      "19 mm"),
    ("DoorThickness",       "19 mm"),
    ("DoorGap",             "2 mm"),
    ("InsetSetback",        "0 mm"),
    ("DoorCount",           "2"),
    ("DoorStyle",           "Glass"),
    ("DoorMount",           "Overlay"),
    ("DoorFrameWidth",      "50.8 mm"),
    ("DoorPanelThickness",  "6 mm"),
    ("GlassThickness",      "6 mm"),
]
PARAM_DEFAULT_MAP = dict(PARAM_DEFAULTS)


PARAMETER_SPECS = {
    "CabinetWidth": ParameterSpec("CabinetWidth", 304.8, 1219.2, "Cabinet Width"),
    "CabinetDepth": ParameterSpec("CabinetDepth", 304.8, 1219.2, "Cabinet Depth"),
    "CabinetHeight": ParameterSpec("CabinetHeight", 406.4, 3657.6, "Cabinet Height"),
    "CabinetThickness": ParameterSpec("CabinetThickness", 6.35, 25.4, "Cabinet Thickness"),
    # This command specifically constructs rabbets, so a positive rabbet is required.
    "RabbetDepth": ParameterSpec("RabbetDepth", 1.5875, 12.7, "Rabbet Depth"),
    "ShelfThickness": ParameterSpec("ShelfThickness", 6.35, 25.4, "Shelf Thickness"),
    "DoorThickness": ParameterSpec("DoorThickness", 12.7, 31.75, "Door Thickness"),
    "DoorGap": ParameterSpec("DoorGap", 1.0, 6.35, "Door Gap"),
    "InsetSetback": ParameterSpec("InsetSetback", 0.0, 25.4, "Inset Setback"),
    "DoorFrameWidth": ParameterSpec("DoorFrameWidth", 25.4, 101.6, "Door Frame Width"),
    "DoorPanelThickness": ParameterSpec("DoorPanelThickness", 3.0, 19.0, "Door Panel Thickness"),
    "GlassThickness": ParameterSpec("GlassThickness", 3.0, 12.7, "Glass Thickness"),
}




def read_parameter_values(sheet):
    """Read one cabinet Parameters sheet using strict parsing and canonical names."""
    params = SheetParams(sheet)
    values = {}
    for name, _default_value in PARAM_DEFAULTS:
        raw = params.get(name, None)
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


class OpenShelfDoorLayout:
    """Centralized one/two-door sizing and placement for the upper open-shelf cabinet."""
    MOUNT_OVERLAY = "Overlay"
    MOUNT_INSET = "Inset"
    @classmethod
    def calculate(cls, width, height, cabinet_thickness, door_thickness, gap, count, mount, inset_setback):
        if width <= 0 or height <= 0:
            raise RuntimeError("Cabinet width and height must be greater than zero.")
        if cabinet_thickness <= 0:
            raise RuntimeError("CabinetThickness must be greater than zero.")
        if count not in (0, 1, 2):
            raise RuntimeError("DoorCount must be 0, 1 or 2.")
        if mount not in DOOR_MOUNTS:
            raise RuntimeError("DoorMount must be Inset or Overlay.")
        if mount == cls.MOUNT_OVERLAY:
            opening_width = width
            door_height = height
            left_x = 0.0
            z = 0.0
            back_y = 0.0
        else:
            opening_width = width - 2.0 * cabinet_thickness
            door_height = height - 2.0 * cabinet_thickness
            if opening_width <= 0 or door_height <= 0:
                raise RuntimeError("CabinetThickness leaves no opening for inset doors.")
            left_x = cabinet_thickness
            z = cabinet_thickness
            # CabinetDoor local geometry extends from -DoorThickness to 0 in Y.
            back_y = door_thickness + inset_setback
        # Count zero keeps a valid one-door envelope available for hidden placeholder geometry.
        if count == 2:
            door_width = (opening_width - gap) / 2.0
        else:
            door_width = opening_width
        if door_width <= 0 or door_height <= 0:
            raise RuntimeError("Door layout leaves no usable door width or height.")
        right_x = left_x if count != 2 else left_x + door_width + gap
        return {
            "door_width": door_width,
            "door_height": door_height,
            "left_x": left_x,
            "right_x": right_x,
            "z": z,
            "back_y": back_y,
            "left_visible": count >= 1,
            "right_visible": count == 2,
        }

class OpenShelfCabinetValidator:
    """Reusable cabinet-family rules plus open-shelf-specific geometry constraints."""
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
        tolerance = OpenShelfCabinetValidator.RANGE_TOLERANCE_MM
        if value < spec.minimum - tolerance or value > spec.maximum + tolerance:
            result.add_error(
                "{} is {:.3f} mm. Allowed range is {}.".format(spec.label, value, spec.limit_text())
            )
    @classmethod
    def validate(cls, values):
        result = ValidationResult()
        required = [name for name, _default in PARAM_DEFAULTS]
        missing = [name for name in required if name not in values]
        if missing:
            result.add_error("Missing parameters: {}.".format(", ".join(missing)))
            return result
        count = values["DoorCount"]
        style = str(values["DoorStyle"])
        mount = str(values["DoorMount"])
        if count not in (0, 1, 2):
            result.add_error("DoorCount must be 0, 1 or 2.")
        if style not in DOOR_STYLES:
            result.add_error("DoorStyle must be Slab, Shaker or Glass.")
        if mount not in DOOR_MOUNTS:
            result.add_error("DoorMount must be Inset or Overlay.")
        for name in (
            "CabinetWidth", "CabinetDepth", "CabinetHeight", "CabinetThickness",
            "RabbetDepth", "ShelfThickness"
        ):
            cls._check_range(result, values, name)
        has_doors = count > 0
        cls._check_range(result, values, "DoorThickness", active=has_doors)
        cls._check_range(result, values, "DoorGap", active=(count == 2))
        cls._check_range(result, values, "InsetSetback", active=(has_doors and mount == "Inset"))
        cls._check_range(result, values, "DoorFrameWidth", active=(has_doors and style in ("Shaker", "Glass")))
        cls._check_range(result, values, "DoorPanelThickness", active=(has_doors and style == "Shaker"))
        cls._check_range(result, values, "GlassThickness", active=(has_doors and style == "Glass"))
        if result.errors:
            return result
        W = float(values["CabinetWidth"])
        D = float(values["CabinetDepth"])
        H = float(values["CabinetHeight"])
        T = float(values["CabinetThickness"])
        R = float(values["RabbetDepth"])
        shelf_t = float(values["ShelfThickness"])
        door_t = float(values["DoorThickness"])
        gap = float(values["DoorGap"])
        inset = float(values["InsetSetback"])
        frame = float(values["DoorFrameWidth"])
        panel = float(values["DoorPanelThickness"])
        glass = float(values["GlassThickness"])
        if R > 0.5 * T:
            result.add_error("RabbetDepth cannot exceed 50% of CabinetThickness.")
        try:
            CabinetCarcass.validate_dimensions(W, D, H, T, R)
        except Exception as exc:
            result.add_error(str(exc))
        interior_h = H - 2.0 * T
        interior_w = W - 2.0 * T
        if shelf_t >= interior_h / 3.0:
            result.add_error(
                "ShelfThickness is too large for two shelves at one-third and two-thirds of the usable interior height."
            )
        if interior_w <= 0:
            result.add_error("CabinetThickness leaves no usable shelf width.")
        layout = None
        if has_doors:
            try:
                layout = OpenShelfDoorLayout.calculate(
                    width=W, height=H, cabinet_thickness=T, door_thickness=door_t,
                    gap=gap, count=count, mount=mount, inset_setback=inset
                )
            except Exception as exc:
                result.add_error(str(exc))
            if mount == "Inset" and inset + door_t > D - T:
                result.add_error(
                    "InsetSetback + DoorThickness must remain in front of the cabinet back's inside face."
                )
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
        # Shelf depth follows the existing Rev0.04 rule: inset fronts clear the door back.
        shelf_front_y = inset + door_t if has_doors and mount == "Inset" else 0.0
        shelf_back_y = D - T
        shelf_depth = shelf_back_y - shelf_front_y
        if shelf_depth <= 0:
            result.add_error("Door setback leaves no usable shelf depth before the cabinet back.")
        if T < 12.7:
            result.add_warning(
                "CabinetThickness is below 12.7 mm (1/2 in). Geometry is permitted, but verify material strength and joinery."
            )
        if shelf_t < 12.7:
            result.add_warning(
                "ShelfThickness is below 12.7 mm (1/2 in). Verify shelf material, loading and deflection."
            )
        if W > 914.4:
            result.add_warning(
                "CabinetWidth exceeds 36 in. Verify shelf span, door hardware, internal support and wall attachment."
            )
        if D > 609.6:
            result.add_warning(
                "CabinetDepth exceeds 24 in. This is unusually deep for an upper cabinet; verify access and wall attachment."
            )
        if H > 1371.6:
            result.add_warning(
                "CabinetHeight exceeds 54 in. This is unusually tall for an upper cabinet; verify wall attachment and internal support."
            )
        if has_doors and (door_t < cls.NORMAL_HINGE_DOOR_MIN or door_t > cls.NORMAL_HINGE_DOOR_MAX):
            result.add_warning(
                "DoorThickness is outside the 15-24 mm normal concealed-hinge design band; verify selected hardware."
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
            "ShelfThickness": p["shelf_thickness"],
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
PARAMETER_SCHEMA = apply_schema_overrides(PARAMETER_SCHEMA, {'CabinetWidth': {'group': 'Cabinet'}, 'CabinetDepth': {'group': 'Cabinet'}, 'CabinetHeight': {'group': 'Cabinet'}, 'CabinetThickness': {'group': 'Cabinet'}, 'RabbetDepth': {'group': 'Cabinet'}, 'ShelfThickness': {'group': 'Interior'}, 'DoorThickness': {'group': 'Doors', 'active_when': (('DoorCount', '>', 0),)}, 'DoorGap': {'group': 'Doors', 'active_when': (('DoorCount', 2),)}, 'InsetSetback': {'group': 'Doors', 'active_when': (('DoorCount', '>', 0), ('DoorMount', 'Inset'))}, 'DoorCount': {'group': 'Doors', 'minimum': 0, 'maximum': 2, 'label': 'Door Count'}, 'DoorStyle': {'group': 'Doors', 'active_when': (('DoorCount', '>', 0),)}, 'DoorMount': {'group': 'Doors', 'active_when': (('DoorCount', '>', 0),)}, 'DoorFrameWidth': {'group': 'Doors', 'active_when': (('DoorCount', '>', 0), ('DoorStyle', ('Shaker', 'Glass')))}, 'DoorPanelThickness': {'group': 'Doors', 'active_when': (('DoorCount', '>', 0), ('DoorStyle', 'Shaker'))}, 'GlassThickness': {'group': 'Doors', 'active_when': (('DoorCount', '>', 0), ('DoorStyle', 'Glass'))}})
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
        super().__init__(sheet, PARAMETER_SCHEMA, title='Upper Open-Shelf Cabinet Parameters', validator=OpenShelfCabinetValidator.validate, notes=('DoorCount may be 0, 1, or 2. Door-related fields are disabled when no doors are selected. Two fixed shelf elevations remain at one-third and two-thirds of the usable interior height.',))





class OpenShelfCabinetFP:
    """FeaturePython controller; geometry is created once and resized on recompute."""
    def __init__(self, obj, assembly, sheet):
        self._building = True
        self._last_signature = None
        self._last_warning_signature = ()
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
            name="{}_OriginPoint".format(prefix), point_size=8
        )
        origin_point.Label = "Assembly Origin Point"
        try:
            origin_point.ViewObject.Visibility = True
        except Exception:
            pass
        p = self._read_parameters(sheet)
        self._validate(p)
        # Build the manufactured carcass and fixed shelves before doors.
        carcass = CabinetCarcass.create(doc, prefix)
        shelf1 = CabinetPanel.create(doc, prefix, "Shelf1", "Shelf 1 - One Third")
        shelf2 = CabinetPanel.create(doc, prefix, "Shelf2", "Shelf 2 - Two Thirds")
        self._update_carcass(carcass, p)
        self._update_shelves(shelf1, shelf2, p)
        try:
            for body in carcass.bodies():
                body.ViewObject.ShapeColor = (0.78, 0.78, 0.74)
            shelf1.body.ViewObject.ShapeColor = (0.78, 0.78, 0.74)
            shelf2.body.ViewObject.ShapeColor = (0.78, 0.78, 0.74)
        except Exception:
            pass
        assembly.addObject(sheet)
        assembly.addObject(origin_point)
        for body in carcass.bodies():
            assembly.addObject(body)
        assembly.addObject(shelf1.body)
        assembly.addObject(shelf2.body)
        doc.recompute()
        # Create permanent door objects last so 0/1/2-door edits never add/remove document objects.
        left = CabinetDoor.create(doc, prefix, "LeftDoor", "Left Door", style=CabinetDoor.STYLE_SLAB)
        right = CabinetDoor.create(doc, prefix, "RightDoor", "Right Door", style=CabinetDoor.STYLE_SLAB)
        # Give both PartDesign Bodies valid initial geometry before applying the requested visibility/style.
        safe_t = 19.0
        left.update(p["width"], p["height"], safe_t, 50.8, 6.0, 6.0, x=0.0, z=0.0, back_y=0.0)
        right.update(p["width"], p["height"], safe_t, 50.8, 6.0, 6.0, x=0.0, z=0.0, back_y=0.0)
        self._update_doors(
            left.body, left.feature, left.glass,
            right.body, right.feature, right.glass, p
        )
        assembly.addObject(left.body)
        assembly.addObject(left.glass)
        assembly.addObject(right.body)
        assembly.addObject(right.glass)
        assembly.addObject(obj)
        required = [sheet, origin_point] + carcass.bodies() + [
            shelf1.body, shelf2.body,
            left.body, left.glass, right.body, right.glass, obj
        ]
        missing = [member.Name for member in required if member not in assembly.Group]
        if missing:
            raise RuntimeError(
                "FreeCAD did not place all open-shelf cabinet members inside '{}'. Missing: {}"
                .format(assembly.Name, ", ".join(missing))
            )
    def onDocumentRestored(self, obj):
        obj.Proxy = self
        self._building = False
        self._last_warning_signature = ()
        self._last_signature = None
    def _assembly(self, obj):
        # Prefer actual current containment so copied/renamed instances resolve safely.
        for parent in obj.InList:
            if parent.TypeId == "App::Part":
                return parent
        name = ""
        try:
            name = str(obj.AssemblyObjectName).strip()
        except Exception:
            pass
        if name:
            assembly = obj.Document.getObject(name)
            if assembly is not None and assembly.TypeId == "App::Part":
                return assembly
        raise RuntimeError("Open Shelf Cabinet Controller cannot resolve its owning App::Part.")
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
        def obj(suffix):
            result = doc.getObject("{}_{}".format(prefix, suffix))
            if result is None:
                raise RuntimeError("Open-shelf object '{}_{}' not found.".format(prefix, suffix))
            return result
        shelf1 = CabinetPanel.from_existing(obj("Shelf1"), obj("Shelf1Blank"))
        shelf2 = CabinetPanel.from_existing(obj("Shelf2"), obj("Shelf2Blank"))
        names = {
            "left_door": "{}_LeftDoor".format(prefix),
            "left_shape": "{}_LeftDoorShape".format(prefix),
            "left_glass": "{}_LeftDoorGlass".format(prefix),
            "right_door": "{}_RightDoor".format(prefix),
            "right_shape": "{}_RightDoorShape".format(prefix),
            "right_glass": "{}_RightDoorGlass".format(prefix),
        }
        g = {key: doc.getObject(name) for key, name in names.items()}
        missing = [name for key, name in names.items() if g[key] is None]
        if missing:
            raise RuntimeError("Open-shelf door geometry is incomplete. Missing: {}".format(", ".join(missing)))
        return carcass, shelf1, shelf2, g
    def _read_parameters(self, sheet):
        values = read_parameter_values(sheet)
        return {
            "width": values["CabinetWidth"],
            "depth": values["CabinetDepth"],
            "height": values["CabinetHeight"],
            "cabinet_thickness": values["CabinetThickness"],
            "rabbet_depth": values["RabbetDepth"],
            "shelf_thickness": values["ShelfThickness"],
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
        result = OpenShelfCabinetValidator.validate_internal(p)
        result.raise_for_errors()
        warning_signature = tuple(result.warnings)
        if warning_signature != getattr(self, "_last_warning_signature", ()):
            self._last_warning_signature = warning_signature
            if warning_signature:
                App.Console.PrintWarning(
                    "Open Shelf Cabinet parameter warning:\n{}\n".format(result.warning_text())
                )
    @staticmethod
    def _shelf_layout(p):
        T = p["cabinet_thickness"]
        D = p["depth"]
        front_y = 0.0
        if p["door_count"] > 0 and p["door_mount"] == "Inset":
            front_y = p["inset_setback"] + p["door_thickness"]
        back_y = D - T
        depth = back_y - front_y
        if depth <= 0:
            raise RuntimeError("Shelf depth must be greater than zero.")
        return {"front_y": front_y, "back_y": back_y, "depth": depth}
    def _update_carcass(self, carcass, p):
        carcass.update(
            width=p["width"], depth=p["depth"], height=p["height"],
            thickness=p["cabinet_thickness"], rabbet_depth=p["rabbet_depth"]
        )
    def _update_shelves(self, shelf1, shelf2, p):
        W = p["width"]
        H = p["height"]
        T = p["cabinet_thickness"]
        shelf_t = p["shelf_thickness"]
        interior_w = W - 2.0 * T
        interior_h = H - 2.0 * T
        shelf_layout = self._shelf_layout(p)
        z1 = T + interior_h / 3.0 - shelf_t / 2.0
        z2 = T + 2.0 * interior_h / 3.0 - shelf_t / 2.0
        shelf1.update(interior_w, shelf_layout["depth"], shelf_t, T, shelf_layout["front_y"], z1)
        shelf2.update(interior_w, shelf_layout["depth"], shelf_t, T, shelf_layout["front_y"], z2)
        try:
            shelf1.body.ViewObject.Visibility = True
            shelf2.body.ViewObject.Visibility = True
        except Exception:
            pass
    def _update_doors(self, left_door, left_shape, left_glass, right_door, right_shape, right_glass, p):
        count = p["door_count"]
        style = p["door_style"]
        left = CabinetDoor.from_existing(left_door, left_shape, left_glass, style)
        right = CabinetDoor.from_existing(right_door, right_shape, right_glass, style)
        if count == 0:
            left.set_visible(False)
            right.set_visible(False)
            return
        layout = OpenShelfDoorLayout.calculate(
            width=p["width"], height=p["height"], cabinet_thickness=p["cabinet_thickness"],
            door_thickness=p["door_thickness"], gap=p["door_gap"], count=count,
            mount=p["door_mount"], inset_setback=p["inset_setback"]
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
        left.set_visible(layout["left_visible"])
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
        carcass, shelf1, shelf2, g = self._geometry(assembly)
        self._update_carcass(carcass, p)
        self._update_shelves(shelf1, shelf2, p)
        self._update_doors(
            g["left_door"], g["left_shape"], g["left_glass"],
            g["right_door"], g["right_shape"], g["right_glass"], p
        )

def validate_dialog_values(values):
    result = OpenShelfCabinetValidator.validate(values)
    return result.valid, result.error_text()

def _sanitize_object_name(name):
    return sanitize_object_name(name, INSTANCE_BASENAME)

def next_open_shelf_cabinet_name(document):
    return next_instance_name(document, INSTANCE_BASENAME)


class OpenShelfCabinetBuilder:
    """Create one independent validated open-shelf cabinet in the active layout document."""
    def __init__(self, document, instance_name):
        if document is None:
            raise ValueError("create_open_shelf_cabinet() requires an existing FreeCAD document.")
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
            print("Open shelf cabinet creation cancelled. The active layout document was not changed.")
            return False
        self.values = dialog.values()
        valid, message = validate_dialog_values(self.values)
        if not valid:
            QtWidgets.QMessageBox.critical(None, "Invalid Open Shelf Cabinet Parameters", message)
            return False
        ParameterTable.update(self.document, self.parameters, self.values)
        ParameterTable.verify(self.parameters)
        return True
    def _accepted(self, point):
        self.insertion_point = App.Vector(point)
        self._picker = None
        try:
            self.assembly = self.document.addObject("App::Part", self.instance_name)
            self.assembly.Label = "Open Shelf Cabinet"
            self.assembly.Placement.Base = App.Vector(self.insertion_point)
            self.controller = self.document.addObject(
                "Part::FeaturePython", "{}_Controller".format(self.instance_name)
            )
            self.controller.Label = "Open Shelf Cabinet Controller"
            OpenShelfCabinetFP(self.controller, self.assembly, self.parameters)
            self.document.recompute()
            self._show()
            self._print_report()
            self._transaction.commit()
        except Exception as exc:
            self._rollback()
            QtWidgets.QMessageBox.critical(None, "Open Shelf Cabinet Creation Error", str(exc))
            App.Console.PrintError("Open shelf cabinet creation failed: {}\n".format(exc))
    def _cancelled(self):
        self._picker = None
        self._rollback()
        print("Open shelf cabinet insertion cancelled. The active layout document was not changed.")
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
        print("PARAMETRIC UPPER OPEN-SHELF CABINET - FIVE-PART RABBETED CARCASS")
        print("FREECAD 1.1.4 - REVISION 0.05")
        print("Target document: {}".format(self.document.Name))
        print("Instance name:   {}".format(self.instance_name))
        print("=" * 72)
    def _print_report(self):
        values = read_parameter_values(self.parameters)
        W = values["CabinetWidth"]
        D = values["CabinetDepth"]
        H = values["CabinetHeight"]
        T = values["CabinetThickness"]
        R = values["RabbetDepth"]
        shelf_t = values["ShelfThickness"]
        count = values["DoorCount"]
        style = values["DoorStyle"]
        mount = values["DoorMount"]
        p = {
            "width": W,
            "depth": D,
            "height": H,
            "cabinet_thickness": T,
            "rabbet_depth": R,
            "shelf_thickness": shelf_t,
            "door_thickness": values["DoorThickness"],
            "door_gap": values["DoorGap"],
            "inset_setback": values["InsetSetback"],
            "door_count": count,
            "door_style": style,
            "door_mount": mount,
            "frame_width": values["DoorFrameWidth"],
            "panel_thickness": values["DoorPanelThickness"],
            "glass_thickness": values["GlassThickness"],
        }
        carcass_d = CabinetCarcass.derived_dimensions(W, D, T, R)
        shelf_layout = OpenShelfCabinetFP._shelf_layout(p)
        interior_h = H - 2.0 * T
        shelf1_center = T + interior_h / 3.0
        shelf2_center = T + 2.0 * interior_h / 3.0
        print("")
        print("-" * 72)
        print("OPEN SHELF CABINET INSTANCE CREATED SUCCESSFULLY")
        print("-" * 72)
        print("Cabinet instance:       ", self.assembly.Name)
        print("Parameters sheet:       ", self.parameters.Name)
        print("Cabinet Width:          ", W, "mm")
        print("Cabinet Depth:          ", D, "mm")
        print("Cabinet Height:         ", H, "mm")
        print("Carcass Stock:          ", T, "mm")
        print("Rabbet Depth:           ", R, "mm")
        print("Carcass parts:           Left Side, Right Side, Top, Bottom, Back")
        print("Top/Bottom/Back width:  ", carcass_d["panel_width"], "mm")
        print("Top/Bottom depth:       ", carcass_d["panel_depth"], "mm")
        print("Shelf Thickness:        ", shelf_t, "mm")
        print("Shelf Front Y:          ", shelf_layout["front_y"], "mm")
        print("Shelf Usable Depth:     ", shelf_layout["depth"], "mm")
        print("Shelf 1 Center Z:       ", shelf1_center, "mm")
        print("Shelf 2 Center Z:       ", shelf2_center, "mm")
        print("Cabinet interior width: ", W - 2.0 * T, "mm")
        print("Cabinet interior depth: ", D - T, "mm")
        print("Cabinet interior height:", interior_h, "mm")
        print("Door Count:             ", count)
        if count == 0:
            print("Door Configuration:      Open Shelving - No Doors")
        else:
            layout = OpenShelfDoorLayout.calculate(
                width=W, height=H, cabinet_thickness=T,
                door_thickness=values["DoorThickness"], gap=values["DoorGap"],
                count=count, mount=mount, inset_setback=values["InsetSetback"]
            )
            print("Door Style:             ", style)
            print("Door Mount:             ", mount)
            print("Door Width:             ", layout["door_width"], "mm" + (" each" if count == 2 else ""))
            print("Door Height:            ", layout["door_height"], "mm")
            print("Door Thickness:         ", values["DoorThickness"], "mm")
            print("Door visible front Y:   ", layout["back_y"] - values["DoorThickness"], "mm")
            if mount == "Inset":
                print("Inset Setback:          ", values["InsetSetback"], "mm")
            if style in ("Shaker", "Glass"):
                print("Door Frame Width:       ", values["DoorFrameWidth"], "mm")
            if style == "Shaker":
                print("Door Panel Thickness:   ", values["DoorPanelThickness"], "mm")
            if style == "Glass":
                print("Glass Thickness:        ", values["GlassThickness"], "mm")
                print("Glass Transparency:      70%")
        if self.insertion_point is not None:
            print("Insertion Point:         X={:.3f}, Y={:.3f}, Z={:.3f} mm".format(
                self.insertion_point.x, self.insertion_point.y, self.insertion_point.z
            ))
        result = OpenShelfCabinetValidator.validate(values)
        if result.warnings:
            print("")
            print("Design warnings:")
            for warning in result.warnings:
                print("-", warning)
        print("")
        print("Edit '{}' to resize only this cabinet.".format(self.parameters.Name))
        print("Move/rotate '{}' with its App::Part Placement.".format(self.assembly.Name))
        print("=" * 72)
        print("")

def create_open_shelf_cabinet(document, instance_name):
    """Begin creation of one independent open-shelf cabinet inside *document*."""
    return OpenShelfCabinetBuilder(document, instance_name).run()

def main():
    """Workbench entry point; do not call automatically when this module is imported."""
    document = App.ActiveDocument
    if document is None:
        QtWidgets.QMessageBox.warning(
            None,
            "No Active FreeCAD Document",
            "Open or create the kitchen/layout document first, then run this macro again."
        )
        return None
    return create_open_shelf_cabinet(document, next_open_shelf_cabinet_name(document))

# ============================================================
# WORKBENCH MODULE NOTE
# ============================================================
# Do not call main() automatically here.
# CabinetsWorkbench.py imports this module, calls main(), and retains the
# returned OpenShelfCabinetBuilder while endpoint selection is active.

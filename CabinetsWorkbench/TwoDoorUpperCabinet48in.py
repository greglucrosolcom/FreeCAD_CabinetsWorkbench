# ============================================================
# PARAMETRIC UPPER CABINET
# FIVE-PART RABBETED CARCASS VERSION
# ============================================================
# Target: FreeCAD 1.1.4
# REVISION: 0.19
#
# 0.09 - Five-part manufactured carcass revision
#        - replaces hollow-shell CabinetBody with five actual cabinet parts
#        - Left Side and Right Side are independent PartDesign::Body objects
#        - Top, Bottom and Back are independent PartDesign::Body objects
#        - side panels contain real top, bottom and back rabbet cuts
#        - default cabinet stock is 3/4 in = 19.05 mm
#        - default rabbet depth is 1/4 in = 6.35 mm
#        - rabbet width is derived from CabinetThickness; no redundant parameter
#        - top/bottom/back penetrate the side rabbets by RabbetDepth
#        - preserves one/two-door behavior and Slab/Shaker/Glass door styles
#        - preserves internal Parameters sheet and FeaturePython controller
#        - preserves assembly-origin Draft Point and two-attempt endpoint insertion
#        - uses FreeCAD's canonical shared Draft GUI Snapper through DraftTools
#
# 0.10 - Overlay / Inset door-mount revision
#        - adds native Data-tab DoorMount = Overlay / Inset
#        - adds InsetReveal dimensional parameter; default 2.4 mm (~3/32 in)
#        - adds UpperDoorLayout to centralize door size and placement logic
#        - Overlay preserves Revision 0.09 door geometry exactly
#        - Inset doors fit inside the carcass front opening
#        - inset perimeter clearance uses InsetReveal
#        - two-door center clearance continues to use DoorGap
#        - inset door front face is flush with cabinet front plane Y=0
#        - Slab, Shaker and Glass remain valid with either mounting method
#        - preserves five-part rabbeted carcass and proven endpoint snap behavior
#
# 0.11 - Recessed inset-door revision
#        - adds InsetDepth parameter; default 19.05 mm = 3/4 in
#        - InsetReveal continues to control X/Z perimeter clearance
#        - DoorGap continues to control the two-door center clearance
#        - inset door face is recessed +Y by InsetDepth from cabinet front Y=0
#        - inset door back plane = InsetDepth + DoorThickness
#        - Overlay placement remains identical to Revision 0.10
#        - validates that recessed inset door depth remains inside CabinetDepth
#        - preserves Slab / Shaker / Glass, one/two-door logic, carcass and snapping
#
# 0.12 - True inset-depth sizing revision
#        - InsetDepth now controls inset geometry in X, Y and Z
#        - inset door width is reduced by 2 * InsetDepth
#        - inset door height is reduced by 2 * InsetDepth
#        - inset door X and Z positions are both InsetDepth
#        - inset door front face is recessed +Y by InsetDepth
#        - two-door center clearance continues to use DoorGap
#        - removes InsetReveal from active inset sizing to avoid competing controls
#        - Overlay behavior remains unchanged
#        - preserves five-part rabbeted carcass and all door styles
#
# 0.13 - Corrected inset-opening and Y-placement revision
#        - inset sizing starts from the actual carcass front opening
#        - opening width = CabinetWidth - 2 * CabinetThickness
#        - opening height = CabinetHeight - 2 * CabinetThickness
#        - InsetDepth is then removed from both X and Z edges of that opening
#        - two-door center clearance continues to use DoorGap
#        - inset X/Z origin = CabinetThickness + InsetDepth
#        - fixes Y placement so DoorThickness is not applied twice
#        - inset door back/reference plane = +InsetDepth
#        - with InsetDepth approximately equal to DoorThickness, the door face
#          is approximately flush with the cabinet front while the carcass
#          perimeter remains exposed
#        - Overlay behavior remains unchanged
#
# 0.14 - Explicit inset-geometry and selection revision
#        - opening dialog now defaults DoorMount to Inset for direct testing
#        - Overlay remains available from the same selector and Data property
#        - inset width = CabinetWidth - 2 * InsetDepth
#        - inset height = CabinetHeight - 2 * InsetDepth
#        - two-door center gap is then removed before dividing the width
#        - inset X = InsetDepth and Z = InsetDepth
#        - inset door front face = +InsetDepth in cabinet Y
#        - because CabinetDoor geometry extends toward -Y from its reference
#          plane, inset back_y = InsetDepth + DoorThickness
#        - creation report prints calculated door dimensions and Y positions
#          so the selected branch can be verified directly in FreeCAD
#
# 0.15 - Front-opening / late-door-creation revision
#        - creates and updates the five-piece carcass before creating any doors
#        - recomputes the carcass before the door objects are constructed
#        - inset opening width = CabinetWidth - 2 * CabinetThickness
#        - inset opening height = CabinetHeight - 2 * CabinetThickness
#        - one inset door uses the complete carcass opening
#        - two inset doors divide the same opening after subtracting DoorGap
#        - inset X/Z origin = CabinetThickness
#        - removes InsetDepth from active door sizing
#        - replaces it with independent InsetSetback for Y only
#        - InsetSetback default = 0 mm, making the inset door face flush at Y=0
#        - a positive InsetSetback moves the complete door rearward into +Y
#        - Overlay behavior, door styles, rabbet carcass and snapping are retained
#
# 0.16 - Parameter-driven Overlay / Inset revision
#        - adds DoorMount to the Parameters spreadsheet
#        - DoorMount choices are Inset and Overlay
#        - creation dialog reads and writes the same DoorMount parameter
#        - removes the duplicate controller DoorMount enumeration so there is
#          one authoritative source of truth for mounting method
#        - Overlay reuses the original Revision 0.08 geometry:
#              one door: W x H, X=0, Z=0, back_y=0
#              two doors: (W-DoorGap)/2 x H, back_y=0
#          CabinetDoor geometry then projects outward toward negative Y
#        - Inset preserves Revision 0.15 front-opening geometry:
#              opening W = CabinetWidth - 2*CabinetThickness
#              opening H = CabinetHeight - 2*CabinetThickness
#        - doors continue to be created after the completed carcass
#        - InsetSetback remains an independent Y-only inset adjustment
#
# 0.17 - Parameter-driven DoorStyle + Options-column revision
#        - adds DoorStyle to the Parameters spreadsheet
#        - DoorStyle choices are Slab, Shaker and Glass
#        - DoorMount remains in the Parameters spreadsheet
#        - removes the duplicate controller DoorStyle enumeration
#        - Parameters sheet is now the single authoritative source for both
#          DoorStyle and DoorMount
#        - creation dialog reads and writes DoorStyle and DoorMount from/to
#          the same Parameters sheet
#        - adds spreadsheet Options column:
#              DoorCount: 1 | 2
#              DoorStyle: Slab | Shaker | Glass
#              DoorMount: Inset | Overlay
#        - preserves the proven Revision 0.16 Overlay / Inset geometry
#        - preserves late door creation after the completed carcass
#
# 0.18 - Cabinet-family validation standard
#        - targets FreeCAD 1.1.4
#        - strict parsing: invalid user/spreadsheet text is never silently replaced
#        - reusable ParameterSpec / ValidationResult / UpperCabinetValidator pattern
#        - hard dimensional envelopes for cabinet, stock and door inputs
#        - geometry-dependent relational checks remain centralized
#        - warning tier added for unusual but geometrically permitted dimensions
#        - spreadsheet adds an Allowed Range column
#        - dialog disables style/mount fields that do not apply
#        - default CabinetDepth standardized from 300 mm to 304.8 mm (12 in)
#        - existing carcass, door, insertion and Draft Snapper geometry preserved
#
#
# 0.19 - Inclusive hard-range boundary patch
#        - exact minimum and maximum dimensional limits are valid
#        - adds 1e-6 mm tolerance for microscopic FreeCAD unit-conversion noise
#        - values genuinely outside the permitted range remain blocking errors
#        - no cabinet geometry, parameter ranges, warnings or snap behavior changed
#
# Coordinate system:
# X = cabinet width
# Y = cabinet depth
# Z = cabinet height
# cabinet front/reference plane = Y=0
# cabinet extends +Y
# doors extend toward -Y
#
# Carcass construction:
# Left Side / Right Side:
#   full height x full depth x stock thickness
#   top rabbet:    stock-width recess, RabbetDepth into inside face
#   bottom rabbet: stock-width recess, RabbetDepth into inside face
#   back rabbet:   stock-width recess, RabbetDepth into inside face
#
# Top / Bottom:
#   width = CabinetWidth - 2*(CabinetThickness - RabbetDepth)
#   depth = CabinetDepth - CabinetThickness
#   thickness = CabinetThickness
#
# Back:
#   width = CabinetWidth - 2*(CabinetThickness - RabbetDepth)
#   thickness in Y = CabinetThickness
#   height = CabinetHeight
# ============================================================
import FreeCAD as App
import FreeCADGui as Gui
import Draft
import Part
import warnings
from PySide import QtWidgets
from pivy import coin
from draftutils import gui_utils

SHEET_NAME = "Parameters"
INSTANCE_BASENAME = "UpperCabinet"
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
    ("CabinetDepth",       "304.8 mm"),
    ("CabinetHeight",      "720 mm"),
    ("CabinetThickness",   "19.5 mm"),
    ("RabbetDepth",        "6.35 mm"),
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

class ParameterSpec:
    """Reusable hard-limit metadata for one dimensional cabinet parameter."""
    def __init__(self, name, minimum, maximum, label=None):
        self.name = name
        self.minimum = float(minimum)
        self.maximum = float(maximum)
        self.label = label or name
    @staticmethod
    def _compact(value):
        return ("{:.4f}".format(float(value))).rstrip("0").rstrip(".")
    def limit_text(self):
        min_in = self.minimum / 25.4
        max_in = self.maximum / 25.4
        return "{}-{} mm ({}-{} in)".format(
            self._compact(self.minimum), self._compact(self.maximum),
            self._compact(min_in), self._compact(max_in)
        )

PARAMETER_SPECS = {
    "CabinetWidth": ParameterSpec("CabinetWidth", 304.8, 1219.2, "Cabinet Width"),
    "CabinetDepth": ParameterSpec("CabinetDepth", 304.8, 1219.2, "Cabinet Depth"),
    "CabinetHeight": ParameterSpec("CabinetHeight", 406.4, 3657.6, "Cabinet Height"),
    "CabinetThickness": ParameterSpec("CabinetThickness", 6.35, 25.4, "Cabinet Thickness"),
    # This command is specifically a rabbeted carcass, so a positive rabbet is required.
    "RabbetDepth": ParameterSpec("RabbetDepth", 1.5875, 12.7, "Rabbet Depth"),
    "DoorThickness": ParameterSpec("DoorThickness", 12.7, 31.75, "Door Thickness"),
    "DoorGap": ParameterSpec("DoorGap", 1.0, 6.35, "Door Gap"),
    "InsetSetback": ParameterSpec("InsetSetback", 0.0, 25.4, "Inset Setback"),
    "DoorFrameWidth": ParameterSpec("DoorFrameWidth", 25.4, 101.6, "Door Frame Width"),
    "DoorPanelThickness": ParameterSpec("DoorPanelThickness", 3.0, 19.0, "Door Panel Thickness"),
    "GlassThickness": ParameterSpec("GlassThickness", 3.0, 12.7, "Glass Thickness"),
}

class SheetParams:
    def __init__(self, sheet, row_start=2, row_end=30):
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
        self.sheet.set("B{}".format(row), str(value))

def qty_mm(value, fallback=None, parameter_name="Length"):
    """Parse a FreeCAD length; missing values may use a fallback, invalid text never does."""
    if value is None or not str(value).strip():
        if fallback is not None:
            return float(fallback)
        raise ValueError("{} is required.".format(parameter_name))
    text = str(value).strip()
    if all(c.isdigit() or c in ".-+" for c in text):
        text += " mm"
    try:
        return float(App.Units.Quantity(text).Value)
    except Exception:
        raise ValueError("{} must be a valid length, for example 600 mm or 24 in.".format(parameter_name))

def qty_int(value, fallback=None, parameter_name="Integer value"):
    """Parse an exact integer; fractional text is rejected rather than rounded."""
    if value is None or not str(value).strip():
        if fallback is not None:
            return int(fallback)
        raise ValueError("{} is required.".format(parameter_name))
    try:
        number = float(str(value).strip())
    except Exception:
        raise ValueError("{} must be an integer.".format(parameter_name))
    if not number.is_integer():
        raise ValueError("{} must be a whole number.".format(parameter_name))
    return int(number)

def read_parameter_values(sheet):
    """Read one cabinet's Parameters sheet using canonical names and strict parsing."""
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

class ValidationResult:
    """Collect all blocking errors and non-blocking warnings in one validation pass."""
    def __init__(self):
        self.errors = []
        self.warnings = []
    @property
    def valid(self):
        return not self.errors
    def add_error(self, message):
        if message not in self.errors:
            self.errors.append(message)
    def add_warning(self, message):
        if message not in self.warnings:
            self.warnings.append(message)
    def error_text(self):
        return "\n".join("- {}".format(item) for item in self.errors)
    def warning_text(self):
        return "\n".join("- {}".format(item) for item in self.warnings)
    def raise_for_errors(self):
        if self.errors:
            raise RuntimeError(self.error_text())

class UpperCabinetValidator:
    """Reusable upper-cabinet profile: hard limits + geometry-dependent rules."""
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
        tolerance = UpperCabinetValidator.RANGE_TOLERANCE_MM
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
            "RabbetDepth", "DoorThickness"
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
        layout = None
        try:
            layout = UpperDoorLayout.calculate(
                width=W, height=H, cabinet_thickness=T, door_thickness=door_t,
                gap=gap, count=door_count, mount=mount, inset_setback=inset
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
                "CabinetWidth exceeds 36 in. Verify door hardware, internal support and wall attachment for the intended load."
            )
        if D > 609.6:
            result.add_warning(
                "CabinetDepth exceeds 24 in. This is unusually deep for an upper cabinet; verify access, support and wall attachment."
            )
        if H > 1371.6:
            result.add_warning(
                "CabinetHeight exceeds 54 in. This is unusually tall for an upper cabinet; verify wall attachment and internal support."
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
        ParameterTable.update_inches_column(sheet)
        ParameterTable.update_options_column(sheet)
        ParameterTable.update_limits_column(sheet)
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
        for row, (name, default_value) in enumerate(PARAM_DEFAULTS, start=2):
            if name in INTEGER_PARAMETERS or name in TEXT_PARAMETERS:
                continue
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
            sheet.setColumnWidth("D", 240)
        except Exception:
            pass
        for row, (name, _default_value) in enumerate(PARAM_DEFAULTS, start=2):
            sheet.set("D{}".format(row), PARAMETER_OPTIONS.get(name, ""))
    @staticmethod
    def update_limits_column(sheet):
        sheet.set("E1", "Allowed Range")
        try:
            sheet.setColumnWidth("E", 280)
        except Exception:
            pass
        for row, (name, _default_value) in enumerate(PARAM_DEFAULTS, start=2):
            spec = PARAMETER_SPECS.get(name)
            sheet.set("E{}".format(row), spec.limit_text() if spec is not None else "")
    @staticmethod
    def update(doc, sheet, values):
        params = SheetParams(sheet)
        for name, default_value in PARAM_DEFAULTS:
            value = values.get(name, params.get(name, default_value))
            if name in INTEGER_PARAMETERS:
                text = str(int(value))
            elif name in TEXT_PARAMETERS:
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
        ParameterTable.update_limits_column(sheet)
        doc.recompute()
    @staticmethod
    def verify(sheet):
        failures = []
        params = SheetParams(sheet)
        for name, _default in PARAM_DEFAULTS:
            value = params.get(name, None)
            text = "" if value is None else str(value).strip()
            if not text or "#REF" in text.upper():
                failures.append(name)
        if failures:
            raise RuntimeError("Parameters did not resolve: {}".format(", ".join(failures)))
        values = read_parameter_values(sheet)
        result = UpperCabinetValidator.validate(values)
        result.raise_for_errors()

class CabinetDialog(QtWidgets.QDialog):
    def __init__(self, sheet):
        super().__init__()
        p = SheetParams(sheet)
        self._validated_values = None
        self.setWindowTitle("Upper Cabinet Parameters")
        layout = QtWidgets.QFormLayout(self)
        fields = [
            ("width", "CabinetWidth", 600.0, "Cabinet Width / X:"),
            ("depth", "CabinetDepth", 304.8, "Cabinet Depth / Y:"),
            ("height", "CabinetHeight", 720.0, "Cabinet Height / Z:"),
            ("cabinet_thickness", "CabinetThickness", 19.5, "Carcass Stock Thickness:"),
            ("rabbet_depth", "RabbetDepth", 6.35, "Rabbet Depth:"),
            ("door_thickness", "DoorThickness", 19.0, "Door Thickness:"),
            ("door_gap", "DoorGap", 2.0, "Door Gap:"),
            ("inset_setback", "InsetSetback", 0.0, "Inset Door Setback / Y:"),
            ("frame_width", "DoorFrameWidth", 50.0, "Door Frame Width:"),
            ("panel_thickness", "DoorPanelThickness", 6.0, "Door Panel Thickness:"),
            ("glass_thickness", "GlassThickness", 6.0, "Glass Thickness:"),
        ]
        self._field_specs = fields
        for attr, key, fallback, label in fields:
            raw = p.get(key, PARAM_DEFAULT_MAP[key])
            widget = QtWidgets.QLineEdit(str(qty_mm(raw, fallback, key)))
            spec = PARAMETER_SPECS.get(key)
            if spec is not None:
                widget.setToolTip("Allowed range: {}. FreeCAD units such as mm or in are accepted.".format(spec.limit_text()))
            setattr(self, attr, widget)
            layout.addRow(label, widget)
        door_count = qty_int(p.get("DoorCount", "2"), 2, "DoorCount")
        if door_count not in (1, 2):
            door_count = 2
        self.door_count = QtWidgets.QComboBox()
        self.door_count.addItems(["1", "2"])
        self.door_count.setCurrentText(str(door_count))
        style = str(p.get("DoorStyle", "Slab")).strip()
        if style not in DOOR_STYLES:
            style = "Slab"
        self.door_style = QtWidgets.QComboBox()
        self.door_style.addItems(list(DOOR_STYLES))
        self.door_style.setCurrentText(style)
        mount = str(p.get("DoorMount", "Inset")).strip()
        if mount not in DOOR_MOUNTS:
            mount = "Inset"
        self.door_mount = QtWidgets.QComboBox()
        self.door_mount.addItems(list(DOOR_MOUNTS))
        self.door_mount.setCurrentText(mount)
        layout.addRow("Number of Doors:", self.door_count)
        layout.addRow("Door Style:", self.door_style)
        layout.addRow("Door Mount:", self.door_mount)
        self.door_count.currentTextChanged.connect(self._update_applicable_fields)
        self.door_style.currentTextChanged.connect(self._update_applicable_fields)
        self.door_mount.currentTextChanged.connect(self._update_applicable_fields)
        self._update_applicable_fields()
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    def _update_applicable_fields(self, *_args):
        style = str(self.door_style.currentText())
        mount = str(self.door_mount.currentText())
        count = int(self.door_count.currentText())
        self.door_gap.setEnabled(count == 2)
        self.inset_setback.setEnabled(mount == "Inset")
        self.frame_width.setEnabled(style in ("Shaker", "Glass"))
        self.panel_thickness.setEnabled(style == "Shaker")
        self.glass_thickness.setEnabled(style == "Glass")
    def values(self):
        if self._validated_values is not None:
            return dict(self._validated_values)
        result = {}
        style = str(self.door_style.currentText())
        mount = str(self.door_mount.currentText())
        count = qty_int(self.door_count.currentText(), None, "DoorCount")
        active = {
            "DoorGap": count == 2,
            "InsetSetback": mount == "Inset",
            "DoorFrameWidth": style in ("Shaker", "Glass"),
            "DoorPanelThickness": style == "Shaker",
            "GlassThickness": style == "Glass",
        }
        for attr, key, fallback, _label in self._field_specs:
            try:
                result[key] = qty_mm(getattr(self, attr).text(), fallback, key)
            except ValueError:
                if active.get(key, True):
                    raise
                result[key] = float(fallback)
        result["DoorCount"] = count
        result["DoorStyle"] = style
        result["DoorMount"] = mount
        return result
    def accept(self):
        try:
            values = self.values()
        except Exception as exc:
            QtWidgets.QMessageBox.critical(None, "Invalid Upper Cabinet Parameters", str(exc))
            return
        result = UpperCabinetValidator.validate(values)
        if result.errors:
            QtWidgets.QMessageBox.critical(
                None, "Invalid Upper Cabinet Parameters",
                "Correct the following before creating the cabinet:\n\n{}".format(result.error_text())
            )
            return
        if result.warnings:
            choice = QtWidgets.QMessageBox.warning(
                None, "Upper Cabinet Parameter Warning",
                "The cabinet is geometrically valid, but review these conditions:\n\n{}\n\nContinue?".format(result.warning_text()),
                QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
                QtWidgets.QMessageBox.Cancel
            )
            if choice != QtWidgets.QMessageBox.Ok:
                return
        self._validated_values = dict(values)
        super().accept()

class CabinetPanel:
    """One manufactured rectangular cabinet panel."""
    def __init__(self, body, blank):
        self.body = body
        self.blank = blank
    @classmethod
    def create(cls, doc, prefix, component_name, label):
        body = doc.addObject("PartDesign::Body", "{}_{}".format(prefix, component_name))
        body.Label = label
        blank = body.newObject("PartDesign::AdditiveBox", "{}_{}Blank".format(prefix, component_name))
        blank.Label = "{} Blank".format(label)
        return cls(body, blank)
    @classmethod
    def from_existing(cls, body, blank):
        return cls(body, blank)
    def update(self, length, depth, height, x=0.0, y=0.0, z=0.0):
        if length <= 0 or depth <= 0 or height <= 0:
            raise RuntimeError("{} dimensions must be greater than zero.".format(self.body.Label))
        self.body.Placement = App.Placement(App.Vector(x, y, z), App.Rotation())
        self.blank.Placement = App.Placement()
        self.blank.Length = length
        self.blank.Width = depth
        self.blank.Height = height

class RabbetedSidePanel:
    """Side panel with actual top, bottom and back rabbets cut from its inside face."""
    LEFT = "Left"
    RIGHT = "Right"
    def __init__(self, body, blank, bottom_cut, top_cut, back_cut, side):
        self.body = body
        self.blank = blank
        self.bottom_cut = bottom_cut
        self.top_cut = top_cut
        self.back_cut = back_cut
        self.side = side
    @classmethod
    def create(cls, doc, prefix, side):
        if side not in (cls.LEFT, cls.RIGHT):
            raise ValueError("Side must be Left or Right.")
        component_name = "{}Side".format(side)
        body = doc.addObject("PartDesign::Body", "{}_{}".format(prefix, component_name))
        body.Label = "{} Side".format(side)
        blank = body.newObject("PartDesign::AdditiveBox", "{}_{}Blank".format(prefix, component_name))
        blank.Label = "{} Side Blank".format(side)
        bottom_cut = body.newObject("PartDesign::SubtractiveBox", "{}_{}BottomRabbet".format(prefix, component_name))
        bottom_cut.Label = "{} Side Bottom Rabbet".format(side)
        top_cut = body.newObject("PartDesign::SubtractiveBox", "{}_{}TopRabbet".format(prefix, component_name))
        top_cut.Label = "{} Side Top Rabbet".format(side)
        back_cut = body.newObject("PartDesign::SubtractiveBox", "{}_{}BackRabbet".format(prefix, component_name))
        back_cut.Label = "{} Side Back Rabbet".format(side)
        return cls(body, blank, bottom_cut, top_cut, back_cut, side)
    @classmethod
    def from_existing(cls, body, blank, bottom_cut, top_cut, back_cut, side):
        return cls(body, blank, bottom_cut, top_cut, back_cut, side)
    def update(self, thickness, depth, height, rabbet_depth, panel_depth, x):
        if thickness <= 0 or depth <= 0 or height <= 0 or rabbet_depth <= 0 or panel_depth <= 0:
            raise RuntimeError("Rabbeted side-panel dimensions must all be greater than zero.")
        self.body.Placement = App.Placement(App.Vector(x, 0.0, 0.0), App.Rotation())
        self.blank.Placement = App.Placement()
        self.blank.Length = thickness
        self.blank.Width = depth
        self.blank.Height = height
        cut_x = thickness - rabbet_depth if self.side == self.LEFT else 0.0
        self.bottom_cut.Length = rabbet_depth
        self.bottom_cut.Width = panel_depth
        self.bottom_cut.Height = thickness
        self.bottom_cut.Placement.Base = App.Vector(cut_x, 0.0, 0.0)
        self.top_cut.Length = rabbet_depth
        self.top_cut.Width = panel_depth
        self.top_cut.Height = thickness
        self.top_cut.Placement.Base = App.Vector(cut_x, 0.0, height - thickness)
        self.back_cut.Length = rabbet_depth
        self.back_cut.Width = thickness
        self.back_cut.Height = height
        self.back_cut.Placement.Base = App.Vector(cut_x, panel_depth, 0.0)

class CabinetCarcass:
    """Five-piece plywood carcass with actual rabbets in both side panels."""
    def __init__(self, left, right, top, bottom, back):
        self.left = left
        self.right = right
        self.top = top
        self.bottom = bottom
        self.back = back
    @classmethod
    def create(cls, doc, prefix):
        left = RabbetedSidePanel.create(doc, prefix, RabbetedSidePanel.LEFT)
        right = RabbetedSidePanel.create(doc, prefix, RabbetedSidePanel.RIGHT)
        top = CabinetPanel.create(doc, prefix, "Top", "Top")
        bottom = CabinetPanel.create(doc, prefix, "Bottom", "Bottom")
        back = CabinetPanel.create(doc, prefix, "Back", "Back")
        return cls(left, right, top, bottom, back)
    @classmethod
    def from_document(cls, doc, prefix):
        def obj(suffix):
            result = doc.getObject("{}_{}".format(prefix, suffix))
            if result is None:
                raise RuntimeError("Cabinet carcass object '{}_{}' not found.".format(prefix, suffix))
            return result
        left = RabbetedSidePanel.from_existing(
            obj("LeftSide"), obj("LeftSideBlank"), obj("LeftSideBottomRabbet"),
            obj("LeftSideTopRabbet"), obj("LeftSideBackRabbet"), RabbetedSidePanel.LEFT
        )
        right = RabbetedSidePanel.from_existing(
            obj("RightSide"), obj("RightSideBlank"), obj("RightSideBottomRabbet"),
            obj("RightSideTopRabbet"), obj("RightSideBackRabbet"), RabbetedSidePanel.RIGHT
        )
        top = CabinetPanel.from_existing(obj("Top"), obj("TopBlank"))
        bottom = CabinetPanel.from_existing(obj("Bottom"), obj("BottomBlank"))
        back = CabinetPanel.from_existing(obj("Back"), obj("BackBlank"))
        return cls(left, right, top, bottom, back)
    @staticmethod
    def validate_dimensions(width, depth, height, thickness, rabbet_depth):
        if width <= 0 or depth <= 0 or height <= 0:
            raise RuntimeError("Cabinet Width, Depth and Height must be greater than zero.")
        if thickness <= 0:
            raise RuntimeError("CabinetThickness must be greater than zero.")
        if rabbet_depth <= 0:
            raise RuntimeError("RabbetDepth must be greater than zero.")
        if rabbet_depth >= thickness:
            raise RuntimeError("RabbetDepth must be less than CabinetThickness.")
        if rabbet_depth > 0.5 * thickness:
            raise RuntimeError("RabbetDepth cannot exceed 50% of CabinetThickness.")
        if width - 2.0 * thickness <= 0:
            raise RuntimeError("CabinetThickness leaves no usable interior width.")
        if depth - thickness <= 0:
            raise RuntimeError("CabinetThickness leaves no usable top/bottom panel depth.")
        if height - 2.0 * thickness <= 0:
            raise RuntimeError("CabinetThickness leaves no usable interior height.")
        panel_width = width - 2.0 * (thickness - rabbet_depth)
        if panel_width <= 0:
            raise RuntimeError("Stock thickness and RabbetDepth leave no usable top/bottom/back width.")
    @staticmethod
    def derived_dimensions(width, depth, thickness, rabbet_depth):
        return {
            "panel_width": width - 2.0 * (thickness - rabbet_depth),
            "panel_depth": depth - thickness,
            "rabbet_width": thickness,
        }
    def update(self, width, depth, height, thickness, rabbet_depth):
        self.validate_dimensions(width, depth, height, thickness, rabbet_depth)
        d = self.derived_dimensions(width, depth, thickness, rabbet_depth)
        panel_width = d["panel_width"]
        panel_depth = d["panel_depth"]
        self.left.update(thickness, depth, height, rabbet_depth, panel_depth, 0.0)
        self.right.update(thickness, depth, height, rabbet_depth, panel_depth, width - thickness)
        panel_x = thickness - rabbet_depth
        self.bottom.update(panel_width, panel_depth, thickness, panel_x, 0.0, 0.0)
        self.top.update(panel_width, panel_depth, thickness, panel_x, 0.0, height - thickness)
        self.back.update(panel_width, thickness, height, panel_x, panel_depth, 0.0)
    def bodies(self):
        return [self.left.body, self.right.body, self.top.body, self.bottom.body, self.back.body]
    def set_visible(self, visible):
        state = bool(visible)
        for body in self.bodies():
            try:
                body.ViewObject.Visibility = state
            except Exception:
                pass

class CabinetDoor:
    STYLE_SLAB = "Slab"
    STYLE_SHAKER = "Shaker"
    STYLE_GLASS = "Glass"
    def __init__(self, body, feature, glass, style=STYLE_SLAB):
        self.body = body
        self.feature = feature
        self.glass = glass
        self.style = style
        if style not in (self.STYLE_SLAB, self.STYLE_SHAKER, self.STYLE_GLASS):
            raise ValueError("Unsupported CabinetDoor style: {}".format(style))
    @classmethod
    def create(cls, doc, prefix, component_name, label, style=STYLE_SLAB):
        body = doc.addObject("PartDesign::Body", "{}_{}".format(prefix, component_name))
        body.Label = label
        feature = body.newObject("PartDesign::Feature", "{}_{}Shape".format(prefix, component_name))
        feature.Label = "{} Shape".format(label)
        glass = doc.addObject("Part::Feature", "{}_{}Glass".format(prefix, component_name))
        glass.Label = "{} Glass".format(label)
        try:
            glass.ViewObject.ShapeColor = (0.60, 0.80, 0.90)
            glass.ViewObject.Transparency = 70
            glass.ViewObject.Visibility = False
        except Exception:
            pass
        return cls(body, feature, glass, style)
    @classmethod
    def from_existing(cls, body, feature, glass, style=STYLE_SLAB):
        return cls(body, feature, glass, style)
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
    @classmethod
    def _glass_shapes(cls, width, height, thickness, frame_width, glass_thickness):
        frame = cls._frame_shape(width, height, thickness, frame_width)
        opening_width = width - 2.0 * frame_width
        opening_height = height - 2.0 * frame_width
        glass_y = -(thickness + glass_thickness) / 2.0
        glass = Part.makeBox(opening_width, glass_thickness, opening_height, App.Vector(frame_width, glass_y, frame_width))
        return frame, glass
    def update(self, width, height, thickness, frame_width, panel_thickness, glass_thickness, x=0.0, z=0.0, back_y=0.0):
        if width <= 0 or height <= 0 or thickness <= 0:
            raise RuntimeError("CabinetDoor dimensions must be greater than zero.")
        if self.style in (self.STYLE_SHAKER, self.STYLE_GLASS):
            if frame_width <= 0:
                raise RuntimeError("DoorFrameWidth must be greater than zero.")
            if width - 2.0 * frame_width <= 0 or height - 2.0 * frame_width <= 0:
                raise RuntimeError("DoorFrameWidth leaves no center opening.")
        if self.style == self.STYLE_SHAKER:
            if panel_thickness <= 0 or panel_thickness > thickness:
                raise RuntimeError("DoorPanelThickness must be > 0 and <= DoorThickness.")
        if self.style == self.STYLE_GLASS:
            if glass_thickness <= 0 or glass_thickness > thickness:
                raise RuntimeError("GlassThickness must be > 0 and <= DoorThickness.")
        placement = App.Placement(App.Vector(x, back_y, z), App.Rotation())
        self.body.Placement = placement
        self.feature.Placement = App.Placement()
        if self.style == self.STYLE_SLAB:
            self.feature.Shape = self._slab_shape(width, height, thickness)
            self.glass.Shape = Part.Shape()
            self.glass.Placement = placement
            try:
                self.glass.ViewObject.Visibility = False
            except Exception:
                pass
        elif self.style == self.STYLE_SHAKER:
            self.feature.Shape = self._shaker_shape(width, height, thickness, frame_width, panel_thickness)
            self.glass.Shape = Part.Shape()
            self.glass.Placement = placement
            try:
                self.glass.ViewObject.Visibility = False
            except Exception:
                pass
        else:
            frame_shape, glass_shape = self._glass_shapes(width, height, thickness, frame_width, glass_thickness)
            self.feature.Shape = frame_shape
            self.glass.Shape = glass_shape
            self.glass.Placement = placement
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
        try:
            self.glass.ViewObject.Visibility = state and self.style == self.STYLE_GLASS
        except Exception:
            pass

class UpperDoorLayout:
    """Door sizing and placement for overlay and inset upper-cabinet fronts."""
    MOUNT_OVERLAY = "Overlay"
    MOUNT_INSET = "Inset"
    @classmethod
    def calculate(cls, width, height, cabinet_thickness, door_thickness, gap, count, mount, inset_setback):
        if width <= 0 or height <= 0:
            raise RuntimeError("Cabinet width and height must be greater than zero.")
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
        if mount == cls.MOUNT_OVERLAY:
            door_width = width if count == 1 else (width - gap) / 2.0
            door_height = height
            left_x = 0.0
            left_z = 0.0
            back_y = 0.0
        else:
            # The finished carcass defines the front opening. Door width and
            # height are independent of the Y setback.
            opening_width = width - 2.0 * cabinet_thickness
            opening_height = height - 2.0 * cabinet_thickness
            if opening_width <= 0 or opening_height <= 0:
                raise RuntimeError("CabinetThickness leaves no opening for inset doors.")
            available_width = opening_width
            door_height = opening_height
            if count == 2:
                available_width -= gap
            door_width = available_width if count == 1 else available_width / 2.0
            left_x = cabinet_thickness
            left_z = cabinet_thickness
            # CabinetDoor local geometry runs from -DoorThickness to 0 in Y.
            # Therefore the visible front face is exactly InsetSetback when
            # the back/reference plane is DoorThickness + InsetSetback.
            back_y = door_thickness + inset_setback
        if door_width <= 0:
            raise RuntimeError("Door layout leaves no usable door width.")
        if door_height <= 0:
            raise RuntimeError("Door layout leaves no usable door height.")
        right_x = left_x if count == 1 else left_x + door_width + gap
        return {
            "door_width": door_width,
            "door_height": door_height,
            "left_x": left_x,
            "right_x": right_x,
            "z": left_z,
            "back_y": back_y,
            "right_visible": count == 2,
        }

class UpperCabinetFP:
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
        # 1. Read and validate final cabinet parameters.
        p = self._read_parameters(sheet)
        self._validate(p)
        # 2. Create and fully establish the carcass first.
        carcass = CabinetCarcass.create(doc, prefix)
        self._update_carcass(carcass, p)
        try:
            for body in carcass.bodies():
                body.ViewObject.ShapeColor = (0.72, 0.72, 0.72)
        except Exception:
            pass
        assembly.addObject(sheet)
        assembly.addObject(origin_point)
        for body in carcass.bodies():
            assembly.addObject(body)
        doc.recompute()
        # 3. Create the door objects last from the finished front opening.
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
        # Controller is intentionally grouped last.
        assembly.addObject(obj)
        required = (
            [sheet, origin_point]
            + carcass.bodies()
            + [left.body, left.glass, right.body, right.glass, obj]
        )
        missing = [
            member.Name for member in required
            if member not in assembly.Group
        ]
        if missing:
            raise RuntimeError(
                "FreeCAD did not place all cabinet members inside '{}'. Missing: {}"
                .format(assembly.Name, ", ".join(missing))
            )
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
        raise RuntimeError("Upper Cabinet Controller cannot resolve its owning App::Part.")
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
        return carcass, resolved
    def _read_parameters(self, sheet):
        values = read_parameter_values(sheet)
        return {
            "width": values["CabinetWidth"],
            "depth": values["CabinetDepth"],
            "height": values["CabinetHeight"],
            "cabinet_thickness": values["CabinetThickness"],
            "rabbet_depth": values["RabbetDepth"],
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
        result = UpperCabinetValidator.validate_internal(p)
        result.raise_for_errors()
        warning_signature = tuple(result.warnings)
        if warning_signature != getattr(self, "_last_warning_signature", ()):
            self._last_warning_signature = warning_signature
            if warning_signature:
                App.Console.PrintWarning(
                    "Upper Cabinet parameter warning:\n{}\n".format(result.warning_text())
                )
        return result
    def _update_carcass(self, carcass, p):
        carcass.update(
            width=p["width"],
            depth=p["depth"],
            height=p["height"],
            thickness=p["cabinet_thickness"],
            rabbet_depth=p["rabbet_depth"],
        )
    def _update_doors(self, left_door, left_shape, left_glass, right_door, right_shape, right_glass, p):
        style = p["door_style"]
        left = CabinetDoor.from_existing(left_door, left_shape, left_glass, style)
        right = CabinetDoor.from_existing(right_door, right_shape, right_glass, style)
        layout = UpperDoorLayout.calculate(
            width=p["width"],
            height=p["height"],
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
        carcass, g = self._geometry(assembly)
        self._update_carcass(carcass, p)
        self._update_doors(
            g["left_door"], g["left_shape"], g["left_glass"],
            g["right_door"], g["right_shape"], g["right_glass"], p
        )

def validate_dialog_values(values):
    result = UpperCabinetValidator.validate(values)
    return result.valid, result.error_text()

def _sanitize_object_name(name):
    cleaned = "".join(c if (c.isalnum() or c == "_") else "_" for c in str(name).strip())
    if not cleaned:
        cleaned = INSTANCE_BASENAME
    if cleaned[0].isdigit():
        cleaned = INSTANCE_BASENAME + "_" + cleaned
    return cleaned

def next_upper_cabinet_name(document):
    if document is None:
        raise ValueError("A valid FreeCAD document is required.")
    index = 1
    while True:
        candidate = "{}{:03d}".format(INSTANCE_BASENAME, index)
        if document.getObject(candidate) is None:
            return candidate
        index += 1

class EndpointSnapPointPicker:
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
                category=DeprecationWarning
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
        self._show_status(
            "Select upper-cabinet insertion point: hover over an existing endpoint until "
            "the snap marker appears, then left-click. Press Esc or right-click to cancel."
        )
        try:
            Gui.updateGui()
        except Exception:
            pass
    def _ensure_snapper(self):
        try:
            import DraftTools  # noqa: F401
        except Exception as exc:
            raise RuntimeError("Draft GUI tools could not be initialized: {}".format(exc))
        snapper = getattr(Gui, "Snapper", None)
        if snapper is None:
            raise RuntimeError("FreeCAD's canonical Draft Snapper was not initialized.")
        return snapper
    def _mouse_move(self, cb):
        if self._finished:
            return
        try:
            event = cb.getEvent()
            self.snapper.snap(event.getPosition(), lastpoint=None, active=True, constrain=False, noTracker=False)
            endpoint = str(getattr(self.snapper, "cursorMode", "") or "").lower() == "endpoint"
            if endpoint != self._last_endpoint_state:
                self._last_endpoint_state = endpoint
                if endpoint:
                    self._show_status("Endpoint found — left-click to place the upper cabinet.")
                elif self._failed_endpoint_picks == 0:
                    self._show_status("Select an existing endpoint/vertex.")
                else:
                    self._show_status("Second pick: select an endpoint. If no endpoint exists, click again to place at 0,0,0.")
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
            point = self.snapper.snap(event.getPosition(), lastpoint=None, active=True, constrain=False, noTracker=False)
            mode = str(getattr(self.snapper, "cursorMode", "") or "").lower()
            if point is None or mode != "endpoint":
                cb.setHandled()
                if self._failed_endpoint_picks == 0:
                    self._failed_endpoint_picks = 1
                    self._show_status("Second pick: select an endpoint. If no endpoint exists, click again to place at 0,0,0.")
                    QtWidgets.QMessageBox.information(
                        None,
                        "Endpoint Required",
                        "An endpoint is required, please select an endpoint, if none exists on second pick cabinet will be drawn at 0,0,0."
                    )
                    return
                self._finished = True
                accepted = App.Vector(0.0, 0.0, 0.0)
                App.Console.PrintMessage("No endpoint selected on second pick; placing Upper Cabinet at 0,0,0.\n")
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
            if event.getState() == coin.SoButtonEvent.DOWN and event.getKey() == coin.SoKeyboardEvent.ESCAPE:
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
            for event_type, token in [
                (coin.SoLocation2Event.getClassTypeId(), self.callback_move),
                (coin.SoMouseButtonEvent.getClassTypeId(), self.callback_click),
                (coin.SoKeyboardEvent.getClassTypeId(), self.callback_key),
            ]:
                if token is not None:
                    try:
                        self.view.removeEventCallbackPivy(event_type, token)
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

class UpperCabinetBuilder:
    def __init__(self, document, instance_name):
        if document is None:
            raise ValueError("create_upper_cabinet() requires an existing FreeCAD document.")
        self.document = document
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
            print("Upper cabinet creation cancelled. The active layout document was not changed.")
            return False
        self.values = dialog.values()
        valid, message = validate_dialog_values(self.values)
        if not valid:
            QtWidgets.QMessageBox.critical(None, "Invalid Upper Cabinet Parameters", message)
            return False
        ParameterTable.update(self.document, self.parameters, self.values)
        ParameterTable.verify(self.parameters)
        return True
    def _accepted(self, point):
        self.insertion_point = App.Vector(point)
        self._picker = None
        try:
            self.assembly = self.document.addObject("App::Part", self.instance_name)
            self.assembly.Label = "Upper Cabinet"
            self.assembly.Placement.Base = App.Vector(self.insertion_point)
            self.controller = self.document.addObject(
                "Part::FeaturePython", "{}_Controller".format(self.instance_name)
            )
            self.controller.Label = "Upper Cabinet Controller"
            UpperCabinetFP(
                self.controller,
                self.assembly,
                self.parameters
            )
            self.document.recompute()
            self._show()
            self._print_report()
        except Exception as exc:
            self._rollback()
            QtWidgets.QMessageBox.critical(None, "Upper Cabinet Creation Error", str(exc))
            App.Console.PrintError("Upper cabinet creation failed: {}\n".format(exc))
    def _cancelled(self):
        self._picker = None
        self._rollback()
        print("Upper cabinet insertion cancelled. The active layout document was not changed.")
    def _rollback(self):
        new_names = [
            obj.Name for obj in self.document.Objects
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
        print("PARAMETRIC UPPER CABINET - FIVE-PART RABBETED CARCASS")
        print("FREECAD 1.1.4 - REVISION 0.19")
        print("Target document: {}".format(self.document.Name))
        print("Instance name:   {}".format(self.instance_name))
        print("=" * 72)
    def _print_report(self):
        p = SheetParams(self.parameters)
        W = qty_mm(p.get("CabinetWidth"), 600.0)
        D = qty_mm(p.get("CabinetDepth"), 304.8)
        t = qty_mm(p.get("CabinetThickness"), 19.5)
        r = qty_mm(p.get("RabbetDepth"), 6.35)
        inset_setback = qty_mm(p.get("InsetSetback"), 0.0)
        d = CabinetCarcass.derived_dimensions(W, D, t, r)
        print("")
        print("-" * 72)
        print("UPPER CABINET INSTANCE CREATED SUCCESSFULLY")
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
        print("Inset door setback Y:   ", inset_setback, "mm")
        report_count = qty_int(p.get("DoorCount"), 2)
        report_gap = qty_mm(p.get("DoorGap"), 2.0)
        report_door_t = qty_mm(p.get("DoorThickness"), 19.0)
        report_layout = UpperDoorLayout.calculate(
            width=W,
            height=qty_mm(p.get("CabinetHeight"), 720.0),
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

def create_upper_cabinet(document, instance_name):
    return UpperCabinetBuilder(document, instance_name).run()

def main():
    document = App.ActiveDocument
    if document is None:
        QtWidgets.QMessageBox.warning(
            None,
            "No Active FreeCAD Document",
            "Open or create the kitchen/layout document first, then run this macro again."
        )
        return None
    return create_upper_cabinet(document, next_upper_cabinet_name(document))

# ============================================================
# WORKBENCH MODULE NOTE
# ============================================================
# Do not call main() automatically here.
# CabinetsWorkbench.py imports this module, calls main(), and retains the
# returned UpperCabinetBuilder while endpoint selection is active.

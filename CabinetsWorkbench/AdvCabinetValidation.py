# Advanced Cabinets Workbench - shared validation core
# Target: FreeCAD 1.1.4
# CABINET CORE V1
from dataclasses import dataclass, field
RANGE_TOLERANCE_MM = 1.0e-6
@dataclass(frozen=True)
class ParameterSpec:
    name: str
    minimum: float
    maximum: float
    label: str = None
    def __post_init__(self):
        object.__setattr__(self, "minimum", float(self.minimum))
        object.__setattr__(self, "maximum", float(self.maximum))
        if self.label is None:
            object.__setattr__(self, "label", self.name)
    @staticmethod
    def _compact(value):
        return ("{:.4f}".format(float(value))).rstrip("0").rstrip(".")
    def limit_text(self):
        return "{}-{} mm ({}-{} in)".format(self._compact(self.minimum), self._compact(self.maximum), self._compact(self.minimum / 25.4), self._compact(self.maximum / 25.4))
@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    severity: str = "error"
    parameters: tuple = field(default_factory=tuple)
    category: str = "general"
    def __str__(self):
        return self.message
class ValidationResult:
    def __init__(self):
        self.error_issues = []
        self.warning_issues = []
    @property
    def errors(self):
        return [issue.message for issue in self.error_issues]
    @property
    def warnings(self):
        return [issue.message for issue in self.warning_issues]
    @property
    def valid(self):
        return not self.error_issues
    def add_error(self, message, code="VALIDATION_ERROR", parameters=(), category="general"):
        issue = message if isinstance(message, ValidationIssue) else ValidationIssue(code, str(message), "error", tuple(parameters), category)
        if issue.message not in self.errors:
            self.error_issues.append(issue)
        return issue
    def add_warning(self, message, code="VALIDATION_WARNING", parameters=(), category="general"):
        issue = message if isinstance(message, ValidationIssue) else ValidationIssue(code, str(message), "warning", tuple(parameters), category)
        if issue.message not in self.warnings:
            self.warning_issues.append(issue)
        return issue
    def error_text(self):
        return "\n".join("- {}".format(issue.message) for issue in self.error_issues)
    def warning_text(self):
        return "\n".join("- {}".format(issue.message) for issue in self.warning_issues)
    def raise_for_errors(self):
        if self.error_issues:
            raise RuntimeError(self.error_text())
@dataclass(frozen=True)
class CabinetProfile:
    name: str
    width: tuple = (304.8, 1219.2)
    depth: tuple = (304.8, 1219.2)
    height: tuple = (406.4, 3657.6)
    thickness: tuple = (6.35, 25.4)
    toe_kick_height: tuple = (76.2, 152.4)
    toe_kick_setback: tuple = (50.8, 152.4)
GENERAL_CABINET_PROFILE = CabinetProfile("General")
BASE_CABINET_PROFILE = CabinetProfile("Base")
UPPER_CABINET_PROFILE = CabinetProfile("Upper")
TALL_CABINET_PROFILE = CabinetProfile("Tall", height=(1524.0, 3048.0))
def in_inclusive_range(value, minimum, maximum, tolerance=RANGE_TOLERANCE_MM):
    value = float(value)
    return not (value < float(minimum) - tolerance or value > float(maximum) + tolerance)
def validate_spec(result, values, name, spec, active=True, tolerance=RANGE_TOLERANCE_MM):
    if not active:
        return
    if name not in values:
        result.add_error("{} is required.".format(spec.label), "MISSING_PARAMETER", (name,), "parameter")
        return
    value = float(values[name])
    if not in_inclusive_range(value, spec.minimum, spec.maximum, tolerance):
        result.add_error("{} is {:.3f} mm. Allowed range is {}.".format(spec.label, value, spec.limit_text()), "RANGE_ERROR", (name,), "range")
def validate_profile_envelope(result, values, profile, width_name="CabinetWidth", depth_name="CabinetDepth", height_name="CabinetHeight", thickness_name="CabinetThickness"):
    mapping = (
        (width_name, profile.width, "Cabinet Width"),
        (depth_name, profile.depth, "Cabinet Depth"),
        (height_name, profile.height, "Cabinet Height"),
        (thickness_name, profile.thickness, "Cabinet Thickness"),
    )
    for name, limits, label in mapping:
        if name in values:
            spec = ParameterSpec(name, limits[0], limits[1], label)
            validate_spec(result, values, name, spec)

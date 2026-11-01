# Advanced Cabinets Workbench - shared parameter/schema core
# Target: FreeCAD 1.1.4
# CABINET CORE V1.01 - active_when normalization/formatting hotfix
from dataclasses import dataclass, field, replace
from AdvCabinetValidation import ParameterSpec
try:
    import FreeCAD as App
except Exception:
    App = None
def normalize_active_when(active_when):
    """Return active_when as a tuple of validated 2- or 3-item conditions.

    Accepted forms:
      ("Mount", "Overlay")
      ("Count", ">", 0)
      (("Mount", "Overlay"), ("Style", "Shaker"))
    """
    if not active_when:
        return ()
    if isinstance(active_when, (list, tuple)) and len(active_when) in (2, 3) and isinstance(active_when[0], str):
        conditions = (tuple(active_when),)
    else:
        try:
            conditions = tuple(tuple(condition) for condition in active_when)
        except Exception:
            raise ValueError("active_when must be a condition or iterable of conditions.")
    for condition in conditions:
        if len(condition) not in (2, 3) or not isinstance(condition[0], str):
            raise ValueError("Invalid active_when condition: {}".format(condition))
    return conditions
def format_active_when(active_when):
    """Return concise user-facing text for active_when conditions."""
    parts = []
    for condition in normalize_active_when(active_when):
        if len(condition) == 2:
            name, expected = condition
            if isinstance(expected, (tuple, list, set)):
                parts.append("{} in {}".format(name, " | ".join(str(item) for item in expected)))
            else:
                parts.append("{}={}".format(name, expected))
        else:
            name, operator, expected = condition
            parts.append("{} {} {}".format(name, operator, expected))
    return ", ".join(parts)
@dataclass(frozen=True)
class ParameterDefinition:
    name: str
    default: object
    kind: str = "length"
    label: str = None
    minimum: float = None
    maximum: float = None
    options: tuple = field(default_factory=tuple)
    group: str = "General"
    tooltip: str = ""
    active_when: tuple = field(default_factory=tuple)
    legacy_names: tuple = field(default_factory=tuple)
    read_only: bool = False
    display_inches: bool = True
    display_unit: str = None
    def __post_init__(self):
        if self.label is None:
            object.__setattr__(self, "label", self.name)
        object.__setattr__(self, "active_when", normalize_active_when(self.active_when))
    @property
    def spec(self):
        if self.minimum is None or self.maximum is None:
            return None
        return ParameterSpec(self.name, self.minimum, self.maximum, self.label)
class ParameterSchema:
    def __init__(self, definitions, version=1, cabinet_type="Cabinet"):
        self.definitions = list(definitions)
        self.version = int(version)
        self.cabinet_type = str(cabinet_type)
        self._by_name = {item.name: item for item in self.definitions}
    def get(self, name):
        return self._by_name[name]
    def names(self):
        return [item.name for item in self.definitions]
    def defaults(self):
        return {item.name: item.default for item in self.definitions}
    def is_active(self, name, values):
        item = self.get(name)
        for condition in item.active_when:
            if len(condition) == 2:
                other_name, expected = condition
                actual = values.get(other_name)
                if isinstance(expected, (tuple, list, set)):
                    if actual not in expected:
                        return False
                elif actual != expected:
                    return False
            elif len(condition) == 3:
                other_name, operator, expected = condition
                actual = values.get(other_name)
                if actual is None:
                    return False
                if operator == ">" and not actual > expected:
                    return False
                if operator == ">=" and not actual >= expected:
                    return False
                if operator == "<" and not actual < expected:
                    return False
                if operator == "<=" and not actual <= expected:
                    return False
                if operator == "!=" and not actual != expected:
                    return False
            else:
                raise ValueError("Invalid active_when condition for {}: {}".format(name, condition))
        return True
class SheetParams:
    def __init__(self, sheet, row_start=2, row_end=120):
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
def _fallback_length(text):
    raw = str(text).strip().lower().replace('"', ' in')
    if raw.endswith("mm"):
        return float(raw[:-2].strip())
    if raw.endswith("in"):
        number = raw[:-2].strip()
        parts = number.split()
        if len(parts) == 2 and "/" in parts[1]:
            whole = float(parts[0])
            num, den = parts[1].split("/", 1)
            inches = whole + (float(num) / float(den) if whole >= 0 else -float(num) / float(den))
        elif "/" in number:
            num, den = number.split("/", 1)
            inches = float(num) / float(den)
        else:
            inches = float(number)
        return inches * 25.4
    return float(raw)
def qty_mm(value, fallback=None, parameter_name="Length"):
    if value is None or not str(value).strip():
        if fallback is not None:
            return float(fallback)
        raise ValueError("{} is required.".format(parameter_name))
    text = str(value).strip()
    if all(c.isdigit() or c in ".-+" for c in text):
        text += " mm"
    try:
        if App is not None:
            return float(App.Units.Quantity(text).Value)
        return float(_fallback_length(text))
    except Exception:
        raise ValueError("{} must be a valid length, for example 600 mm, 24 in, or 1 1/2 in.".format(parameter_name))
def qty_int(value, fallback=None, parameter_name="Integer"):
    if value is None or not str(value).strip():
        if fallback is not None:
            return int(fallback)
        raise ValueError("{} is required.".format(parameter_name))
    try:
        number = float(str(value).strip())
        rounded = int(round(number))
        if abs(number - rounded) > 1.0e-9:
            raise ValueError
        return rounded
    except Exception:
        raise ValueError("{} must be a whole number.".format(parameter_name))
def qty_scalar(value, fallback=None, parameter_name="Number"):
    if value is None or not str(value).strip():
        if fallback is not None:
            return float(fallback)
        raise ValueError("{} is required.".format(parameter_name))
    try:
        return float(str(value).strip())
    except Exception:
        raise ValueError("{} must be numeric.".format(parameter_name))
def parameter_raw(params, name, default=None, legacy_aliases=None):
    value = params.get(name, None)
    if value is not None and str(value).strip():
        return value
    aliases = () if legacy_aliases is None else legacy_aliases.get(name, ())
    for legacy_name in aliases:
        value = params.get(legacy_name, None)
        if value is not None and str(value).strip():
            return value
    return default
def read_schema_values(sheet, schema):
    params = SheetParams(sheet)
    values = {}
    for definition in schema.definitions:
        raw = parameter_raw(params, definition.name, None, {definition.name: definition.legacy_names})
        if raw is None or not str(raw).strip():
            raise ValueError("{} is required.".format(definition.label))
        if definition.kind == "text":
            values[definition.name] = str(raw).strip()
        elif definition.kind == "integer":
            values[definition.name] = qty_int(raw, None, definition.label)
        elif definition.kind == "scalar":
            values[definition.name] = qty_scalar(raw, None, definition.label)
        else:
            values[definition.name] = qty_mm(raw, None, definition.label)
    return values
class ParameterTable:
    def __init__(self, schema):
        self.schema = schema
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
        return "=({r}==0?{wo}:({w}==0?{fo}:{mn}))".format(r=remainder, wo=whole_only, w=whole, fo=fraction_only, mn=mixed_number)
    def create(self, doc, object_name="Parameters"):
        sheet = doc.addObject("Spreadsheet::Sheet", object_name)
        sheet.Label = "Parameters"
        for cell, text in (("A1", "Name"), ("B1", "Value"), ("C1", "Inches"), ("D1", "Options"), ("E1", "Allowed Range")):
            sheet.set(cell, text)
        for row, definition in enumerate(self.schema.definitions, start=2):
            sheet.set("A{}".format(row), definition.name)
            sheet.set("B{}".format(row), str(definition.default))
            try:
                sheet.setAlias("B{}".format(row), definition.name)
            except Exception:
                pass
            if definition.options:
                sheet.set("D{}".format(row), " | ".join(str(x) for x in definition.options))
            elif definition.active_when:
                sheet.set("D{}".format(row), "Applies when " + format_active_when(definition.active_when))
            spec = definition.spec
            if spec is not None:
                sheet.set("E{}".format(row), spec.limit_text())
            if definition.kind == "length" and definition.display_inches:
                sheet.set("C{}".format(row), self._fractional_inch_expression("B{}".format(row)))
            if definition.display_unit:
                try:
                    sheet.setDisplayUnit("B{}".format(row), definition.display_unit)
                except Exception:
                    pass
        for column, width in (("A", 240), ("B", 180), ("C", 140), ("D", 290), ("E", 290)):
            try:
                sheet.setColumnWidth(column, width)
            except Exception:
                pass
        doc.recompute()
        return sheet
    def update(self, doc, sheet, values):
        params = SheetParams(sheet)
        for definition in self.schema.definitions:
            if definition.name in values:
                value = values[definition.name]
            else:
                value = parameter_raw(params, definition.name, definition.default, {definition.name: definition.legacy_names})
            if definition.kind == "text":
                text = str(value)
            elif definition.kind == "integer":
                text = str(int(value))
            elif definition.kind == "scalar":
                text = str(float(value))
            else:
                text = "{} mm".format(value) if definition.name in values else str(value)
            row = params.row_of(definition.name)
            if row is None:
                for legacy_name in definition.legacy_names:
                    row = params.row_of(legacy_name)
                    if row is not None:
                        sheet.set("A{}".format(row), definition.name)
                        break
            if row is None:
                raise KeyError("Parameter '{}' was not found in the Parameters sheet.".format(definition.name))
            sheet.set("B{}".format(row), text)
            try:
                sheet.setAlias("B{}".format(row), definition.name)
            except Exception:
                pass
            if definition.kind == "length" and definition.display_inches:
                sheet.set("C{}".format(row), self._fractional_inch_expression("B{}".format(row)))
            if definition.display_unit:
                try:
                    sheet.setDisplayUnit("B{}".format(row), definition.display_unit)
                except Exception:
                    pass
        doc.recompute()
    def verify(self, sheet):
        values = read_schema_values(sheet, self.schema)
        return values
def apply_schema_overrides(schema, overrides):
    definitions = []
    for definition in schema.definitions:
        changes = dict(overrides.get(definition.name, {}))
        definitions.append(replace(definition, **changes) if changes else definition)
    return ParameterSchema(definitions, version=schema.version, cabinet_type=schema.cabinet_type)

def schema_from_legacy(param_defaults, parameter_specs=None, text_parameters=None, integer_parameters=None, scalar_parameters=None, parameter_options=None, legacy_aliases=None, cabinet_type="Cabinet", version=1, display_unit_names=None):
    parameter_specs = parameter_specs or {}
    text_parameters = set(text_parameters or ())
    integer_parameters = set(integer_parameters or ())
    scalar_parameters = set(scalar_parameters or ())
    parameter_options = parameter_options or {}
    legacy_aliases = legacy_aliases or {}
    display_unit_names = set(display_unit_names or ())
    definitions = []
    for name, default in param_defaults:
        if name in text_parameters:
            kind = "text"
        elif name in integer_parameters:
            kind = "integer"
        elif name in scalar_parameters:
            kind = "scalar"
        else:
            kind = "length"
        spec = parameter_specs.get(name)
        option_text = parameter_options.get(name, "")
        options = tuple(part.strip() for part in option_text.split("|") if part.strip()) if option_text and "Applies" not in option_text and ";" not in option_text else ()
        definitions.append(ParameterDefinition(name=name, default=default, kind=kind, label=(spec.label if spec else name), minimum=(spec.minimum if spec else None), maximum=(spec.maximum if spec else None), options=options, legacy_names=tuple(legacy_aliases.get(name, ())), display_unit=("in" if name in display_unit_names else None)))
    return ParameterSchema(definitions, version=version, cabinet_type=cabinet_type)

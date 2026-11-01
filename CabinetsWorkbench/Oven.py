# ============================================================

# SELF-CONTAINED PARAMETRIC OVEN / RANGE

# CLEAN REFACTORED FEATUREPYTHON VERSION

# ============================================================

#

# Target: FreeCAD 1.1.3
#
# REVISION: 0.02
#
# REVISION HISTORY:
#   0.00 - Baseline Self-Contained Parametric Oven / Range
#          - active-document independent instance architecture
#          - per-instance Parameters spreadsheet
#          - nearest-1/16-inch display
#          - oven body, cooktop and oven door
#          - configurable 4-8 burners
#          - configurable 4-8 control knobs
#          - FeaturePython controller with build guard
#          - preference-free endpoint select-to-insert
#
#   0.01 - Insertion usability revision
#          - first non-endpoint pick displays an Endpoint Required dialog
#          - second pick still accepts a valid endpoint
#          - second non-endpoint pick creates the oven at 0,0,0
#          - Esc / right-click still cancel normally
#          - no persistent Draft snap preferences are changed
#
#   0.02 - Assembly origin snap-point revision
#          - adds a visible Draft Point at local component origin 0,0,0
#          - point is grouped inside the component App::Part
#          - point moves and rotates with the component parent Placement
#          - provides an Endpoint snap reference for Draft Move placement
#

#

# FUNCTIONAL GEOMETRY PRESERVED

#

# OvenAssemblyPart

# ├── Parameters

# ├── OvenController

# ├── Oven Body

# │   └── Oven Body Box

# ├── Cooktop

# │   └── Cooktop Box

# ├── Oven Door

# │   └── Oven Door Box

# ├── Knob 1 ... Knob 8

# └── Burner 1 ... Burner 8

#

# Controller links only to Parameters.

# Geometry is resolved locally inside OvenAssemblyPart.

#

# KnobCount:

#     minimum = 4

#     maximum = 8

#

# Burners:

#     minimum = 4

#     maximum = 8

#

# ============================================================

import FreeCAD as App

import FreeCADGui as Gui

import Draft

from PySide import QtGui

from pivy import coin

from draftutils import gui_utils

# ============================================================

# ACTIVE-DOCUMENT INSTANCE CONFIGURATION

# ============================================================

SHEET_NAME = "Parameters"

CONTROLLER_NAME = "OvenController"

INSTANCE_BASENAME = "ParametricOven"

KNOB_MAX = 8

BURNER_MAX = 8

# ============================================================

# PARAMETER DEFINITIONS

# ============================================================

PARAM_DEFAULTS = [

    ("OvenWidth",              "730 mm"),

    ("OvenDepth",              "680 mm"),

    ("OvenHeight",             "910 mm"),

    ("BaseRaise",              "50 mm"),

    ("CooktopThickness",       "152 mm"),

    ("BurnerDiameter",         "210 mm"),

    ("BurnerHeight",           "12 mm"),

    ("BurnerCount",            "4"),

    ("KnobDiameter",           "50 mm"),

    ("KnobLength",             "20 mm"),

    ("KnobCount",              "4"),

    ("OvenDoorThickness",      "20 mm"),

    ("OvenDoorGap",            "3 mm"),

    ("OvenDoorBottomGap",      "3 mm"),

    ("OvenDoorTopClearance",   "175 mm"),

]

INTEGER_PARAMETERS = {

    "BurnerCount",

    "KnobCount",

}

# ============================================================

# SPREADSHEET ADAPTER

# ============================================================

class SheetParams:

    def __init__(

        self,

        sheet,

        row_start=2,

        row_end=70

    ):

        self.sheet = sheet

        self.row_start = row_start

        self.row_end = row_end

    def get_cell(

        self,

        address

    ):

        try:

            return self.sheet.get(address)

        except Exception:

            pass

        try:

            return self.sheet.getContents(address)

        except Exception:

            pass

        try:

            return getattr(

                self.sheet,

                address

            )

        except Exception:

            return None

    def set_cell(

        self,

        address,

        value

    ):

        self.sheet.set(

            address,

            str(value)

        )

    def row_of(

        self,

        key

    ):

        for row in range(

            self.row_start,

            self.row_end + 1

        ):

            value = self.get_cell(

                "A{}".format(row)

            )

            if (

                value is not None

                and

                str(value).strip() == key

            ):

                return row

        return None

    def get(

        self,

        key,

        default=None

    ):

        row = self.row_of(key)

        if row is None:

            return default

        value = self.get_cell(

            "B{}".format(row)

        )

        if value is None:

            return default

        return value

    def set(

        self,

        key,

        value

    ):

        row = self.row_of(key)

        if row is None:

            raise KeyError(

                "Parameter '{}' was not found."

                .format(key)

            )

        self.set_cell(

            "B{}".format(row),

            value

        )

# ============================================================

# UNIT HELPERS

# ============================================================

def qty_mm(

    value,

    fallback

):

    try:

        if value is None:

            return float(fallback)

        text = str(value).strip()

        if not text:

            return float(fallback)

        if all(

            character.isdigit()

            or character in ".-+"

            for character in text

        ):

            text += " mm"

        return float(

            App.Units.Quantity(text).Value

        )

    except Exception:

        return float(fallback)

def qty_int(

    value,

    fallback

):

    try:

        if value is None:

            return int(fallback)

        text = str(value).strip()

        if not text:

            return int(fallback)

        return int(

            float(text)

        )

    except Exception:

        return int(fallback)

# ============================================================

# PARAMETER TABLE

# ============================================================

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

        sheet.set(

            "A1",

            "Name"

        )

        sheet.set(

            "B1",

            "Value"

        )

        for row, (

            name,

            default_value

        ) in enumerate(

            PARAM_DEFAULTS,

            start=2

        ):

            sheet.set(

                "A{}".format(row),

                name

            )

            sheet.set(

                "B{}".format(row),

                default_value

            )

            try:

                sheet.setAlias(

                    "B{}".format(row),

                    name

                )

            except Exception:

                pass

        try:

            sheet.setColumnWidth(

                "A",

                220

            )

            sheet.setColumnWidth(

                "B",

                180

            )

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

        """Populate column C for dimensional parameters only."""

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

            name,

            default_value

        ) in enumerate(

            PARAM_DEFAULTS,

            start=2

        ):

            if name in INTEGER_PARAMETERS:

                continue

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

    def update(

        doc,

        sheet,

        values

    ):

        for row, (

            name,

            _default

        ) in enumerate(

            PARAM_DEFAULTS,

            start=2

        ):

            value = values[name]

            if name in INTEGER_PARAMETERS:

                text = str(

                    int(value)

                )

            else:

                text = "{} mm".format(

                    value

                )

            sheet.set(

                "A{}".format(row),

                name

            )

            sheet.set(

                "B{}".format(row),

                text

            )

            try:

                sheet.setAlias(

                    "B{}".format(row),

                    name

                )

            except Exception:

                pass

        ParameterTable.update_inches_column(

            sheet

        )

        doc.recompute()

    @staticmethod

    def verify(

        sheet

    ):

        params = SheetParams(sheet)

        failures = []

        for name, _default in PARAM_DEFAULTS:

            value = params.get(name)

            text = (

                ""

                if value is None

                else str(value).strip()

            )

            if (

                not text

                or

                "#REF" in text.upper()

            ):

                failures.append(name)

        if failures:

            raise RuntimeError(

                "Parameters did not resolve: {}"

                .format(

                    ", ".join(failures)

                )

            )

# ============================================================

# INPUT DIALOG

# ============================================================

class OvenDialog(

    QtGui.QDialog

):

    def __init__(

        self,

        sheet

    ):

        super().__init__()

        params = SheetParams(sheet)

        self.setWindowTitle(

            "Parametric Oven / Range"

        )

        layout = QtGui.QFormLayout(

            self

        )

        self.width = self._dimension_field(

            params,

            "OvenWidth",

            730

        )

        self.depth = self._dimension_field(

            params,

            "OvenDepth",

            680

        )

        self.height = self._dimension_field(

            params,

            "OvenHeight",

            910

        )

        self.base_raise = self._dimension_field(

            params,

            "BaseRaise",

            50

        )

        self.cooktop_t = self._dimension_field(

            params,

            "CooktopThickness",

            152

        )

        self.burner_d = self._dimension_field(

            params,

            "BurnerDiameter",

            210

        )

        self.burner_h = self._dimension_field(

            params,

            "BurnerHeight",

            12

        )

        self.burner_count = QtGui.QLineEdit(

            str(

                qty_int(

                    params.get(

                        "BurnerCount"

                    ),

                    4

                )

            )

        )

        self.knob_d = self._dimension_field(

            params,

            "KnobDiameter",

            50

        )

        self.knob_len = self._dimension_field(

            params,

            "KnobLength",

            20

        )

        self.knob_count = QtGui.QLineEdit(

            str(

                qty_int(

                    params.get(

                        "KnobCount"

                    ),

                    4

                )

            )

        )

        self.door_t = self._dimension_field(

            params,

            "OvenDoorThickness",

            20

        )

        self.door_gap = self._dimension_field(

            params,

            "OvenDoorGap",

            3

        )

        self.door_bottom = self._dimension_field(

            params,

            "OvenDoorBottomGap",

            3

        )

        self.door_top = self._dimension_field(

            params,

            "OvenDoorTopClearance",

            175

        )

        layout.addRow(

            "Oven Width (mm):",

            self.width

        )

        layout.addRow(

            "Oven Depth (mm):",

            self.depth

        )

        layout.addRow(

            "Oven Height (mm):",

            self.height

        )

        layout.addRow(

            "Base Raise (mm):",

            self.base_raise

        )

        layout.addRow(

            "Cooktop Thickness (mm):",

            self.cooktop_t

        )

        layout.addRow(

            "Burner Diameter (mm):",

            self.burner_d

        )

        layout.addRow(

            "Burner Height (mm):",

            self.burner_h

        )

        layout.addRow(

            "Burner Count (4-8):",

            self.burner_count

        )

        layout.addRow(

            "Knob Diameter (mm):",

            self.knob_d

        )

        layout.addRow(

            "Knob Length (mm):",

            self.knob_len

        )

        layout.addRow(

            "Knob Count (4-8):",

            self.knob_count

        )

        layout.addRow(

            "Oven Door Thickness (mm):",

            self.door_t

        )

        layout.addRow(

            "Oven Door Side Gap (mm):",

            self.door_gap

        )

        layout.addRow(

            "Oven Door Bottom Gap (mm):",

            self.door_bottom

        )

        layout.addRow(

            "Oven Door Top Clearance (mm):",

            self.door_top

        )

        buttons = QtGui.QDialogButtonBox(

            QtGui.QDialogButtonBox.Ok

            |

            QtGui.QDialogButtonBox.Cancel

        )

        buttons.accepted.connect(

            self.accept

        )

        buttons.rejected.connect(

            self.reject

        )

        layout.addRow(buttons)

    @staticmethod

    def _dimension_field(

        params,

        name,

        fallback

    ):

        return QtGui.QLineEdit(

            str(

                qty_mm(

                    params.get(name),

                    fallback

                )

            )

        )

    def values(

        self

    ):

        return {

            "OvenWidth":

                qty_mm(

                    self.width.text(),

                    730

                ),

            "OvenDepth":

                qty_mm(

                    self.depth.text(),

                    680

                ),

            "OvenHeight":

                qty_mm(

                    self.height.text(),

                    910

                ),

            "BaseRaise":

                qty_mm(

                    self.base_raise.text(),

                    50

                ),

            "CooktopThickness":

                qty_mm(

                    self.cooktop_t.text(),

                    152

                ),

            "BurnerDiameter":

                qty_mm(

                    self.burner_d.text(),

                    210

                ),

            "BurnerHeight":

                qty_mm(

                    self.burner_h.text(),

                    12

                ),

            "BurnerCount":

                qty_int(

                    self.burner_count.text(),

                    4

                ),

            "KnobDiameter":

                qty_mm(

                    self.knob_d.text(),

                    50

                ),

            "KnobLength":

                qty_mm(

                    self.knob_len.text(),

                    20

                ),

            "KnobCount":

                qty_int(

                    self.knob_count.text(),

                    4

                ),

            "OvenDoorThickness":

                qty_mm(

                    self.door_t.text(),

                    20

                ),

            "OvenDoorGap":

                qty_mm(

                    self.door_gap.text(),

                    3

                ),

            "OvenDoorBottomGap":

                qty_mm(

                    self.door_bottom.text(),

                    3

                ),

            "OvenDoorTopClearance":

                qty_mm(

                    self.door_top.text(),

                    175

                ),

        }

# ============================================================

# FEATUREPYTHON CONTROLLER

# ============================================================

class OvenFP:

    KNOB_MAX = KNOB_MAX

    BURNER_MAX = BURNER_MAX

    def __init__(

        self,

        obj,

        assembly,

        sheet

    ):

        # FreeCAD may call execute() while an instance is still being built

        # inside an already-active layout document.

        self._building = True

        obj.Proxy = self

        # --------------------------------------------------------

        # CONTROLLER LINKS / INSTANCE OWNERSHIP

        # --------------------------------------------------------

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

        # Build and group all geometry before activating the parameter link.

        self._create_geometry(

            obj,

            assembly,

            sheet

        )

        obj.Parameters = sheet

        self._building = False

        obj.touch()

    # ==========================================================

    # CREATE GEOMETRY ONCE

    # ==========================================================

    def _create_geometry(

        self,

        obj,

        assembly,

        sheet

    ):

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

        # ------------------------------------------------------

        # OVEN BODY

        # ------------------------------------------------------

        oven_body = doc.addObject(

            "PartDesign::Body",

            "{}_OvenBody".format(prefix)

        )

        oven_body.Label = (

            "Oven Body"

        )

        body_box = oven_body.newObject(

            "PartDesign::AdditiveBox",

            "{}_OvenBodyBox".format(prefix)

        )

        body_box.Label = (

            "Oven Body Box"

        )

        # ------------------------------------------------------

        # COOKTOP

        # ------------------------------------------------------

        cooktop = doc.addObject(

            "PartDesign::Body",

            "{}_Cooktop".format(prefix)

        )

        cooktop.Label = (

            "Cooktop"

        )

        cooktop_box = cooktop.newObject(

            "PartDesign::AdditiveBox",

            "{}_CooktopBox".format(prefix)

        )

        cooktop_box.Label = (

            "Cooktop Box"

        )

        # ------------------------------------------------------

        # OVEN DOOR

        # ------------------------------------------------------

        oven_door = doc.addObject(

            "PartDesign::Body",

            "{}_OvenDoor".format(prefix)

        )

        oven_door.Label = (

            "Oven Door"

        )

        door_box = oven_door.newObject(

            "PartDesign::AdditiveBox",

            "{}_OvenDoorBox".format(prefix)

        )

        door_box.Label = (

            "Oven Door Box"

        )

        # ------------------------------------------------------

        # EIGHT PERMANENT KNOBS

        # ------------------------------------------------------

        knobs = self._create_numbered_cylinders(

            doc=doc,

            instance_prefix=prefix,

            object_prefix="Knob",

            feature_prefix="KnobCyl",

            label_prefix="Knob",

            feature_label_prefix="Knob Cylinder",

            count=self.KNOB_MAX

        )

        # ------------------------------------------------------

        # EIGHT PERMANENT BURNERS

        # ------------------------------------------------------

        burners = self._create_numbered_cylinders(

            doc=doc,

            instance_prefix=prefix,

            object_prefix="Burner",

            feature_prefix="BurnerCyl",

            label_prefix="Burner",

            feature_label_prefix="Burner Cylinder",

            count=self.BURNER_MAX

        )

        # ------------------------------------------------------

        # COMPONENT MEMBERSHIP

        # ------------------------------------------------------

        # Add passive members first.  The FeaturePython controller is added

        # last so execute() cannot see a partially built oven instance.

        assembly.addObject(sheet)

        assembly.addObject(origin_point)

        assembly.addObject(oven_body)

        assembly.addObject(cooktop)

        assembly.addObject(oven_door)

        for knob in knobs:

            assembly.addObject(knob)

        for burner in burners:

            assembly.addObject(burner)

        assembly.addObject(obj)

        required_members = [

            sheet,

            origin_point,

            oven_body,

            cooktop,

            oven_door,

            obj

        ] + knobs + burners

        missing_members = [

            member.Name

            for member in required_members

            if member not in assembly.Group

        ]

        if missing_members:

            raise RuntimeError(

                "FreeCAD did not place all oven members inside '{}'. "

                "Missing group members: {}"

                .format(

                    assembly.Name,

                    ", ".join(

                        missing_members

                    )

                )

            )

    @staticmethod

    def _create_numbered_cylinders(

        doc,

        instance_prefix,

        object_prefix,

        feature_prefix,

        label_prefix,

        feature_label_prefix,

        count

    ):

        bodies = []

        for index in range(

            1,

            count + 1

        ):

            body = doc.addObject(

                "PartDesign::Body",

                "{}_{}_{}".format(

                    instance_prefix,

                    object_prefix,

                    index

                )

            )

            body.Label = (

                "{} {}".format(

                    label_prefix,

                    index

                )

            )

            cylinder = body.newObject(

                "PartDesign::AdditiveCylinder",

                "{}_{}_{}".format(

                    instance_prefix,

                    feature_prefix,

                    index

                )

            )

            cylinder.Label = (

                "{} {}".format(

                    feature_label_prefix,

                    index

                )

            )

            bodies.append(body)

        return bodies

    # ==========================================================

    # DOCUMENT RESTORE

    # ==========================================================

    def onDocumentRestored(

        self,

        obj

    ):

        obj.Proxy = self

        self._building = False

    # ==========================================================

    # LOCAL COMPONENT LOOKUP

    # ==========================================================

    def _assembly(

        self,

        obj

    ):

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

            "Oven Controller cannot resolve its owning App::Part."

        )

    def _child_by_label(

        self,

        assembly,

        label,

        type_id=None

    ):

        for child in assembly.Group:

            if child.Label != label:

                continue

            if (

                type_id is None

                or

                child.TypeId == type_id

            ):

                return child

        return None

    def _parameters(

        self,

        obj,

        assembly

    ):

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

    def _numbered_children(

        self,

        assembly,

        prefix,

        count

    ):

        objects = []

        for number in range(

            1,

            count + 1

        ):

            internal_name = "{}_{}_{}".format(

                assembly.Name,

                prefix,

                number

            )

            child = assembly.Document.getObject(

                internal_name

            )

            if child is None:

                # Backward-compatible visible-label fallback.

                label = "{} {}".format(

                    prefix,

                    number

                )

                child = self._child_by_label(

                    assembly,

                    label,

                    "PartDesign::Body"

                )

            if child is None:

                raise RuntimeError(

                    "{} {} not found for '{}'."

                    .format(

                        prefix,

                        number,

                        assembly.Name

                    )

                )

            objects.append(

                child

            )

        return objects

    def _body_feature(

        self,

        body,

        label,

        type_id

    ):

        # First preserve the original exact-label lookup for compatibility.

        for child in body.Group:

            if (

                child.TypeId == type_id

                and

                child.Label == label

            ):

                return child

        # FreeCAD may automatically make duplicate visible Labels unique when

        # a second oven is created (for example "Knob Cylinder 1" can become

        # "Knob Cylinder 001").  The PartDesign Body Tip is instance-local and

        # remains the correct feature regardless of any visible-label change.

        try:

            tip = body.Tip

            if (

                tip is not None

                and

                tip.TypeId == type_id

            ):

                return tip

        except Exception:

            pass

        # Final instance-local fallback: if there is exactly one child of the

        # requested type inside this Body, that child is unambiguous.

        matching_children = [

            child

            for child in body.Group

            if child.TypeId == type_id

        ]

        if len(matching_children) == 1:

            return matching_children[0]

        raise RuntimeError(

            "{} not found inside {}."

            .format(

                label,

                body.Label

            )

        )

    def _resolve_geometry(

        self,

        assembly

    ):

        doc = assembly.Document

        prefix = assembly.Name

        oven_body = doc.getObject(

            "{}_OvenBody".format(

                prefix

            )

        )

        cooktop = doc.getObject(

            "{}_Cooktop".format(

                prefix

            )

        )

        oven_door = doc.getObject(

            "{}_OvenDoor".format(

                prefix

            )

        )

        if oven_body is None:

            oven_body = self._child_by_label(

                assembly,

                "Oven Body",

                "PartDesign::Body"

            )

        if cooktop is None:

            cooktop = self._child_by_label(

                assembly,

                "Cooktop",

                "PartDesign::Body"

            )

        if oven_door is None:

            oven_door = self._child_by_label(

                assembly,

                "Oven Door",

                "PartDesign::Body"

            )

        if oven_body is None:

            raise RuntimeError(

                "Oven Body not found for '{}'."

                .format(

                    assembly.Name

                )

            )

        if cooktop is None:

            raise RuntimeError(

                "Cooktop not found for '{}'."

                .format(

                    assembly.Name

                )

            )

        if oven_door is None:

            raise RuntimeError(

                "Oven Door not found for '{}'."

                .format(

                    assembly.Name

                )

            )

        body_box = doc.getObject(

            "{}_OvenBodyBox".format(

                prefix

            )

        )

        cooktop_box = doc.getObject(

            "{}_CooktopBox".format(

                prefix

            )

        )

        door_box = doc.getObject(

            "{}_OvenDoorBox".format(

                prefix

            )

        )

        if body_box is None:

            body_box = self._body_feature(

                oven_body,

                "Oven Body Box",

                "PartDesign::AdditiveBox"

            )

        if cooktop_box is None:

            cooktop_box = self._body_feature(

                cooktop,

                "Cooktop Box",

                "PartDesign::AdditiveBox"

            )

        if door_box is None:

            door_box = self._body_feature(

                oven_door,

                "Oven Door Box",

                "PartDesign::AdditiveBox"

            )

        knobs = self._numbered_children(

            assembly,

            "Knob",

            self.KNOB_MAX

        )

        burners = self._numbered_children(

            assembly,

            "Burner",

            self.BURNER_MAX

        )

        return (

            body_box,

            cooktop_box,

            door_box,

            knobs,

            burners

        )

    # ==========================================================

    # READ PARAMETERS

    # ==========================================================

    def _read_parameters(

        self,

        sheet

    ):

        params = SheetParams(sheet)

        return {

            "width":

                qty_mm(

                    params.get(

                        "OvenWidth"

                    ),

                    730

                ),

            "depth":

                qty_mm(

                    params.get(

                        "OvenDepth"

                    ),

                    680

                ),

            "height":

                qty_mm(

                    params.get(

                        "OvenHeight"

                    ),

                    910

                ),

            "base_raise":

                qty_mm(

                    params.get(

                        "BaseRaise"

                    ),

                    50

                ),

            "cooktop_thickness":

                qty_mm(

                    params.get(

                        "CooktopThickness"

                    ),

                    152

                ),

            "burner_diameter":

                qty_mm(

                    params.get(

                        "BurnerDiameter"

                    ),

                    210

                ),

            "burner_height":

                qty_mm(

                    params.get(

                        "BurnerHeight"

                    ),

                    12

                ),

            "burner_count":

                qty_int(

                    params.get(

                        "BurnerCount"

                    ),

                    4

                ),

            "knob_diameter":

                qty_mm(

                    params.get(

                        "KnobDiameter"

                    ),

                    50

                ),

            "knob_length":

                qty_mm(

                    params.get(

                        "KnobLength"

                    ),

                    20

                ),

            "knob_count":

                qty_int(

                    params.get(

                        "KnobCount"

                    ),

                    4

                ),

            "door_thickness":

                qty_mm(

                    params.get(

                        "OvenDoorThickness"

                    ),

                    20

                ),

            "door_gap":

                qty_mm(

                    params.get(

                        "OvenDoorGap"

                    ),

                    3

                ),

            "door_bottom_gap":

                qty_mm(

                    params.get(

                        "OvenDoorBottomGap"

                    ),

                    3

                ),

            "door_top_clearance":

                qty_mm(

                    params.get(

                        "OvenDoorTopClearance"

                    ),

                    175

                ),

        }

    # ==========================================================

    # VALIDATION

    # ==========================================================

    def _validate(

        self,

        p

    ):

        W = p["width"]

        D = p["depth"]

        H = p["height"]

        if (

            W <= 0

            or

            D <= 0

            or

            H <= 0

        ):

            raise RuntimeError(

                "Oven dimensions must be greater than zero."

            )

        if p[

            "base_raise"

        ] < 0:

            raise RuntimeError(

                "BaseRaise cannot be negative."

            )

        if p[

            "cooktop_thickness"

        ] <= 0:

            raise RuntimeError(

                "CooktopThickness must be greater than zero."

            )

        if (

            p["burner_diameter"] <= 0

            or

            p["burner_height"] <= 0

        ):

            raise RuntimeError(

                "Burner dimensions must be greater than zero."

            )

        if (

            p["burner_diameter"] > W

            or

            p["burner_diameter"] > D

        ):

            raise RuntimeError(

                "BurnerDiameter is too large for the cooktop."

            )

        if (

            p["burner_count"] < 4

            or

            p["burner_count"] > 8

        ):

            raise RuntimeError(

                "BurnerCount must be between 4 and 8."

            )

        if (

            p["knob_diameter"] <= 0

            or

            p["knob_length"] <= 0

        ):

            raise RuntimeError(

                "Knob dimensions must be greater than zero."

            )

        if (

            p["knob_count"] < 4

            or

            p["knob_count"] > 8

        ):

            raise RuntimeError(

                "KnobCount must be between 4 and 8."

            )

        if p[

            "door_thickness"

        ] <= 0:

            raise RuntimeError(

                "OvenDoorThickness must be greater than zero."

            )

        if (

            p["door_gap"] < 0

            or

            p["door_bottom_gap"] < 0

            or

            p["door_top_clearance"] < 0

        ):

            raise RuntimeError(

                "Door gaps cannot be negative."

            )

    # ==========================================================

    # GENERIC POSITION HELPERS

    # ==========================================================

    def _x_positions(

        self,

        span,

        diameter,

        count

    ):

        if count <= 0:

            return []

        radius = (

            diameter

            /

            2.0

        )

        edge = max(

            10.0,

            radius * 0.20

        )

        start = (

            radius

            +

            edge

        )

        end = (

            span

            -

            radius

            -

            edge

        )

        if end <= start:

            start = radius

            end = span - radius

        if count == 1:

            return [

                span / 2.0

            ]

        step = (

            end

            -

            start

        ) / float(

            count - 1

        )

        return [

            start

            +

            index * step

            for index in range(count)

        ]

    # ==========================================================

    # BURNER LAYOUT

    # ==========================================================

    def _burner_centers(

        self,

        width,

        depth,

        diameter,

        count

    ):

        layouts = {

            4: (2, 2),

            5: (3, 2),

            6: (3, 3),

            7: (4, 3),

            8: (4, 4),

        }

        if count not in layouts:

            raise RuntimeError(

                "BurnerCount must be between 4 and 8."

            )

        front_count, rear_count = (

            layouts[count]

        )

        radius = (

            diameter

            /

            2.0

        )

        front_y = max(

            radius,

            depth * 0.30

        )

        rear_y = min(

            depth - radius,

            depth * 0.70

        )

        if rear_y <= front_y:

            front_y = radius

            rear_y = depth - radius

        front_x = self._x_positions(

            width,

            diameter,

            front_count

        )

        rear_x = self._x_positions(

            width,

            diameter,

            rear_count

        )

        centers = [

            (

                x,

                front_y

            )

            for x in front_x

        ]

        centers.extend(

            (

                x,

                rear_y

            )

            for x in rear_x

        )

        if len(centers) != count:

            raise RuntimeError(

                "Burner layout expected {} positions "

                "but generated {}."

                .format(

                    count,

                    len(centers)

                )

            )

        return centers

    # ==========================================================

    # UPDATE BODY

    # ==========================================================

    def _update_body(

        self,

        body_box,

        p

    ):

        body_z = p[

            "base_raise"

        ]

        body_box.Length = (

            p["width"]

        )

        body_box.Width = (

            p["depth"]

        )

        body_box.Height = (

            p["height"]

        )

        body_box.Placement.Base = App.Vector(

            0,

            0,

            body_z

        )

    # ==========================================================

    # UPDATE COOKTOP

    # ==========================================================

    def _update_cooktop(

        self,

        cooktop_box,

        p

    ):

        cooktop_z = (

            p["base_raise"]

            +

            p["height"]

        )

        cooktop_box.Length = (

            p["width"]

        )

        cooktop_box.Width = (

            p["depth"]

        )

        cooktop_box.Height = (

            p["cooktop_thickness"]

        )

        cooktop_box.Placement.Base = App.Vector(

            0,

            0,

            cooktop_z

        )

    # ==========================================================

    # UPDATE OVEN DOOR

    # ==========================================================

    def _update_door(

        self,

        door_box,

        p

    ):

        W = p["width"]

        H = p["height"]

        body_z = p[

            "base_raise"

        ]

        door_t = p[

            "door_thickness"

        ]

        door_gap = p[

            "door_gap"

        ]

        door_bottom = p[

            "door_bottom_gap"

        ]

        door_top = p[

            "door_top_clearance"

        ]

        # ------------------------------------------------------

        # PROVEN DOOR CALCULATION - UNCHANGED

        # ------------------------------------------------------

        door_width = (

            W

            -

            2.0 * door_gap

        )

        door_height = (

            H

            -

            2.0 * door_gap

            -

            door_top

        )

        door_z = (

            body_z

            +

            door_bottom

        )

        max_top_z = (

            body_z

            +

            H

            -

            door_gap

            -

            door_top

        )

        if door_width <= 0:

            raise RuntimeError(

                "OvenDoorGap leaves no usable door width."

            )

        if door_height <= 0:

            raise RuntimeError(

                "OvenDoorTopClearance leaves "

                "no usable door height."

            )

        if (

            door_z

            +

            door_height

            >

            max_top_z

        ):

            door_height = max(

                1.0,

                max_top_z - door_z

            )

        door_box.Length = (

            door_width

        )

        door_box.Width = (

            door_t

        )

        door_box.Height = (

            door_height

        )

        door_box.Placement.Base = App.Vector(

            door_gap,

            -door_t,

            door_z

        )

    # ==========================================================

    # UPDATE KNOBS

    # ==========================================================

    def _update_knobs(

        self,

        knobs,

        p

    ):

        W = p[

            "width"

        ]

        knob_d = p[

            "knob_diameter"

        ]

        knob_len = p[

            "knob_length"

        ]

        knob_count = p[

            "knob_count"

        ]

        knob_radius = (

            knob_d

            /

            2.0

        )

        cooktop_z = (

            p["base_raise"]

            +

            p["height"]

        )

        knob_z = (

            cooktop_z

            +

            p["cooktop_thickness"] / 2.0

        )

        # +90 degrees about X:

        # cylinder +Z axis points toward -Y.

        knob_rotation = App.Rotation(

            App.Vector(

                1,

                0,

                0

            ),

            90

        )

        # ------------------------------------------------------

        # EXISTING KNOB SPACING BEHAVIOR

        # ------------------------------------------------------

        if knob_count == 1:

            knob_positions = [

                W / 2.0

            ]

        else:

            start = (

                knob_radius

                +

                10.0

            )

            end = (

                W

                -

                knob_radius

                -

                10.0

            )

            if end <= start:

                start = knob_radius

                end = W - knob_radius

            step = (

                end

                -

                start

            ) / float(

                knob_count - 1

            )

            knob_positions = [

                start

                +

                index * step

                for index in range(

                    knob_count

                )

            ]

        for index, knob in enumerate(

            knobs

        ):

            cylinder = self._body_feature(

                knob,

                "Knob Cylinder {}".format(

                    index + 1

                ),

                "PartDesign::AdditiveCylinder"

            )

            cylinder.Radius = (

                knob_radius

            )

            cylinder.Height = (

                knob_len

            )

            if index < knob_count:

                cylinder.Placement = App.Placement(

                    App.Vector(

                        knob_positions[index],

                        0,

                        knob_z

                    ),

                    knob_rotation

                )

                knob.ViewObject.Visibility = True

            else:

                knob.ViewObject.Visibility = False

    # ==========================================================

    # UPDATE BURNERS

    # ==========================================================

    def _update_burners(

        self,

        burners,

        p

    ):

        burner_d = p[

            "burner_diameter"

        ]

        burner_h = p[

            "burner_height"

        ]

        burner_count = p[

            "burner_count"

        ]

        burner_radius = (

            burner_d

            /

            2.0

        )

        cooktop_z = (

            p["base_raise"]

            +

            p["height"]

        )

        burner_z = (

            cooktop_z

            +

            p["cooktop_thickness"]

        )

        centers = self._burner_centers(

            p["width"],

            p["depth"],

            burner_d,

            burner_count

        )

        for index, burner in enumerate(

            burners

        ):

            cylinder = self._body_feature(

                burner,

                "Burner Cylinder {}".format(

                    index + 1

                ),

                "PartDesign::AdditiveCylinder"

            )

            cylinder.Radius = (

                burner_radius

            )

            cylinder.Height = (

                burner_h

            )

            if index < burner_count:

                x, y = centers[index]

                cylinder.Placement.Base = App.Vector(

                    x,

                    y,

                    burner_z

                )

                burner.ViewObject.Visibility = True

            else:

                burner.ViewObject.Visibility = False

    # ==========================================================

    # EXECUTE

    # ==========================================================

    def execute(

        self,

        obj

    ):

        if getattr(

            self,

            "_building",

            False

        ):

            return

        assembly = self._assembly(

            obj

        )

        sheet = self._parameters(

            obj,

            assembly

        )

        parameters = self._read_parameters(

            sheet

        )

        self._validate(

            parameters

        )

        (

            body_box,

            cooktop_box,

            door_box,

            knobs,

            burners

        ) = self._resolve_geometry(

            assembly

        )

        self._update_body(

            body_box,

            parameters

        )

        self._update_cooktop(

            cooktop_box,

            parameters

        )

        self._update_door(

            door_box,

            parameters

        )

        self._update_knobs(

            knobs,

            parameters

        )

        self._update_burners(

            burners,

            parameters

        )

# ============================================================

# DIALOG VALIDATION

# ============================================================

def validate_values(

    values

):

    if (

        values["OvenWidth"] <= 0

        or

        values["OvenDepth"] <= 0

        or

        values["OvenHeight"] <= 0

    ):

        return (

            False,

            "Oven dimensions must be greater than zero."

        )

    if values[

        "BaseRaise"

    ] < 0:

        return (

            False,

            "Base Raise cannot be negative."

        )

    if values[

        "CooktopThickness"

    ] <= 0:

        return (

            False,

            "Cooktop Thickness must be greater than zero."

        )

    if (

        values["BurnerDiameter"] <= 0

        or

        values["BurnerHeight"] <= 0

    ):

        return (

            False,

            "Burner dimensions must be greater than zero."

        )

    if (

        values["BurnerDiameter"]

        >

        values["OvenWidth"]

        or

        values["BurnerDiameter"]

        >

        values["OvenDepth"]

    ):

        return (

            False,

            "Burner Diameter is too large for the cooktop."

        )

    if (

        values["BurnerCount"] < 4

        or

        values["BurnerCount"] > 8

    ):

        return (

            False,

            "Burner Count must be between 4 and 8."

        )

    if (

        values["KnobDiameter"] <= 0

        or

        values["KnobLength"] <= 0

    ):

        return (

            False,

            "Knob dimensions must be greater than zero."

        )

    if (

        values["KnobCount"] < 4

        or

        values["KnobCount"] > 8

    ):

        return (

            False,

            "Knob Count must be between 4 and 8."

        )

    if values[

        "OvenDoorThickness"

    ] <= 0:

        return (

            False,

            "Oven Door Thickness must be greater than zero."

        )

    if (

        values["OvenDoorGap"] < 0

        or

        values["OvenDoorBottomGap"] < 0

        or

        values["OvenDoorTopClearance"] < 0

    ):

        return (

            False,

            "Oven door gaps cannot be negative."

        )

    if (

        values["OvenWidth"]

        -

        2.0 * values["OvenDoorGap"]

        <= 0

    ):

        return (

            False,

            "Oven Door Gap leaves no usable door width."

        )

    if (

        values["OvenHeight"]

        -

        2.0 * values["OvenDoorGap"]

        -

        values["OvenDoorTopClearance"]

        <= 0

    ):

        return (

            False,

            "Door settings leave no usable door height."

        )

    return (

        True,

        ""

    )

# ============================================================

# INSTANCE-NAME HELPERS

# ============================================================

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

def next_parametric_oven_name(

    document

):

    """Return the next available ParametricOven### name."""

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

      - second non-endpoint left-click places the oven at 0,0,0

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

            getattr(self.snapper, "active_snaps", [])

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

            "Select oven insertion point: "

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

                "Oven endpoint-cancel callback failed: {}\n".format(exc)

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

                        "Endpoint found — left-click to place the oven."

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
                            "if none exists on second pick oven will be drawn "
                            "at 0,0,0."
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
                    "placing Parametric Oven / Range at 0,0,0.\n"

                )

                self._cleanup()

                try:

                    self.on_accept(

                        accepted_point

                    )

                except Exception as exc:

                    App.Console.PrintError(

                        "Oven insertion callback failed: {}\n".format(exc)

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

                    "Oven insertion callback failed: {}\n".format(exc)

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

                and event.getKey() == coin.SoKeyboardEvent.ESCAPE

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

# ============================================================

# ACTIVE-DOCUMENT INSTANCE BUILDER

# ============================================================

class OvenBuilder:

    """Create one independent parametric oven/range instance."""

    def __init__(

        self,

        document,

        instance_name

    ):

        if document is None:

            raise ValueError(

                "create_parametric_oven() requires "

                "an existing FreeCAD document."

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

    def run(

        self

    ):

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

    # ==========================================================

    # PARAMETERS

    # ==========================================================

    def _collect_parameters(

        self

    ):

        dialog = OvenDialog(

            self.parameters

        )

        if not dialog.exec():

            print(

                "Oven creation cancelled. "

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

                "Invalid Oven Parameters",

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

    # ==========================================================

    # INSERTION POINT

    # ==========================================================

    def _begin_insertion_point(self):

        """Begin non-blocking endpoint selection after the parameter dialog."""

        self._picker = EndpointSnapPointPicker(

            on_accept=self._insertion_point_accepted,

            on_cancel=self._insertion_point_cancelled

        )

        self._picker.begin()

    def _insertion_point_accepted(self, point):

        """Create the oven after a valid endpoint has been selected."""

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

                "Parametric Oven Creation Error",

                str(exc)

            )

            App.Console.PrintError(

                "Parametric oven creation failed: {}\n".format(exc)

            )

    def _insertion_point_cancelled(self):

        """Rollback temporary objects if insertion-point selection is cancelled."""

        self._picker = None

        self._rollback_new_objects()

        print(

            "Oven insertion cancelled. "

            "The active layout document was not changed."

        )

    # ==========================================================

    # COMPONENT

    # ==========================================================

    def _create_component(

        self

    ):

        self.assembly = self.document.addObject(

            "App::Part",

            self.instance_name

        )

        self.assembly.Label = (

            "Parametric Oven / Range"

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

            "Oven Controller"

        )

        OvenFP(

            self.controller,

            self.assembly,

            self.parameters

        )

    # ==========================================================

    # ROLLBACK / DISPLAY

    # ==========================================================

    def _rollback_new_objects(

        self

    ):

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

    def _show_component(

        self

    ):

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

    # ==========================================================

    # REPORT

    # ==========================================================

    def _print_header(

        self

    ):

        print("")

        print("=" * 60)

        print(

            "PARAMETRIC OVEN / RANGE"

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

        print("=" * 60)

    def _print_report(

        self

    ):

        p = SheetParams(

            self.parameters

        )

        width = qty_mm(

            p.get(

                "OvenWidth"

            ),

            730

        )

        depth = qty_mm(

            p.get(

                "OvenDepth"

            ),

            680

        )

        height = qty_mm(

            p.get(

                "OvenHeight"

            ),

            910

        )

        burner_count = qty_int(

            p.get(

                "BurnerCount"

            ),

            4

        )

        knob_count = qty_int(

            p.get(

                "KnobCount"

            ),

            4

        )

        print("")

        print("-" * 60)

        print(

            "OVEN INSTANCE CREATED SUCCESSFULLY"

        )

        print("-" * 60)

        print(

            "Document:               ",

            self.document.Name

        )

        print(

            "Oven instance:          ",

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

            "Oven Width:             ",

            width,

            "mm"

        )

        print(

            "Oven Depth:             ",

            depth,

            "mm"

        )

        print(

            "Oven Height:            ",

            height,

            "mm"

        )

        print(

            "Burner Count:           ",

            burner_count

        )

        print(

            "Knob Count:             ",

            knob_count

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

            "Edit '{}' to resize only this oven."

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

        print("=" * 60)

        print("")

# ============================================================

# PUBLIC APPLIANCE FACTORY

# ============================================================

def create_parametric_oven(

    document,

    instance_name

):

    """Begin creation of one independent oven/range inside *document*."""

    builder = OvenBuilder(

        document=document,

        instance_name=instance_name

    )

    return builder.run()

# ============================================================

# MAIN

# ============================================================

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

    instance_name = next_parametric_oven_name(

        document

    )

    return create_parametric_oven(

        document=document,

        instance_name=instance_name

    )

# ============================================================
# WORKBENCH MODULE NOTE
# ============================================================
# Do not call main() automatically here.
# CabinetsWorkbench.py imports this module, calls main(), and retains the
# returned OvenBuilder while endpoint selection is active.

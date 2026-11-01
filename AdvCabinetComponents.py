# Advanced Cabinets Workbench - shared FreeCAD geometry components
# Target: FreeCAD 1.1.4
# CABINET CORE V1
import FreeCAD as App
import Part
class CabinetPanel:
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
        if min(length, depth, height) <= 0:
            raise RuntimeError("{} dimensions must be greater than zero.".format(self.body.Label))
        self.body.Placement = App.Placement(App.Vector(x, y, z), App.Rotation())
        self.blank.Placement = App.Placement()
        self.blank.Length = length
        self.blank.Width = depth
        self.blank.Height = height
class RabbetedSidePanel:
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
    def update(self, thickness, depth, height, rabbet_depth, panel_depth, x, z=0.0):
        if min(thickness, depth, height, rabbet_depth, panel_depth) <= 0:
            raise RuntimeError("Rabbeted side-panel dimensions must all be greater than zero.")
        self.body.Placement = App.Placement(App.Vector(x, 0.0, z), App.Rotation())
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
    def __init__(self, left, right, top, bottom, back):
        self.left = left
        self.right = right
        self.top = top
        self.bottom = bottom
        self.back = back
    @classmethod
    def create(cls, doc, prefix):
        return cls(RabbetedSidePanel.create(doc, prefix, RabbetedSidePanel.LEFT), RabbetedSidePanel.create(doc, prefix, RabbetedSidePanel.RIGHT), CabinetPanel.create(doc, prefix, "Top", "Top"), CabinetPanel.create(doc, prefix, "Bottom", "Bottom"), CabinetPanel.create(doc, prefix, "Back", "Back"))
    @classmethod
    def from_document(cls, doc, prefix):
        def obj(suffix):
            result = doc.getObject("{}_{}".format(prefix, suffix))
            if result is None:
                raise RuntimeError("Cabinet carcass object '{}_{}' not found.".format(prefix, suffix))
            return result
        return cls(RabbetedSidePanel.from_existing(obj("LeftSide"), obj("LeftSideBlank"), obj("LeftSideBottomRabbet"), obj("LeftSideTopRabbet"), obj("LeftSideBackRabbet"), RabbetedSidePanel.LEFT), RabbetedSidePanel.from_existing(obj("RightSide"), obj("RightSideBlank"), obj("RightSideBottomRabbet"), obj("RightSideTopRabbet"), obj("RightSideBackRabbet"), RabbetedSidePanel.RIGHT), CabinetPanel.from_existing(obj("Top"), obj("TopBlank")), CabinetPanel.from_existing(obj("Bottom"), obj("BottomBlank")), CabinetPanel.from_existing(obj("Back"), obj("BackBlank")))
    @staticmethod
    def validate_dimensions(width, depth, height, thickness, rabbet_depth):
        if width <= 0 or depth <= 0 or height <= 0:
            raise RuntimeError("Cabinet Width, Depth and Height must be greater than zero.")
        if thickness <= 0:
            raise RuntimeError("CabinetThickness must be greater than zero.")
        if rabbet_depth <= 0 or rabbet_depth >= thickness:
            raise RuntimeError("RabbetDepth must be greater than zero and less than CabinetThickness.")
        if rabbet_depth > 0.5 * thickness + 1.0e-6:
            raise RuntimeError("RabbetDepth cannot exceed 50% of CabinetThickness.")
        if width - 2.0 * thickness <= 0:
            raise RuntimeError("CabinetThickness leaves no usable interior width.")
        if depth - thickness <= 0:
            raise RuntimeError("CabinetThickness leaves no usable interior depth.")
        if height - 2.0 * thickness <= 0:
            raise RuntimeError("CabinetThickness leaves no usable interior height.")
        if width - 2.0 * (thickness - rabbet_depth) <= 0:
            raise RuntimeError("CabinetThickness and RabbetDepth leave no usable top/bottom/back width.")
    @staticmethod
    def derived_dimensions(width, depth, thickness, rabbet_depth):
        return {"panel_width": width - 2.0 * (thickness - rabbet_depth), "panel_depth": depth - thickness}
    def update(self, width, depth, height, thickness, rabbet_depth, base_z=0.0):
        self.validate_dimensions(width, depth, height, thickness, rabbet_depth)
        derived = self.derived_dimensions(width, depth, thickness, rabbet_depth)
        panel_width = derived["panel_width"]
        panel_depth = derived["panel_depth"]
        self.left.update(thickness, depth, height, rabbet_depth, panel_depth, 0.0, base_z)
        self.right.update(thickness, depth, height, rabbet_depth, panel_depth, width - thickness, base_z)
        panel_x = thickness - rabbet_depth
        self.bottom.update(panel_width, panel_depth, thickness, panel_x, 0.0, base_z)
        self.top.update(panel_width, panel_depth, thickness, panel_x, 0.0, base_z + height - thickness)
        self.back.update(panel_width, thickness, height, panel_x, panel_depth, base_z)
    def bodies(self):
        return [self.left.body, self.right.body, self.top.body, self.bottom.body, self.back.body]
class ToeKick:
    def __init__(self, box):
        self.box = box
    @classmethod
    def create(cls, doc, prefix, component_name="ToeKickRiser", label="Toe Kick Riser"):
        box = doc.addObject("Part::Box", "{}_{}".format(prefix, component_name))
        box.Label = label
        return cls(box)
    @classmethod
    def from_existing(cls, box):
        if box is None:
            raise RuntimeError("Toe kick object was not found.")
        return cls(box)
    @staticmethod
    def validate_dimensions(width, depth, height, setback):
        if min(width, depth, height) <= 0:
            raise RuntimeError("Toe-kick dimensions must be greater than zero.")
        if setback < 0 or setback >= depth:
            raise RuntimeError("ToeKickSetback must be >= 0 and less than CabinetDepth.")
    def update(self, width, depth, height, setback):
        self.validate_dimensions(width, depth, height, setback)
        self.box.Length = width
        self.box.Width = depth - setback
        self.box.Height = height
        self.box.Placement = App.Placement(App.Vector(0.0, setback, 0.0), App.Rotation())
    def set_visible(self, visible):
        try:
            self.box.ViewObject.Visibility = bool(visible)
        except Exception:
            pass
class FrontStyleStrategy:
    name = "Base"
    @classmethod
    def validate(cls, width, height, thickness, frame_width, panel_thickness, glass_thickness):
        if min(width, height, thickness) <= 0:
            raise RuntimeError("Cabinet front dimensions must be greater than zero.")
    @classmethod
    def build(cls, width, height, thickness, frame_width, panel_thickness, glass_thickness):
        raise NotImplementedError
class SlabFrontStrategy(FrontStyleStrategy):
    name = "Slab"
    @classmethod
    def build(cls, width, height, thickness, frame_width, panel_thickness, glass_thickness):
        return Part.makeBox(width, thickness, height, App.Vector(0, -thickness, 0)), None
class FrameFrontStrategy(FrontStyleStrategy):
    @staticmethod
    def frame(width, height, thickness, frame_width):
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
    def validate(cls, width, height, thickness, frame_width, panel_thickness, glass_thickness):
        super().validate(width, height, thickness, frame_width, panel_thickness, glass_thickness)
        if frame_width <= 0 or width - 2.0 * frame_width <= 0 or height - 2.0 * frame_width <= 0:
            raise RuntimeError("Frame width leaves no center opening.")
class ShakerFrontStrategy(FrameFrontStrategy):
    name = "Shaker"
    @classmethod
    def validate(cls, width, height, thickness, frame_width, panel_thickness, glass_thickness):
        super().validate(width, height, thickness, frame_width, panel_thickness, glass_thickness)
        if panel_thickness <= 0 or panel_thickness > thickness:
            raise RuntimeError("Panel thickness must be > 0 and <= front thickness.")
    @classmethod
    def build(cls, width, height, thickness, frame_width, panel_thickness, glass_thickness):
        frame = cls.frame(width, height, thickness, frame_width)
        opening_width = width - 2.0 * frame_width
        opening_height = height - 2.0 * frame_width
        panel_y = -(thickness + panel_thickness) / 2.0
        panel = Part.makeBox(opening_width, panel_thickness, opening_height, App.Vector(frame_width, panel_y, frame_width))
        shape = frame.fuse(panel)
        try:
            shape = shape.removeSplitter()
        except Exception:
            pass
        return shape, None
class GlassFrontStrategy(FrameFrontStrategy):
    name = "Glass"
    @classmethod
    def validate(cls, width, height, thickness, frame_width, panel_thickness, glass_thickness):
        super().validate(width, height, thickness, frame_width, panel_thickness, glass_thickness)
        if glass_thickness <= 0 or glass_thickness > thickness:
            raise RuntimeError("Glass thickness must be > 0 and <= front thickness.")
    @classmethod
    def build(cls, width, height, thickness, frame_width, panel_thickness, glass_thickness):
        frame = cls.frame(width, height, thickness, frame_width)
        opening_width = width - 2.0 * frame_width
        opening_height = height - 2.0 * frame_width
        glass_y = -(thickness + glass_thickness) / 2.0
        glass = Part.makeBox(opening_width, glass_thickness, opening_height, App.Vector(frame_width, glass_y, frame_width))
        return frame, glass
FRONT_STYLE_BUILDERS = {strategy.name: strategy for strategy in (SlabFrontStrategy, ShakerFrontStrategy, GlassFrontStrategy)}
class CabinetFront:
    STYLE_SLAB = "Slab"
    STYLE_SHAKER = "Shaker"
    STYLE_GLASS = "Glass"
    def __init__(self, body, feature, style=STYLE_SLAB, glass=None):
        self.body = body
        self.feature = feature
        self.glass = glass
        self.style = style
        if style not in FRONT_STYLE_BUILDERS:
            raise ValueError("Unsupported CabinetFront style: {}".format(style))
    @classmethod
    def create(cls, doc, prefix, component_name, label, style=STYLE_SLAB, glass_capable=False):
        body = doc.addObject("PartDesign::Body", "{}_{}".format(prefix, component_name))
        body.Label = label
        feature = body.newObject("PartDesign::Feature", "{}_{}Shape".format(prefix, component_name))
        feature.Label = "{} Shape".format(label)
        glass = None
        if glass_capable:
            glass = doc.addObject("Part::Feature", "{}_{}Glass".format(prefix, component_name))
            glass.Label = "{} Glass".format(label)
            try:
                glass.ViewObject.ShapeColor = (0.60, 0.80, 0.90)
                glass.ViewObject.Transparency = 70
                glass.ViewObject.Visibility = False
            except Exception:
                pass
        return cls(body, feature, style, glass)
    @classmethod
    def from_existing(cls, body, feature, style=STYLE_SLAB, glass=None):
        return cls(body, feature, style, glass)
    def update(self, width, height, thickness, frame_width=0.0, panel_thickness=0.0, glass_thickness=0.0, x=0.0, z=0.0, back_y=0.0):
        strategy = FRONT_STYLE_BUILDERS[self.style]
        strategy.validate(width, height, thickness, frame_width, panel_thickness, glass_thickness)
        primary_shape, glass_shape = strategy.build(width, height, thickness, frame_width, panel_thickness, glass_thickness)
        placement = App.Placement(App.Vector(x, back_y, z), App.Rotation())
        self.body.Placement = placement
        self.feature.Placement = App.Placement()
        self.feature.Shape = primary_shape
        if self.glass is not None:
            self.glass.Placement = placement
            self.glass.Shape = glass_shape if glass_shape is not None else Part.Shape()
            try:
                self.glass.ViewObject.Visibility = self.style == self.STYLE_GLASS
            except Exception:
                pass
        elif glass_shape is not None:
            raise RuntimeError("Glass style requires a glass-capable CabinetFront object.")
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
        if self.glass is not None:
            try:
                self.glass.ViewObject.Visibility = state and self.style == self.STYLE_GLASS
            except Exception:
                pass
class CabinetDoor(CabinetFront):
    @classmethod
    def create(cls, doc, prefix, component_name, label, style=CabinetFront.STYLE_SLAB):
        front = super().create(doc, prefix, component_name, label, style, glass_capable=True)
        return cls(front.body, front.feature, style, front.glass)
    @classmethod
    def from_existing(cls, body, feature, glass, style=CabinetFront.STYLE_SLAB):
        return cls(body, feature, style, glass)
class CabinetDrawerBox:
    def __init__(self, feature):
        self.feature = feature
    @classmethod
    def create(cls, doc, prefix, component_name, label):
        feature = doc.addObject("Part::Feature", "{}_{}".format(prefix, component_name))
        feature.Label = label
        return cls(feature)
    @classmethod
    def from_existing(cls, feature):
        return cls(feature)
    @staticmethod
    def _shape(width, depth, height, wall):
        if width <= 2.0 * wall or depth <= 2.0 * wall or height <= wall:
            raise RuntimeError("Drawer box wall thickness leaves no usable cavity.")
        outer = Part.makeBox(width, depth, height)
        inner = Part.makeBox(width - 2.0 * wall, depth - 2.0 * wall, height - wall, App.Vector(wall, wall, wall))
        return outer.cut(inner)
    def update(self, width, depth, height, wall, x, y, z):
        self.feature.Shape = self._shape(width, depth, height, wall)
        self.feature.Placement = App.Placement(App.Vector(x, y, z), App.Rotation())
class BoxComponent:
    def __init__(self, box):
        self.box = box
    @classmethod
    def create(cls, doc, prefix, component_name, label):
        box = doc.addObject("Part::Box", "{}_{}".format(prefix, component_name))
        box.Label = label
        return cls(box)
    @classmethod
    def from_existing(cls, box):
        if box is None:
            raise RuntimeError("Box component was not found.")
        return cls(box)
    def update(self, length, depth, height, x=0.0, y=0.0, z=0.0):
        if min(length, depth, height) <= 0:
            raise RuntimeError("Box component dimensions must be greater than zero.")
        self.box.Length = length
        self.box.Width = depth
        self.box.Height = height
        self.box.Placement = App.Placement(App.Vector(x, y, z), App.Rotation())

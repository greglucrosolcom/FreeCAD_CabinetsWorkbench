# Advanced Cabinets Workbench - shared resolved-layout records
# Target: FreeCAD 1.1.4
# CABINET CORE V1
from dataclasses import dataclass, field
@dataclass(frozen=True)
class PlacementBox:
    x: float
    y: float
    z: float
    width: float
    depth: float = 0.0
    height: float = 0.0
@dataclass(frozen=True)
class ResolvedLayout:
    front: object = None
    drawer_boxes: object = None
    dividers: object = None
    shelves: object = None
    boxes: object = None
    extras: dict = field(default_factory=dict)
    def __getitem__(self, key):
        if hasattr(self, key):
            return getattr(self, key)
        return self.extras[key]

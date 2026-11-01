# Advanced Cabinets Workbench - shared runtime/build helpers
# Target: FreeCAD 1.1.4
# CABINET CORE V1
import FreeCAD as App
import FreeCADGui as Gui
class CabinetCreationTransaction:
    def __init__(self, document):
        if document is None:
            raise ValueError("A valid FreeCAD document is required.")
        self.document = document
        self._original = set(obj.Name for obj in document.Objects)
        self._committed = False
    def commit(self):
        self._committed = True
    def rollback(self):
        new_names = [obj.Name for obj in self.document.Objects if obj.Name not in self._original]
        for name in reversed(new_names):
            try:
                self.document.removeObject(name)
            except Exception:
                pass
        try:
            self.document.recompute()
        except Exception:
            pass
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None or not self._committed:
            self.rollback()
        return False
def sanitize_object_name(name, basename="Cabinet"):
    cleaned = "".join(c if (c.isalnum() or c == "_") else "_" for c in str(name).strip())
    if not cleaned:
        cleaned = basename
    if cleaned[0].isdigit():
        cleaned = "{}_{}".format(basename, cleaned)
    return cleaned
def next_instance_name(document, basename):
    if document is None:
        raise ValueError("A valid FreeCAD document is required.")
    index = 1
    while True:
        candidate = "{}{:03d}".format(basename, index)
        if document.getObject(candidate) is None:
            return candidate
        index += 1
def find_owning_part(obj):
    for parent in getattr(obj, "InList", []):
        if getattr(parent, "TypeId", "") == "App::Part":
            return parent
    try:
        name = str(obj.AssemblyObjectName).strip()
    except Exception:
        name = ""
    if name:
        assembly = obj.Document.getObject(name)
        if assembly is not None and assembly.TypeId == "App::Part":
            return assembly
    raise RuntimeError("Cabinet controller cannot resolve its owning App::Part.")
def ensure_link_property(obj, name, group="Component", description=""):
    if not hasattr(obj, name):
        obj.addProperty("App::PropertyLink", name, group, description)
    return getattr(obj, name)
def ensure_link_list_property(obj, name, group="Components", description=""):
    if not hasattr(obj, name):
        obj.addProperty("App::PropertyLinkList", name, group, description)
    return getattr(obj, name)
def set_component_links(controller, mapping):
    for property_name, target in mapping.items():
        ensure_link_property(controller, property_name, "Components")
        setattr(controller, property_name, target)
def set_component_link_lists(controller, mapping):
    for property_name, targets in mapping.items():
        ensure_link_list_property(controller, property_name, "Components")
        setattr(controller, property_name, list(targets))
def normalized_signature(values, extra=()):
    items = []
    for key in sorted(values):
        value = values[key]
        if isinstance(value, float):
            value = round(value, 9)
        items.append((key, value))
    return tuple(items) + tuple(extra)
class FeatureProxyRuntimeMixin:
    def _runtime_init(self):
        self._building = False
        self._last_signature = None
        self._warning_signature = None
    def _should_rebuild(self, values, extra=()):
        signature = normalized_signature(values, extra)
        if signature == getattr(self, "_last_signature", None):
            return False
        self._last_signature = signature
        return True
    def onDocumentRestored(self, obj):
        obj.Proxy = self
        self._building = False
        self._last_signature = None
        self._warning_signature = None
def show_component(document, assembly):
    try:
        App.setActiveDocument(document.Name)
    except Exception:
        pass
    try:
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(assembly)
    except Exception:
        pass
    try:
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.activeDocument().activeView().fitAll()
    except Exception:
        pass

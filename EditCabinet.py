import importlib
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

CABINET_MARKER_PROPERTY = "CabinetType"

def _has_cabinet_marker(obj):
    if obj is None:
        return False
    try:
        return CABINET_MARKER_PROPERTY in obj.PropertiesList and bool(str(obj.CabinetType).strip())
    except Exception:
        return False

def _parents(obj):
    try:
        return list(obj.InList)
    except Exception:
        return []

def _group_children(obj):
    try:
        return list(obj.Group)
    except Exception:
        return []

def find_controller_from_object(start_obj):
    """Resolve a selected cabinet, controller, or cabinet member to its controller."""
    if start_obj is None:
        return None
    queue = [start_obj]
    seen = set()
    assemblies = []
    while queue:
        current = queue.pop(0)
        if current is None:
            continue
        name = getattr(current, "Name", None)
        if name in seen:
            continue
        if name is not None:
            seen.add(name)
        if _has_cabinet_marker(current):
            return current
        try:
            if current.TypeId == "App::Part":
                assemblies.append(current)
        except Exception:
            pass
        queue.extend(_parents(current))
    for assembly in assemblies:
        for child in _group_children(assembly):
            if _has_cabinet_marker(child):
                return child
    return None

def selected_controller():
    try:
        selection = Gui.Selection.getSelection()
    except Exception:
        selection = []
    for selected in selection:
        controller = find_controller_from_object(selected)
        if controller is not None:
            return controller
    return None

def is_active():
    return selected_controller() is not None

def _proxy_module_name(controller):
    # Preferred future hook: a cabinet may explicitly name its editor module.
    try:
        if "EditModule" in controller.PropertiesList:
            name = str(controller.EditModule).strip()
            if name:
                return name
    except Exception:
        pass
    try:
        proxy = controller.Proxy
        if proxy is not None:
            name = str(proxy.__class__.__module__).strip()
            if name:
                return name
    except Exception:
        pass
    return ""

def _cabinet_description(controller):
    try:
        cabinet_type = str(controller.CabinetType).strip()
    except Exception:
        cabinet_type = "Unknown cabinet"
    try:
        label = str(controller.Label).strip()
    except Exception:
        label = str(getattr(controller, "Name", "Cabinet"))
    return cabinet_type, label

def edit_controller(controller):
    if controller is None:
        return None
    module_name = _proxy_module_name(controller)
    cabinet_type, label = _cabinet_description(controller)
    if not module_name:
        raise RuntimeError(
            "The selected cabinet controller does not identify an importable editor module."
        )
    if module_name == "__main__":
        raise RuntimeError(
            "The selected cabinet was created from __main__ and cannot be reopened reliably. "
            "Create the test cabinet through the CabinetsWorkbench Testing command so its "
            "FeaturePython class belongs to the importable testing module."
        )
    module = importlib.import_module(module_name)
    # First-choice protocol for production cabinet modules.
    if hasattr(module, "edit_controller"):
        return module.edit_controller(controller)
    # Current Task Panel prototype protocol. Selection remains intact, so the
    # cabinet module can resolve its own controller exactly as it already does.
    if hasattr(module, "edit_selected"):
        return module.edit_selected()
    raise RuntimeError(
        "Cabinet '{}' ({}) was found, but module '{}' does not provide "
        "edit_controller(controller) or edit_selected()."
        .format(label, cabinet_type, module_name)
    )

def edit_selected():
    controller = selected_controller()
    if controller is None:
        QtWidgets.QMessageBox.information(
            None,
            "Edit Cabinet",
            "Select a CabinetsWorkbench cabinet, its controller, or one of its components, "
            "then click Edit Cabinet again."
        )
        return None
    try:
        return edit_controller(controller)
    except Exception as exc:
        QtWidgets.QMessageBox.critical(
            None,
            "Edit Cabinet Error",
            str(exc)
        )
        App.Console.PrintError("Edit Cabinet failed: {}\n".format(exc))
        return None

import os
import traceback
import importlib
import re
import FreeCAD as App
import FreeCADGui as Gui

def _ensure_draft_snapper():
    """Initialize FreeCAD's standard Draft GUI Snapper singleton."""
    if hasattr(Gui, "Snapper"):
        return Gui.Snapper
    try:
        # FreeCAD's own DraftTools module creates FreeCADGui.Snapper.
        import DraftTools  # noqa: F401
    except Exception:
        App.Console.PrintError(
            "CabinetsWorkbench: DraftTools could not initialize Draft snapping:\n"
        )
        App.Console.PrintError(traceback.format_exc())
        return None
    if not hasattr(Gui, "Snapper"):
        App.Console.PrintError(
            "CabinetsWorkbench: DraftTools loaded but FreeCADGui.Snapper "
            "was not created.\n"
        )
        return None
    App.Console.PrintMessage(
        "CabinetsWorkbench: Draft Snapper initialized successfully.\n"
    )
    return Gui.Snapper

def _label_builder_parameters(builder, cabinet_label):
    """Set a descriptive tree label on a sheet-driven Parameters spreadsheet.

    Only the user-visible FreeCAD Label is changed. The spreadsheet's internal
    Name remains unchanged so existing links, aliases, expressions, and
    controller references continue to work.
    """
    if builder is None:
        return

    sheet = getattr(builder, "parameters", None)
    if sheet is None:
        return

    # Preserve the familiar Parameters### suffix whenever one is available.
    # Check the current label first, then the internal object name, then the
    # builder's cabinet instance name.
    candidates = (
        str(getattr(sheet, "Label", "") or ""),
        str(getattr(sheet, "Name", "") or ""),
        str(getattr(builder, "instance_name", "") or ""),
    )

    suffix = ""
    for candidate in candidates:
        # Examples matched:
        #   Parameters001
        #   LowerCabinet001_Parameters
        #   LowerCabinet001
        match = re.search(r"(?:Parameters)?(\d+)(?:_Parameters)?$", candidate, re.IGNORECASE)
        if match:
            suffix = match.group(1)
            break

    parameter_label = "Parameters{}".format(suffix) if suffix else "Parameters"
    sheet.Label = "{} {}".format(str(cabinet_label).strip(), parameter_label)

class TestingCommand:
    """Launch testing.py from CabinetsWorkbench."""
    def __init__(self):
        self._active_builder = None
    def GetResources(self):
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "Resources", "icons", "testing.svg"
        )
        resources = {
            "MenuText": "Testing",
            "ToolTip": "Run testing.py"
        }
        if os.path.isfile(icon_path):
            resources["Pixmap"] = icon_path
        return resources
    def IsActive(self):
        return True
    def Activated(self):
        App.Console.PrintMessage("Testing command activated.\n")
        try:
            if _ensure_draft_snapper() is None:
                return
            if self._active_builder is not None:
                try:
                    picker = getattr(self._active_builder, "_picker", None)
                    if picker is not None:
                        picker.cancel()
                except Exception:
                    pass
            import testing
            testing = importlib.reload(testing)
            App.Console.PrintMessage("testing.py imported/reloaded successfully.\n")
            if not hasattr(testing, "main"):
                App.Console.PrintError(
                    "testing.py does not contain a main() function.\n"
                )
                return
            self._active_builder = testing.main()
            if self._active_builder is not None:
                App.Console.PrintMessage(
                    "Testing command is active. Complete the current operation in the 3D view.\n"
                )
            else:
                App.Console.PrintMessage("Testing command finished.\n")
        except Exception:
            App.Console.PrintError("Error while running testing.py:\n")
            App.Console.PrintError(traceback.format_exc())

class EditCabinetCommand:
    """Open the Task Panel editor for the selected CabinetsWorkbench cabinet."""
    def __init__(self):
        self._active_editor = None
    def GetResources(self):
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "Resources", "icons", "EditCabinet.svg"
        )
        resources = {
            "MenuText": "Edit Cabinet",
            "ToolTip": "Edit the selected parametric cabinet in its Task Panel"
        }
        if os.path.isfile(icon_path):
            resources["Pixmap"] = icon_path
        return resources
    def IsActive(self):
        try:
            import EditCabinet
            return bool(EditCabinet.is_active())
        except Exception:
            return False
    def Activated(self):
        App.Console.PrintMessage("Edit Cabinet command activated.\n")
        try:
            import EditCabinet
            EditCabinet = importlib.reload(EditCabinet)
            self._active_editor = EditCabinet.edit_selected()
        except Exception:
            App.Console.PrintError("Error while running Edit Cabinet:\n")
            App.Console.PrintError(traceback.format_exc())

class CabinetsWorkbenchTestCommand:
    """Verify that CabinetsWorkbench commands are registered correctly."""
    def GetResources(self):
        return {
            "MenuText": "Test CabinetsWorkbench",
            "ToolTip": "Verify that CabinetsWorkbench is installed and operating"
        }
    def IsActive(self):
        return True
    def Activated(self):
        App.Console.PrintMessage("CabinetsWorkbench is installed and operating correctly.\n")

class LowerTwoDoorCabinetCommand:
    """Launch the lower one/two-door cabinet generator."""
    def __init__(self):
        self._active_builder = None
    def GetResources(self):
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "Resources", "icons", "LowerTwoDoorCabinet.svg"
        )
        resources = {
            "MenuText": "Lower Two Door Cabinet",
            "ToolTip": "Create a parametric lower cabinet with one or two doors"
        }
        if os.path.isfile(icon_path):
            resources["Pixmap"] = icon_path
        return resources
    def IsActive(self):
        return True
    def Activated(self):
        App.Console.PrintMessage("Lower Two Door Cabinet command activated.\n")
        try:
            if _ensure_draft_snapper() is None:
                return
            import LowerTwoDoorCabinet
            App.Console.PrintMessage("LowerTwoDoorCabinet.py imported successfully.\n")
            if not hasattr(LowerTwoDoorCabinet, "main"):
                App.Console.PrintError("LowerTwoDoorCabinet.py does not contain a main() function.\n")
                return
            if self._active_builder is not None:
                try:
                    picker = getattr(self._active_builder, "_picker", None)
                    if picker is not None:
                        picker.cancel()
                except Exception:
                    pass
            self._active_builder = LowerTwoDoorCabinet.main()
            _label_builder_parameters(self._active_builder, "Lower Two Door Cabinet")
            if self._active_builder is not None:
                App.Console.PrintMessage(
                    "Lower cabinet insertion command is active. Select an insertion point in the 3D view.\n"
                )
            else:
                App.Console.PrintMessage(
                    "Lower cabinet command finished or was cancelled before point selection.\n"
                )
        except Exception:
            App.Console.PrintError("Error while running LowerTwoDoorCabinet:\n")
            App.Console.PrintError(traceback.format_exc())

class TwoDoorUpperCabinetCommand:
    """Launch the upper one/two-door cabinet generator."""
    def __init__(self):
        self._active_builder = None
    def GetResources(self):
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "Resources", "icons", "TwoDoorUpperCabinet.svg"
        )
        resources = {
            "MenuText": "TwoDoorUpperCabinet",
            "ToolTip": "Create a parametric upper cabinet with one or two doors"
        }
        if os.path.isfile(icon_path):
            resources["Pixmap"] = icon_path
        return resources
    def IsActive(self):
        return True
    def Activated(self):
        App.Console.PrintMessage("TwoDoorUpperCabinet command activated.\n")
        try:
            if _ensure_draft_snapper() is None:
                return
            import TwoDoorUpperCabinet
            App.Console.PrintMessage("TwoDoorUpperCabinet.py imported successfully.\n")
            if not hasattr(TwoDoorUpperCabinet, "main"):
                App.Console.PrintError("TwoDoorUpperCabinet.py does not contain a main() function.\n")
                return
            if self._active_builder is not None:
                try:
                    picker = getattr(self._active_builder, "_picker", None)
                    if picker is not None:
                        picker.cancel()
                except Exception:
                    pass
            self._active_builder = TwoDoorUpperCabinet.main()
            _label_builder_parameters(self._active_builder, "Two Door Upper Cabinet")
            if self._active_builder is not None:
                App.Console.PrintMessage(
                    "Upper cabinet insertion command is active. Select an insertion point in the 3D view.\n"
                )
            else:
                App.Console.PrintMessage(
                    "Upper cabinet command finished or was cancelled before point selection.\n"
                )
        except Exception:
            App.Console.PrintError("Error while running TwoDoorUpperCabinet:\n")
            App.Console.PrintError(traceback.format_exc())

class UpperOpenShelfCommand:
    """Launch the parametric upper open-shelf cabinet generator."""
    def __init__(self):
        self._active_builder = None
    def GetResources(self):
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "Resources", "icons", "TwoDoorUpperCabinet.svg"
        )
        resources = {
            "MenuText": "Upper Open Shelf",
            "ToolTip": "Create a parametric upper open-shelf cabinet"
        }
        if os.path.isfile(icon_path):
            resources["Pixmap"] = icon_path
        return resources
    def IsActive(self):
        return True
    def Activated(self):
        App.Console.PrintMessage("Upper Open Shelf command activated.\n")
        try:
            if _ensure_draft_snapper() is None:
                return
            import upperOpenShelf
            App.Console.PrintMessage("upperOpenShelf.py imported successfully.\n")
            if not hasattr(upperOpenShelf, "main"):
                App.Console.PrintError("upperOpenShelf.py does not contain a main() function.\n")
                return
            if self._active_builder is not None:
                try:
                    picker = getattr(self._active_builder, "_picker", None)
                    if picker is not None:
                        picker.cancel()
                except Exception:
                    pass
            self._active_builder = upperOpenShelf.main()
            _label_builder_parameters(self._active_builder, "Upper Open Shelf")
            if self._active_builder is not None:
                App.Console.PrintMessage(
                    "Upper open-shelf insertion command is active. "
                    "Select an insertion point in the 3D view.\n"
                )
            else:
                App.Console.PrintMessage(
                    "Upper open-shelf command finished or was cancelled "
                    "before point selection.\n"
                )
        except Exception:
            App.Console.PrintError("Error while running upperOpenShelf:\n")
            App.Console.PrintError(traceback.format_exc())

class OvenCommand:
    """Launch the parametric oven/range generator."""
    def __init__(self):
        self._active_builder = None
    def GetResources(self):
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "Resources", "icons", "Oven.svg"
        )
        resources = {
            "MenuText": "Oven",
            "ToolTip": "Create a parametric oven/range"
        }
        if os.path.isfile(icon_path):
            resources["Pixmap"] = icon_path
        return resources
    def IsActive(self):
        return True
    def Activated(self):
        App.Console.PrintMessage("Oven command activated.\n")
        try:
            if _ensure_draft_snapper() is None:
                return
            import Oven
            App.Console.PrintMessage("Oven.py imported successfully.\n")
            if not hasattr(Oven, "main"):
                App.Console.PrintError("Oven.py does not contain a main() function.\n")
                return
            if self._active_builder is not None:
                try:
                    picker = getattr(self._active_builder, "_picker", None)
                    if picker is not None:
                        picker.cancel()
                except Exception:
                    pass
            self._active_builder = Oven.main()
            _label_builder_parameters(self._active_builder, "Oven")
            if self._active_builder is not None:
                App.Console.PrintMessage(
                    "Oven insertion command is active. "
                    "Select an insertion point in the 3D view.\n"
                )
            else:
                App.Console.PrintMessage(
                    "Oven command finished or was cancelled "
                    "before point selection.\n"
                )
        except Exception:
            App.Console.PrintError("Error while running Oven:\n")
            App.Console.PrintError(traceback.format_exc())

class SideBySideRefrigeratorCommand:
    """Launch the parametric side-by-side refrigerator/freezer generator."""
    def __init__(self):
        self._active_builder = None
    def GetResources(self):
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "Resources", "icons", "SideBySideRefrigerator.svg"
        )
        resources = {
            "MenuText": "Side-by-Side Refrigerator",
            "ToolTip": "Create a parametric side-by-side refrigerator/freezer"
        }
        if os.path.isfile(icon_path):
            resources["Pixmap"] = icon_path
        return resources
    def IsActive(self):
        return True
    def Activated(self):
        App.Console.PrintMessage("Side-by-Side Refrigerator command activated.\n")
        try:
            if _ensure_draft_snapper() is None:
                return
            import SideBySideRefrigerator
            App.Console.PrintMessage(
                "SideBySideRefrigerator.py imported successfully.\n"
            )
            if not hasattr(SideBySideRefrigerator, "main"):
                App.Console.PrintError(
                    "SideBySideRefrigerator.py does not contain a main() function.\n"
                )
                return
            if self._active_builder is not None:
                try:
                    picker = getattr(self._active_builder, "_picker", None)
                    if picker is not None:
                        picker.cancel()
                except Exception:
                    pass
            self._active_builder = SideBySideRefrigerator.main()
            _label_builder_parameters(self._active_builder, "Side-by-Side Refrigerator")
            if self._active_builder is not None:
                App.Console.PrintMessage(
                    "Side-by-side refrigerator insertion command is active. "
                    "Select an insertion point in the 3D view.\n"
                )
            else:
                App.Console.PrintMessage(
                    "Side-by-side refrigerator command finished or was cancelled "
                    "before point selection.\n"
                )
        except Exception:
            App.Console.PrintError(
                "Error while running SideBySideRefrigerator:\n"
            )
            App.Console.PrintError(traceback.format_exc())

class WineFridgeCommand:
    """Launch the parametric floor-standing wine fridge generator."""
    def __init__(self):
        self._active_builder = None
    def GetResources(self):
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "Resources", "icons", "WineFridge.svg"
        )
        resources = {
            "MenuText": "Wine Fridge",
            "ToolTip": "Create a parametric floor-standing wine fridge"
        }
        if os.path.isfile(icon_path):
            resources["Pixmap"] = icon_path
        return resources
    def IsActive(self):
        return True
    def Activated(self):
        App.Console.PrintMessage("Wine Fridge command activated.\n")
        try:
            if _ensure_draft_snapper() is None:
                return
            import WineFridge
            App.Console.PrintMessage("WineFridge.py imported successfully.\n")
            if not hasattr(WineFridge, "main"):
                App.Console.PrintError(
                    "WineFridge.py does not contain a main() function.\n"
                )
                return
            if self._active_builder is not None:
                try:
                    picker = getattr(self._active_builder, "_picker", None)
                    if picker is not None:
                        picker.cancel()
                except Exception:
                    pass
            self._active_builder = WineFridge.main()
            _label_builder_parameters(self._active_builder, "Wine Fridge")
            if self._active_builder is not None:
                App.Console.PrintMessage(
                    "Wine Fridge insertion command is active. "
                    "Select an insertion point in the 3D view.\n"
                )
            else:
                App.Console.PrintMessage(
                    "Wine Fridge command finished or was cancelled "
                    "before point selection.\n"
                )
        except Exception:
            App.Console.PrintError("Error while running WineFridge:\n")
            App.Console.PrintError(traceback.format_exc())

class LowerTwoDoorTwoDrawersAboveCommand:
    """Launch the lower cabinet with two doors and up to two drawers above."""
    def __init__(self):
        self._active_builder = None
    def GetResources(self):
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "Resources", "icons", "LowerTwoDoorTwoDrawersAbove.svg"
        )
        resources = {
            "MenuText": "Lower Two Door with Two Drawers Above",
            "ToolTip": "Create a parametric lower cabinet with two doors and drawers above"
        }
        if os.path.isfile(icon_path):
            resources["Pixmap"] = icon_path
        return resources
    def IsActive(self):
        return True
    def Activated(self):
        App.Console.PrintMessage(
            "Lower Two Door with Two Drawers Above command activated.\n"
        )
        try:
            if _ensure_draft_snapper() is None:
                return
            import LowerCabinet2Drawers2Door
            App.Console.PrintMessage(
                "LowerCabinet2Drawers2Door.py imported successfully.\n"
            )
            if not hasattr(LowerCabinet2Drawers2Door, "main"):
                App.Console.PrintError(
                    "LowerCabinet2Drawers2Door.py does not contain a main() function.\n"
                )
                return
            if self._active_builder is not None:
                try:
                    picker = getattr(self._active_builder, "_picker", None)
                    if picker is not None:
                        picker.cancel()
                except Exception:
                    pass
            self._active_builder = LowerCabinet2Drawers2Door.main()
            _label_builder_parameters(self._active_builder, "Lower Two Door with Two Drawers Above")
            if self._active_builder is not None:
                App.Console.PrintMessage(
                    "Lower drawer/door cabinet insertion command is active. "
                    "Select an insertion point in the 3D view.\n"
                )
            else:
                App.Console.PrintMessage(
                    "Lower drawer/door cabinet command finished or was cancelled "
                    "before point selection.\n"
                )
        except Exception:
            App.Console.PrintError(
                "Error while running LowerCabinet2Drawers2Door:\n"
            )
            App.Console.PrintError(traceback.format_exc())

class FourDrawerLowerCabinetCommand:
    """Launch the parametric four drawer lower cabinet generator."""
    def __init__(self):
        self._active_builder = None
    def GetResources(self):
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "Resources", "icons", "FourDrawerLowerCabinet.svg"
        )
        resources = {
            "MenuText": "Four Drawer Lower Cabinet",
            "ToolTip": "Create a parametric lower cabinet with four drawer fronts"
        }
        if os.path.isfile(icon_path):
            resources["Pixmap"] = icon_path
        return resources
    def IsActive(self):
        return True
    def Activated(self):
        App.Console.PrintMessage("Four Drawer Lower Cabinet command activated.\n")
        try:
            if _ensure_draft_snapper() is None:
                return
            import FourDrawerLowerCabinet
            App.Console.PrintMessage("FourDrawerLowerCabinet.py imported successfully.\n")
            if not hasattr(FourDrawerLowerCabinet, "main"):
                App.Console.PrintError(
                    "FourDrawerLowerCabinet.py does not contain a main() function.\n"
                )
                return
            if self._active_builder is not None:
                try:
                    picker = getattr(self._active_builder, "_picker", None)
                    if picker is not None:
                        picker.cancel()
                except Exception:
                    pass
            self._active_builder = FourDrawerLowerCabinet.main()
            _label_builder_parameters(self._active_builder, "Four Drawer Lower Cabinet")
            if self._active_builder is not None:
                App.Console.PrintMessage(
                    "Four drawer lower cabinet insertion command is active. "
                    "Select an insertion point in the 3D view.\n"
                )
            else:
                App.Console.PrintMessage(
                    "Four drawer lower cabinet command finished or was cancelled "
                    "before point selection.\n"
                )
        except Exception:
            App.Console.PrintError("Error while running FourDrawerLowerCabinet:\n")
            App.Console.PrintError(traceback.format_exc())

class MultiDoorDrawerLowerCabinetCommand:
    """Launch the mixed-front lower cabinet with door and drawer components."""
    def __init__(self):
        self._active_builder = None
    def GetResources(self):
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "Resources", "icons", "MultiDoorDrawerLowerCabinet.svg"
        )
        resources = {
            "MenuText": "Multi Door Drawer Lower Cabinet",
            "ToolTip": "Create a parametric mixed-front lower cabinet with door and drawers"
        }
        if os.path.isfile(icon_path):
            resources["Pixmap"] = icon_path
        return resources
    def IsActive(self):
        return True
    def Activated(self):
        App.Console.PrintMessage(
            "Multi Door Drawer Lower Cabinet command activated.\n"
        )
        try:
            if _ensure_draft_snapper() is None:
                return
            import MultiDoorDrawerLowerCabinet
            App.Console.PrintMessage(
                "MultiDoorDrawerLowerCabinet.py imported successfully.\n"
            )
            if not hasattr(MultiDoorDrawerLowerCabinet, "main"):
                App.Console.PrintError(
                    "MultiDoorDrawerLowerCabinet.py does not contain a main() function.\n"
                )
                return
            if self._active_builder is not None:
                try:
                    picker = getattr(self._active_builder, "_picker", None)
                    if picker is not None:
                        picker.cancel()
                except Exception:
                    pass
            self._active_builder = MultiDoorDrawerLowerCabinet.main()
            _label_builder_parameters(self._active_builder, "Multi Door Drawer Lower Cabinet")
            if self._active_builder is not None:
                App.Console.PrintMessage(
                    "Multi door drawer lower cabinet insertion command is active. "
                    "Select an insertion point in the 3D view.\n"
                )
            else:
                App.Console.PrintMessage(
                    "Multi door drawer lower cabinet command finished or was "
                    "cancelled before point selection.\n"
                )
        except Exception:
            App.Console.PrintError(
                "Error while running MultiDoorDrawerLowerCabinet:\n"
            )
            App.Console.PrintError(traceback.format_exc())

class LowerUserDefinedDrawersCommand:
    """Launch the lower cabinet with user-defined drawers."""
    def __init__(self):
        self._active_builder = None
    def GetResources(self):
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "Resources", "icons", "LowerUserDefinedDrawers.svg"
        )
        resources = {
            "MenuText": "Lower User Defined Drawers",
            "ToolTip": "Create a parametric lower cabinet with user-defined drawers"
        }
        if os.path.isfile(icon_path):
            resources["Pixmap"] = icon_path
        return resources
    def IsActive(self):
        return True
    def Activated(self):
        App.Console.PrintMessage(
            "Lower User Defined Drawers command activated.\n"
        )
        try:
            if _ensure_draft_snapper() is None:
                return
            import LowerUserDefinedDrawers
            App.Console.PrintMessage(
                "LowerUserDefinedDrawers.py imported successfully.\n"
            )
            if not hasattr(LowerUserDefinedDrawers, "main"):
                App.Console.PrintError(
                    "LowerUserDefinedDrawers.py does not contain a main() function.\n"
                )
                return
            if self._active_builder is not None:
                try:
                    picker = getattr(self._active_builder, "_picker", None)
                    if picker is not None:
                        picker.cancel()
                except Exception:
                    pass
            self._active_builder = LowerUserDefinedDrawers.main()
            _label_builder_parameters(self._active_builder, "Lower User Defined Drawers")
            if self._active_builder is not None:
                App.Console.PrintMessage(
                    "Lower User Defined Drawers insertion command is active. "
                    "Select an insertion point in the 3D view.\n"
                )
            else:
                App.Console.PrintMessage(
                    "Lower User Defined Drawers command finished or was cancelled "
                    "before point selection.\n"
                )
        except Exception:
            App.Console.PrintError(
                "Error while running LowerUserDefinedDrawers:\n"
            )
            App.Console.PrintError(traceback.format_exc())

class TallPantryUtilityCabinetCommand:
    """Launch the parametric tall pantry utility cabinet generator."""
    def __init__(self):
        self._active_builder = None
    def GetResources(self):
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "Resources", "icons", "tall_pantry_utility_cabinet.svg"
        )
        resources = {
            "MenuText": "Tall Pantry Utility Cabinet",
            "ToolTip": "Create a parametric tall pantry utility cabinet"
        }
        if os.path.isfile(icon_path):
            resources["Pixmap"] = icon_path
        return resources
    def IsActive(self):
        return True
    def Activated(self):
        App.Console.PrintMessage(
            "Tall Pantry Utility Cabinet command activated.\n"
        )
        try:
            if _ensure_draft_snapper() is None:
                return
            import tall_pantry_utility_cabinet
            App.Console.PrintMessage(
                "tall_pantry_utility_cabinet.py imported successfully.\n"
            )
            if not hasattr(tall_pantry_utility_cabinet, "main"):
                App.Console.PrintError(
                    "tall_pantry_utility_cabinet.py does not contain a main() function.\n"
                )
                return
            if self._active_builder is not None:
                try:
                    picker = getattr(self._active_builder, "_picker", None)
                    if picker is not None:
                        picker.cancel()
                except Exception:
                    pass
            self._active_builder = tall_pantry_utility_cabinet.main()
            _label_builder_parameters(self._active_builder, "Tall Pantry Utility Cabinet")
            if self._active_builder is not None:
                App.Console.PrintMessage(
                    "Tall pantry insertion command is active. "
                    "Select an insertion point in the 3D view.\n"
                )
            else:
                App.Console.PrintMessage(
                    "Tall pantry command finished or was cancelled before point selection.\n"
                )
        except Exception:
            App.Console.PrintError(
                "Error while running tall_pantry_utility_cabinet:\n"
            )
            App.Console.PrintError(traceback.format_exc())

_testing_command = TestingCommand()
_edit_cabinet_command = EditCabinetCommand()
_lower_two_door_command = LowerTwoDoorCabinetCommand()
_two_door_upper_command = TwoDoorUpperCabinetCommand()
_upper_open_shelf_command = UpperOpenShelfCommand()
_oven_command = OvenCommand()
_side_by_side_refrigerator_command = SideBySideRefrigeratorCommand()
_wine_fridge_command = WineFridgeCommand()
_lower_two_door_two_drawers_above_command = LowerTwoDoorTwoDrawersAboveCommand()
_four_drawer_lower_cabinet_command = FourDrawerLowerCabinetCommand()
_multi_door_drawer_lower_cabinet_command = MultiDoorDrawerLowerCabinetCommand()
_lower_user_defined_drawers_command = LowerUserDefinedDrawersCommand()
_tall_pantry_utility_cabinet_command = TallPantryUtilityCabinetCommand()

Gui.addCommand("CabinetsWorkbench_Testing", _testing_command)
Gui.addCommand("CabinetsWorkbench_EditCabinet", _edit_cabinet_command)
Gui.addCommand("CabinetsWorkbench_TestCommand", CabinetsWorkbenchTestCommand())
Gui.addCommand("CabinetsWorkbench_LowerTwoDoorCabinet", _lower_two_door_command)
Gui.addCommand("CabinetsWorkbench_TwoDoorUpperCabinet", _two_door_upper_command)
Gui.addCommand("CabinetsWorkbench_UpperOpenShelf", _upper_open_shelf_command)
Gui.addCommand("CabinetsWorkbench_Oven", _oven_command)
Gui.addCommand(
    "CabinetsWorkbench_SideBySideRefrigerator",
    _side_by_side_refrigerator_command
)
Gui.addCommand("CabinetsWorkbench_WineFridge", _wine_fridge_command)
Gui.addCommand(
    "CabinetsWorkbench_LowerTwoDoorTwoDrawersAbove",
    _lower_two_door_two_drawers_above_command
)
Gui.addCommand(
    "CabinetsWorkbench_FourDrawerLowerCabinet",
    _four_drawer_lower_cabinet_command
)
Gui.addCommand(
    "CabinetsWorkbench_MultiDoorDrawerLowerCabinet",
    _multi_door_drawer_lower_cabinet_command
)
Gui.addCommand(
    "CabinetsWorkbench_LowerUserDefinedDrawers",
    _lower_user_defined_drawers_command
)
Gui.addCommand(
    "CabinetsWorkbench_TallPantryUtilityCabinet",
    _tall_pantry_utility_cabinet_command
)

App.Console.PrintMessage("CabinetsWorkbench.py: commands registered successfully.\n")

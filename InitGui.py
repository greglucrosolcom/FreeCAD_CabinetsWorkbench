import os
import sys
import traceback
import FreeCAD as App
import FreeCADGui as Gui

class CabinetsWorkbench(Workbench):
    """CabinetsWorkbench FreeCAD Python workbench."""
    MenuText = "CabinetsWorkbench"
    ToolTip = "Parametric cabinet design tools"
    def __init__(self):
        # FreeCAD may execute InitGui.py without defining __file__.
        # Locate the installed workbench module without relying on importlib.
        workbench_path = ""
        for search_dir in sys.path:
            if search_dir and os.path.isfile(os.path.join(search_dir, "CabinetsWorkbench.py")):
                workbench_path = os.path.abspath(search_dir)
                break
        if not workbench_path:
            # Also inspect the usual FreeCAD user Mod installation location.
            candidate = os.path.join(App.getUserAppDataDir(), "Mod", "CabinetsWorkbench")
            if os.path.isfile(os.path.join(candidate, "CabinetsWorkbench.py")):
                workbench_path = candidate
        icon_path = os.path.join(
            workbench_path,
            "Resources",
            "icons",
            "CABworkBenIcon.svg"
        )
        if os.path.isfile(icon_path):
            self.__class__.Icon = icon_path
        else:
            self.__class__.Icon = ""
            App.Console.PrintWarning(
                "CabinetsWorkbench: CABworkBenIcon.svg was not found at: "
                + icon_path
                + "\n"
            )
    def Initialize(self):
        App.Console.PrintMessage("CabinetsWorkbench: Initialize() started.\n")
        try:
            import Draft_rc  # noqa: F401
            import DraftTools  # noqa: F401
            import DraftGui  # noqa: F401
            import CabinetsWorkbench
            App.Console.PrintMessage(
                "CabinetsWorkbench: Draft GUI tools initialized successfully.\n"
            )
            App.Console.PrintMessage(
                "CabinetsWorkbench: CabinetsWorkbench.py imported successfully.\n"
            )
        except Exception:
            App.Console.PrintError(
                "CabinetsWorkbench: error importing CabinetsWorkbench.py:\n"
            )
            App.Console.PrintError(traceback.format_exc())
            return
        self.command_list = [
            "CabinetsWorkbench_Testing",
            "CabinetsWorkbench_EditCabinet",
            "CabinetsWorkbench_TestCommand",
            "CabinetsWorkbench_LowerTwoDoorCabinet",
            "CabinetsWorkbench_TwoDoorUpperCabinet",
            "CabinetsWorkbench_UpperOpenShelf",
            "CabinetsWorkbench_Oven",
            "CabinetsWorkbench_SideBySideRefrigerator",
            "CabinetsWorkbench_WineFridge",
            "CabinetsWorkbench_LowerTwoDoorTwoDrawersAbove",
            "CabinetsWorkbench_FourDrawerLowerCabinet",
            "CabinetsWorkbench_MultiDoorDrawerLowerCabinet",
            "CabinetsWorkbench_LowerUserDefinedDrawers",
            "CabinetsWorkbench_TallPantryUtilityCabinet",
            "Draft_Move"
        ]
        self.appendToolbar("Cabinets", self.command_list)
        self.appendMenu("Cabinets", self.command_list)
        App.Console.PrintMessage(
            "CabinetsWorkbench: toolbar and menu created successfully.\n"
        )
    def Activated(self):
        App.Console.PrintMessage("CabinetsWorkbench activated.\n")
    def Deactivated(self):
        return
    def ContextMenu(self, recipient):
        return
    def GetClassName(self):
        return "Gui::PythonWorkbench"

Gui.addWorkbench(CabinetsWorkbench())
App.Console.PrintMessage("CabinetsWorkbench: workbench registered successfully.\n")

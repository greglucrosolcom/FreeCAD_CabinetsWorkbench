# Advanced Cabinets Workbench - canonical endpoint snap picker
# Target: FreeCAD 1.1.4
# CABINET CORE V1
import warnings
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets
from pivy import coin
from draftutils import gui_utils
class EndpointSnapPointPicker:
    """Preference-free two-attempt endpoint picker using FreeCAD's shared Draft Snapper."""
    def __init__(self, on_accept, on_cancel, subject="cabinet"):
        self.on_accept = on_accept
        self.on_cancel = on_cancel
        self.subject = str(subject)
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
            warnings.filterwarnings("ignore", message=r"builtin type SwigPyObject has no __module__ attribute", category=DeprecationWarning)
            self.callback_move = self.view.addEventCallbackPivy(coin.SoLocation2Event.getClassTypeId(), self._mouse_move)
            self.callback_click = self.view.addEventCallbackPivy(coin.SoMouseButtonEvent.getClassTypeId(), self._mouse_click)
            self.callback_key = self.view.addEventCallbackPivy(coin.SoKeyboardEvent.getClassTypeId(), self._key_press)
        self._status("Select {} insertion point: hover over an existing endpoint until the snap marker appears, then left-click. Press Esc or right-click to cancel.".format(self.subject))
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
                    self._status("Endpoint found — left-click to place the {}.".format(self.subject))
                elif self._failed_endpoint_picks == 0:
                    self._status("Select an existing endpoint/vertex.")
                else:
                    self._status("Second pick: select an endpoint. If no endpoint exists, click again to place at 0,0,0.")
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
                    self._status("Second pick: select an endpoint. If no endpoint exists, click again to place at 0,0,0.")
                    QtWidgets.QMessageBox.information(None, "Endpoint Required", "An endpoint is required, please select an endpoint, if none exists on second pick cabinet will be drawn at 0,0,0.")
                    return
                self._finished = True
                accepted = App.Vector(0.0, 0.0, 0.0)
                App.Console.PrintMessage("No endpoint selected on second pick; placing {} at 0,0,0.\n".format(self.subject))
                self._cleanup()
                self._safe_accept(accepted)
                return
            cb.setHandled()
            self._finished = True
            accepted = App.Vector(point)
            self._cleanup()
            self._safe_accept(accepted)
        except Exception as exc:
            App.Console.PrintError("Endpoint click handling failed: {}\n".format(exc))
            self.cancel()
    def _safe_accept(self, point):
        try:
            self.on_accept(point)
        except Exception as exc:
            App.Console.PrintError("{} insertion callback failed: {}\n".format(self.subject, exc))
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
        try:
            self.on_cancel()
        except Exception as exc:
            App.Console.PrintError("{} endpoint-cancel callback failed: {}\n".format(self.subject, exc))
    def _cleanup(self):
        removed = False
        if self.view is not None:
            callbacks = ((coin.SoLocation2Event.getClassTypeId(), self.callback_move), (coin.SoMouseButtonEvent.getClassTypeId(), self.callback_click), (coin.SoKeyboardEvent.getClassTypeId(), self.callback_key))
            for typeid, token in callbacks:
                if token is not None:
                    try:
                        self.view.removeEventCallbackPivy(typeid, token)
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
    def _status(message):
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

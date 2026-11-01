# Publication review — preview only

- Kept existing spreadsheet-driven cabinet and appliance module implementations.
- Added six supplied core modules, plus `AdvCabinetRuntime.py` copied from supplied `AdvCoreRuntime.py` to resolve existing imports.
- Changed `InitGui.py` and toolbar icon paths to resolve from the actual installed folder rather than the current user's FreeCAD app data directory.
- Added `README.md` and `.gitignore`.
- Did not alter the Advanced Workbench or the uploaded archives.
- No license was selected on the owner's behalf. A public Github upload is **not** open source until a suitable license is provided.
- `package.xml` cannot be finalized until repository URL, branch, license and release version are confirmed.
- Python syntax and local import resolution checked statically, not run inside FreeCAD.
- Existing relative/top-level imports are retained for stability; modern namespaced layout can be considered after GUI testing.
- Existing `CabinetCoreV1_MANIFEST.txt` refers to optional files not in this package; it reflects a broader core manifest and is not an installation dependency list.

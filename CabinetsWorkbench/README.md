# FreeCAD Cabinets Workbench

A Python-based, spreadsheet-driven parametric cabinet design workbench for FreeCAD.

**Repository:** https://github.com/greglucrosolcom/FreeCAD_cabinetsWorkbench  
**Maintainer:** GSR (`greglucrosolcom`)  
**License:** [The Unlicense](LICENSE) (`Unlicense` SPDX identifier)

## Features

- Parametric lower, upper, pantry and open-shelf cabinet tools.
- Spreadsheet-controlled cabinet dimensions, components and updates.
- Adjustable door/drawer arrangements and toe kicks in supported commands.
- Additional appliance geometry commands including oven, refrigerator and wine refrigerator.
- Cabinet-specific parameter-sheet labels, while preserving FreeCAD's unique internal spreadsheet object names.
- Custom command toolbar and SVG icons.

The project is the **standard spreadsheet-driven Cabinets Workbench**, not the separate Advanced Cabinets Workbench.

## Installation (manual)

1. Install a supported FreeCAD version. This package has been user-tested starting in **FreeCAD 1.1.4 on Linux**; other versions/platforms need validation.
2. Download the repository's ZIP archive or clone it.
3. Place the **contents of this repository** in a folder named `CabinetsWorkbench` inside your FreeCAD user `Mod` directory. In the tested installation this was `~/.local/share/FreeCAD/v1-1/Mod/CabinetsWorkbench/`.
4. Verify that the installed directory contains `Init.py`, `InitGui.py`, `CabinetsWorkbench.py`, `package.xml`, and `Resources/icons/` directly within it (no extra nested directory).
5. Restart FreeCAD and select **CabinetsWorkbench** from the workbench selector.

**Important:** If a development copy is already installed, back it up outside `Mod` before replacing it. Do not install two copies of this workbench simultaneously.

## Basic usage

1. Create or open a FreeCAD document.
2. Switch to the **CabinetsWorkbench** workbench.
3. Choose a cabinet creation command from the **Cabinets** toolbar/menu.
4. Enter dimensions in the command dialog as applicable.
5. Edit the generated parameter spreadsheet to change the design, where supported by that command.
6. Save the FreeCAD document (`.FCStd`).

## Compatibility and dependencies

- FreeCAD's Python environment is required (this code cannot run as standalone system Python).
- The workbench imports FreeCAD Draft GUI modules and uses FreeCAD's built-in Python/Qt environment.
- Seven `AdvCabinet*.py` shared helper modules are included **inside this repository**. Their names are historical; the public workbench does not require the separately installed Advanced Cabinets Workbench.
- **Known tested setup:** FreeCAD 1.1.4, Linux. Other releases and platforms are not yet confirmed.

## Development status

This is a publication-preparation package based on the author-verified functioning Revision 4 workbench. Its original application Python source and SVG assets are preserved. The first GitHub release version and official Addon Manager approval are pending.

Please report reproducible problems through [GitHub Issues](https://github.com/greglucrosolcom/FreeCAD_cabinetsWorkbench/issues), including FreeCAD version, OS, command used and the complete Report View traceback.

## Licensing

The repository is intended to be published under [The Unlicense](LICENSE). Before publication the maintainer should confirm ownership or compatible permissions for **all** included code and artwork, including the historically shared `AdvCabinet*.py` modules and SVG icons. Third-party material is not automatically relicensed by this declaration.

Not affiliated with or endorsed by the FreeCAD project.

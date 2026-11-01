CABINET CORE V1.01 - FREECAD 1.1.4 TEST PACKAGE
==============================================

V1.01 hotfix
------------
- fixes AdvCabinetParameters Options-column formatting for 3-part active_when conditions such as ("DoorCount", ">", 0)
- centrally normalizes single 2-part, single 3-part, and multiple active_when conditions
- adds regression coverage that creates a Parameters sheet containing 3-part and multi-condition rules
- no cabinet geometry, parameter ranges, snapping, or cabinet module revisions changed

Purpose
-------
This package migrates the recently validated cabinet family to a shared architecture while preserving the current cabinet-specific geometry and default dimensions.

Install for testing
-------------------
1. Back up:
   ~/.local/share/FreeCAD/v1-1/Mod/CabinetsWorkbench/
2. Copy ALL files from this package into that CabinetsWorkbench directory.
3. Keep your existing CabinetsWorkbench.py unless you intentionally want to change workbench command registration. The cabinet module filenames were preserved so the existing imports continue to work.
4. Restart FreeCAD 1.1.4.
5. Optional: run CabinetCoreV1_FreeCADSmokeTest.py as a macro or import it in the FreeCAD Python console and call run().
6. Test cabinet creation, endpoint insertion, spreadsheet edits/recompute, Overlay/Inset switching, Slab/Shaker/Glass where applicable, copy/link behavior, and cancel/error rollback.

Shared core modules
-------------------
AdvCabinetValidation.py
- ParameterSpec
- structured ValidationIssue / ValidationResult
- inclusive 1e-6 mm range tolerance
- General/Base/Upper/Tall validation profiles
- Tall profile height = 1524-3048 mm (60-120 in)

AdvCabinetParameters.py
- declarative ParameterDefinition / ParameterSchema
- shared SheetParams and strict quantity parsing
- schema-derived parameter spreadsheet A-E columns
- conditional parameter activation
- legacy alias handling
- schema overrides for cabinet-specific UI grouping

AdvCabinetComponents.py
- five-part rabbeted CabinetCarcass
- ToeKick
- CabinetFront
- Slab/Shaker/Glass front-style strategies
- CabinetDrawerBox
- generic BoxComponent

AdvCabinetLayouts.py
- typed ResolvedLayout record with both attribute and mapping access
- shared placement record for future layout migrations

AdvCabinetRuntime.py
- CabinetCreationTransaction rollback/commit
- standardized name sanitization and next-instance naming
- direct FreeCAD link helpers
- normalized parameter signature helper for recompute caching

AdvCabinetSnap.py
- frozen proven endpoint picker
- DraftTools initializes the canonical shared FreeCADGui.Snapper
- temporary Lock + Endpoint snaps
- exact callback cleanup and snap-list restoration
- no persistent Draft preference changes

AdvCabinetDialog.py
- schema-driven parameter dialog
- automatic text/length/integer controls
- conditional enable/disable behavior
- range tooltips
- validator error/warning handling
- derived-value preview support

AdvCabinetMigration.py
- centralized standard parameter migrations/legacy aliases
- BoxWallThickness -> CabinetThickness
- FrontOffset -> FrontProud
- ToeKickDepth -> ToeKickSetback
- DrawerThickness -> DrawerFrontThickness

AdvCabinetProfiles.py
- named validation profile registry

CabinetCoreV1_regression.py
- pure-Python regression checks for boundaries, quantities, schema conditions, structured issues and migrations

CabinetCoreV1_FreeCADSmokeTest.py
- imports all migrated cabinets inside FreeCAD and validates every default parameter set

Migrated cabinet modules
------------------------
LowerTwoDoorCabinet.py                 Revision 0.13 / Schema 2
TwoDoorUpperCabinet.py                 Revision 0.20 / Schema 2
upperOpenShelf.py                      Revision 0.07 / Schema 2
LowerCabinet2Drawers2Door.py           Revision 0.13 / Schema 2
FourDrawerLowerCabinet.py              Revision 0.16 / Schema 2
MultiDoorDrawerLowerCabinet.py         Revision 0.15 / Schema 2
tall_pantry_utility_cabinet.py         Revision 0.16 / Schema 2

Architecture changes applied to all migrated cabinets
-----------------------------------------------------
- shared ParameterSpec / ValidationResult infrastructure
- shared quantity parsers and SheetParams
- shared parameter spreadsheet generator
- shared five-part carcass/front/toe-kick/drawer-box components where applicable
- shared frozen endpoint picker
- shared creation transaction for clean cancel/error rollback
- shared instance-name sanitization/numbering
- controller CabinetType, CabinetSchemaVersion and GeneratorRevision metadata
- controller App::PropertyLinkList Components direct object references
- normalized parameter-signature recompute cache
- schema-driven dialogs with conditional fields
- explicit parameter schemas for future upgrades/migrations

Important testing note
----------------------
The purpose of this package is architectural equivalence. No intentional default cabinet geometry changes were made during the Core v1 migration. If a cabinet differs geometrically from its immediately previous validated revision at default settings, treat that as a regression and report the exact cabinet/module and behavior.

Recommended test order
----------------------
1. LowerTwoDoorCabinet - simplest reference cabinet.
2. TwoDoorUpperCabinet - upper reference + Glass style.
3. upperOpenShelf - zero/one/two doors + shelf behavior.
4. FourDrawerLowerCabinet - derived repeated drawer layout.
5. LowerCabinet2Drawers2Door - coupled drawer/door layout.
6. MultiDoorDrawerLowerCabinet - complex fronts + boxes + dividers.
7. tall_pantry_utility_cabinet - tallest/most complex stress test.

If Core v1 passes these tests, new cabinet refactors should target this architecture rather than copying infrastructure from an older standalone macro.

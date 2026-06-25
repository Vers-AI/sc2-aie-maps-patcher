# SC2 AIE Map Patching Process

## Background

- SC2 Linux binary is frozen at 4.10.0 (used by AI Arena, ProBots). The game API does not update with live patches.
- To mimic newer patches (5.0.x), updated game data XML files and new assets are injected into the map's MPQ archive. The map overrides the game's default data when loaded.
- AIE maps already contain 109 GameData XML files + assets. Patching = replacing those files with updated versions from the target patch.

## What's Inside an AIE Map (.SC2Map)

An SC2Map file is an MPQ archive containing:
- `Base.SC2Data/GameData/*.xml` — 109 XML files with all game data
- `enUS.SC2Data/LocalizedData/*.txt` — localized strings
- `Assets/` — 3D models (.m3), textures (.dds), sounds (.ogg)
- `MapScript.galaxy`, `Triggers`, terrain data, minimap, map info

## Manual Process (Scarlett's Workflow)

1. Open the map in SC2 Editor (Windows). Verify map loads correctly.
2. Open the .SC2Map file with Ladik's MPQ Editor
3. Navigate to `Base.SC2Data/GameData/` and replace all 109 XML files with updated versions
4. Navigate to `enUS.SC2Data/LocalizedData/` and replace string files
5. Add any new Assets from the patch
6. Save the MPQ archive
7. Test by loading the map in SC2

## Automated Process (Headless Linux)

1. Extract the .SC2Map MPQ archive using mpyq/StormLib
2. Replace GameData XML files with target patch versions
3. Replace localized string files
4. Add/update new Assets from the patch folder
5. Repackage into a new .SC2Map MPQ archive (16MB sector size for compression)
6. Test with Docker tournament infrastructure

## Patch Sources

- `aiarena/sc2patch` (GitHub) — patch data files for versions 5.0.3 through 5.0.14
- `Cryptyc/Sc2-AIE-Maps` (GitHub) — pre-patched AIE maps for 5.0.12, 5.0.13, 5.0.14

## Example: What Changed Between 5.0.12 and 5.0.13

- Cyclone: speed 0.7851 → 0.914, new CycloneFakeWeapon (range 6, min scan 6.5)
- Widow Mine: Armory requirement → Drilling Claws requirement (tech tree shift)
- Lurker (burrowed): new SubgroupPriority 93
- Observer (siege mode): shields 30/30 added (was missing)
- Various weapons: new Range 0.2 values, AcquirePrioritization changes

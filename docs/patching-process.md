# SC2 AIE Map Patching Process

How to update AIE maps to mimic SC2 balance patches when the game API is frozen at an older version. This is the process used by the VersusAI team to keep bot competition maps current.

## Background

The StarCraft 2 Linux binary (used by AI Arena and bot competitions) is frozen at version 4.10.0. The game API does not receive balance updates. To run bots on current balance, map files are modified to include updated game data — the map overrides the binary's default data when loaded into the game.

This document covers the full process, from understanding the map format to automated patching on Linux.

---

## What's Inside an AIE Map (.SC2Map)

An SC2Map file is an MPQ archive (Blizzard's proprietary archive format) containing:

**Game Data (the balance values):**
- `Base.SC2Data/GameData/*.xml` — 109 XML files with all game data
- Key files: UnitData.xml, WeaponData.xml, AbilData.xml, EffectData.xml, UpgradeData.xml, BehaviorData.xml, RequirementData.xml, stableid.json

**Localized Strings:**
- `enUS.SC2Data/LocalizedData/GameStrings.txt`
- `enUS.SC2Data/LocalizedData/ObjectStrings.txt`
- `enUS.SC2Data/LocalizedData/TriggerStrings.txt`
- `enUS.SC2Data/LocalizedData/GameHotkeys.txt`

**Assets (visual/audio):**
- `Assets/` — 3D models (.m3), textures (.dds), sounds (.ogg) for new or changed visual elements

**Map Structure:**
- `MapScript.galaxy` — the trigger script (Galaxy scripting language)
- `Triggers`, `Triggers.version` — compiled trigger data
- `t3*` files — terrain data (height maps, texture masks, cell flags, etc.)
- `Minimap.tga` — minimap image
- `MapInfo`, `DocumentInfo`, `Objects`, `Preload.xml` — map metadata

---

## Patch Sources

Patch data files come from the [aiarena/sc2patch](https://github.com/aiarena/sc2patch) repository, which contains data extracted from SC2 patches 5.0.3 through 5.0.14. Each version folder contains:
- `Base.SC2Data/GameData/*.xml` — the updated game data XMLs
- `enUS.SC2Data/LocalizedData/*.txt` — updated string files
- `Assets/` — new or changed visual/audio assets

Pre-patched reference maps are available in [Cryptyc/Sc2-AIE-Maps](https://github.com/Cryptyc/Sc2-AIE-Maps) for versions 5.0.12–5.0.14.

---

## Manual Process (Windows + SC2 Editor)

This is the original workflow used by Scarlett for AI Arena:

1. Open the map in SC2 Editor (Windows). Verify it loads correctly.
2. Open the `.SC2Map` file with Ladik's MPQ Editor — a Windows tool for browsing and editing MPQ archives.
3. Navigate to `Base.SC2Data/GameData/` and replace all 109 XML files with the updated versions from the target patch.
4. Navigate to `enUS.SC2Data/LocalizedData/` and replace the string files (GameStrings.txt, ObjectStrings.txt, TriggerStrings.txt, GameHotkeys.txt).
5. Add any new Assets (models, textures, sounds) from the patch to the `Assets/` folder. When replacing existing files, confirm the overwrite.
6. Save the MPQ archive. The `.SC2Map` file is now patched.
7. Test by loading the map in StarCraft 2 and playing a game.

**Known issue:** The loading screen image may break after patching. This is cosmetic and does not affect gameplay.

---

## Automated Process (Headless Linux)

The same process can be done programmatically without Windows, SC2 Editor, or Ladik's MPQ Editor. The [sc2-aie-maps-patcher](https://github.com/Vers-AI/sc2-aie-maps-patcher) tool automates the full workflow.

### Prerequisites

**StormLib** (C library for MPQ read/write):
```bash
git clone https://github.com/ladislav-zezula/StormLib.git
cd StormLib
cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON .
make -j$(nproc)
sudo make install
sudo ldconfig
```

**Python dependencies:**
```bash
pip install sc2reader
```

### Patching a Map

```bash
python3 patch_aie_map.py <input_map.SC2Map> <patch_dir> <output_map.SC2Map>
```

Example:
```bash
python3 patch_aie_map.py PylonLE.SC2Map patches/5.0.14.94137 PylonAIE_v4.SC2Map
```

### What the Patcher Does

1. Extracts the original map's MPQ archive (preserving terrain, triggers, map structure)
2. Replaces all 109 GameData XMLs with the target patch versions
3. Replaces localized string files
4. Adds new assets from the patch folder
5. Repackages into a new `.SC2Map` with 16MB MPQ sector size for optimal compression

### Batch Patching

```bash
for map in maps/*.SC2Map; do
  name=$(basename "$map" .SC2Map)
  python3 patch_aie_map.py "$map" patches/5.0.14.94137 "patched/${name}_5.0.14.SC2Map"
done
```

### Compression Note

MPQ archives compress data per-sector. With small sector sizes (e.g., 512 bytes or 64KB), large files like terrain data are split into many independently-compressed chunks with no shared context, resulting in poor compression (~1x). Using a 16MB sector size allows each file to be compressed as a single unit, achieving ~5x compression ratios comparable to SC2 Editor output.

### Verification

After patching, verify that balance data matches a known-good reference map by reading and comparing the GameData XML files byte-for-byte. The key files to check: UnitData.xml, WeaponData.xml, AbilData.xml, EffectData.xml, BehaviorData.xml, UpgradeData.xml.

---

## Key Data Files for Balance Changes

| File | Contains |
|------|----------|
| UnitData.xml | Unit HP, shields, supply cost, speed, sight radius, attributes (armored/light), build times |
| WeaponData.xml | Weapon range, damage period, arc, scan range, damage points |
| AbilData.xml | Ability costs (energy), cooldowns, cast ranges, button layouts |
| EffectData.xml | Damage amounts, healing, shields, applied behaviors |
| UpgradeData.xml | Research costs, build times, what upgrades unlock |
| BehaviorData.xml | Buffs/debuffs, durations, modifiers (speed, armor, damage) |
| RequirementData.xml | Tech tree requirements (what needs to be built before X) |
| stableid.json | Internal ID mappings (must be consistent with new unit/ability IDs) |

---

## Example: What Changed Between 5.0.12 and 5.0.13

Comparing the same map (Gresvan) across patch versions reveals the balance changes being injected:

- Cyclone: speed 0.7851 → 0.914, new CycloneFakeWeapon added (range 6, min scan 6.5)
- Widow Mine: Armory requirement → Drilling Claws requirement (tech tree shift)
- Lurker (burrowed): new SubgroupPriority 93 added
- Observer (siege mode): shields 30/30 added (was missing)
- Various weapons: new Range 0.2 values, AcquirePrioritization changes

---

## Alternative Approaches (Not Recommended)

**Protobuf/API interception** — Not practical. The SC2 API exposes game state and actions, not game data definitions. Unit stats cannot be changed at runtime through the API. Those values are baked into the data files loaded at game start.

**SC2Mod dependency files** — SC2 supports dependency mods that override game data without modifying the map itself. Cleaner separation, but requires understanding the mod dependency chain. The maps already reference `Base.SC2Data` — a mod would sit on top of that layer. More complex to set up but worth considering if you need to frequently switch between patch versions.

**Map XML editing remains the recommended approach.** It's what the SC2 modding community uses, it's what Blizzard's own patches do (they modify the same XML data files), and the tooling is straightforward.

---

## References

- [sc2-aie-maps-patcher](https://github.com/Vers-AI/sc2-aie-maps-patcher) — automated patcher tool (VersusAI)
- [aiarena/sc2patch](https://github.com/aiarena/sc2patch) — patch data files (versions 5.0.3–5.0.14)
- [Cryptyc/Sc2-AIE-Maps](https://github.com/Cryptyc/Sc2-AIE-Maps) — pre-patched AIE maps (5.0.12–5.0.14)
- [StormLib](https://github.com/ladislav-zezula/StormLib) — C library for MPQ archive manipulation
- [AI Arena map patching demo](https://www.youtube.com/watch?v=lTBFy-R01Wo) — original tutorial video
- Scarlett — original AIE map patching workflow for AI Arena

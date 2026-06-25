# SC2 AIE Map Patcher

Headless tool for patching StarCraft 2 maps to mimic balance updates when the SC2 Linux binary is frozen at an older API version.

## Why

The SC2 Linux binary (used by [AI Arena](https://aiarena.net) and bot competitions) is frozen at version 4.10.0. Balance patches (5.0.x) are not applied to the API. To run bots on current balance, map files are modified to include updated game data — the map overrides the binary's default data when loaded.

This tool automates that process on Linux. No Windows, no SC2 Editor, no Ladik's MPQ Editor required.

## How It Works

SC2 map files (`.SC2Map`) are MPQ archives containing:
- **109 GameData XML files** — unit stats, weapons, abilities, effects, upgrades, behaviors, tech tree
- **Localized string files** — GameStrings.txt, ObjectStrings.txt, TriggerStrings.txt, GameHotkeys.txt
- **Assets** — 3D models, textures, sounds for new/changed visual elements
- **Map structure** — terrain, triggers, minimap, map script

The patcher:
1. Extracts the original map's MPQ archive
2. Replaces GameData XMLs and localized strings with the target patch version
3. Adds any new assets from the patch
4. Repackages into a new `.SC2Map` with 16MB sector size for optimal compression

## Requirements

- Python 3.10+
- [StormLib](https://github.com/ladislav-zezula/StormLib) (C library for MPQ read/write)
- [sc2reader](https://github.com/ggtracker/sc2reader) (Python, for MPQ reading)
- [mpyq](https://github.com/arkx/mpyq) (Python, comes with sc2reader)

### Installing StormLib

```bash
git clone https://github.com/ladislav-zezula/StormLib.git
cd StormLib
cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON .
make -j$(nproc)
sudo make install
sudo ldconfig
```

### Installing Python deps

```bash
pip install sc2reader
```

## Usage

```bash
python3 patch_aie_map.py <input_map.SC2Map> <patch_dir> <output_map.SC2Map>
```

Example:
```bash
python3 patch_aie_map.py PylonLE.SC2Map ./patches/5.0.14.94137 PylonAIE_v4.SC2Map
```

## Patch Data

Patch data files are sourced from the [aiarena/sc2patch](https://github.com/aiarena/sc2patch) repository, which covers versions 5.0.3 through 5.0.14.

Pre-patched reference maps are available in [Cryptyc/Sc2-AIE-Maps](https://github.com/Cryptyc/Sc2-AIE-Maps).

## Batch Patching

To patch all maps in a folder:

```bash
for map in maps/*.SC2Map; do
  name=$(basename "$map" .SC2Map)
  python3 patch_aie_map.py "$map" patches/5.0.14.94137 "patched/${name}_5.0.14.SC2Map"
done
```

## Verification

After patching, verify that balance data matches a known-good reference map:

```python
import ctypes
lib = ctypes.cdll.LoadLibrary('/usr/local/lib/libstorm.so')

# Read UnitData.xml from both maps and compare bytes
# If they match, the patch was applied correctly
```

## Key Data Files

| File | Contains |
|------|----------|
| UnitData.xml | Unit HP, shields, supply cost, speed, sight, attributes, build times |
| WeaponData.xml | Weapon range, damage period, arc, scan range |
| AbilData.xml | Ability costs, cooldowns, cast ranges, button layouts |
| EffectData.xml | Damage amounts, healing, shields, applied behaviors |
| UpgradeData.xml | Research costs, build times, unlock tree |
| BehaviorData.xml | Buffs/debuffs, durations, modifiers |
| RequirementData.xml | Tech tree requirements |
| stableid.json | Internal ID mappings |

## Compression

The patcher uses 16MB MPQ sector size to achieve compression ratios comparable to the SC2 Editor's output (~5x on typical maps). Using smaller sector sizes (e.g., 64KB) results in nearly uncompressed archives because StormLib compresses per-sector, not per-file.

## Credits

- [AI Arena](https://aiarena.net) — original patch data and methodology
- [Cryptyc](https://github.com/Cryptyc) — pre-patched AIE maps and patch repo
- Scarlett — original AIE map patching tutorial

## License

MIT

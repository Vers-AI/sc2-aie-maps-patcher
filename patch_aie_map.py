#!/usr/bin/env python3
"""
SC2 AIE Map Patcher
Takes a clean LE map and injects patch data to create an AIE-patched map.

Usage: python3 patch_aie_map.py <input_map.SC2Map> <patch_dir> <output_map.SC2Map>
Example: python3 patch_aie_map.py /tmp/PylonLE.SC2Map /mnt/forge/repos/sc2patch/Patch/5.0.14.94137 /tmp/PylonAIE_v4.SC2Map
"""

import ctypes
import os
import sys
import shutil
import tempfile

# StormLib constants
MPQ_OPEN_READ_ONLY = 0
MPQ_FILE_COMPRESS = 0x00000200
MPQ_FILE_REPLACEEXISTING = 0x80000000
MPQ_FILE_SINGLE_UNIT = 0x01000000
MPQ_FILE_SECTOR_CRC = 0x04000000
MPQ_COMPRESSION_ZLIB = 0x00000002


class SFILE_CREATE_MPQ(ctypes.Structure):
    _fields_ = [
        ('cbSize', ctypes.c_uint32),
        ('dwMpqVersion', ctypes.c_uint32),
        ('pvUserData', ctypes.c_void_p),
        ('cbUserData', ctypes.c_uint32),
        ('dwStreamFlags', ctypes.c_uint32),
        ('dwFileFlags1', ctypes.c_uint32),
        ('dwFileFlags2', ctypes.c_uint32),
        ('dwFileFlags3', ctypes.c_uint32),
        ('dwAttrFlags', ctypes.c_uint32),
        ('dwSectorSize', ctypes.c_uint32),
        ('dwRawChunkSize', ctypes.c_uint32),
        ('dwMaxFileCount', ctypes.c_uint32),
    ]


class StormLib:
    def __init__(self, lib_path='/usr/local/lib/libstorm.so'):
        self.lib = ctypes.cdll.LoadLibrary(lib_path)
        self._setup_prototypes()

    def _setup_prototypes(self):
        lib = self.lib
        lib.SFileCreateArchive2.argtypes = [ctypes.c_char_p, ctypes.POINTER(SFILE_CREATE_MPQ), ctypes.POINTER(ctypes.c_void_p)]
        lib.SFileCreateArchive2.restype = ctypes.c_bool
        lib.SFileOpenArchive.argtypes = [ctypes.c_char_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p)]
        lib.SFileOpenArchive.restype = ctypes.c_bool
        lib.SFileCloseArchive.argtypes = [ctypes.c_void_p]
        lib.SFileCloseArchive.restype = ctypes.c_bool
        lib.SFileAddFileEx.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_void_p]
        lib.SFileAddFileEx.restype = ctypes.c_bool
        lib.SFileExtractFile.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint32]
        lib.SFileExtractFile.restype = ctypes.c_bool
        lib.SFileHasFile.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        lib.SFileHasFile.restype = ctypes.c_bool

    def create_archive(self, path, max_files=256, sector_size=16777216):
        info = SFILE_CREATE_MPQ()
        info.cbSize = ctypes.sizeof(SFILE_CREATE_MPQ)
        info.dwMpqVersion = 0
        info.pvUserData = None
        info.cbUserData = 0
        info.dwStreamFlags = 0
        info.dwFileFlags1 = 0x80000200
        info.dwFileFlags2 = 0x80000200
        info.dwFileFlags3 = 0x80000200
        info.dwAttrFlags = 0
        info.dwSectorSize = sector_size
        info.dwRawChunkSize = 0
        info.dwMaxFileCount = max_files
        handle = ctypes.c_void_p()
        if not self.lib.SFileCreateArchive2(path.encode('utf-8'), ctypes.byref(info), ctypes.byref(handle)):
            raise RuntimeError(f"Failed to create archive: {path}")
        return handle.value

    def open_archive(self, path, read_only=True):
        handle = ctypes.c_void_p()
        flags = MPQ_OPEN_READ_ONLY if read_only else 0
        if not self.lib.SFileOpenArchive(path.encode('utf-8'), 0, flags, ctypes.byref(handle)):
            raise RuntimeError(f"Failed to open archive: {path}")
        return handle.value

    def close_archive(self, handle):
        self.lib.SFileCloseArchive(handle)

    def add_file(self, mpq_handle, local_path, archive_path, compress=True):
        flags = MPQ_FILE_REPLACEEXISTING | MPQ_FILE_COMPRESS
        compression = MPQ_COMPRESSION_ZLIB if compress else 0
        result = self.lib.SFileAddFileEx(mpq_handle, local_path.encode('utf-8'), archive_path.encode('utf-8'), flags, compression, None, None)
        if not result:
            flags = MPQ_FILE_COMPRESS
            result = self.lib.SFileAddFileEx(mpq_handle, local_path.encode('utf-8'), archive_path.encode('utf-8'), flags, compression, None, None)
            if not result:
                raise RuntimeError(f"Failed to add file: {archive_path}")

    def extract_file(self, mpq_handle, archive_path, local_path):
        if not self.lib.SFileExtractFile(mpq_handle, archive_path.encode('utf-8'), local_path.encode('utf-8'), 0):
            raise RuntimeError(f"Failed to extract: {archive_path}")

    def has_file(self, mpq_handle, archive_path):
        return self.lib.SFileHasFile(mpq_handle, archive_path.encode('utf-8'))


def patch_map(input_map, patch_dir, output_map):
    storm = StormLib()
    print(f"Input map: {input_map}")
    print(f"Patch dir: {patch_dir}")
    print(f"Output map: {output_map}")
    print()

    # Open input archive
    print("=== Opening input map ===")
    in_handle = storm.open_archive(input_map, read_only=True)

    from mpyq import MPQArchive as MPQReader
    reader = MPQReader(input_map)
    all_files = [f.decode() if isinstance(f, bytes) else f for f in reader.files]
    print(f"Input map has {len(all_files)} files")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Extract all original files
        print("\n=== Extracting original map files ===")
        for f in all_files:
            rel_path = f.replace('\\', '/')
            local_path = os.path.join(tmpdir, 'original', rel_path)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            try:
                storm.extract_file(in_handle, f, local_path)
            except RuntimeError:
                pass  # skip unextractable files (listfile, attributes)

        storm.close_archive(in_handle)

        # Copy patch files over originals
        print("\n=== Copying patch files ===")

        patch_gamedata = os.path.join(patch_dir, 'Base.SC2Data', 'GameData')
        if os.path.isdir(patch_gamedata):
            for xml_file in sorted(os.listdir(patch_gamedata)):
                src = os.path.join(patch_gamedata, xml_file)
                if os.path.isfile(src):
                    dst_dir = os.path.join(tmpdir, 'original', 'Base.SC2Data', 'GameData')
                    os.makedirs(dst_dir, exist_ok=True)
                    shutil.copy2(src, os.path.join(dst_dir, xml_file))

        patch_localized = os.path.join(patch_dir, 'enUS.SC2Data', 'LocalizedData')
        if os.path.isdir(patch_localized):
            for txt_file in sorted(os.listdir(patch_localized)):
                src = os.path.join(patch_localized, txt_file)
                if os.path.isfile(src):
                    dst_dir = os.path.join(tmpdir, 'original', 'enUS.SC2Data', 'LocalizedData')
                    os.makedirs(dst_dir, exist_ok=True)
                    shutil.copy2(src, os.path.join(dst_dir, txt_file))

        patch_assets = os.path.join(patch_dir, 'Assets')
        if os.path.isdir(patch_assets):
            for root, dirs, files in os.walk(patch_assets):
                for f in files:
                    src = os.path.join(root, f)
                    rel = os.path.relpath(src, patch_dir)
                    dst = os.path.join(tmpdir, 'original', rel)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)

        # Build new MPQ archive
        print(f"\n=== Building patched map (16MB sector size) ===")

        staging_dir = os.path.join(tmpdir, 'original')
        file_list = []
        for root, dirs, files in os.walk(staging_dir):
            for f in files:
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, staging_dir)
                archive_path = rel_path.replace('/', '\\')
                file_list.append((full_path, archive_path))

        print(f"Total files to inject: {len(file_list)}")

        if os.path.exists(output_map):
            os.remove(output_map)

        mpq_handle = storm.create_archive(output_map, max_files=max(256, len(file_list) + 32), sector_size=16777216)

        added = 0
        failed = 0
        for local_path, archive_path in sorted(file_list):
            try:
                storm.add_file(mpq_handle, local_path, archive_path, compress=True)
                added += 1
            except RuntimeError as e:
                print(f"  FAILED: {archive_path} - {e}")
                failed += 1

        storm.close_archive(mpq_handle)

        out_size = os.path.getsize(output_map)
        print(f"\n=== Results ===")
        print(f"Files added: {added}")
        print(f"Files failed: {failed}")
        print(f"Output: {output_map}")
        print(f"Size: {out_size / 1024 / 1024:.2f} MB")

        if failed > 0:
            print(f"\n  {failed} files failed. Map may be incomplete.")
            return False
        else:
            print("\nAll files injected successfully.")
            return True


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <input_map.SC2Map> <patch_dir> <output_map.SC2Map>")
        sys.exit(1)

    success = patch_map(sys.argv[1], sys.argv[2], sys.argv[3])
    sys.exit(0 if success else 1)

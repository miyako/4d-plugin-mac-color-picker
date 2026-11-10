"""Compile actual wrappers and the complete unmodified SDK; no 4D or release build."""

import os
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get("OWNERSHIP_SOURCE_ROOT", ROOT)).resolve()
BASELINE = "f54c69fc0de98cfb6930009c138ffc447faaf7cd"
EXPECT_BASELINE_FAILURES = os.environ.get("OWNERSHIP_BASELINE_FAILURES") == BASELINE
SDK_HASHES = {
    "4DPluginAPI.c": "355ee208ad6c61dcc68e8432546fc42484888211dd07ed8fa3fdb4440f3edbd8",
    "4DPluginAPI.h": "7391841f0046f9e822b65ca6b07cafb3565aecfb58f65be4e0661adf97b8c786",
    "EntryPoints.h": "130b06373937b58ac6c5336a342fd291974371dd462d9c56c06cea4ffc8a717d",
    "Flags.h": "89be5f9526b4f066543d93142760f2f7a630ddcdfb0540dfc20191c43563aa56",
    "PrivateTypes.h": "99e66ee558612e3fcc4efa11d8439aad65bdc982e4006e9122b4bfc1533bc6e7",
    "PublicTypes.h": "acce13e0896a3f55a3d96bf849a42bdae7cbd5c6f92874f1f47e0e34ad070dcc",
}


@unittest.skipUnless(sys.platform == "darwin", "macOS framework shim")
class OwnershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(
            prefix="color-picker-ownership-", dir=os.environ.get("OWNERSHIP_TMPDIR"),
        )
        cls.binary = Path(cls.temp.name) / "ownership"
        api = SOURCE / "4D Plugin API"
        for name, digest in SDK_HASHES.items():
            if hashlib.sha256((api / name).read_bytes()).hexdigest() != digest:
                cls.temp.cleanup()
                raise AssertionError(f"Re-audit changed SDK before updating pinned hash: {name}")
        print("Compiled C_PICTURE.cpp SHA-256:",
              hashlib.sha256((api / "Classes/C_PICTURE.cpp").read_bytes()).hexdigest(),
              flush=True)
        command = [
            "clang++", "-std=c++14", "-x", "objective-c++",
            "-I", str(ROOT / ".github/tests/platform"),
            "-include", "Carbon/Carbon.h", "-I", str(api),
            "-I", str(api / "Classes"), "-fsanitize=address,undefined",
            "-fno-sanitize=alignment", "-fno-omit-frame-pointer", "-g",
            "-Wno-deprecated-declarations", "-Wno-return-type-c-linkage",
            "-Wno-ignored-attributes", "-Wno-writable-strings",
            str(api / "4DPluginAPI.c"),
            *map(str, sorted((api / "Classes").glob("*.cpp"))),
            str(ROOT / ".github/tests/ownership_host.mm"),
            "-framework", "Foundation", "-framework", "CoreGraphics",
            "-o", str(cls.binary),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            cls.temp.cleanup()
            raise AssertionError(result.stdout + result.stderr)
        linked = subprocess.run(
            ["otool", "-L", str(cls.binary)], check=True, capture_output=True, text=True,
        ).stdout
        if "AppKit" in linked or "Cocoa.framework" in linked:
            cls.temp.cleanup()
            raise AssertionError("Ownership harness must not link AppKit/Cocoa")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_case(self, case, text="", empty="allocated"):
        result = subprocess.run(
            [str(self.binary), case, text, empty],
            env={**os.environ, "ASAN_OPTIONS": "detect_leaks=0",
                 "UBSAN_OPTIONS": "halt_on_error=1"},
            capture_output=True, text=True,
        )
        if EXPECT_BASELINE_FAILURES and case not in ("arrays", "scalar", "foundation"):
            diagnostic = "unbalanced picture references"
            if case.startswith("path"):
                diagnostic = ("return must independently retain" if not text and empty == "null"
                              else "duplicate/unowned string disposal")
            elif case == "bytes":
                diagnostic = "return must independently retain"
            elif case.startswith("copy"):
                if text == ".png":
                    diagnostic = "AddressSanitizer: heap-buffer-overflow"
                elif not text and empty == "allocated":
                    diagnostic = "unbalanced string allocations"
            self.assertNotEqual(result.returncode, 0, f"baseline unexpectedly passed {case}")
            self.assertIn(diagnostic, result.stdout + result.stderr)
            print(f"BASELINE expected failure {case} {text!r} {empty}: {diagnostic}", flush=True)
            return
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("strings=0 pictures=0 handles=0", result.stdout)
        print(f"PASS {case} {text!r} {empty}: strings=0 pictures=0 handles=0", flush=True)

    def test_path_single_disposal_and_retained_output(self):
        for text in ("ASCII", "\u65e5", "\U0001f600", ""):
            for empty in ("allocated", "null"):
                with self.subTest(text=text, empty=empty):
                    self.run_case("path", text, empty)

    def test_setbytes_temporary_release(self):
        self.run_case("bytes")

    def test_copy_byte_unit_boundary(self):
        for text in (".png", "\u65e5", "\U0001f600"):
            with self.subTest(text=text):
                self.run_case("copy", text, "null")

    def test_copy_initial_empty_owners(self):
        self.run_case("copy", "")

    def test_grayscale_initial_empty_owner(self):
        self.run_case("gray")

    def test_size_borrowed_input_and_empty_owner(self):
        self.run_case("size")

    def test_thumbnail_borrowed_input_and_owning_return(self):
        self.run_case("thumbnail")

    def test_array_transfers_copies_replacement_shrink_clear_rejection(self):
        for empty in ("allocated", "null"):
            with self.subTest(empty=empty):
                self.run_case("arrays", "", empty)

    def test_scalar_borrowed_copy_and_content_setter_returns(self):
        for text in ("ASCII", "\u65e5", "\U0001f600", ""):
            for empty in ("allocated", "null"):
                with self.subTest(text=text, empty=empty):
                    self.run_case("scalar", text, empty)

    def test_foundation_title_copy_and_unicode_roundtrip_without_ui(self):
        for text in ("ASCII", "\u65e5", "\U0001f600", ""):
            with self.subTest(text=text):
                self.run_case("foundation", text)

    def test_command_handle_failure_preserves_argument_owners(self):
        for case in ("path", "copy", "gray", "size", "thumbnail"):
            with self.subTest(case=case):
                self.run_case(case + "-handle-failure", "")


def compare_baseline():
    if sys.platform != "darwin":
        raise SystemExit("The ownership differential requires macOS Foundation")
    with tempfile.TemporaryDirectory(prefix="color-picker-baseline-") as directory:
        archive = Path(directory) / "baseline.tar"
        baseline = Path(directory) / "source"
        baseline.mkdir()
        with archive.open("wb") as stream:
            subprocess.run(
                ["git", "-C", str(ROOT), "archive", BASELINE, "4D Plugin API"],
                stdout=stream, check=True,
            )
        subprocess.run(["tar", "-xf", str(archive), "-C", str(baseline)], check=True)
        for label, source, expected in (("FINAL", SOURCE, ""), ("BASELINE", baseline, BASELINE)):
            print(f"=== {label}: {source} ===", flush=True)
            subprocess.run(
                [sys.executable, str(Path(__file__).resolve())],
                env={**os.environ, "OWNERSHIP_SOURCE_ROOT": str(source),
                     "OWNERSHIP_BASELINE_FAILURES": expected},
                check=True,
            )


if __name__ == "__main__":
    if sys.argv[1:] == ["--compare-baseline"]:
        compare_baseline()
    else:
        unittest.main()

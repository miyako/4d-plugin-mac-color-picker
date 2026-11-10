# 4d-plugin-mac-color-picker
Alternative color picker for 4D on Mac.

Note
---
Consider using the native command and [convert-color-space](https://github.com/miyako/4d-plugin-convert-color-space) to convert the RGB values. Running ```NSColorPanel``` from a plugin has some modality issues.

About
---
You might have noticed that if you pass the RGB value returned from the built-in [Select RGB color](http://doc.4d.com/4Dv15/4D/15/Select-RGB-Color.301-2007529.en.html) command directly to [OBJECT SET RGB COLORS](http://doc.4d.com/4Dv15/4D/15/OBJECT-SET-RGB-COLORS.301-2006928.en.html), you get a slightly **darker** colour.

![](https://github.com/miyako/4d-plugin-mac-color-picker/blob/master/images/picker.png)

For example, the standard window background colour is ```#E7E7E7```.

However, if you pass this value to a form object, or even reference it in SVG, it is rendered slightly darker on an LCD.

![](https://github.com/miyako/4d-plugin-mac-color-picker/blob/master/images/result.png)

Apparently the RGB value must be calibrated for the device colour space.

c.f. http://stackoverflow.com/questions/14578759/wrong-color-in-interface-builder

This plugin returns the exact RGB needed on screen, if you pass ```Picker standard color space```.

The aforementioned ```#E7E7E7``` is converted to ```#ECECEC```.

![](https://github.com/miyako/4d-plugin-mac-color-picker/blob/master/images/plugin.png)

In addition, it lets you displayed the alpha channel tool if you pass ```Picker RGBA color```.

The alpha value is returned in the most significant byte, currently not used in 4D.

![](https://github.com/miyako/4d-plugin-mac-color-picker/blob/master/images/alpha.png)

Finally, the crayon tool, which displays wrongly on El Capitan + 4D 32 bits, is hidden.

Remarks
---
~~The calibrartion is not perfect; in the above example, the window background should be ```#ECECEC```.~~

The conversion is OK but the panel is not modal to the window that invoked it.

Release workflow
---
Releases use source metadata, not a pre-existing tag. Both release-related Actions
workflows are manual; pushing commits or tags does not start a release build.
The separate **Native ownership** workflow runs unsigned, isolated source tests
on relevant pushes and pull requests; it never packages or publishes the plugin.

1. Run **Bump version** on the explicitly selected branch with `patch`, `minor`
   or `major`. It validates the selected commit, clean checkout and remote branch,
   then commits only coordinated source version fields. Its non-force push
   disables tag following and requires the branch SHA advertised to the pre-push
   hook to exactly match the dispatch SHA. A moved, rewound, deleted or already
   updated branch is rejected. It creates no tag and does not start Build.
2. Run **Build** separately on the desired ref. There are no inputs. Every job
   checks out the immutable dispatch `github.sha`; the strict source `X.Y.Z`
   determines `vX.Y.Z`. An authenticated, paginated releases-list check (including
   drafts) and a remote-tag check must both show the version is unused.
3. The existing macOS-only pipeline builds the universal arm64/x86_64 plugin,
   verifies the fresh binary, signs it, notarizes both archives and staples the
   DMG. Only after these gates does it recheck availability and create a new tag
   at the exact selected SHA, verify that remote SHA, create a published release
   with empty notes (no generated notes), and upload
   `Mac Color Picker-X.Y.Z.zip` and `Mac Color Picker-X.Y.Z.dmg` to its new ID.

Publication is serialized repository-wide across refs. API/auth/network errors,
404s and malformed responses on any releases page fail closed. Existing tags
(even at the same SHA), draft releases and published releases are never reused.
Tag creation and release creation are separate create-only operations; uploads
never overwrite assets. There is no automatic retry, deletion, update or rollback.

**Partial publication recovery:** a failed release POST can leave a tag; a failed
upload can leave a published release with only some assets. Inspect the failed
run, tag SHA, release (including drafts) and assets manually. Do not rerun Build
expecting it to repair that version. Retain the partial state for investigation,
resolve the cause, then use a new source version for a fresh release. Any manual
repair of an existing release is outside these workflows.

Source version contract
---
The three project configurations coordinate `MARKETING_VERSION` and
`CURRENT_PROJECT_VERSION` with root `Info.plist` and
`English.lproj/InfoPlist.strings`. Valid version build-variable references are
preserved. An absent `CFBundleVersion` stays absent. Prebuilt bundles, the 4D
database, manifest IDs, SDK/dependency versions and `locversion.plist` are not
release-version inputs.

The modernization commit `d982ac6` introduced both project version keys at
`1.0.0`, and the old bump workflow explicitly promised to coordinate them.
Commit `7822ba3` updated only marketing and the source plist to `1.0.1`, leaving
the current-project fields stale. This migration restores those fields to
`1.0.1` and updates the localized `1.0` strings to the same authority; it does
not increment the release version or introduce an independent build counter.
The localization's copyright and UTF-8 BOM are preserved, with CR line endings
normalized to LF.

Local regression checks (no plugin build, signing or publication):

```sh
python3 .github/scripts/source_version.py
python3 -m unittest discover -s .github/tests -v
actionlint .github/workflows/*.yml
```

Tests cover fixed metadata fixtures and live-derived versions, strict drift and
reference handling, pagination failures and drafts, retained partial publication,
and real temporary bare-Git branch/tag races. Helpers and race regressions are
adapted from reviewed `miyako/4d-plugin-script#1` at
`4cdf7b5d4ec645385654e6cb17a2ff0603925fb5`.

Native string ownership audit
---
Baseline: `f54c69fc0de98cfb6930009c138ffc447faaf7cd`. Guidance:
[`miyako/skills` at `e6b492fcb81e5e1a7f7db723594b420e63bf6eb9`](https://github.com/miyako/skills/blob/e6b492fcb81e5e1a7f7db723594b420e63bf6eb9/4d-skills/skills/4dplugin/SKILL.md).
The following inventory covers all 42 tracked native source/header/prefix files,
including compiled helpers not called by the current command.

| Files (relative to repository root) | Reachability and ownership findings |
|---|---|
| `4DPlugin.cpp`, `4DPlugin.h` | SDK `FourDPackex` calls `PluginMain`, then `CommandDispatcher`. Init/server-init select `OnStartup`; command 1 selects `Mac_Select_RGB_color`. The root and bundled `manifest.json` declare `(&L;&T;&L):L`, not arrays. `C_TEXT` copies the borrowed title; `copyUTF16String` creates an owned Foundation title released after synchronous main-process callbacks. Listener copies/releases the saved panel title. UI/exception behavior is static-inspection-only, not host-certified. |
| `4D Plugin API/4DPluginAPI.c`, `4DPluginAPI.h`, `PublicTypes.h`, `PrivateTypes.h`, `EntryPoints.h`, `Flags.h` | Complete unchanged bundled SDK and its include graph. `4DPluginAPI.h` includes all wrapper headers. Engine source last changed in `d982ac66cb3219c7885692d1fb018b98d7ffa1de`; its v14 comment and header's v13 comment are not verified upstream SDK identities. |
| `4D Plugin API/Classes/C_TEXT.{h,cpp}` | Independent `std::basic_string` copies of borrowed parameter/descriptor contents; engine-backed scalar content setters and Foundation/CF create-copy/release paths. No array transfer cleanup added. |
| `4D Plugin API/Classes/ARRAY_TEXT.{h,cpp}` | Copies borrowed elements into independent C++ strings before replacement/shrink/clear. Each output creates its own descriptor and transfers it without post-transfer disposal. Normal destinations and exact rejection predicates are covered; OOM limitations below remain. |
| `4D Plugin API/Classes/C_PICTURE.{h,cpp}` | Compiled dormant helper family: fixed path double disposal and initial empty string leak, retain-before-output-clear, `setBytes` temporary release, overwritten empty picture/string owners, and converter bytes/code-units mismatch. Borrowed `getSize`/thumbnail inputs still detach before clear; owning copy/grayscale/thumbnail results detach and survive caller cleanup. No invented owning procedure return. |
| `4D Plugin API/Classes/C_POINTER.{h,cpp}` | Metadata/variable-definition union copying, no direct string descriptor disposal. `PA_GetPointerValue` forwards to the engine; interpretation of returned definition metadata and cleanup requires host evidence, so no speculative clear/relabel patch. |
| `4D Plugin API/Classes/C_BLOB.{h,cpp}` | `CBytes`/`C_BLOB` own vectors, borrow/produce handles, and convert hex/base64 through `C_TEXT`; no shallow `PA_Unistring` assignment. Nonstring buffer/allocation issues are outside this bounded fix. |
| `4D Plugin API/Classes/C_DATE.{h,cpp}`, `C_INTEGER.{h,cpp}`, `C_LONGINT.{h,cpp}`, `C_REAL.{h,cpp}`, `C_TIME.{h,cpp}` | Value-only parameter/return wrappers; date, numeric and time operations do not create or adopt string descriptors. |
| `4D Plugin API/Classes/ARRAY_BOOLEAN.{h,cpp}`, `ARRAY_DATE.{h,cpp}`, `ARRAY_INTEGER.{h,cpp}`, `ARRAY_LONGINT.{h,cpp}`, `ARRAY_REAL.{h,cpp}`, `ARRAY_TIME.{h,cpp}` | Numeric/date/bit-array value copies; shared SDK allocation/resize boundaries inspected, not certified for OOM. |
| `4D Plugin API/Classes/C_TYPES.h`, `4D Plugin_Prefix.pch` | Standard string/vector typedefs, Foundation/AppKit/platform includes and Carbon prefix. Test-only platform headers replace Cocoa/AppKit before compilation. |

Both `Mac Color Picker.xcodeproj/project.pbxproj` and
`Mac Color Picker.vcxproj` list the 16 helper implementations and plugin entry
source; the Windows project also explicitly compiles the SDK engine, while the
Xcode project compiles the engine through its build phase. The Windows `.def`
exports `FourDPackex`. No alternative first-party native implementation or
JSON/property/collection wrapper is present in this tracked inventory. The
prebuilt bundle/database are not source reachability evidence and are untouched.

**Verified local SDK contracts:** engine git blob
`478081f0238f6bc5393222f574bc2656f010b67b`, SHA-256
`355ee208ad6c61dcc68e8432546fc42484888211dd07ed8fa3fdb4440f3edbd8`.
The driver pins all six SDK source/header hashes. `PA_SetStringInArray`
(engine lines 4444-4459) disposes the old element and shallow-transfers only for
Unicode array kind, non-null array handle, non-null input, and
`0 <= index <= fNbElements`. Index zero is accepted. Rejection leaves the
input caller-owned; `PA_GetStringInArray` is borrowed.
`PA_SetStringVariable`/`PA_SetPictureVariable` shallow-assign without releasing
old contents; creating `Unistring`/`Picture` variables first allocates empty
owners. Use `Undefined` only for immediately overwritten destinations.
`PA_ClearVariable` forwards owning cleanup to the engine.
`PA_ReturnString`/`PA_SetUnistring` use a distinct engine content setter.
`PA_DuplicatePicture(..., 1)` retains; output parameter retention precedes
clearing its original owner. `PA_ConvertCharsetToCharset` explicitly returns
bytes, not UTF-16 code units (lines 4775-4793).

**Regression:** on macOS, run:

```sh
python3 .github/tests/test_ownership.py --compare-baseline
```

The same final harness compiles the actual 16 wrapper implementations and
complete, unmodified SDK twice: current production sources, and the exact
baseline extracted with `git archive` (not a checkout/session). It records the
compiled picture source hash. The reference harness/driver were imported from
[`miyako/4d-plugin-jpegoptim` at `e49adcd32bd5500cf3de680faa3649b32463ff5e`](https://github.com/miyako/4d-plugin-jpegoptim/tree/e49adcd32bd5500cf3de680faa3649b32463ff5e/.github/tests)
and independently adapted to this target's verified SDK.

There are 35 runtime cases across 11 test methods. Baseline has 21 exact,
named expected failures and 14 passing controls; fixed sources pass all 35.
Failures are path duplicate/unowned string disposal (8), incorrect retained
output count (2), converter ASan heap-buffer-overflow (1), leaked initial string
owners (2), and unbalanced picture references (8).
Cases cover allocated/null empty strings, ASCII/BMP/supplementary text, exact
UTF-8 content and UTF-16 lengths/capacity/termination, replacement/shrink/clear,
rejected transfers, independent scalar/callback allocations, borrowed input
copies, Foundation title copies, output handoff survival, poisoned failed
picture-data getter outputs, and command argument-handle allocation failure.
The latter confirms the SDK's raw-kind-zero command failure sentinel versus
the method's `Undefined` result; production helpers neither adopt nor clear
an invented procedure result.

ASan and UBSan run with explicit string/handle/picture reference counts
(`strings=0 pictures=0 handles=0` for every passing case). LeakSanitizer is
unavailable on this macOS target; UBSan alignment checking is disabled for the
SDK's packed ABI. The test binary links Foundation/CoreGraphics, not
Cocoa/AppKit (checked with `otool`). Fake `NSImage` methods abort; every
unrecognized engine selector aborts. The real dispatcher, startup,
color picker, screen conversion, filesystem picture loading, UI/event loop,
preferences, clipboard and devices are never executed. Synthetic picture
procedures operate solely on in-memory reference-counted tokens.

**Deferred, not certified:** initial `PA_CreateUnistring` failure has no
established wrapper error channel; its SDK forwarding does not itself validate
the returned descriptor. No fallback or success-shaped replacement is added.
Array creation/reallocation failure and SDK resize-count corruption remain
unfixed; ordinary-array tests do not establish OOM safety. Nonstring/CBytes
allocation failures, successful SDK-only `PA_GetPictureData` string ownership,
application-path/localization strings and pointer metadata ownership require
separate engine/host evidence. No Windows, real-4D, UI or exception-path
certification is implied. SDK files, native projects, manifests, release
workflows, prebuilt binaries and their modes remain unchanged.

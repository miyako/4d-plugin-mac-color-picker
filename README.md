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
Releases use source metadata, not a pre-existing tag. Both Actions workflows
are manual; pushing commits or tags does not start a build.

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

Local regression checks (no native build, signing or publication):

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

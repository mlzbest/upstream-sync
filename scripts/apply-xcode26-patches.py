#!/usr/bin/env python3
"""
Apply the CI workspace patches to a pristine checkout of jo32/tvbox-silicon
(mirrored at mlzbest/mmusic).

The build now runs on the GitHub `xcode-27` runner image (Xcode 27.2 /
ios27 SDK), matching the upstream author's toolchain. With an iOS 27 SDK the
upstream iOS 27 source compiles as-is, so the earlier "Xcode 26 compatibility"
patches (Swift 6 closure capture, ExternalDisplay UISceneAccessory guards,
VideoEnhancement iOS 27 limits) are no longer needed and have been removed.

The single remaining patch is a functional fix, not an SDK workaround: the
upstream file importer only allows .json/.py/.js UTTypes, which leaves most
files saved from WeChat / Safari / the Files app greyed out in the iOS
document picker. Widening the whitelist to include .item (the root UTType,
matching every file) makes the importer tolerant of dyn.* / public.data types.

All patches are applied to the CI workspace ONLY - mlzbest/mmusic stays a
byte-identical mirror of upstream and never contains custom files.

Each patch is idempotent (checked by looking for the full replacement text). If
upstream later changes the anchored snippet, this script fails loudly with a
clear message instead of silently producing a broken or reverted tree.

Usage: python3 apply-xcode26-patches.py <source-root>
"""
import pathlib
import sys

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()

# (relative path, human-readable label, old, new)
PATCHES = [
    (
        "App/SettingsView.swift",
        "SubscriptionFile.types widened with .item + .data",
        """    static let types: [UTType] = [.json, .pythonScript, .javaScript]
""",
        """    // CI patch: iOS classifies files saved from WeChat, Safari, QQ or the
    // Files app as public.data or a dynamic UTType (dyn.*), which may
    // conform to public.item but NOT to public.data. With only
    // .json / .pythonScript / .javaScript the document picker shows those
    // files greyed out and they cannot be selected at all. .item is the
    // ROOT of the UTType hierarchy and matches literally every file,
    // including extension-less and dyn.* ones. The importer still parses
    // by CONTENT (subscriptionImport probes the bytes, not the extension).
    static let types: [UTType] = [.item, .data, .content, .text, .plainText, .json, .pythonScript, .javaScript]
""",
    ),
]


def read(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def main():
    print("Applying CI workspace patches in", ROOT)
    for rel, _label, old, new in PATCHES:
        path = ROOT / rel
        if not path.is_file():
            sys.exit("MISSING SOURCE FILE: %s" % path)
        text = read(path)
        if new in text:
            state = "already patched"
        elif text.count(old) != 1:
            sys.exit(
                "PATCH ANCHOR CHANGED in %s (expected exactly 1 match, got %d).\n"
                "Upstream likely modified this code; review and update this script."
                % (rel, text.count(old))
            )
        else:
            text = text.replace(old, new, 1)
            write(path, text)
            state = "patched"
        print("  %-52s %s" % (rel, state))

    # Sanity: the file-importer whitelist must be widened.
    settings = read(ROOT / "App/SettingsView.swift")
    assert "[.item, .data, .content" in settings, "file importer whitelist not widened"
    print("All CI workspace patches verified.")


if __name__ == "__main__":
    main()

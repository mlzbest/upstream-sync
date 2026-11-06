#!/usr/bin/env python3
"""Add the CI-only entry-card widget to the build workspace.

mlzbest/mmusic is a byte-identical mirror of jo32/tvbox-silicon: it may not gain
a single extra file, so the widget lives in THIS repository
(widget/YingxiaWidget.swift) and is copied into the CI workspace only.

What this does, inside the workspace:
  1. writes Widget/YingxiaWidget.swift
  2. inserts a TVBox-Widget app-extension target into project.yml

It deliberately does NOT add the widget as a dependency of TVBox-iOS. XcodeGen's
docs do not guarantee how target-template arrays merge, and the SharedApp
template already owns TVBox-iOS's `dependencies` (the TVCore package). Leaving
that list alone is safer: the workflow builds TVBox-Widget on its own scheme and
copies the .appex into Payload/TVBox-iOS.app/PlugIns before zipping.

Idempotent: running twice is a no-op. Fails loudly if an anchor is missing, so a
silent "widget missing from the IPA" can never happen.

Usage: python3 apply-widget-patch.py <workspace-root>
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

# <controller>/scripts/apply-widget-patch.py -> parents[1] is the controller root
# (in CI the controller is checked out at .ci, so this resolves to .ci).
CONTROLLER_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = CONTROLLER_ROOT / "widget" / "YingxiaWidget.swift"

WIDGET_REL = Path("Widget") / "YingxiaWidget.swift"

MARKER = "  # >>> CI widget patch (mlzbest/upstream-sync)"

TARGET_BLOCK = """  # >>> CI widget patch (mlzbest/upstream-sync) - not present upstream.
  # An entry-card widget for the home and lock screen. No App Groups (a free
  # Apple ID cannot use them), so the card shares nothing with the app; it only
  # opens the app through the yingxia:// scheme. Built by its own scheme in the
  # workflow and copied into PlugIns, which is why TVBox-iOS's dependency list
  # below is left exactly as upstream wrote it.
  # <<< CI widget patch
  TVBox-Widget:
    type: app-extension
    platform: iOS
    sources:
      - path: Widget
    info:
      path: Config/Info-TVBox-Widget.plist
      properties:
        CFBundleDisplayName: Yingxia
        # XcodeGen defaults a generated plist to APPL; an appex must be XPC! or
        # installd refuses it. The version keys mirror the app's (upstream sets
        # GENERATE_INFOPLIST_FILE=YES, we opt out, so expand $(...) here).
        CFBundlePackageType: XPC!
        CFBundleShortVersionString: $(MARKETING_VERSION)
        CFBundleVersion: $(CURRENT_PROJECT_VERSION)
        NSExtension:
          NSExtensionPointIdentifier: com.apple.widgetkit-extension
    settings:
      base:
        PRODUCT_BUNDLE_IDENTIFIER: com.jo32.yingxia.ios.widget
        GENERATE_INFOPLIST_FILE: NO
        SKIP_INSTALL: YES
        TARGETED_DEVICE_FAMILY: '1,2'
        APPLICATION_EXTENSION_API_ONLY: YES
    scheme:
      testTargets: []
"""

ANCHOR = "  TVBox-tvOS:\n"


def die(msg: str) -> None:
    print("apply-widget-patch: ERROR " + msg, file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    if len(sys.argv) != 2:
        die("usage: apply-widget-patch.py <workspace-root>")

    root = Path(sys.argv[1]).resolve()
    project_yml = root / "project.yml"
    if not project_yml.is_file():
        die("project.yml not found in %s" % root)
    if not TEMPLATE.is_file():
        die("widget template missing at %s" % TEMPLATE)

    # 1. Widget sources (always refreshed, so template edits take effect).
    widget_dst = root / WIDGET_REL
    widget_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(TEMPLATE, widget_dst)
    print("copied %s -> %s" % (TEMPLATE.name, WIDGET_REL.as_posix()))

    # 2. project.yml target, inserted just before the last target (TVBox-tvOS).
    raw = project_yml.read_bytes()
    newline = "\r\n" if b"\r\n" in raw else "\n"
    text = raw.decode("utf-8")

    if MARKER in text:
        print("project.yml already carries the widget target; skipped")
    else:
        if text.count(ANCHOR) != 1:
            die("anchor %r matched %d times (expected exactly 1)"
                % (ANCHOR.strip(), text.count(ANCHOR)))
        block = TARGET_BLOCK.replace("\n", newline) if newline != "\n" else TARGET_BLOCK
        text = text.replace(ANCHOR, block + ANCHOR.replace("\n", newline), 1)
        project_yml.write_bytes(text.encode("utf-8"))
        print("project.yml: inserted TVBox-Widget target")

    # 3. Sanity: everything the build depends on must be in place.
    final = project_yml.read_text(encoding="utf-8")
    assert "  TVBox-Widget:\n" in final, "widget target not in project.yml"
    assert "type: app-extension" in final, "widget target has wrong product type"
    assert "com.apple.widgetkit-extension" in final, "widget Info.plist missing extension point"
    assert "com.jo32.yingxia.ios.widget" in final, "widget bundle id missing"
    assert "  TVBox-iOS:\n" in final, "TVBox-iOS target disappeared"
    assert "  TVBox-tvOS:\n" in final, "TVBox-tvOS target disappeared"
    src = widget_dst.read_text(encoding="utf-8")
    assert "@main" in src and "WidgetBundle" in src, "widget entry point missing"
    assert 'URL(string: "yingxia://")' in src, "deep link missing"
    print("apply-widget-patch: OK (widget sources + target in place)")


if __name__ == "__main__":
    main()

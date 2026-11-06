#!/usr/bin/env python3
"""Add the CI-only widgets to the build workspace.

mlzbest/mmusic is a byte-identical mirror of jo32/tvbox-silicon: it may not gain
a single extra file, so the widgets live in THIS repository (widget/*.swift) and
are copied into the CI workspace only.

What this does, inside the workspace:
  1. copies widget/*.swift to Widget/
  2. inserts a TVBox-Widget app-extension target into project.yml

It deliberately does NOT add the widget as a dependency of TVBox-iOS. XcodeGen's
docs do not guarantee how target-template arrays merge, and the SharedApp
template already owns TVBox-iOS's `dependencies` (the TVCore package). Leaving
that list alone is safer: the workflow builds TVBox-Widget on its own scheme and
copies the .appex into Payload/TVBox-iOS.app/PlugIns before zipping.

Every Widget declared in the bundle shows up in the widget gallery on its own,
so adding a widget is just adding a file plus a line in the bundle.

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
TEMPLATES = CONTROLLER_ROOT / "widget"

WIDGET_DIR = Path("Widget")

MARKER = "  # >>> CI widget patch (mlzbest/upstream-sync)"

# Every widget the bundle must contain, and the scheme the workflow builds.
EXPECTED_KINDS = [
    "YingxiaEntryCard",
    "YingxiaImportShortcuts",
    "YingxiaTips",
    "YingxiaClock",
]

TARGET_BLOCK = """  # >>> CI widget patch (mlzbest/upstream-sync) - not present upstream.
  # Home and lock screen widgets. No App Groups (a free Apple ID cannot use
  # them), so they share nothing with the app; they only open it through the
  # yingxia:// scheme. Built by its own scheme in the workflow and copied into
  # PlugIns, which is why TVBox-iOS's dependency list below is left exactly as
  # upstream wrote it.
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
    if not TEMPLATES.is_dir():
        die("widget template directory missing at %s" % TEMPLATES)

    sources = sorted(TEMPLATES.glob("*.swift"))
    if not sources:
        die("no widget sources in %s" % TEMPLATES)

    # 1. Widget sources (always refreshed, so template edits take effect).
    widget_dst = root / WIDGET_DIR
    widget_dst.mkdir(parents=True, exist_ok=True)
    for stale in widget_dst.glob("*.swift"):
        stale.unlink()
    for source in sources:
        shutil.copyfile(source, widget_dst / source.name)
    print("copied %d widget file(s) -> %s" % (len(sources), WIDGET_DIR.as_posix()))

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

    combined = ""
    for copy in sorted(widget_dst.glob("*.swift")):
        combined += copy.read_text(encoding="utf-8")
    # A line of its own: one source URL contains "@main" as part of a git ref.
    assert combined.count("\n@main\n") == 1, "expected exactly one @main in the widget target"
    assert "WidgetBundle" in combined, "widget entry point missing"
    assert '"yingxia"' in combined and 'components.scheme = "yingxia"' in combined, \
        "import deep link missing"
    for kind in EXPECTED_KINDS:
        assert kind in combined, "widget %s missing from the bundle" % kind
        assert 'kind: "%s"' % kind in combined, "widget %s has no unique kind" % kind
    print("widgets in bundle: " + ", ".join(EXPECTED_KINDS))
    print("apply-widget-patch: OK (widget sources + target in place)")


if __name__ == "__main__":
    main()

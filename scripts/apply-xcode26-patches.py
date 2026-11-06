#!/usr/bin/env python3
"""
Apply the Xcode 26 / iOS 26 SDK compatibility patches to a pristine checkout
of jo32/tvbox-silicon (mirrored at mlzbest/mmusic).

These are the exact source fixes validated by run 42036607258 on 2026-11-05.
They are applied to the CI workspace ONLY - mlzbest/mmusic stays a
byte-identical mirror of upstream and never contains custom files.

Root cause: upstream ships forward-looking iOS 27 branches, but GitHub's
macos-latest runner has Xcode 26 / iOS 26 SDK. @available() guards the runtime
call, not compile-time symbol resolution, so those branches fail to type-check.

The last patch is a small functional fix (not an SDK workaround): the upstream
file importer only allows .json/.py/.js UTTypes, which leaves most files saved
from WeChat / Safari / the Files app greyed out in the iOS document picker.

Each patch is idempotent (checked by looking for the full replacement text). If
upstream later changes one of the anchored snippets, this script fails loudly
with a clear message instead of silently producing a broken or reverted tree.

Usage: python3 apply-xcode26-patches.py <source-root>
"""
import pathlib
import sys

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()

# (relative path, human-readable label, old, new)
# Idempotence is checked by looking for the full replacement text, so added
# comments or reordered lines can never break a second run.
PATCHES = [
    (
        "Sources/TVCore/ScriptSniffing.swift",
        "var sites = self.sites",
        """        let pending = sites.indices.filter { sites[$0].needsSniffing }
        guard !pending.isEmpty else { return self }
        var sites = sites
""",
        """        // Xcode 26 / Swift 6 rejects a closure that captures the local `sites`
        // before its declaration. Declare the mutable copy first and read the
        // property explicitly. Behaviour is unchanged.
        var sites = self.sites
        let pending = sites.indices.filter { sites[$0].needsSniffing }
        guard !pending.isEmpty else { return self }
""",
    ),
    (
        "App/ExternalDisplay.swift",
        "#if TVBOX_OS27_SDK\n        if #available(iOS 27.0, *)",
        """    func makeUIViewController(context: Context) -> UIViewController {
        if #available(iOS 27.0, *) { return ExternalDisplayAccessoryController() }
        return UIViewController()
    }
""",
        """    func makeUIViewController(context: Context) -> UIViewController {
#if TVBOX_OS27_SDK
        if #available(iOS 27.0, *) { return ExternalDisplayAccessoryController() }
#endif
        return UIViewController()
    }
""",
    ),
    (
        "App/ExternalDisplay.swift",
        "#if TVBOX_OS27_SDK\n@available(iOS 27.0, *)",
        """@available(iOS 27.0, *)
private final class ExternalDisplayAccessoryController: UIViewController {
""",
        """// UISceneAccessory* / registerSceneAccessory exist only in an iOS 27 SDK.
// Gate the whole type behind a compilation condition that is OFF by default;
// on iOS 26 the registrar already returned an empty controller, so behaviour
// is unchanged. Define TVBOX_OS27_SDK when building with an iOS 27 SDK.
#if TVBOX_OS27_SDK
@available(iOS 27.0, *)
private final class ExternalDisplayAccessoryController: UIViewController {
""",
    ),
    (
        "App/ExternalDisplay.swift",
        "#endif  // TVBOX_OS27_SDK",
        """        self.registration = nil
    }
}

/// The external-display scene's delegate. Its window is made by `ExternalDisplay`, when a video is playing.
""",
        """        self.registration = nil
    }
}
#endif  // TVBOX_OS27_SDK

/// The external-display scene's delegate. Its window is made by `ExternalDisplay`, when a video is playing.
""",
    ),
    (
        "App/LiveRoomsView.swift",
        "Result<[LiveRoom], Error>.success(rooms)",
        """                    group.addTask { await (platform, Result { try await LiveCatalog.search(platform, keyword: query) }) }
""",
        """                    // Swift 6: Result(catching:) takes a synchronous closure,
                    // so `try await` cannot live inside it. Unwrap explicitly.
                    group.addTask {
                        do {
                            let rooms = try await LiveCatalog.search(platform, keyword: query)
                            return (platform, Result<[LiveRoom], Error>.success(rooms))
                        } catch {
                            return (platform, Result<[LiveRoom], Error>.failure(error))
                        }
                    }
""",
    ),
    (
        "App/VideoEnhancement.swift",
        "#if TVBOX_OS27_SDK\n        if #available(macOS 27",
        """    private static func interpolationFits(width: Int, height: Int) -> Bool {
        if #available(macOS 27, iOS 27, tvOS 27, *) {
""",
        """    private static func interpolationFits(width: Int, height: Int) -> Bool {
#if TVBOX_OS27_SDK
        // maximumDimension / maximumPixelCount were added in the iOS 27 SDK.
        // With an iOS 26 SDK the branch cannot type-check, so fall through to
        // the OS 26 limits below (what the app already does at runtime).
        if #available(macOS 27, iOS 27, tvOS 27, *) {
""",
    ),
    (
        "App/VideoEnhancement.swift",
        "#endif\n        return max(width, height) <= 1280",
        """            return max(width, height) <= side && width * height <= pixels
        }
        return max(width, height) <= 1280 && width * height <= 1280 * 720
""",
        """            return max(width, height) <= side && width * height <= pixels
        }
#endif
        return max(width, height) <= 1280 && width * height <= 1280 * 720
""",
    ),
    (
        "App/SettingsView.swift",
        "SubscriptionFile.types widened with .data",
        """    static let types: [UTType] = [.json, .pythonScript, .javaScript]
""",
        """    // CI patch: iOS classifies files saved from WeChat, Safari or the Files
    // app as public.data or a dynamic UTType, not public.json. With only
    // .json / .pythonScript / .javaScript the document picker shows those
    // files greyed out and they cannot be selected at all. `.data` is the
    // base type of every file; the importer still parses by CONTENT
    // (subscriptionImport probes the bytes, not the extension).
    static let types: [UTType] = [.json, .plainText, .data, .pythonScript, .javaScript]
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
    print("Applying Xcode 26 / iOS 26 SDK compatibility patches in", ROOT)
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

    # Sanity: the three hard compile errors must be gone.
    sniff = read(ROOT / "Sources/TVCore/ScriptSniffing.swift")
    live = read(ROOT / "App/LiveRoomsView.swift")
    video = read(ROOT / "App/VideoEnhancement.swift")
    settings = read(ROOT / "App/SettingsView.swift")
    assert "var sites = sites" not in sniff, "Swift 6 sites shadowing still present"
    assert "Result { try await" not in live, "async Result closure still present"
    assert "#if TVBOX_OS27_SDK" in video, "iOS 27 symbol guard missing"
    assert ".data, .pythonScript" in settings, "file importer whitelist not widened"
    print("All CI workspace patches verified.")


if __name__ == "__main__":
    main()

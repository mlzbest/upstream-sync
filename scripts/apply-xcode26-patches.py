#!/usr/bin/env python3
"""
Apply the CI workspace patches to a pristine checkout of jo32/tvbox-silicon
(mirrored at mlzbest/mmusic).

The build runs on the GitHub `xcode-27` runner image (Xcode 27.2 / ios27 SDK),
matching the upstream author's toolchain, so the old "Xcode 26 compatibility"
patches are no longer needed and have been removed.

Two functional patches remain, both applied to the CI workspace ONLY -
mlzbest/mmusic stays a byte-identical mirror of upstream and never contains
custom files:

  PATCH 1  SubscriptionFile.types widened with .item + .data
            Upstream only allows .json/.py/.js, leaving files saved from
            WeChat / Safari / the Files app greyed out. .item is the root
            UTType and matches every file (incl. dyn.* / public.data).

  PATCH 2  Replace the iOS SwiftUI `.fileImporter` (inside the custom-detent
            AddSubscriptionSheet) with a UIKit UIDocumentPickerViewController
            presented full-screen. On iOS 26/27 a `.fileImporter` hosted in a
            `.presentationDetents([.medium, .large])` sheet shows the picker but
            taps on files do nothing - the picker's own modal presentation
            conflicts with the parent detented sheet. Dropping to UIKit and
            presenting full-screen from a hosted view controller sidesteps the
            SwiftUI nested-modal bug entirely.

Each patch is idempotent (checked by looking for the full replacement text). If
upstream later changes an anchored snippet, this script fails loudly instead of
silently producing a broken tree.
"""
import pathlib
import sys

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()

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
    (
        "App/SettingsView.swift",
        "iOS .fileImporter replaced with UIKit full-screen UIDocumentPickerViewController",
        """        .fileImporter(isPresented: $choosesFile, allowedContentTypes: SubscriptionFile.types) { result in
            guard case .success(let file) = result else { return }
            Task {
                await store.importSubscriptionFile(file)
                if store.importError == nil { dismiss() }
            }
        }
""",
        """        .sheet(isPresented: $choosesFile) {
            DocumentImporter(types: SubscriptionFile.types) { url in
                choosesFile = false
                Task {
                    await store.importSubscriptionFile(url)
                    if store.importError == nil { dismiss() }
                }
            } onCancel: {
                choosesFile = false
            }
        }
""",
    ),
]

# Appended once at EOF of SettingsView.swift (inside #if os(iOS) so macOS is untouched).
DOC_IMPORTER_BLOCK = '''#if os(iOS)
import UIKit
import UniformTypeIdentifiers

/// Presents UIDocumentPickerViewController as a top-level full-screen modal.
///
/// A plain SwiftUI `.fileImporter` hosted inside a custom-detent sheet
/// (AddSubscriptionSheet sets `.presentationDetents([.medium, .large])`) shows
/// the picker on iOS 26/27 but taps on files do nothing: the picker's own modal
/// presentation conflicts with the parent detented sheet. Dropping to UIKit and
/// presenting the picker full-screen from a hosted view controller sidesteps the
/// SwiftUI nested-modal bug entirely. The file is copied out (asCopy: true) so
/// the returned URL is directly readable without security-scoped bookkeeping.
private struct DocumentImporter: UIViewControllerRepresentable {
    let types: [UTType]
    let onPick: (URL) -> Void
    let onCancel: () -> Void

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    func makeUIViewController(context: Context) -> UIViewController {
        let host = UIViewController()
        host.view.backgroundColor = .clear
        return host
    }

    func updateUIViewController(_ uiViewController: UIViewController, context: Context) {
        context.coordinator.presentIfNeeded(from: uiViewController)
    }

    final class Coordinator: NSObject, UIDocumentPickerDelegate {
        let parent: DocumentImporter
        var didPresent = false
        init(_ parent: DocumentImporter) { self.parent = parent }

        func presentIfNeeded(from vc: UIViewController) {
            guard !didPresent, vc.presentedViewController == nil else { return }
            if vc.viewIfLoaded?.window == nil {
                DispatchQueue.main.async { self.presentIfNeeded(from: vc) }
                return
            }
            didPresent = true
            let picker = UIDocumentPickerViewController(forOpeningContentTypes: parent.types, asCopy: true)
            picker.delegate = self
            picker.allowsMultipleSelection = false
            picker.modalPresentationStyle = .fullScreen
            vc.present(picker, animated: true)
        }

        func documentPicker(_ controller: UIDocumentPickerViewController, didPickDocumentsAt urls: [URL]) {
            if let url = urls.first { parent.onPick(url) }
        }
        func documentPickerWasCancelled(_ controller: UIDocumentPickerViewController) {
            parent.onCancel()
        }
    }
}
#endif
'''


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

    # Append the UIKit DocumentImporter (idempotent by marker).
    settings_path = ROOT / "App/SettingsView.swift"
    settings_text = read(settings_path)
    if "private struct DocumentImporter:" not in settings_text:
        settings_text = settings_text.rstrip("\n") + "\n\n" + DOC_IMPORTER_BLOCK
        write(settings_path, settings_text)
        print("  %-52s %s" % ("App/SettingsView.swift", "appended DocumentImporter"))
    else:
        print("  %-52s %s" % ("App/SettingsView.swift", "DocumentImporter already present"))

    # Sanity checks.
    settings = read(ROOT / "App/SettingsView.swift")
    assert "[.item, .data, .content" in settings, "file importer whitelist not widened"
    assert "private struct DocumentImporter:" in settings, "DocumentImporter not appended"
    assert ".sheet(isPresented: $choosesFile)" in settings, "fileImporter not replaced with sheet"
    print("All CI workspace patches verified.")


if __name__ == "__main__":
    main()

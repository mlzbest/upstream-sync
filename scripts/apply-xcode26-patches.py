#!/usr/bin/env python3
"""
Apply CI workspace patches to a pristine checkout of jo32/tvbox-silicon
(mirrored at mlzbest/mmusic).

The build runs on the GitHub `xcode-27` runner image (Xcode 27.2 / ios27 SDK),
matching the upstream author's toolchain, so the old "Xcode 26 compatibility"
patches have been removed.

All patches are applied to the CI workspace ONLY - mlzbest/mmusic stays a
byte-identical mirror of upstream and never contains custom files.

WHY THIS EXISTS
    On iOS 26/27 a SwiftUI `.fileImporter` presented from inside a sheet
    (especially one with `.presentationDetents`) shows the document picker but
    taps on files do nothing - the picker's own modal presentation conflicts
    with the parent sheet. The fix is to drop to UIKit and present a
    UIDocumentPickerViewController full-screen from a hosted view controller.
    `DocumentImporter` (appended to SettingsView.swift, iOS-only) does that,
    and every iOS `.fileImporter` in the app is routed through it.

PATCHES
    1  SubscriptionFile.types widened with .item + .data   (greyed-out files)
    2  AddSubscriptionSheet .fileImporter  -> DocumentImporter
    3  MusicLXSourcesSection .fileImporter -> DocumentImporter
    4  MusicExtensionsSection .fileImporter -> DocumentImporter
    5  CatalogDanmakuSettingsView .fileImporter -> DocumentImporter

(FeedbackView's `.fileImporter` is macOS-only — iOS uses PhotosPicker — and is
intentionally left untouched.)

Each patch is idempotent (checked by looking for the full replacement text). If
upstream later changes an anchored snippet, this script fails loudly instead of
silently producing a broken tree.
"""
import pathlib
import sys

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()

# --- the shared UIKit picker (appended once to SettingsView.swift) -----------
DOC_IMPORTER_BLOCK = '''#if os(iOS)
import UIKit
import UniformTypeIdentifiers

/// Presents UIDocumentPickerViewController as a top-level full-screen modal.
///
/// A plain SwiftUI `.fileImporter` hosted inside a sheet (especially one with
/// `.presentationDetents`) shows the picker on iOS 26/27 but taps on files do
/// nothing: the picker's own modal presentation conflicts with the parent
/// sheet. Dropping to UIKit and presenting full-screen from a hosted view
/// controller sidesteps the SwiftUI nested-modal bug entirely. Files are copied
/// out (asCopy: true) so the returned URLs are directly readable.
struct DocumentImporter: UIViewControllerRepresentable {
    let types: [UTType]
    var allowsMultiple = false
    let onPick: ([URL]) -> Void
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
            picker.allowsMultipleSelection = parent.allowsMultiple
            picker.modalPresentationStyle = .fullScreen
            vc.present(picker, animated: true)
        }

        func documentPicker(_ controller: UIDocumentPickerViewController, didPickDocumentsAt urls: [URL]) {
            parent.onPick(urls)
        }

        func documentPickerWasCancelled(_ controller: UIDocumentPickerViewController) {
            parent.onCancel()
        }
    }
}
#endif
'''

PATCHES = [
    # 1. Widen the subscription file whitelist.
    #    Upstream 1.8.14 (commit 645ad2b, #725) added .m3uPlaylist + .plainText
    #    for M3U / TXT live playlists; re-anchored on top of that.
    (
        "App/SettingsView.swift",
        "SubscriptionFile.types widened with .item + .data",
        """    static let types: [UTType] = [.json, .pythonScript, .javaScript, .m3uPlaylist, .plainText]
""",
        """    // CI patch: iOS classifies files saved from WeChat, Safari, QQ or the
    // Files app as public.data or a dynamic UTType (dyn.*), which may
    // conform to public.item but NOT to public.data. Upstream's own list
    // still leaves those greyed out. .item is the ROOT of the UTType
    // hierarchy and matches literally every file, including extension-less
    // and dyn.* ones. The importer still parses by CONTENT
    // (subscriptionImport probes the bytes, not the extension).
    static let types: [UTType] = [.item, .data, .content, .text, .plainText, .json, .m3uPlaylist, .pythonScript, .javaScript]
""",
    ),
    # 2. Add subscription sheet (iOS): .fileImporter -> UIKit picker.
    (
        "App/SettingsView.swift",
        "AddSubscriptionSheet fileImporter -> DocumentImporter",
        """        .fileImporter(isPresented: $choosesFile, allowedContentTypes: SubscriptionFile.types) { result in
            guard case .success(let file) = result else { return }
            Task {
                await store.importSubscriptionFile(file)
                if store.importError == nil { dismiss() }
            }
        }
""",
        """        .sheet(isPresented: $choosesFile) {
            DocumentImporter(types: SubscriptionFile.types,
                             onPick: { urls in
                                 choosesFile = false
                                 guard let url = urls.first else { return }
                                 Task {
                                     await store.importSubscriptionFile(url)
                                     if store.importError == nil { dismiss() }
                                 }
                             },
                             onCancel: { choosesFile = false })
        }
""",
    ),
    # 3. Music: LX custom sources (luoxue) import.
    (
        "App/MusicPlayerViews.swift",
        "MusicLXSourcesSection fileImporter -> DocumentImporter",
        """        } footer: {
            Text(MusicLXSourcesModel.note)
        }
        .fileImporter(isPresented: $importing, allowedContentTypes: [.javaScript, .plainText, .data]) { result in
            if case .success(let file) = result { model.add(file: file) }
        }
""",
        """        } footer: {
            Text(MusicLXSourcesModel.note)
        }
        #if os(iOS)
        .sheet(isPresented: $importing) {
            DocumentImporter(types: [.javaScript, .plainText, .data],
                             onPick: { urls in
                                 importing = false
                                 if let file = urls.first { model.add(file: file) }
                             },
                             onCancel: { importing = false })
        }
        #else
        .fileImporter(isPresented: $importing, allowedContentTypes: [.javaScript, .plainText, .data]) { result in
            if case .success(let file) = result { model.add(file: file) }
        }
        #endif
""",
    ),
    # 4. Music: extensions import.
    (
        "App/MusicPlayerViews.swift",
        "MusicExtensionsSection fileImporter -> DocumentImporter",
        """        } footer: {
            Text(MusicExtensionsModel.note)
        }
        .fileImporter(isPresented: $importing, allowedContentTypes: [.javaScript, .plainText, .data]) { result in
            if case .success(let file) = result { model.add(file: file) }
        }
""",
        """        } footer: {
            Text(MusicExtensionsModel.note)
        }
        #if os(iOS)
        .sheet(isPresented: $importing) {
            DocumentImporter(types: [.javaScript, .plainText, .data],
                             onPick: { urls in
                                 importing = false
                                 if let file = urls.first { model.add(file: file) }
                             },
                             onCancel: { importing = false })
        }
        #else
        .fileImporter(isPresented: $importing, allowedContentTypes: [.javaScript, .plainText, .data]) { result in
            if case .success(let file) = result { model.add(file: file) }
        }
        #endif
""",
    ),
    # 5. Danmaku (xml/json) import.
    (
        "App/CatalogDanmakuView.swift",
        "CatalogDanmakuSettingsView fileImporter -> DocumentImporter",
        """        .onDisappear { work?.cancel() }
        .fileImporter(isPresented: $showsImporter, allowedContentTypes: [.xml, .json]) { result in
            do { try model.importFile(result.get()); dismiss() }
            catch { self.error = error.localizedDescription }
        }
""",
        """        .onDisappear { work?.cancel() }
        #if os(iOS)
        .sheet(isPresented: $showsImporter) {
            DocumentImporter(types: [.xml, .json],
                             onPick: { urls in
                                 showsImporter = false
                                 guard let url = urls.first else { return }
                                 do { try model.importFile(url); dismiss() }
                                 catch { self.error = error.localizedDescription }
                             },
                             onCancel: { showsImporter = false })
        }
        #else
        .fileImporter(isPresented: $showsImporter, allowedContentTypes: [.xml, .json]) { result in
            do { try model.importFile(result.get()); dismiss() }
            catch { self.error = error.localizedDescription }
        }
        #endif
""",
    ),
    # NOTE: FeedbackView's `.fileImporter` is macOS-only (iOS uses PhotosPicker),
    # so it is intentionally left untouched.
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
        print("  %-40s %s" % (rel, state))

    # Append the shared UIKit DocumentImporter (idempotent by marker).
    settings_path = ROOT / "App/SettingsView.swift"
    settings_text = read(settings_path)
    if "struct DocumentImporter: UIViewControllerRepresentable" not in settings_text:
        settings_text = settings_text.rstrip("\n") + "\n\n" + DOC_IMPORTER_BLOCK
        write(settings_path, settings_text)
        print("  %-40s %s" % ("App/SettingsView.swift", "appended DocumentImporter"))
    else:
        print("  %-40s %s" % ("App/SettingsView.swift", "DocumentImporter already present"))

    # Sanity checks.
    settings = read(ROOT / "App/SettingsView.swift")
    music = read(ROOT / "App/MusicPlayerViews.swift")
    danmaku = read(ROOT / "App/CatalogDanmakuView.swift")
    assert "[.item, .data, .content" in settings, "whitelist not widened"
    assert "struct DocumentImporter: UIViewControllerRepresentable" in settings, "DocumentImporter not appended"
    assert ".sheet(isPresented: $choosesFile)" in settings, "add-subscription not routed"
    assert "DocumentImporter(types: [.javaScript, .plainText, .data]" in music, "music LX/ext not routed"
    assert "DocumentImporter(types: [.xml, .json]" in danmaku, "danmaku not routed"
    print("All CI workspace patches verified.")


if __name__ == "__main__":
    main()

// CI patch: home- and lock-screen widgets, injected by mlzbest/upstream-sync.
//
// The upstream mirror (jo32/tvbox-silicon) has no widget target and must stay
// byte-identical, so these files live in THIS repository (widget/*.swift) and
// are copied into the CI workspace by scripts/apply-widget-patch.py, which also
// adds the TVBox-Widget target to the workspace copy of project.yml. The
// workflow builds that target on its own scheme and copies the resulting .appex
// into Payload/TVBox-iOS.app/PlugIns.
//
// Deliberate limitation: a free Apple ID cannot use App Groups, and a widget's
// sandbox is separate from the app's. None of these widgets therefore shares
// data with the app. They open it through the yingxia:// scheme the app already
// registers (Config/Info-TVBox-iOS.plist):
//   yingxia://                          -> bring the app to the front
//   yingxia://import?url=&name=         -> open the import sheet, address
//                                          already filled in (TVCore's
//                                          SubscriptionImportLink parses it)
// Widgets in the bundle:
//   YingxiaEntryCard        entry card, home + lock screen
//   YingxiaImportShortcuts  up to three configurable subscription addresses,
//                           one tap each to import
//   YingxiaTips             one short how-to per day
//   YingxiaClock            time and date

import SwiftUI
import WidgetKit

/// Shared look and the app's two URL entry points.
enum WidgetBrand {
    static var title: String { "Yingxia" }
    static var subtitle: String { "影视 · 音乐 · 漫画" }
    static var hint: String { "轻点打开" }

    /// yingxia:// — the app registers the scheme purely as an entry point.
    static var appLink: URL { URL(string: "yingxia://")! }

    static var accent: Color { Color(red: 0.62, green: 0.47, blue: 0.99) }
    static var accentDeep: Color { Color(red: 0.30, green: 0.20, blue: 0.62) }

    // Computed on purpose: static stored properties of SwiftUI types are not
    // Sendable under Swift 6.0 language mode, which the project builds with.
    static var background: LinearGradient {
        LinearGradient(
            colors: [Color(red: 0.32, green: 0.24, blue: 0.72),
                     Color(red: 0.11, green: 0.08, blue: 0.26)],
            startPoint: .topLeading,
            endPoint: .bottomTrailing)
    }

    static var lightBackground: LinearGradient {
        LinearGradient(
            colors: [Color(red: 0.36, green: 0.28, blue: 0.78),
                     Color(red: 0.18, green: 0.13, blue: 0.40)],
            startPoint: .top,
            endPoint: .bottom)
    }

    /// Builds the app's import link. Returns nil unless the address is a real
    /// http(s) URL with a host — the same rule the app applies to a typed
    /// address, so a broken slot opens nothing instead of an empty sheet.
    static func importLink(address: String, name: String?) -> URL? {
        let trimmed = address.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let parsed = URL(string: trimmed),
              let scheme = parsed.scheme?.lowercased(),
              scheme == "http" || scheme == "https",
              let host = parsed.host(), !host.isEmpty
        else { return nil }

        var components = URLComponents()
        components.scheme = "yingxia"
        components.host = "import"
        var items = [URLQueryItem(name: "url", value: trimmed)]
        let label = (name ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        if !label.isEmpty { items.append(URLQueryItem(name: "name", value: label)) }
        components.queryItems = items
        return components.url
    }

    /// A readable name for an address: its host, minus a leading "www.".
    static func hostName(of address: String) -> String {
        let host = URL(string: address)?.host() ?? address
        return host.hasPrefix("www.") ? String(host.dropFirst(4)) : host
    }
}

@main
struct YingxiaWidgets: WidgetBundle {
    var body: some Widget {
        EntryCardWidget()
        ImportShortcutsWidget()
        TipsWidget()
        ClockWidget()
    }
}

// CI patch: a home- and lock-screen entry card, injected by mlzbest/upstream-sync.
//
// The upstream mirror (jo32/tvbox-silicon) has no widget target and must stay
// byte-identical, so this file is copied into the CI workspace by
// scripts/apply-widget-patch.py, which also adds the TVBox-Widget target to the
// workspace copy of project.yml. The workflow builds that target on its own
// scheme and copies the resulting .appex into Payload/TVBox-iOS.app/PlugIns.
//
// Deliberate limitation: a free Apple ID cannot use App Groups, and the widget
// sandbox is separate from the app's. This card therefore shares NO data with
// the app - it is an entry point that opens the app through the yingxia:// URL
// scheme the app already registers (Config/Info-TVBox-iOS.plist).

import SwiftUI
import WidgetKit

private enum CardBrand {
    static var title: String { "Yingxia" }
    static var subtitle: String { "影视 · 音乐 · 漫画" }
    static var hint: String { "轻点打开" }
    static var deepLink: URL { URL(string: "yingxia://")! }

    // Computed on purpose: a static stored property of a SwiftUI view type is
    // not Sendable under Swift 6.0 language mode, which the project builds with.
    static var background: LinearGradient {
        LinearGradient(
            colors: [Color(red: 0.32, green: 0.24, blue: 0.72),
                     Color(red: 0.11, green: 0.08, blue: 0.26)],
            startPoint: .topLeading,
            endPoint: .bottomTrailing)
    }
}

struct EntryCardEntry: TimelineEntry {
    let date: Date
}

struct EntryCardProvider: TimelineProvider {
    func placeholder(in context: Context) -> EntryCardEntry {
        EntryCardEntry(date: Date())
    }

    func getSnapshot(in context: Context, completion: @escaping (EntryCardEntry) -> Void) {
        completion(EntryCardEntry(date: Date()))
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<EntryCardEntry>) -> Void) {
        // The card has no time-dependent content: one entry, then never reload.
        completion(Timeline(entries: [EntryCardEntry(date: Date())], policy: .never))
    }
}

struct EntryCardView: View {
    @Environment(\.widgetFamily) private var family
    let entry: EntryCardEntry

    var body: some View {
        content
            .containerBackground(for: .widget) { background }
            .widgetURL(CardBrand.deepLink)
    }

    @ViewBuilder
    private var content: some View {
        switch family {
        case .accessoryCircular:
            Image(systemName: "play.tv.fill")
                .font(.system(size: 21, weight: .semibold))
                .widgetAccentable()
        case .accessoryRectangular:
            HStack(spacing: 6) {
                Image(systemName: "play.tv.fill")
                    .font(.system(size: 13, weight: .semibold))
                    .widgetAccentable()
                VStack(alignment: .leading, spacing: 1) {
                    Text(CardBrand.title).font(.system(size: 13, weight: .semibold))
                    Text(CardBrand.hint).font(.system(size: 11))
                }
                Spacer(minLength: 0)
            }
        case .systemSmall:
            smallCard
        default:
            wideCard
        }
    }

    @ViewBuilder
    private var background: some View {
        switch family {
        case .accessoryCircular, .accessoryRectangular:
            AccessoryWidgetBackground()
        default:
            CardBrand.background
        }
    }

    private var smallCard: some View {
        VStack(alignment: .leading, spacing: 0) {
            glyph(size: 30)
            Spacer(minLength: 6)
            Text(CardBrand.title)
                .font(.system(size: 15, weight: .semibold))
            Text(CardBrand.hint)
                .font(.system(size: 11))
                .opacity(0.75)
        }
        .foregroundStyle(.white)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
    }

    private var wideCard: some View {
        HStack(spacing: 12) {
            glyph(size: 38)
            VStack(alignment: .leading, spacing: 3) {
                Text(CardBrand.title)
                    .font(.system(size: 16, weight: .semibold))
                Text(CardBrand.subtitle)
                    .font(.system(size: 12))
                    .opacity(0.78)
            }
            Spacer(minLength: 0)
            Text(CardBrand.hint)
                .font(.system(size: 11))
                .opacity(0.7)
        }
        .foregroundStyle(.white)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
    }

    private func glyph(size: CGFloat) -> some View {
        Image(systemName: "play.tv.fill")
            .font(.system(size: size * 0.58, weight: .semibold))
            .frame(width: size, height: size)
            .background(.white.opacity(0.16),
                        in: RoundedRectangle(cornerRadius: size * 0.3, style: .continuous))
    }
}

struct EntryCardWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "YingxiaEntryCard", provider: EntryCardProvider()) { entry in
            EntryCardView(entry: entry)
        }
        .configurationDisplayName("Yingxia")
        .description("轻点卡片直接打开 Yingxia。")
        .supportedFamilies([.systemSmall, .systemMedium,
                            .accessoryCircular, .accessoryRectangular])
    }
}

@main
struct YingxiaWidgets: WidgetBundle {
    var body: some Widget {
        EntryCardWidget()
    }
}

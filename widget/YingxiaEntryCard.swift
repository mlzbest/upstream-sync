// Entry card: the original widget. Opens the app, shares no data.

import SwiftUI
import WidgetKit

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
        // Nothing time-dependent: one entry, then never reload.
        completion(Timeline(entries: [EntryCardEntry(date: Date())], policy: .never))
    }
}

struct EntryCardView: View {
    @Environment(\.widgetFamily) private var family
    let entry: EntryCardEntry

    var body: some View {
        content
            .containerBackground(for: .widget) { background }
            .widgetURL(WidgetBrand.appLink)
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
                    Text(WidgetBrand.title).font(.system(size: 13, weight: .semibold))
                    Text(WidgetBrand.hint).font(.system(size: 11))
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
            WidgetBrand.background
        }
    }

    private var smallCard: some View {
        VStack(alignment: .leading, spacing: 0) {
            glyph(size: 30)
            Spacer(minLength: 6)
            Text(WidgetBrand.title)
                .font(.system(size: 15, weight: .semibold))
            Text(WidgetBrand.hint)
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
                Text(WidgetBrand.title)
                    .font(.system(size: 16, weight: .semibold))
                Text(WidgetBrand.subtitle)
                    .font(.system(size: 12))
                    .opacity(0.78)
            }
            Spacer(minLength: 0)
            Text(WidgetBrand.hint)
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

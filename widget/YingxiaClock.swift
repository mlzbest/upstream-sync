// Time and date. Text(date, style: .time) keeps ticking without timeline
// reloads, so this widget costs nothing to run.

import SwiftUI
import WidgetKit

struct ClockEntry: TimelineEntry {
    let date: Date
}

struct ClockProvider: TimelineProvider {
    func placeholder(in context: Context) -> ClockEntry {
        ClockEntry(date: Date())
    }

    func getSnapshot(in context: Context, completion: @escaping (ClockEntry) -> Void) {
        completion(ClockEntry(date: Date()))
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<ClockEntry>) -> Void) {
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: Date())
        var entries = [ClockEntry(date: Date())]
        for offset in 1...2 {
            if let midnight = calendar.date(byAdding: .day, value: offset, to: today) {
                entries.append(ClockEntry(date: midnight))
            }
        }
        completion(Timeline(entries: entries, policy: .atEnd))
    }
}

struct ClockView: View {
    @Environment(\.widgetFamily) private var family
    let entry: ClockEntry

    var body: some View {
        content
            .containerBackground(for: .widget) { background }
            .widgetURL(WidgetBrand.appLink)
    }

    @ViewBuilder
    private var content: some View {
        switch family {
        case .accessoryCircular:
            Text(entry.date, style: .time)
                .font(.system(size: 13, weight: .semibold, design: .rounded))
                .minimumScaleFactor(0.6)
                .lineLimit(1)
                .widgetAccentable()
        case .accessoryRectangular:
            VStack(alignment: .leading, spacing: 0) {
                Text(entry.date, style: .time)
                    .font(.system(size: 15, weight: .semibold, design: .rounded))
                    .widgetAccentable()
                Text(entry.date, format: .dateTime.month(.abbreviated).day().weekday(.abbreviated))
                    .font(.system(size: 11))
            }
            .frame(maxWidth: .infinity, alignment: .leading)
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
            WidgetBrand.lightBackground
        }
    }

    private var smallCard: some View {
        VStack(alignment: .leading, spacing: 1) {
            Text(entry.date, style: .time)
                .font(.system(size: 34, weight: .semibold, design: .rounded))
                .minimumScaleFactor(0.6)
                .lineLimit(1)
            Text(entry.date, format: .dateTime.month(.wide).day())
                .font(.system(size: 12))
                .opacity(0.85)
            Text(entry.date, format: .dateTime.weekday(.wide))
                .font(.system(size: 11))
                .opacity(0.6)
            Spacer(minLength: 0)
        }
        .foregroundStyle(.white)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
    }

    private var wideCard: some View {
        HStack(spacing: 14) {
            VStack(alignment: .leading, spacing: 2) {
                Text(entry.date, style: .time)
                    .font(.system(size: 40, weight: .semibold, design: .rounded))
                    .minimumScaleFactor(0.6)
                    .lineLimit(1)
                Text(entry.date, format: .dateTime.year().month(.wide).day().weekday(.wide))
                    .font(.system(size: 12))
                    .opacity(0.82)
                    .lineLimit(1)
            }
            Spacer(minLength: 0)
            VStack(alignment: .trailing, spacing: 4) {
                Image(systemName: "play.tv.fill")
                    .font(.system(size: 15, weight: .semibold))
                    .frame(width: 30, height: 30)
                    .background(.white.opacity(0.16),
                                in: RoundedRectangle(cornerRadius: 9, style: .continuous))
                Text(WidgetBrand.title)
                    .font(.system(size: 10, weight: .medium))
                    .opacity(0.7)
            }
        }
        .foregroundStyle(.white)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
    }
}

struct ClockWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "YingxiaClock", provider: ClockProvider()) { entry in
            ClockView(entry: entry)
        }
        .configurationDisplayName("时间")
        .description("时间与日期，轻点打开 Yingxia。")
        .supportedFamilies([.systemSmall, .systemMedium,
                            .accessoryCircular, .accessoryRectangular])
    }
}

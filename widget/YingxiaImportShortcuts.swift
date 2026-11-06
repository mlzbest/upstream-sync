// Subscription shortcuts: up to three configurable addresses on the home
// screen, each opening the app's import sheet with the address already filled
// in (yingxia://import?url=&name=). Nothing is read from the app, so no App
// Groups are needed; the addresses live in the widget's own configuration.

import AppIntents
import SwiftUI
import WidgetKit

struct ImportShortcutsIntent: WidgetConfigurationIntent {
    static var title: LocalizedStringResource { "快捷导入订阅" }
    static var description: IntentDescription? {
        IntentDescription("把常用订阅地址放在桌面上，轻点即可在 Yingxia 里导入。")
    }

    @Parameter(title: "名称一") var name1: String?
    @Parameter(title: "地址一") var address1: String?
    @Parameter(title: "名称二") var name2: String?
    @Parameter(title: "地址二") var address2: String?
    @Parameter(title: "名称三") var name3: String?
    @Parameter(title: "地址三") var address3: String?

    func perform() async throws -> some IntentResult { .result() }
}

struct ImportSlot: Identifiable {
    let id: Int
    let name: String
    let address: String

    var link: URL? { WidgetBrand.importLink(address: address, name: name) }
}

struct ImportEntry: TimelineEntry {
    let date: Date
    let configuration: ImportShortcutsIntent
}

struct ImportShortcutsProvider: AppIntentTimelineProvider {
    func placeholder(in context: Context) -> ImportEntry {
        ImportEntry(date: Date(), configuration: ImportShortcutsIntent())
    }

    func snapshot(for configuration: ImportShortcutsIntent, in context: Context) async -> ImportEntry {
        ImportEntry(date: Date(), configuration: configuration)
    }

    func timeline(for configuration: ImportShortcutsIntent, in context: Context) async -> Timeline<ImportEntry> {
        // The content only changes when the user edits the widget, which asks
        // for a new snapshot; no periodic reload is needed.
        Timeline(entries: [ImportEntry(date: Date(), configuration: configuration)], policy: .never)
    }
}

struct ImportShortcutsView: View {
    @Environment(\.widgetFamily) private var family
    let entry: ImportEntry

    /// Venera's comic source list: the one subscription every new install
    /// needs, and the reason the Manga tab is hidden (Store.swift only shows it
    /// once a comic source list is among the subscriptions).
    private static var mangaList: ImportSlot {
        ImportSlot(id: 90,
                   name: "漫画源列表",
                   address: "https://cdn.jsdelivr.net/gh/venera-app/venera-configs@main/index.json")
    }

    private var configured: [ImportSlot] {
        let configuration = entry.configuration
        let pairs: [(String?, String?)] = [(configuration.name1, configuration.address1),
                                           (configuration.name2, configuration.address2),
                                           (configuration.name3, configuration.address3)]
        var slots: [ImportSlot] = []
        for (index, pair) in pairs.enumerated() {
            guard let address = pair.1?.trimmingCharacters(in: .whitespacesAndNewlines),
                  !address.isEmpty,
                  WidgetBrand.importLink(address: address, name: pair.0) != nil
            else { continue }
            let typed = (pair.0 ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
            slots.append(ImportSlot(id: index,
                                    name: typed.isEmpty ? WidgetBrand.hostName(of: address) : typed,
                                    address: address))
        }
        return slots
    }

    private var rows: [ImportSlot] {
        var slots = configured
        if slots.count < 3 { slots.append(Self.mangaList) }
        return Array(slots.prefix(3))
    }

    private var firstSlot: ImportSlot? { rows.first }

    var body: some View {
        content
            .containerBackground(for: .widget) { background }
    }

    @ViewBuilder
    private var content: some View {
        switch family {
        case .accessoryRectangular:
            accessoryCard
        case .systemSmall:
            smallCard.widgetURL(firstSlot?.link ?? WidgetBrand.appLink)
        default:
            listCard
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

    private var listCard: some View {
        VStack(alignment: .leading, spacing: 9) {
            HStack(spacing: 5) {
                Image(systemName: "square.and.arrow.down.on.square.fill")
                    .font(.system(size: 11))
                Text("订阅导入")
                    .font(.system(size: 11, weight: .semibold))
                Spacer(minLength: 0)
                if configured.isEmpty {
                    Text("长按 → 编辑组件")
                        .font(.system(size: 10))
                        .opacity(0.72)
                }
            }
            .foregroundStyle(.white.opacity(0.82))

            ForEach(rows) { slot in
                if let link = slot.link {
                    Link(destination: link) { row(slot) }
                } else {
                    row(slot)
                }
            }
            Spacer(minLength: 0)
        }
        .foregroundStyle(.white)
    }

    private func row(_ slot: ImportSlot) -> some View {
        HStack(spacing: 9) {
            Text(String(slot.name.prefix(1)))
                .font(.system(size: 12, weight: .bold))
                .frame(width: 24, height: 24)
                .background(WidgetBrand.accent.opacity(0.38),
                            in: RoundedRectangle(cornerRadius: 7, style: .continuous))
            VStack(alignment: .leading, spacing: 1) {
                Text(slot.name)
                    .font(.system(size: 12, weight: .medium))
                    .lineLimit(1)
                Text(WidgetBrand.hostName(of: slot.address))
                    .font(.system(size: 9))
                    .opacity(0.6)
                    .lineLimit(1)
            }
            Spacer(minLength: 0)
            Image(systemName: "arrow.down.circle.fill")
                .font(.system(size: 13))
                .opacity(0.75)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var smallCard: some View {
        VStack(alignment: .leading, spacing: 0) {
            Image(systemName: "square.and.arrow.down.fill")
                .font(.system(size: 16, weight: .semibold))
                .frame(width: 30, height: 30)
                .background(.white.opacity(0.16),
                            in: RoundedRectangle(cornerRadius: 9, style: .continuous))
            Spacer(minLength: 6)
            Text(firstSlot?.name ?? "订阅导入")
                .font(.system(size: 14, weight: .semibold))
                .lineLimit(2)
            Text(firstSlot.map { WidgetBrand.hostName(of: $0.address) } ?? "长按编辑组件")
                .font(.system(size: 10))
                .opacity(0.72)
                .lineLimit(1)
        }
        .foregroundStyle(.white)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
    }

    private var accessoryCard: some View {
        HStack(spacing: 6) {
            Image(systemName: "square.and.arrow.down.fill")
                .font(.system(size: 13, weight: .semibold))
                .widgetAccentable()
            VStack(alignment: .leading, spacing: 1) {
                Text("导入订阅")
                    .font(.system(size: 13, weight: .semibold))
                Text(firstSlot?.name ?? "长按编辑组件")
                    .font(.system(size: 11))
                    .lineLimit(1)
            }
            Spacer(minLength: 0)
        }
        .widgetURL(firstSlot?.link ?? WidgetBrand.appLink)
    }
}

struct ImportShortcutsWidget: Widget {
    var body: some WidgetConfiguration {
        AppIntentConfiguration(kind: "YingxiaImportShortcuts",
                               intent: ImportShortcutsIntent.self,
                               provider: ImportShortcutsProvider()) { entry in
            ImportShortcutsView(entry: entry)
        }
        .configurationDisplayName("快捷导入订阅")
        .description("轻点组件里的地址，直接打开 Yingxia 的导入页，地址已填好。")
        .supportedFamilies([.systemSmall, .systemMedium, .accessoryRectangular])
    }
}

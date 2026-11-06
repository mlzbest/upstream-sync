// One short how-to per day. Text only, so it works with no data and no
// permissions; it rotates at midnight and is deliberately terse enough to read
// on the home screen.

import SwiftUI
import WidgetKit

enum WidgetTips {
    static var all: [String] {
        [
            "添加订阅：设置 → 订阅 → 从文件添加，或直接在输入框粘贴地址。",
            "漫画标签默认隐藏。先添加「漫画源列表」订阅，漫画入口才会出现。",
            "音乐自定义源：音乐 → 右上角 → 洛雪音乐自定义源 → 从文件添加。",
            "洛雪源必须声明 QQ / 网易 / 酷我 / 咪咕任一曲库，否则会被判为无效脚本。",
            "音乐扩展要含 getSongInfo 和 getConfig（或 search），格式不对会直接报错。",
            "订阅可以直接用链接导入：yingxia://import?url=地址",
            "从 iCloud 选文件前，先长按文件下载，未下载的占位文件选不中。",
            "自签的 App 7 天会过期。用 AltStore / SideStore 挂着自动续签。",
            "长按这个组件 → 编辑组件，可以把常用订阅地址固定上去。",
            "订阅变更后下拉首页即可刷新，不用重装 App。"
        ]
    }
}

struct TipsEntry: TimelineEntry {
    let date: Date
    let index: Int
}

struct TipsProvider: TimelineProvider {
    func placeholder(in context: Context) -> TipsEntry {
        TipsEntry(date: Date(), index: 0)
    }

    func getSnapshot(in context: Context, completion: @escaping (TipsEntry) -> Void) {
        completion(currentEntry())
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<TipsEntry>) -> Void) {
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: Date())
        var entries: [TipsEntry] = []
        for offset in 0..<7 {
            guard let day = calendar.date(byAdding: .day, value: offset, to: today) else { continue }
            let ordinal = calendar.ordinality(of: .day, in: .era, for: day) ?? offset
            entries.append(TipsEntry(date: day, index: ordinal % WidgetTips.all.count))
        }
        // A fresh week when the last entry runs out, so the rotation keeps going.
        completion(Timeline(entries: entries.isEmpty ? [currentEntry()] : entries, policy: .atEnd))
    }

    private func currentEntry() -> TipsEntry {
        let calendar = Calendar.current
        let ordinal = calendar.ordinality(of: .day, in: .era, for: Date()) ?? 0
        return TipsEntry(date: Date(), index: ordinal % WidgetTips.all.count)
    }
}

struct TipsView: View {
    @Environment(\.widgetFamily) private var family
    let entry: TipsEntry

    private var tip: String {
        let all = WidgetTips.all
        guard !all.isEmpty else { return "" }
        return all[entry.index % all.count]
    }

    var body: some View {
        content
            .containerBackground(for: .widget) { background }
            .widgetURL(WidgetBrand.appLink)
    }

    @ViewBuilder
    private var content: some View {
        switch family {
        case .accessoryRectangular:
            VStack(alignment: .leading, spacing: 1) {
                Text("Yingxia 小贴士").font(.system(size: 12, weight: .semibold))
                Text(tip).font(.system(size: 11)).lineLimit(3)
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
            WidgetBrand.background
        }
    }

    private var smallCard: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 4) {
                Image(systemName: "lightbulb.fill").font(.system(size: 10))
                Text("小贴士").font(.system(size: 10, weight: .semibold))
            }
            .opacity(0.75)
            Text(tip)
                .font(.system(size: 11.5))
                .lineLimit(6)
                .fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 0)
        }
        .foregroundStyle(.white)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
    }

    private var wideCard: some View {
        HStack(alignment: .top, spacing: 11) {
            Image(systemName: "lightbulb.fill")
                .font(.system(size: 14, weight: .semibold))
                .frame(width: 28, height: 28)
                .background(.white.opacity(0.16),
                            in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            VStack(alignment: .leading, spacing: 3) {
                Text("小贴士")
                    .font(.system(size: 10, weight: .semibold))
                    .opacity(0.72)
                Text(tip)
                    .font(.system(size: 12))
                    .lineLimit(4)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 0)
        }
        .foregroundStyle(.white)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
    }
}

struct TipsWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "YingxiaTips", provider: TipsProvider()) { entry in
            TipsView(entry: entry)
        }
        .configurationDisplayName("小贴士")
        .description("每天一条使用提示：订阅、漫画、音乐源怎么加。")
        .supportedFamilies([.systemSmall, .systemMedium, .accessoryRectangular])
    }
}

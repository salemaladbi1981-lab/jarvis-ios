import SwiftUI

struct JarvisCard<Content: View>: View {
    @ViewBuilder var content: Content
    var body: some View {
        content
            .padding(JarvisSpacing.lg)
            .background(RoundedRectangle(cornerRadius: JarvisRadius.card).fill(JarvisColor.bg_1.opacity(0.45)))
            .overlay(RoundedRectangle(cornerRadius: JarvisRadius.card).stroke(JarvisColor.primary_blue.opacity(0.16), lineWidth: 1))
    }
}

struct DemoBadge: View {
    var body: some View {
        Text("تجريبي")
            .font(.system(size: 11, weight: .semibold))
            .foregroundColor(JarvisColor.warning_demo)
            .padding(.horizontal, 8).padding(.vertical, 3)
            .background(Capsule().fill(JarvisColor.warning_demo.opacity(0.12)))
    }
}

struct UnavailableCapability: View {
    let message: String
    var body: some View {
        Label(message, systemImage: "link.badge.plus")
            .font(.system(size: 13))
            .foregroundColor(JarvisColor.text_muted)
            .fixedSize(horizontal: false, vertical: true)
    }
}

struct SmartHomeCard: View {
    let devices: [SmartDevice]
    var body: some View {
        JarvisCard {
            VStack(alignment: .leading, spacing: JarvisSpacing.md) {
                Label("المنزل", systemImage: "house")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundColor(JarvisColor.text_primary)
                if devices.isEmpty {
                    UnavailableCapability(message: "المنزل الذكي غير متصل")
                } else {
                    LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: JarvisSpacing.md) {
                        ForEach(devices) { device in
                            VStack(alignment: .leading, spacing: 4) {
                                Text(device.name).font(.caption).foregroundColor(JarvisColor.text_muted)
                                Text(device.value).font(.body).foregroundColor(JarvisColor.text_primary)
                            }.frame(maxWidth: .infinity, alignment: .leading)
                        }
                    }
                }
            }.frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

struct SecurityCard: View {
    let status: SecurityStatus?
    var body: some View {
        JarvisCard {
            VStack(alignment: .leading, spacing: JarvisSpacing.md) {
                Label("الأمان", systemImage: "shield")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundColor(JarvisColor.text_primary)
                if let status {
                    Text(status.systemsNormal ? "الأنظمة طبيعية" : "تحتاج الأنظمة إلى مراجعة")
                    Label(status.doorsLocked ? "الأبواب مقفلة" : "الأبواب غير مقفلة", systemImage: status.doorsLocked ? "lock" : "lock.open")
                    Label(status.camerasActive ? "الكاميرات تعمل" : "الكاميرات غير نشطة", systemImage: "video")
                } else {
                    UnavailableCapability(message: "نظام الأمان غير متصل — الحالة غير معروفة")
                }
            }
            .font(.system(size: 13))
            .foregroundColor(JarvisColor.text_secondary)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

struct MediaCard: View {
    let track: MediaTrack?
    var body: some View {
        JarvisCard {
            VStack(alignment: .leading, spacing: JarvisSpacing.md) {
                Label("الوسائط", systemImage: "music.note")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundColor(JarvisColor.text_primary)
                if let track {
                    Text(track.title).font(.body).foregroundColor(JarvisColor.text_primary)
                    Text(track.artist).font(.caption).foregroundColor(JarvisColor.text_muted)
                    Text("\(track.current) / \(track.duration)").font(.caption)
                } else {
                    UnavailableCapability(message: "لا يوجد مشغّل وسائط متصل")
                }
            }.frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

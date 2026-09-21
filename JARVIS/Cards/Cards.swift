import SwiftUI

// MARK: - Shared card chrome
struct JarvisCard<Content: View>: View {
    @ViewBuilder var content: Content
    var body: some View {
        content
            .padding(JarvisSpacing.lg)
            .background(RoundedRectangle(cornerRadius: JarvisRadius.card).fill(JarvisColor.bg_1.opacity(0.45)))
            .overlay(RoundedRectangle(cornerRadius: JarvisRadius.card).stroke(JarvisColor.primary_gold.opacity(0.18), lineWidth: 1))
            .shadow(color: JarvisColor.primary_gold.opacity(0.05), radius: 10, x: 0, y: 0)
    }
}

struct DemoBadge: View {
    var body: some View {
        Text("تجريبي")
            .font(.system(size: 11, weight: .semibold))
            .foregroundColor(JarvisColor.warning_demo)
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(Capsule().fill(JarvisColor.warning_demo.opacity(0.12)))
    }
}

// MARK: - Smart Home card (2×2 grid)
struct SmartHomeCard: View {
    let devices: [SmartDevice]
    var body: some View {
        JarvisCard {
            VStack(alignment: .leading, spacing: JarvisSpacing.md) {
                HStack {
                    Text("المنزل")
                        .font(.system(size: JarvisSpacing.lg, weight: .bold))
                        .foregroundColor(JarvisColor.text_primary)
                    Spacer()
                    DemoBadge()
                }
                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: JarvisSpacing.md) {
                    ForEach(devices) { d in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(d.name)
                                .font(.system(size: 13))
                                .foregroundColor(JarvisColor.text_muted)
                            Text(d.value)
                                .font(.system(size: 16, weight: .bold))
                                .foregroundColor(JarvisColor.text_primary)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(JarvisSpacing.md)
                        .background(RoundedRectangle(cornerRadius: JarvisRadius.control).fill(JarvisColor.bg_0.opacity(0.5)))
                    }
                }
            }
        }
    }
}

// MARK: - Security card
struct SecurityCard: View {
    let status: SecurityStatus
    var body: some View {
        JarvisCard {
            VStack(alignment: .leading, spacing: JarvisSpacing.md) {
                HStack {
                    Label("الأمان", systemImage: JarvisIconResolver.symbol(for: "sec.shield"))
                        .font(.system(size: JarvisSpacing.lg, weight: .bold))
                        .foregroundColor(JarvisColor.text_primary)
                    Spacer()
                    DemoBadge()
                }
                Text("جميع الأنظمة طبيعية")
                    .font(.system(size: 13))
                    .foregroundColor(JarvisColor.success)
                HStack(spacing: JarvisSpacing.lg) {
                    statusRow(icon: "sec.lock", label: "الأبواب مقفلة", ok: status.doorsLocked)
                    statusRow(icon: "sec.camera", label: "الكاميرات تعمل", ok: status.camerasActive)
                }
            }
        }
    }
    private func statusRow(icon: String, label: String, ok: Bool) -> some View {
        HStack(spacing: 6) {
            Image(systemName: JarvisIconResolver.symbol(for: icon))
                .font(.system(size: 13))
                .foregroundColor(JarvisColor.primary_gold)
            Text(label)
                .font(.system(size: 12))
                .foregroundColor(JarvisColor.text_secondary)
        }
    }
}

// MARK: - Media card
struct MediaCard: View {
    let track: MediaTrack
    var body: some View {
        JarvisCard {
            VStack(alignment: .leading, spacing: JarvisSpacing.md) {
                HStack { DemoBadge(); Spacer() }
                HStack(spacing: JarvisSpacing.md) {
                    RoundedRectangle(cornerRadius: JarvisRadius.control)
                        .fill(LinearGradient(colors: [JarvisColor.primary_gold, JarvisColor.bg_1], startPoint: .topLeading, endPoint: .bottomTrailing))
                        .frame(width: 56, height: 56)
                        .overlay(Text("BL").font(.system(size: 20, weight: .bold)).foregroundColor(.white.opacity(0.9)))
                    VStack(alignment: .leading, spacing: 2) {
                        Text(track.title)
                            .font(.system(size: 15, weight: .bold))
                            .foregroundColor(JarvisColor.text_primary)
                        Text(track.artist)
                            .font(.system(size: 12))
                            .foregroundColor(JarvisColor.text_muted)
                        Text("\(track.current) / \(track.duration)")
                            .font(.system(size: 11))
                            .foregroundColor(JarvisColor.text_muted.opacity(0.7))
                    }
                    Spacer()
                }
                GeometryReader { geo in
                    ZStack(alignment: .leading) {
                        Capsule().fill(JarvisColor.primary_gold.opacity(0.15)).frame(height: 4)
                        Capsule().fill(JarvisColor.primary_gold).frame(width: geo.size.width * 0.6, height: 4)
                    }
                }
                .frame(height: 4)
                HStack(spacing: JarvisSpacing.xl) {
                    Spacer()
                    Image(systemName: JarvisIconResolver.symbol(for: "media.previous")).font(.system(size: 16)).foregroundColor(JarvisColor.text_primary)
                    Image(systemName: JarvisIconResolver.symbol(for: "media.play")).font(.system(size: 20)).foregroundColor(JarvisColor.text_primary)
                    Image(systemName: JarvisIconResolver.symbol(for: "media.next")).font(.system(size: 16)).foregroundColor(JarvisColor.text_primary)
                    Spacer()
                }
                .accessibilityLabel("أزرار التحكم بالموسيقى")
            }
        }
    }
}

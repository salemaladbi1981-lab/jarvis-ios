import SwiftUI

/// Bottom navigation — exactly 4 items, Home active (P2.2).
struct BottomNavBar: View {
    @Binding var selected: String
    private let items: [(id: String, label: String, icon: String)] = [
        ("home", "الرئيسية", "nav.home"),
        ("devices", "الأجهزة", "nav.devices"),
        ("car", "السيارة", "nav.car"),
        ("more", "المزيد", "nav.more"),
    ]

    var body: some View {
        HStack {
            ForEach(items, id: \.id) { item in
                Button {
                    selected = item.id
                } label: {
                    VStack(spacing: 4) {
                        Image(systemName: JarvisIconResolver.symbol(for: item.icon))
                            .font(.system(size: 18))
                        Text(item.label)
                            .font(.system(size: 11))
                    }
                    .foregroundColor(selected == item.id ? JarvisColor.highlight_gold : JarvisColor.text_muted)
                    .frame(maxWidth: .infinity)
                }
                .accessibilityLabel(item.label)
                .accessibilityAddTraits(selected == item.id ? .isSelected : [])
            }
        }
        .padding(.vertical, JarvisSpacing.md)
        .padding(.horizontal, JarvisSpacing.lg)
        .frame(maxWidth: .infinity)
        .background(
            JarvisColor.bg_0
                .ignoresSafeArea(edges: .bottom)
        )
    }
}

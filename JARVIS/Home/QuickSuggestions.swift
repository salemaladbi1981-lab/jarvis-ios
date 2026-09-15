import SwiftUI

/// Compact Arabic suggestion chips (1–2 rows). Each chip is tappable.
struct QuickSuggestions: View {
    let suggestions: [String]
    var onTap: (String) -> Void = { _ in }
    private let columns = [GridItem(.flexible()), GridItem(.flexible())]

    var body: some View {
        LazyVGrid(columns: columns, spacing: JarvisSpacing.sm) {
            ForEach(suggestions, id: \.self) { s in
                Text(s)
                    .font(.system(size: 13))
                    .foregroundColor(JarvisColor.text_primary.opacity(0.9))
                    .padding(.horizontal, JarvisSpacing.md)
                    .padding(.vertical, JarvisSpacing.sm)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Capsule().fill(JarvisColor.bg_1.opacity(0.45)))
                    .overlay(Capsule().stroke(JarvisColor.primary_blue.opacity(0.16), lineWidth: 1))
                    .contentShape(Capsule())
                    .onTapGesture { onTap(s) }
                    .accessibilityAddTraits(.isButton)
                    .accessibilityLabel("أمر: \(s)")
            }
        }
    }
}

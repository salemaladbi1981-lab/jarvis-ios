import SwiftUI

/// Compact Arabic suggestion chips. Each chip maps to a typed QuickCommand.
struct QuickSuggestions: View {
    let commands: [QuickCommand]
    var onTap: (QuickCommand) -> Void = { _ in }
    private let columns = [GridItem(.flexible()), GridItem(.flexible())]

    var body: some View {
        LazyVGrid(columns: columns, spacing: JarvisSpacing.sm) {
            ForEach(commands) { cmd in
                Text(cmd.label)
                    .font(.system(size: 13, weight: .medium))
                    .foregroundColor(JarvisColor.text_primary.opacity(0.94))
                    .padding(.horizontal, JarvisSpacing.md)
                    .padding(.vertical, JarvisSpacing.sm)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Capsule().fill(JarvisColor.bg_1.opacity(0.52)))
                    .overlay(Capsule().stroke(JarvisColor.primary_gold.opacity(0.24), lineWidth: 1))
                    .shadow(color: JarvisColor.primary_gold.opacity(0.07), radius: 8, x: 0, y: 0)
                    .contentShape(Capsule())
                    .onTapGesture { onTap(cmd) }
                    .accessibilityAddTraits(.isButton)
                    .accessibilityLabel("أمر: \(cmd.label)")
            }
        }
    }
}

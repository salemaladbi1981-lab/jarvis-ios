import SwiftUI

/// Voice input bar: glowing microphone + placeholder text.
struct VoiceInputBar: View {
    var isListening: Bool = false
    var onTap: () -> Void = {}

    var body: some View {
        HStack(spacing: JarvisSpacing.md) {
            Image(systemName: isListening ? JarvisIconResolver.symbol(for: "util.waveform") : JarvisIconResolver.symbol(for: "util.mic"))
                .font(.system(size: 18))
                .foregroundColor(.white)
                .frame(width: 40, height: 40)
                .background(Circle().fill(JarvisColor.primary_blue.opacity(isListening ? 0.6 : 0.25)))
                .shadow(color: JarvisColor.primary_blue.opacity(isListening ? 0.6 : 0.2), radius: isListening ? 12 : 4)
            Text("أنا أسمعك…")
                .font(.system(size: 14))
                .foregroundColor(JarvisColor.text_muted)
            Spacer()
        }
        .padding(JarvisSpacing.md)
        .background(RoundedRectangle(cornerRadius: JarvisRadius.pill).fill(JarvisColor.bg_1.opacity(0.55)))
        .overlay(RoundedRectangle(cornerRadius: JarvisRadius.pill).stroke(JarvisColor.primary_blue.opacity(0.16), lineWidth: 1))
        .onTapGesture { onTap() }
        .accessibilityLabel("شريط الإدخال الصوتي")
    }
}

import SwiftUI

/// Composer سفلي: زر +، نص، إرسال، مايك.
struct WorkspaceComposerView: View {
    @Binding var text: String
    let hasAttachments: Bool
    let onSend: () -> Void
    let onAttach: () -> Void
    let onMic: () -> Void

    var body: some View {
        HStack(spacing: 10) {
            Button(action: onAttach) {
                Image(systemName: "plus.circle.fill")
                    .font(.title2)
                    .foregroundColor(JarvisColor.primary_gold)
            }

            TextField("اكتب أو أرسل ملفًا…", text: $text)
                .textFieldStyle(.plain)
                .multilineTextAlignment(.trailing)
                .foregroundColor(JarvisColor.text_primary)
                .tint(JarvisColor.highlight_gold)
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
                .background(
                    RoundedRectangle(cornerRadius: JarvisRadius.control, style: .continuous)
                        .fill(JarvisColor.bg_0.opacity(0.58))
                )
                .overlay(
                    RoundedRectangle(cornerRadius: JarvisRadius.control, style: .continuous)
                        .stroke(JarvisColor.primary_gold.opacity(0.16), lineWidth: 1)
                )
                .submitLabel(.send)
                .onSubmit(onSend)

            Button(action: onSend) {
                Image(systemName: "arrow.up.circle.fill")
                    .font(.title2)
                    .foregroundColor(canSend ? JarvisColor.highlight_gold : JarvisColor.text_muted)
            }
            .disabled(!canSend)

            Button(action: onMic) {
                Image(systemName: "mic.fill")
                    .font(.title2)
                    .foregroundColor(JarvisColor.primary_gold)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(
            RoundedRectangle(cornerRadius: JarvisRadius.card, style: .continuous)
                .fill(JarvisColor.bg_1.opacity(0.88))
        )
        .overlay(
            RoundedRectangle(cornerRadius: JarvisRadius.card, style: .continuous)
                .stroke(JarvisColor.primary_gold.opacity(0.18), lineWidth: 1)
        )
        .shadow(color: JarvisColor.primary_gold.opacity(0.06), radius: 10, x: 0, y: 0)
    }

    private var canSend: Bool {
        !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || hasAttachments
    }
}

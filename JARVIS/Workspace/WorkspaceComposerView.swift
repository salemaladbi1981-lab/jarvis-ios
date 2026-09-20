import SwiftUI

/// Composer سفلي: زر +، نص، إرسال، مايك.
struct WorkspaceComposerView: View {
    @Binding var text: String
    let hasAttachments: Bool
    var disabled: Bool = false
    let onSend: () -> Void
    let onAttach: () -> Void
    let onMic: () -> Void

    var body: some View {
        HStack(spacing: 10) {
            Button(action: onAttach) {
                Image(systemName: "plus.circle.fill").font(.title2)
            }
            TextField("اكتب أو أرسل ملفًا…", text: $text)
                .textFieldStyle(.roundedBorder)
                .multilineTextAlignment(.trailing)
                .submitLabel(.send)
                .onSubmit { if !disabled { onSend() } }
            Button(action: onSend) {
                Image(systemName: "arrow.up.circle.fill").font(.title2)
            }
            .disabled(disabled || text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !hasAttachments)
            Button(action: onMic) {
                Image(systemName: "mic.fill").font(.title2)
            }
        }
        .padding(.horizontal)
        .padding(.vertical, 8)
        .background(.thinMaterial)
    }
}

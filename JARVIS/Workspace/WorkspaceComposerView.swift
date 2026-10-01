import SwiftUI

/// Persistent composer shared by the workspace entry points.
struct WorkspaceComposerView: View {
    @Binding var text: String
    let hasAttachments: Bool
    var disabled: Bool = false
    let onSend: () -> Void
    let onAttach: () -> Void
    let onMic: () -> Void

    private var canSend: Bool {
        !disabled && (!text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || hasAttachments)
    }

    var body: some View {
        HStack(spacing: 4) {
            Button(action: onAttach) {
                Image(systemName: "plus").font(.system(size: 18, weight: .medium))
                    .frame(width: 44, height: 44)
            }
            .accessibilityLabel("إضافة مرفق")
            .disabled(disabled)

            TextField("اكتب لجارفس…", text: $text)
                .textFieldStyle(.plain)
                .font(.body)
                .foregroundColor(JarvisColor.text_primary)
                .submitLabel(.send)
                .onSubmit { if !disabled && canSend { onSend() } }
                .accessibilityLabel("رسالتك إلى جارفس")
                .padding(.vertical, 12)

            Button(action: onMic) {
                Image(systemName: "mic").font(.system(size: 19))
                    .frame(width: 44, height: 44)
            }
            .accessibilityLabel("التحكم بالصوت")

            Button(action: onSend) {
                ZStack {
                    Circle().fill(canSend ? JarvisColor.primary_blue : JarvisColor.primary_blue.opacity(0.12))
                        .frame(width: 36, height: 36)
                    Image(systemName: "arrow.up")
                        .font(.system(size: 17, weight: .semibold))
                        .foregroundColor(canSend ? JarvisColor.bg_0 : JarvisColor.text_muted)
                }.frame(width: 44, height: 44)
            }
            .disabled(!canSend)
            .accessibilityLabel("إرسال الرسالة")
        }
        .buttonStyle(.plain)
        .foregroundColor(JarvisColor.highlight_blue)
        .padding(5)
        .background(RoundedRectangle(cornerRadius: 26, style: .continuous).fill(JarvisColor.surface))
        .overlay(RoundedRectangle(cornerRadius: 26, style: .continuous).stroke(JarvisColor.primary_blue.opacity(0.26), lineWidth: 1))
        .padding(.vertical, 10)
    }
}

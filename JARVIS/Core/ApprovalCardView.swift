import SwiftUI

/// Shared approval request card (registry-driven, mock).
struct ApprovalCardView: View {
    @ObservedObject var vm: HomeViewModel
    let action: String

    var body: some View {
        JarvisCard {
            VStack(alignment: .leading, spacing: JarvisSpacing.md) {
                HStack {
                    Image(systemName: JarvisIconResolver.symbol(for: "util.alert"))
                        .foregroundColor(JarvisColor.warning_demo)
                    Text("طلب موافقة")
                        .font(.system(size: 15, weight: .bold))
                        .foregroundColor(JarvisColor.text_primary)
                    Spacer()
                    DemoBadge()
                }
                Text("الإجراء: \(action)")
                    .font(.system(size: 13))
                    .foregroundColor(JarvisColor.text_secondary)
                HStack(spacing: JarvisSpacing.md) {
                    Button("موافقة") { vm.approve() }
                        .buttonStyle(.borderedProminent)
                        .tint(JarvisColor.success)
                    Button("رفض") { vm.reject() }
                        .buttonStyle(.bordered)
                        .tint(JarvisColor.danger)
                }
            }
        }
        .transition(.opacity)
    }
}

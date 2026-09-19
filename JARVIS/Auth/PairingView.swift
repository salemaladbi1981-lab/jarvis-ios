import SwiftUI

/// شاشة إدخال one-time pairing code.
struct PairingView: View {
    @EnvironmentObject var enrollment: EnrollmentManager
    @State private var code = ""
    @State private var busy = false

    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "key.viewfinder").font(.system(size: 56)).foregroundColor(.blue)
            Text("تفعيل جارفس").font(.title2).bold()
            Text("أدخل رمز الاقتران لمرة واحدة الصادر من السيرفر").font(.body).foregroundColor(.secondary)
                .multilineTextAlignment(.center)
            SecureField("رمز الاقتران", text: $code)
                .textFieldStyle(.roundedBorder)
                .multilineTextAlignment(.center)
                #if os(iOS)
                .autocapitalization(.none)
                #endif
                .padding(.horizontal, 40)
            if let e = enrollment.error {
                Text(e).font(.caption).foregroundColor(.red)
            }
            Button {
                busy = true
                Task {
                    _ = await enrollment.enroll(code: code)
                    busy = false
                }
            } label: {
                if busy { ProgressView() }
                else { Text("تفعيل").frame(maxWidth: .infinity) }
            }
            .buttonStyle(.borderedProminent)
            .disabled(code.isEmpty || busy)
            .padding(.horizontal, 40)
        }
        .environment(\.layoutDirection, .rightToLeft)
        .preferredColorScheme(.dark)
    }
}

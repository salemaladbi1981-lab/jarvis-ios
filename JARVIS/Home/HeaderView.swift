import SwiftUI
import Combine

/// Quiet top header: location, live date/time, JARVIS wordmark.
struct HeaderView: View {
    var body: some View {
        HStack(alignment: .center) {
            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 4) {
                    Image(systemName: JarvisIconResolver.symbol(for: "util.location"))
                        .font(.system(size: 11))
                        .foregroundColor(JarvisColor.primary_blue)
                    Text("الدوحة")
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundColor(JarvisColor.text_primary)
                }
                LiveClockView()
            }
            Spacer()
            Text("JARVIS")
                .font(.custom("CormorantGaramond-SemiBold", size: 22))
                .tracking(3)
                .foregroundColor(JarvisColor.highlight_blue)
        }
    }
}

struct LiveClockView: View {
    @State private var now = Date()
    private let timer = Timer.publish(every: 1, on: .main, in: .common).autoconnect()

    var body: some View {
        Text(now, format: .dateTime.hour().minute().weekday(.abbreviated).day().month(.abbreviated))
            .font(.system(size: 11))
            .foregroundColor(JarvisColor.text_muted)
            .onReceive(timer) { now = $0 }
    }
}

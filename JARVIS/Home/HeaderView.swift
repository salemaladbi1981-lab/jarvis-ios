import SwiftUI
import Combine

/// Header: Doha + Arabic date/time on the LEFT, JARVIS wordmark on the RIGHT
/// (matches MOBILE IMAGE A — header composition is not mirrored by RTL).
struct HeaderView: View {
    @StateObject private var location = LocationManager()

    var body: some View {
        HStack(alignment: .center) {
            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 4) {
                    Image(systemName: JarvisIconResolver.symbol(for: "util.location"))
                        .font(.system(size: 11))
                        .foregroundColor(JarvisColor.primary_gold)
                    Text(location.displayCity)
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundColor(JarvisColor.text_primary)
                }
                LiveClockView()
            }
            Spacer()
            Text("JARVIS")
                .font(.custom("CormorantGaramond-SemiBold", size: 22))
                .tracking(3)
                .foregroundColor(JarvisColor.highlight_gold)
        }
        .environment(\.layoutDirection, .leftToRight)
        .onAppear { location.requestWhenNeeded() }
    }
}

/// Live Arabic date/time with Western numerals (locale ar_QA = Qatar/Doha).
struct LiveClockView: View {
    @State private var now = Date()
    private let timer = Timer.publish(every: 1, on: .main, in: .common).autoconnect()

    private static let formatter: DateFormatter = {
        let f = DateFormatter()
        f.locale = Locale(identifier: "ar_QA")
        f.calendar = Calendar(identifier: .gregorian)
        f.dateFormat = "E، d MMM، h:mm a"
        return f
    }()

    var body: some View {
        Text(Self.formatter.string(from: now))
            .font(.system(size: 11))
            .foregroundColor(JarvisColor.text_muted)
            .onReceive(timer) { now = $0 }
    }
}

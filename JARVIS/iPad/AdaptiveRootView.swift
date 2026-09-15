import SwiftUI
import UIKit

/// Chooses single-column (iPhone / iPad portrait / narrow split) vs
/// iPad two-zone landscape. `-landscape` forces the iPad landscape layout
/// for deterministic screenshots.
struct AdaptiveRootView: View {
    private let isIpad = UIDevice.current.userInterfaceIdiom == .pad
    private let forceLandscape = ProcessInfo.processInfo.arguments.contains("-landscape")

    var body: some View {
        GeometryReader { geo in
            let isLandscape = geo.size.width > geo.size.height
            if isIpad && (isLandscape || forceLandscape) {
                iPadLandscapeView()
            } else {
                HomeView()
            }
        }
        .onAppear {
            if forceLandscape {
                forceLandscapeOrientation()
            }
        }
    }

    /// iOS 16+ — request the window scene rotate to landscape (true landscape runtime).
    private func forceLandscapeOrientation() {
        guard let scene = UIApplication.shared.connectedScenes.first as? UIWindowScene else { return }
        if #available(iOS 16.0, *) {
            scene.requestGeometryUpdate(.iOS(interfaceOrientations: .landscapeRight))
        }
    }
}

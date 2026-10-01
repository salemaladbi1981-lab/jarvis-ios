import SwiftUI
#if os(iOS)
import UIKit
#endif

/// Chooses the correct Home layout per platform and orientation.
/// iOS: the same production workspace in every orientation; Home adapts its width.
/// macOS: shared workspace with a native navigation sidebar.
struct AdaptiveRootView: View {
    private let forceLandscape = ProcessInfo.processInfo.arguments.contains("-landscape")

    private var isIpad: Bool {
        #if os(iOS)
        return UIDevice.current.userInterfaceIdiom == .pad
        #else
        return false
        #endif
    }

    var body: some View {
        #if os(macOS)
        MacHomeView()
        #else
        RootView()
        .onAppear {
            LaunchTiming.mark("adaptiveRoot onAppear")
            if forceLandscape { forceLandscapeOrientation() }
        }
        #endif
    }

    #if os(iOS)
    private func forceLandscapeOrientation() {
        guard let scene = UIApplication.shared.connectedScenes.first as? UIWindowScene else { return }
        if #available(iOS 16.0, *) {
            scene.requestGeometryUpdate(.iOS(interfaceOrientations: .landscapeRight))
        }
    }
    #endif
}

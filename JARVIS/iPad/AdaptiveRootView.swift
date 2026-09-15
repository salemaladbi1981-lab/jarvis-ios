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
    }
}

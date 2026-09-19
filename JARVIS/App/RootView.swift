import SwiftUI

/// الجذر iOS — تبويبات (الرئيسية / المهام / التسليمات) + deep-link + launch args للـscreenshots.
struct RootView: View {
    @EnvironmentObject private var enrollment: EnrollmentManager
    @StateObject private var router = DeepLinkRouter()
    @State private var selectedTab: String

    init() {
        let args = ProcessInfo.processInfo.arguments
        if let i = args.firstIndex(of: "-tab"), i + 1 < args.count {
            _selectedTab = State(initialValue: args[i + 1])
        } else {
            _selectedTab = State(initialValue: "home")
        }
    }

    var body: some View {
        TabView(selection: $selectedTab) {
            HomeView()
                .tabItem { Label("الرئيسية", systemImage: "house.fill") }
                .tag("home")
            if let api = enrollment.api {
                TasksView(api: api)
                    .tabItem { Label("المهام", systemImage: "checklist") }
                    .tag("tasks")
                DeliveriesView(api: api)
                    .tabItem { Label("التسليمات", systemImage: "doc.fill") }
                    .tag("deliveries")
            }
        }
        .tint(JarvisColor.highlight_blue)
        .onOpenURL { router.handle($0) }
        .onChange(of: router.target) { t in
            if let t = t { select(t) }
        }
    }

    private func select(_ t: DeepLinkTarget) {
        switch t {
        case .task, .conversation: selectedTab = "tasks"
        case .delivery: selectedTab = "deliveries"
        }
    }
}

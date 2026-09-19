import SwiftUI

/// الجذر iOS — تبويبات (الرئيسية/الدردشة/الوارد/المهام/التسليمات) + deep-link + launch args للـscreenshots.
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
        let api = enrollment.api ?? JarvisAPI(baseURL: JarvisConfig.baseURL, sessionToken: JarvisConfig.injectedSessionToken ?? "")
        TabView(selection: $selectedTab) {
            HomeEntryView(api: api)
                .tabItem { Label("الرئيسية", systemImage: "house.fill") }
                .tag("home")
            ConversationListView(api: api)
                .tabItem { Label("الدردشة", systemImage: "bubble.left.and.bubble.right.fill") }
                .tag("chat")
            InboxView(api: api)
                .tabItem { Label("الوارد", systemImage: "tray.fill") }
                .tag("inbox")
            TasksView(api: api)
                .tabItem { Label("المهام", systemImage: "checklist") }
                .tag("tasks")
            DeliveriesView(api: api)
                .tabItem { Label("التسليمات", systemImage: "doc.fill") }
                .tag("deliveries")
        }
        .tint(JarvisColor.highlight_blue)
        .overlay(alignment: .top) {
            if ProcessInfo.processInfo.arguments.contains("-showArgs") {
                Text(ProcessInfo.processInfo.arguments.joined(separator: " | "))
                    .font(.system(size: 9, weight: .medium))
                    .foregroundColor(.white)
                    .padding(6)
                    .background(Color.black.opacity(0.75))
                    .cornerRadius(6)
                    .padding(.top, 2)
            }
        }
        .onOpenURL { router.handle($0) }
        .onChange(of: router.target) { t in
            if let t = t { select(t) }
        }
    }

    private func select(_ t: DeepLinkTarget) {
        switch t {
        case .conversation: selectedTab = "chat"
        case .task: selectedTab = "tasks"
        case .delivery: selectedTab = "deliveries"
        }
    }
}

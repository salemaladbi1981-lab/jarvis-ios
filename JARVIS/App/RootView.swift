import SwiftUI

/// الجذر iOS — تبويبات (الرئيسية/الدردشة/الوارد/المهام/التسليمات) + deep-link + launch args للـscreenshots.
struct RootView: View {
    @EnvironmentObject private var enrollment: EnrollmentManager
    @StateObject private var router = DeepLinkRouter()
    @State private var selectedTab: String
    @State private var deepLink: DeepLinkTarget?
    @State private var notifDebug = ""

    init() {
        let args = ProcessInfo.processInfo.arguments
        if let i = args.firstIndex(of: "-tab"), i + 1 < args.count {
            _selectedTab = State(initialValue: args[i + 1])
        } else {
            _selectedTab = State(initialValue: "home")
        }
        var dl: DeepLinkTarget?
        if let i = args.firstIndex(of: "-deepLink"), i + 1 < args.count, let u = URL(string: args[i + 1]) {
            dl = DeepLinkTarget.parse(u)
        }
        _deepLink = State(initialValue: dl)
    }

    var body: some View {
        let api = enrollment.api ?? JarvisAPI(baseURL: JarvisConfig.baseURL, sessionToken: JarvisConfig.injectedSessionToken ?? "")
        Group {
            if let dl = deepLink {
                NavigationStack {
                    deepLinkView(dl, api: api)
                        .toolbar {
                            ToolbarItem(placement: .primaryAction) {
                                Button("إغلاق") { deepLink = nil }
                            }
                        }
                }
            } else {
                tabs(api)
            }
        }
        #if os(iOS)
        .onAppear {
            // ضغطة إشعار عند التطبيق المقتول (cold start) — تُلتقط هنا عند الجاهزية.
            if let t = NotificationManager.shared.pendingDeepLink {
                deepLink = t
                NotificationManager.shared.pendingDeepLink = nil
            }
            let args = ProcessInfo.processInfo.arguments
            if args.contains("-requestNotifications") {
                Task { await NotificationManager.shared.requestAuthorization() }
            }
            if let i = args.firstIndex(of: "-scheduleNotification"), i + 1 < args.count,
               let u = URL(string: args[i + 1]), let tg = DeepLinkTarget.parse(u) {
                NotificationManager.shared.schedule(tg, title: "إشعار اختبار", body: "افتح العنصر من الإشعار")
            }
            if args.contains("-showNotifications") {
                Task {
                    await NotificationManager.shared.refreshStatus()
                    notifDebug = "notif status=\(NotificationManager.shared.authorizationStatus.rawValue) pending=\(NotificationManager.shared.pendingCount)"
                }
            }
        }
        .onChange(of: NotificationManager.shared.pendingDeepLink) { t in
            if let t = t { deepLink = t; select(t) }
        }
        .overlay(alignment: .bottom) {
            if !notifDebug.isEmpty {
                Text(notifDebug)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundColor(.white)
                    .padding(8)
                    .background(Color.black.opacity(0.8))
                    .cornerRadius(8)
                    .padding(.bottom, 4)
            }
        }
        #endif
    }

    @ViewBuilder
    private func deepLinkView(_ t: DeepLinkTarget, api: JarvisAPI) -> some View {
        switch t {
        case .conversation(let id): ConversationView(api: api, conversationId: id)
        case .task(let id): TaskDetailView(api: api, taskId: id)
        case .delivery(let id): DeliveryDetailView(api: api, deliveryId: id)
        }
    }

    private func tabs(_ api: JarvisAPI) -> some View {
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
            if let t = t { deepLink = t; select(t) }
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

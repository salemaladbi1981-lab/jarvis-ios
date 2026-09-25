import SwiftUI

#if os(macOS)
/// Desktop companion uses the same authenticated workspace and cinematic Home.
struct MacHomeView: View {
    @EnvironmentObject private var enrollment: EnrollmentManager
    @State private var selectedTab: String? = "home"
    @State private var showConnection = false

    private var api: JarvisAPI {
        enrollment.api ?? JarvisAPI(baseURL: JarvisConfig.baseURL,
                                   sessionToken: JarvisConfig.injectedSessionToken ?? "")
    }

    var body: some View {
        NavigationSplitView {
            VStack(alignment: .leading, spacing: 24) {
                VStack(alignment: .leading, spacing: 5) {
                    Text("JARVIS")
                        .font(.custom("CormorantGaramond-SemiBold", size: 30))
                        .tracking(4)
                        .foregroundColor(JarvisColor.highlight_blue)
                    Text("مساحتك الشخصية")
                        .font(.caption).foregroundColor(JarvisColor.text_muted)
                }
                .padding(.horizontal, 16)
                .padding(.top, 24)

                List(selection: $selectedTab) {
                    Label("الرئيسية", systemImage: "circle.hexagongrid").tag("home")
                    Label("المحادثات", systemImage: "bubble.left.and.bubble.right").tag("chat")
                    Label("الوارد", systemImage: "tray").tag("inbox")
                    Label("المهام", systemImage: "checklist").tag("tasks")
                    Label("التسليمات", systemImage: "doc").tag("deliveries")
                }
                .listStyle(.sidebar)
                .scrollContentBackground(.hidden)

                VStack(alignment: .leading, spacing: 12) {
                    Label("خدمات الأجهزة غير متصلة", systemImage: "link.badge.plus")
                        .font(.caption).foregroundColor(JarvisColor.text_muted)
                    Button { showConnection = true } label: {
                        Label("إعدادات الاتصال", systemImage: "key.horizontal")
                    }
                    .buttonStyle(.plain)
                    .foregroundColor(JarvisColor.highlight_blue)
                }
                .padding(16)
            }
            .background(JarvisColor.bg_0)
            .navigationSplitViewColumnWidth(min: 190, ideal: 225, max: 280)
        } detail: {
            Group {
                switch selectedTab {
                case "chat": ConversationListView(api: api)
                case "inbox": InboxView(api: api)
                case "tasks": TasksView(api: api)
                case "deliveries": DeliveriesView(api: api)
                default: HomeEntryView(api: api)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(JarvisColor.bg_0)
        }
        .tint(JarvisColor.highlight_blue)
        .sheet(isPresented: $showConnection) {
            PairingView().environmentObject(enrollment).frame(width: 460, height: 420)
        }
    }
}
#endif

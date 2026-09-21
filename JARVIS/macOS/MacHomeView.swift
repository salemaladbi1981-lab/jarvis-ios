import SwiftUI
import UniformTypeIdentifiers

/// macOS Home — approved cinematic desktop direction (three-zone):
/// Left: nav + Smart Home + Security + Media
/// Center: JARVIS + Core/orbit + title + greeting + waveform/status + suggestions + voice
/// Right: contextual demo modules (empty for now — no invented live data)
#if os(macOS)
struct MacHomeView: View {
    @StateObject private var vm = HomeViewModel()
    @State private var selectedTab = "home"
    @State private var accessibilityReady = false
    @State private var automationReady = false
    @State private var macOperatorChecked = false
    @State private var showMacFileImporter = false
    @State private var selectedItemMetadataText: String?

    var body: some View {
        HStack(spacing: 0) {
            // LEFT zone — nav + cards
            VStack(spacing: JarvisSpacing.md) {
                macSidebar
                if vm.homeDevices.isEmpty {
                    unavailableCapabilityCard(title: "المنزل الذكي", icon: "house.slash")
                } else {
                    SmartHomeCard(devices: vm.homeDevices)
                        .onTapGesture { vm.requestAction(agentID: "core_home", action: "read-temperature") }
                }

                if let status = vm.securityStatus {
                    SecurityCard(status: status)
                        .onTapGesture { vm.requestAction(agentID: "core_home", action: "unlock-door") }
                } else {
                    unavailableCapabilityCard(title: "الأمان", icon: "shield.slash")
                }

                if let track = vm.mediaTrack {
                    MediaCard(track: track)
                } else {
                    unavailableCapabilityCard(title: "الوسائط", icon: "music.note.slash")
                }

                Spacer()
            }
            .frame(width: 340)
            .padding(JarvisSpacing.lg)
            .background(JarvisColor.bg_0.opacity(0.5))

            // CENTER zone — hero dominant
            ScrollView {
                VStack(spacing: JarvisSpacing.lg) {
                    Text("JARVIS")
                        .font(.custom("CormorantGaramond-SemiBold", size: 30))
                        .tracking(4)
                        .foregroundColor(JarvisColor.highlight_gold)

                    JarvisHeroView(vm: vm, coreSize: 300)

                    JarvisTitleGreetingView()

                    JarvisWaveformStatusView(vm: vm)

                    QuickSuggestions(commands: QuickCommand.productionCases) { cmd in
                            Task { await vm.handleQuickCommand(cmd) }
                        }

                    VoiceInputBar(isListening: vm.isListening) { vm.toggleVoice() }

                    if let approval = vm.pendingApproval {
                        ApprovalCardView(vm: vm, action: approval)
                    }
                }
                .padding(JarvisSpacing.xl)
                .frame(maxWidth: .infinity)
            }

            // RIGHT zone — contextual (empty, no invented live data)
            VStack(spacing: JarvisSpacing.md) {
                Text("جارفس")
                    .font(.custom("IBMPlexSansArabic-Bold", size: 18))
                    .foregroundColor(JarvisColor.text_secondary)

                macOperatorReadinessCard

                Spacer()
            }
            .frame(width: 240)
            .padding(JarvisSpacing.lg)
            .background(JarvisColor.bg_0.opacity(0.3))
        }
        .background(
            LinearGradient(colors: [JarvisColor.bg_0, JarvisColor.bg_1], startPoint: .top, endPoint: .bottom)
                .ignoresSafeArea()
        )
        .fileImporter(
            isPresented: $showMacFileImporter,
            allowedContentTypes: [.item],
            allowsMultipleSelection: false
        ) { result in
            guard case .success(let urls) = result, let url = urls.first else { return }
            Task { await inspectUserSelectedItem(url) }
        }
        .task {
            await vm.load()
            await refreshMacOperatorReadiness()
        }
    }

    private var macOperatorReadinessCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Image(systemName: "desktopcomputer")
                    .foregroundColor(JarvisColor.highlight_gold)
                Text("Mac Operator")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundColor(JarvisColor.text_secondary)
                Spacer()
            }

            permissionRow("Accessibility", ready: accessibilityReady)
            permissionRow("Automation", ready: automationReady)

            HStack {
                Circle()
                    .fill(JarvisColor.text_muted.opacity(0.5))
                    .frame(width: 7, height: 7)
                Text("الملفات: يتطلب اختيارًا صريحًا")
                    .font(.system(size: 11))
                    .foregroundColor(JarvisColor.text_muted)
            }

            Button("فحص ملف مختار") {
                showMacFileImporter = true
            }
            .buttonStyle(.bordered)
            .controlSize(.small)

            if let selectedItemMetadataText {
                Text(selectedItemMetadataText)
                    .font(.system(size: 10))
                    .foregroundColor(JarvisColor.text_secondary)
                    .lineLimit(4)
            }

            Text(macOperatorChecked ? "فحص غير مُطالب بالصلاحيات" : "جارٍ فحص الجاهزية…")
                .font(.system(size: 10))
                .foregroundColor(JarvisColor.text_muted)
        }
        .padding(JarvisSpacing.md)
        .background(
            RoundedRectangle(cornerRadius: JarvisRadius.card)
                .fill(JarvisColor.bg_1.opacity(0.36))
        )
        .overlay(
            RoundedRectangle(cornerRadius: JarvisRadius.card)
                .stroke(JarvisColor.primary_gold.opacity(0.18), lineWidth: 1)
        )
    }

    private func permissionRow(_ label: String, ready: Bool) -> some View {
        HStack {
            Circle()
                .fill(ready ? JarvisColor.success : JarvisColor.text_muted.opacity(0.5))
                .frame(width: 7, height: 7)
            Text("\(label): \(ready ? "جاهز" : "غير ممنوح")")
                .font(.system(size: 11))
                .foregroundColor(ready ? JarvisColor.text_secondary : JarvisColor.text_muted)
            Spacer()
        }
    }

    private func inspectUserSelectedItem(_ url: URL) async {
        let adapter = UserSelectedFileMacOperatorAdapter()
        await adapter.registerUserSelectedURL(url)

        let service = MacOperatorService(
            permissionProvider: adapter,
            executor: adapter
        )
        let request = MacOperatorRequest(
            action: .inspectSelectedItemMetadata,
            target: url.standardizedFileURL.path
        )
        let result = await service.perform(request, ownerApproval: nil)

        switch result {
        case .execution(.metadata(let metadata)):
            let kind = metadata.isDirectory ? "مجلد" : "ملف"
            let size = metadata.sizeBytes.map { "\($0) bytes" } ?? "الحجم غير متاح"
            selectedItemMetadataText = "\(kind) • \(size)\n\(metadata.path)"
        case .authorizationBlocked:
            selectedItemMetadataText = "تم حظر القراءة: الاختيار أو الصلاحية غير مثبتة"
        case .execution(.blocked(let reason)):
            selectedItemMetadataText = "تعذر الفحص: \(reason)"
        case .execution(.completed):
            selectedItemMetadataText = "اكتمل الفحص"
        }
    }

    private func refreshMacOperatorReadiness() async {
        let provider = SystemMacOperatorPermissionProvider()
        let accessibilityRequest = MacOperatorRequest(
            action: .accessibilityInteraction,
            target: "frontmost-app"
        )
        let automationRequest = MacOperatorRequest(
            action: .appleEventAutomation,
            target: "com.apple.Finder"
        )

        let accessibility = await provider.grantedPermissions(for: accessibilityRequest)
        let automation = await provider.grantedPermissions(for: automationRequest)

        accessibilityReady = accessibility.contains(.accessibility)
        automationReady = automation.contains(.automation)
        macOperatorChecked = true
    }

    private var macSidebar: some View {
        VStack(spacing: 6) {
            ForEach(["home", "devices", "car", "more"], id: \.self) { id in
                let (label, icon) = sideItem(id)
                Button {
                    selectedTab = id
                } label: {
                    HStack(spacing: JarvisSpacing.md) {
                        Image(systemName: icon)
                            .font(.system(size: 15))
                            .frame(width: 20)
                        Text(label)
                            .font(.system(size: 14))
                        Spacer()
                    }
                    .foregroundColor(selectedTab == id ? JarvisColor.highlight_gold : JarvisColor.text_muted)
                    .padding(.horizontal, JarvisSpacing.md)
                    .padding(.vertical, JarvisSpacing.sm)
                    .background(
                        RoundedRectangle(cornerRadius: JarvisRadius.control)
                            .fill(selectedTab == id ? JarvisColor.primary_gold.opacity(0.12) : .clear)
                    )
                }
                .buttonStyle(.plain)
                .accessibilityLabel(label)
            }
            Spacer()
        }
    }

    private func unavailableCapabilityCard(title: String, icon: String) -> some View {
        HStack(spacing: JarvisSpacing.md) {
            Image(systemName: icon)
                .font(.system(size: 18, weight: .medium))
                .foregroundColor(JarvisColor.text_muted)
                .frame(width: 28)

            VStack(alignment: .leading, spacing: 3) {
                Text(title)
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundColor(JarvisColor.text_secondary)
                Text("غير متصل")
                    .font(.system(size: 12))
                    .foregroundColor(JarvisColor.text_muted)
            }

            Spacer()
        }
        .padding(JarvisSpacing.md)
        .background(
            RoundedRectangle(cornerRadius: JarvisRadius.card)
                .fill(JarvisColor.bg_1.opacity(0.36))
        )
        .overlay(
            RoundedRectangle(cornerRadius: JarvisRadius.card)
                .stroke(JarvisColor.text_muted.opacity(0.14), lineWidth: 1)
        )
    }

    private func sideItem(_ id: String) -> (String, String) {
        switch id {
        case "home":    return ("الرئيسية", JarvisIconResolver.symbol(for: "nav.home"))
        case "devices": return ("الأجهزة", JarvisIconResolver.symbol(for: "nav.devices"))
        case "car":     return ("السيارة", JarvisIconResolver.symbol(for: "nav.car"))
        default:        return ("المزيد", JarvisIconResolver.symbol(for: "nav.more"))
        }
    }
}
#endif

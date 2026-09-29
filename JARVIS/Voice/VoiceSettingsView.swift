import SwiftUI

/// إعدادات صوت جارفس — يختار د. سالم من 10 أصوات رجولية.
/// الاختيار يُحفظ في UserDefaults (jarvis.tts.voice) ويُطبَّق عند بدء محادثة صوتية جديدة.
struct VoiceSettingsView: View {
    @AppStorage(VoiceCatalog.storeKey) private var selectedKey: String = VoiceCatalog.defaultKey
    @AppStorage(ModelCatalog.storeKey) private var selectedModel: String = ModelCatalog.defaultKey
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List {
                Section {
                    ForEach(VoiceCatalog.all) { voice in
                        Button {
                            selectedKey = voice.key
                        } label: {
                            HStack {
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(voice.nameAr)
                                        .font(.system(size: 16, weight: .semibold))
                                    Text(voice.desc)
                                        .font(.system(size: 12))
                                        .foregroundColor(.secondary)
                                }
                                Spacer()
                                if voice.key == selectedKey {
                                    Image(systemName: "checkmark.circle.fill")
                                        .foregroundColor(.accentColor)
                                }
                            }
                            .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                    }
                } header: {
                    Text("صوت جارفس")
                } footer: {
                    Text("يُطبَّق الصوت المختار عند بدء محادثة صوتية جديدة.")
                }

                Section {
                    ForEach(ModelCatalog.all) { model in
                        Button {
                            selectedModel = model.key
                        } label: {
                            HStack {
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(model.nameAr)
                                        .font(.system(size: 16, weight: .semibold))
                                    Text(model.desc)
                                        .font(.system(size: 12))
                                        .foregroundColor(.secondary)
                                }
                                Spacer()
                                if model.key == selectedModel {
                                    Image(systemName: "checkmark.circle.fill")
                                        .foregroundColor(.accentColor)
                                }
                            }
                            .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                    }
                } header: {
                    Text("جودة الصوت (النموذج)")
                } footer: {
                    Text("الأعلى جودة أوضح لكن أبطأ قليلاً؛ الأسرع أخف زمن استجابة.")
                }
            }
            .navigationTitle("الصوت")
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("تم") { dismiss() }
                }
            }
        }
        .environment(\.layoutDirection, .rightToLeft)
    }
}

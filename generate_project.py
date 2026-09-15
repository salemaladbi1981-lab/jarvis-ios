#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate JARVIS.xcodeproj/project.pbxproj with CORRECT group-relative
PBXFileReference paths (basename only — relative to immediate parent group)."""
import os, random, string

def uid():
    return ''.join(random.choices(string.hexdigits.upper(), k=24))

APP_SOURCES = [
    "JARVIS/App/JARVISApp.swift", "JARVIS/App/ContentView.swift",
    "JARVIS/Home/HomeView.swift", "JARVIS/Home/HomeViewModel.swift",
    "JARVIS/Home/HeaderView.swift", "JARVIS/Home/QuickSuggestions.swift",
    "JARVIS/Home/VoiceInputBar.swift", "JARVIS/Home/BottomNavBar.swift",
    "JARVIS/Core/JarvisCoreView.swift", "JARVIS/Core/JarvisOrbitView.swift", "JARVIS/Core/WaveformView.swift",
    "JARVIS/Core/JarvisHeroView.swift", "JARVIS/Core/ApprovalCardView.swift",
    "JARVIS/iPad/iPadLandscapeView.swift", "JARVIS/iPad/AdaptiveRootView.swift",
    "JARVIS/macOS/MacApp.swift", "JARVIS/macOS/MacHomeView.swift",
    "JARVIS/Voice/VoiceSession.swift", "JARVIS/Voice/RealtimeVoiceSession.swift",
    "JARVIS/Integrations/EventKitModels.swift", "JARVIS/Integrations/AppleEventKitProvider.swift",
    "JARVIS/Integrations/MockCalendarProvider.swift", "JARVIS/Integrations/CalendarTools.swift",
    "JARVIS/Cards/Cards.swift",
    "JARVIS/State/JarvisState.swift",
    "JARVIS/Agents/AgentRegistry.swift", "JARVIS/Agents/AgentStore.swift",
    "JARVIS/DesignSystem/JarvisTokens.swift", "JARVIS/DesignSystem/JarvisIconResolver.swift",
    "JARVIS/Providers/ApprovalPolicyEvaluator.swift",
    "JARVIS/Mocks/MockProviders.swift", "JARVIS/Mocks/MockData.swift",
]
APP_RESOURCES = [
    "JARVIS/Assets/Fonts/IBMPlexSansArabic-Regular.ttf",
    "JARVIS/Assets/Fonts/IBMPlexSansArabic-Bold.ttf",
    "JARVIS/Assets/Fonts/CormorantGaramond-SemiBold.ttf",
    "JARVIS/Resources/AGENT-REGISTRY.json",
    "JARVIS/Resources/DESIGN-TOKENS.json",
]
TEST_SOURCES = [
    "JARVISTests/ApprovalPolicyEvaluatorTests.swift",
    "JARVISTests/HomeViewModelTests.swift",
    "JARVISTests/AgentRegistryTests.swift",
]

objs = {}
def add(isa, **kw):
    i = uid(); kw["isa"] = isa; objs[i] = kw; return i

# basename only — relative to immediate parent group
def file_ref(fullpath, last_known_type):
    return add("PBXFileReference", path=os.path.basename(fullpath),
               lastKnownFileType=last_known_type, sourceTree="<group>")

def group(children, name, path):
    return add("PBXGroup", children=children, name=name, path=path, sourceTree="<group>")

app_src_refs = {p: file_ref(p, "sourcecode.swift") for p in APP_SOURCES}
app_res_refs = {p: file_ref(p, "sourcecode.fonts" if p.endswith(".ttf") else "text.json") for p in APP_RESOURCES}
test_refs = {p: file_ref(p, "sourcecode.swift") for p in TEST_SOURCES}
plist_ref = file_ref("JARVIS/Info.plist", "text.plist.xml")
app_prod_ref = add("PBXFileReference", explicitFileType="wrapper.application", includeInIndex=0, path="JARVIS.app", sourceTree="BUILT_PRODUCTS_DIR")
mac_prod_ref = add("PBXFileReference", explicitFileType="wrapper.application", includeInIndex=0, path="JARVIS Mac.app", sourceTree="BUILT_PRODUCTS_DIR")
test_prod_ref = add("PBXFileReference", explicitFileType="wrapper.cfbundle", includeInIndex=0, path="JARVISTests.xctest", sourceTree="BUILT_PRODUCTS_DIR")

app_src_bf = {p: add("PBXBuildFile", fileRef=app_src_refs[p]) for p in APP_SOURCES}
app_res_bf = {p: add("PBXBuildFile", fileRef=app_res_refs[p]) for p in APP_RESOURCES}
test_bf = {p: add("PBXBuildFile", fileRef=test_refs[p]) for p in TEST_SOURCES}

def subgroup(name, paths):
    refs = [app_src_refs[p] for p in paths]
    return group(sorted(refs), name, name)

groups = {}
groups["App"] = subgroup("App", [p for p in APP_SOURCES if "/App/" in p])
groups["Home"] = subgroup("Home", [p for p in APP_SOURCES if "/Home/" in p])
groups["Core"] = subgroup("Core", [p for p in APP_SOURCES if "/Core/" in p])
groups["Cards"] = subgroup("Cards", [p for p in APP_SOURCES if "/Cards/" in p])
groups["State"] = subgroup("State", [p for p in APP_SOURCES if "/State/" in p])
groups["Agents"] = subgroup("Agents", [p for p in APP_SOURCES if "/Agents/" in p])
groups["DesignSystem"] = subgroup("DesignSystem", [p for p in APP_SOURCES if "/DesignSystem/" in p])
groups["Providers"] = subgroup("Providers", [p for p in APP_SOURCES if "/Providers/" in p])
groups["Mocks"] = subgroup("Mocks", [p for p in APP_SOURCES if "/Mocks/" in p])
groups["iPad"] = subgroup("iPad", [p for p in APP_SOURCES if "/iPad/" in p])
groups["macOS"] = subgroup("macOS", [p for p in APP_SOURCES if "/macOS/" in p])
groups["Voice"] = subgroup("Voice", [p for p in APP_SOURCES if "/Voice/" in p])
groups["Integrations"] = subgroup("Integrations", [p for p in APP_SOURCES if "/Integrations/" in p])

font_refs = [app_res_refs[p] for p in APP_RESOURCES if "Fonts" in p]
json_refs = [app_res_refs[p] for p in APP_RESOURCES if "Resources" in p]
icons_readme = file_ref("JARVIS/Assets/Icons/README.md", "net.daringfireball.markdown")
fonts_group = group(sorted(font_refs), "Fonts", "Fonts")
icons_group = group([icons_readme], "Icons", "Icons")
assets_group = group([fonts_group, icons_group], "Assets", "Assets")
resources_group = group(sorted(json_refs), "Resources", "Resources")

jarvis_group = group(
    [groups["App"], groups["Home"], groups["Core"], groups["Cards"],
     groups["State"], groups["Agents"], groups["DesignSystem"],
     groups["Providers"], groups["Mocks"], groups["iPad"], groups["macOS"], groups["Voice"], groups["Integrations"], assets_group, resources_group, plist_ref],
    "JARVIS", "JARVIS"
)
tests_group = group(sorted(test_refs.values()), "JARVISTests", "JARVISTests")
products_group = group([app_prod_ref, mac_prod_ref, test_prod_ref], "Products", None)
main_group = add("PBXGroup", children=[jarvis_group, tests_group, products_group], sourceTree="<group>")

app_sources_phase = add("PBXSourcesBuildPhase", files=sorted(app_src_bf.values()), buildActionMask=2147483647, runOnlyForDeploymentPostprocessing=0)
app_resources_phase = add("PBXResourcesBuildPhase", files=sorted(app_res_bf.values()), buildActionMask=2147483647, runOnlyForDeploymentPostprocessing=0)
app_frameworks_phase = add("PBXFrameworksBuildPhase", files=[], buildActionMask=2147483647, runOnlyForDeploymentPostprocessing=0)
test_sources_phase = add("PBXSourcesBuildPhase", files=sorted(test_bf.values()), buildActionMask=2147483647, runOnlyForDeploymentPostprocessing=0)
test_resources_phase = add("PBXResourcesBuildPhase", files=[], buildActionMask=2147483647, runOnlyForDeploymentPostprocessing=0)
test_frameworks_phase = add("PBXFrameworksBuildPhase", files=[], buildActionMask=2147483647, runOnlyForDeploymentPostprocessing=0)

app_settings = {
    "CODE_SIGN_STYLE": "Automatic", "CURRENT_PROJECT_VERSION": "1",
    "GENERATE_INFOPLIST_FILE": "NO", "INFOPLIST_FILE": "JARVIS/Info.plist",
    "IPHONEOS_DEPLOYMENT_TARGET": "17.0", "MARKETING_VERSION": "0.1.0",
    "PRODUCT_BUNDLE_IDENTIFIER": "com.salemai.jarvis", "PRODUCT_NAME": "$(TARGET_NAME)",
    "SDKROOT": "iphoneos", "SWIFT_VERSION": "5.0", "TARGETED_DEVICE_FAMILY": "1,2",
    "LD_RUNPATH_SEARCH_PATHS": "$(inherited) @executable_path/Frameworks",
}
test_settings = {
    "BUNDLE_LOADER": "$(TEST_HOST)", "CODE_SIGN_STYLE": "Automatic",
    "CURRENT_PROJECT_VERSION": "1", "GENERATE_INFOPLIST_FILE": "YES",
    "IPHONEOS_DEPLOYMENT_TARGET": "17.0", "MARKETING_VERSION": "0.1.0",
    "PRODUCT_BUNDLE_IDENTIFIER": "com.salemai.jarvisTests", "PRODUCT_NAME": "$(TARGET_NAME)",
    "SDKROOT": "iphoneos", "SWIFT_VERSION": "5.0", "TARGETED_DEVICE_FAMILY": "1,2",
    "TEST_HOST": "$(BUILT_PRODUCTS_DIR)/JARVIS.app/JARVIS",
}
mac_settings = {
    "CODE_SIGN_STYLE": "Automatic", "CURRENT_PROJECT_VERSION": "1",
    "GENERATE_INFOPLIST_FILE": "YES", "MACOSX_DEPLOYMENT_TARGET": "14.0",
    "MARKETING_VERSION": "0.1.0", "PRODUCT_BUNDLE_IDENTIFIER": "com.salemai.jarvis.mac",
    "PRODUCT_NAME": "JARVIS Mac", "SDKROOT": "macosx", "SWIFT_VERSION": "5.0",
    "ENABLE_HARDENED_RUNTIME": "YES",
}
proj_common = {"MACOSX_DEPLOYMENT_TARGET": "14.0", "IPHONEOS_DEPLOYMENT_TARGET": "17.0", "SDKROOT": "macosx", "CLANG_ENABLE_MODULES": "YES"}
app_debug = add("XCBuildConfiguration", buildSettings=dict(app_settings), name="Debug")
app_release = add("XCBuildConfiguration", buildSettings=dict(app_settings), name="Release")
test_debug = add("XCBuildConfiguration", buildSettings=dict(test_settings), name="Debug")
test_release = add("XCBuildConfiguration", buildSettings=dict(test_settings), name="Release")
proj_debug = add("XCBuildConfiguration", buildSettings=dict(proj_common, SWIFT_OPTIMIZATION_LEVEL="-Onone", SWIFT_ACTIVE_COMPILATION_CONDITIONS="DEBUG"), name="Debug")
proj_release = add("XCBuildConfiguration", buildSettings=dict(proj_common, SWIFT_OPTIMIZATION_LEVEL="-O"), name="Release")

mac_debug = add("XCBuildConfiguration", buildSettings=dict(mac_settings), name="Debug")
mac_release = add("XCBuildConfiguration", buildSettings=dict(mac_settings), name="Release")
app_config_list = add("XCConfigurationList", buildConfigurations=[app_debug, app_release], defaultConfigurationIsVisible=0, defaultConfigurationName="Release")
mac_config_list = add("XCConfigurationList", buildConfigurations=[mac_debug, mac_release], defaultConfigurationIsVisible=0, defaultConfigurationName="Release")
test_config_list = add("XCConfigurationList", buildConfigurations=[test_debug, test_release], defaultConfigurationIsVisible=0, defaultConfigurationName="Release")
proj_config_list = add("XCConfigurationList", buildConfigurations=[proj_debug, proj_release], defaultConfigurationIsVisible=0, defaultConfigurationName="Release")

app_target = add("PBXNativeTarget", buildConfigurationList=app_config_list,
    buildPhases=[app_sources_phase, app_frameworks_phase, app_resources_phase],
    buildRules=[], dependencies=[], name="JARVIS", productName="JARVIS",
    productReference=app_prod_ref, productType="com.apple.product-type.application")

mac_target = add("PBXNativeTarget", buildConfigurationList=mac_config_list,
    buildPhases=[app_sources_phase, app_frameworks_phase, app_resources_phase],
    buildRules=[], dependencies=[], name="JARVIS Mac", productName="JARVIS Mac",
    productReference=mac_prod_ref, productType="com.apple.product-type.application")

dep_proxy = add("PBXContainerItemProxy", containerPortal=None, proxyType=1, remoteGlobalIDString=app_target, remoteInfo="JARVIS")
dep = add("PBXTargetDependency", target=app_target, targetProxy=dep_proxy)

test_target = add("PBXNativeTarget", buildConfigurationList=test_config_list,
    buildPhases=[test_sources_phase, test_frameworks_phase, test_resources_phase],
    buildRules=[], dependencies=[dep], name="JARVISTests", productName="JARVISTests",
    productReference=test_prod_ref, productType="com.apple.product-type.bundle.unit-test")

proj = add("PBXProject", attributes={"LastUpgradeCheck": "1500"},
    buildConfigurationList=proj_config_list, compatibilityVersion="Xcode 14.0",
    developmentRegion="en", hasScannedForEncodings=0, knownRegions=["en", "Base"],
    mainGroup=main_group, productRefGroup=products_group, projectDirPath="", projectRoot="",
    targets=[app_target, mac_target, test_target])
objs[dep_proxy]["containerPortal"] = proj

os.makedirs("JARVIS.xcodeproj", exist_ok=True)

def fmt(v):
    if isinstance(v, str):
        return '"' + v.replace('\\', '\\\\').replace('"', '\\"') + '"'
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        return "(" + ", ".join(fmt(x) for x in v) + ")"
    if isinstance(v, dict):
        return "{" + " ".join(f"{k} = {fmt(val)};" for k, val in sorted(v.items())) + "}"
    return str(v)

lines = ["// !$*UTF8*$!", "{", "\tarchiveVersion = 1;", "\tclasses = {};", "\tobjectVersion = 56;", "\tobjects = {"]
for i in sorted(objs.keys()):
    lines.append(f"\t\t{i} = {fmt(objs[i])};")
lines.append("\t};")
lines.append(f"\trootObject = {proj};")
lines.append("}")
open("JARVIS.xcodeproj/project.pbxproj", "w", encoding="utf-8").write("\n".join(lines) + "\n")
print(f"Wrote pbxproj ({len(objs)} objects) — file refs are basename-only (group-relative)")

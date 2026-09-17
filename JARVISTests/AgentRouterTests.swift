//
//  AgentRouterTests.swift — verifies AgentRouter routing for the six routable
//  agent IDs (core_writer, core_home, sys_server, ct_scriptwriter,
//  ct_prompteng) plus unknown-intent fallback to core_coordinator.
//  Includes Arabic and English examples where practical.
//
import XCTest
@testable import JARVIS

final class AgentRouterTests: XCTestCase {

    // MARK: - core_writer (copywriting / captions / drafts)

    func testRouteWriterEnglishCaption() {
        XCTAssertEqual(AgentRouter.route("write a caption for this post"), "core_writer")
    }

    func testRouteWriterEnglishBlogDraft() {
        XCTAssertEqual(AgentRouter.route("draft a short blog about coffee"), "core_writer")
    }

    func testRouteWriterArabicArticle() {
        XCTAssertEqual(AgentRouter.route("اكتب مقالاً قصيراً عن القهوة"), "core_writer")
    }

    func testRouteWriterArabicDraft() {
        XCTAssertEqual(AgentRouter.route("جهّز مسودة للنص الكتابي"), "core_writer")
    }

    // MARK: - core_home (smart home: temperature, lights, doors, scenes)

    func testRouteHomeEnglishTemperature() {
        XCTAssertEqual(AgentRouter.route("set the temperature to 22"), "core_home")
    }

    func testRouteHomeEnglishLights() {
        XCTAssertEqual(AgentRouter.route("turn off the lights in the kitchen"), "core_home")
    }

    func testRouteHomeArabicTemperature() {
        XCTAssertEqual(AgentRouter.route("اضبط الحرارة على اثنتين وعشرين"), "core_home")
    }

    func testRouteHomeArabicLight() {
        XCTAssertEqual(AgentRouter.route("أطفئ الإضاءة في غرفة المعيشة"), "core_home")
    }

    func testRouteHomeArabicDoor() {
        XCTAssertEqual(AgentRouter.route("افتح الباب الأمامي"), "core_home")
    }

    // MARK: - sys_server (server / infrastructure / status / deploy)

    func testRouteServerEnglishStatus() {
        XCTAssertEqual(AgentRouter.route("check the backend server status"), "sys_server")
    }

    func testRouteServerEnglishDeploy() {
        XCTAssertEqual(AgentRouter.route("deploy the new integration"), "sys_server")
    }

    func testRouteServerArabicHealth() {
        XCTAssertEqual(AgentRouter.route("تحقق من صحة الخادم"), "sys_server")
    }

    // MARK: - ct_scriptwriter (scripts / dialogue / storyboards)

    func testRouteScriptwriterEnglishDialogue() {
        XCTAssertEqual(AgentRouter.route("write dialogue for a 30s hook"), "ct_scriptwriter")
    }

    func testRouteScriptwriterEnglishStoryboard() {
        XCTAssertEqual(AgentRouter.route("build a storyboard for the ad"), "ct_scriptwriter")
    }

    func testRouteScriptwriterArabicScenario() {
        XCTAssertEqual(AgentRouter.route("اكتب سيناريو للإعلان"), "ct_scriptwriter")
    }

    func testRouteScriptwriterArabicDialogue() {
        XCTAssertEqual(AgentRouter.route("أعد صياغة الحوار في المشهد"), "ct_scriptwriter")
    }

    // MARK: - ct_prompteng (prompts for image / video / audio generation)

    func testRoutePromptengEnglishMidjourney() {
        XCTAssertEqual(AgentRouter.route("craft a midjourney prompt for a sunset"), "ct_prompteng")
    }

    func testRoutePromptengEnglishSora() {
        XCTAssertEqual(AgentRouter.route("write a sora video prompt"), "ct_prompteng")
    }

    func testRoutePromptengArabicImageGeneration() {
        XCTAssertEqual(AgentRouter.route("توليد صورة لغروب الشمس"), "ct_prompteng")
    }

    func testRoutePromptengArabicPrompt() {
        XCTAssertEqual(AgentRouter.route("اكتب برومبت لتوليد فيديو"), "ct_prompteng")
    }

    // MARK: - Unknown intent → core_coordinator (default)

    func testRouteUnknownEnglishFallback() {
        XCTAssertEqual(AgentRouter.route("what's the meaning of life?"), "core_coordinator")
    }

    func testRouteUnknownArabicFallback() {
        XCTAssertEqual(AgentRouter.route("ما هو معنى الحياة؟"), "core_coordinator")
    }

    func testRouteEmptyStringFallback() {
        XCTAssertEqual(AgentRouter.route(""), "core_coordinator")
    }

    func testRouteWhitespaceOnlyFallback() {
        XCTAssertEqual(AgentRouter.route("    \n  "), "core_coordinator")
    }

    // MARK: - Routing precedence (first match in declared order wins)

    /// "scene" appears in both core_home and ct_scriptwriter keyword sets;
    /// core_home is declared first, so a bare smart-home scene request
    /// must route to core_home, not ct_scriptwriter.
    func testRoutePrecedenceSceneGoesHomeFirst() {
        XCTAssertEqual(AgentRouter.route("activate the home scene"), "core_home")
    }

    /// A clearly cinematic scene (storyboard) should still hit ct_scriptwriter,
    /// confirming the scriptwriter route is reachable for non-home phrasing.
    func testRoutePrecedenceCinematicSceneStillScriptwriter() {
        XCTAssertEqual(AgentRouter.route("draft a storyboard scene"), "ct_scriptwriter")
    }

    // MARK: - routableAgentIDs sanity

    func testRoutableAgentIDsContainsAllExpected() {
        let expected: Set<String> = [
            "core_coordinator",
            "core_writer",
            "core_home",
            "sys_server",
            "ct_scriptwriter",
            "ct_prompteng",
        ]
        XCTAssertEqual(AgentRouter.routableAgentIDs, expected)
    }

    func testDefaultAgentIDIsCoordinator() {
        XCTAssertEqual(AgentRouter.defaultAgentID, "core_coordinator")
    }
}

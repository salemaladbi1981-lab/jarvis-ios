# Reconciliation Report — UPG-2 + Phase A/B/C (source ↔ live)

التاريخ: 2026-09-19. النتيجة: **RECONCILIATION: PASS** — source أصبح superset وظيفي للـ live.

## المنهج
مقارنة SHA256 لكل ملف live مقابل source، ثم merge واعٍ (احتفاظ بسلوك live + إعادة تطبيق UPG-2/Phase) — لا نسخ أعمى.

## Provenance لكل ملف متباعد (14 CHANGED)

| الملف | من live | من source | من UPG-2 | التعارض وحلّه |
|---|---|---|---|---|
| tools.py | ✅ كاملًا (risk_class/contract/all_contracts/bypass_approval) | — | — | source كان نموذجًا أبسط (رجعة) → **اعتمدنا live** |
| orchestrator.py | ✅ كاملًا (classify/ROUTES/_tool_for/handle(text)) | — | — | source قديم → **اعتمدنا live** |
| approval.py | ✅ DESTRUCTIVE_PATTERNS (deny-by-default للتخريبي) | ✅ ApprovalStore positional | ✅ workspace_id/task_id/persistence/is_approved/workspace_mismatch | source أسقط DESTRUCTIVE_PATTERNS → **أعدناها فوق UPG-2** |
| audit.py | ✅ 7 دوال مساعدة (request_received/route_selected/…) | ✅ log + verify (hash chain) | ✅ سلسلة hash + verify | source أسقط الدوال المساعدة → **أعدناها** |
| brain_tools.py | — | ✅ | ✅ identity + memory + audit (superset) | لا تعارض |
| auth.py | — | ✅ | ✅ workspace_id + resolve_session (superset) | لا تعارض |
| config.py | — | ✅ | ✅ JARVIS_HERMES_PROFILE | أضفنا fallback يدوي لتحميل .env بلا python-dotenv |
| deliveries.py | — | ✅ | ✅ workspace_id عزل | لا تعارض |
| files_api.py | — | ✅ | ✅ workspace_id عزل | لا تعارض |
| tasks.py | — | ✅ | ✅ workspace_id عزل | لا تعارض |
| main.py | — | ✅ | ✅ workspace + kill_switch + get_workspace | لا تعارض |
| realtime.py | — | ✅ | ✅ 9 مجموعات أدوات (فوق 6 live) | لا تعارض |
| tests_maps.py | — | ✅ | ✅ | لا تعارض |
| requirements.txt | — | ✅ | ✅ | لا تعارض |

## إصلاحات source أثناء التسوية
1. **agent_runner.py** — إصلاح تظليل المتغير `prof` (كان يُعيّن profile dict ثم يُستبدل باسم profile) → سبّب «string indices must be integers». أُعيدت التسمية إلى `profile_name`.
2. **config.py** — fallback يدوي لتحميل `.env` بدون python-dotenv (بيئات الاختبار).

## ملفات orphan (live-only) — لا تُنشر، تبقى على live
`.env`, `.env.bak-*`, `.gitignore`, `audit.jsonl` (artifacts وقت التشغيل) · `run.sh` (سكربت تشغيل live) · `live_test_harness.py`, `tests.py`, `tests_barge_in.py`, `tests_m34.py` (اختبارات قديمة حلّت محلها tests_*.py الفردية) · `safe_tools.py` (أثر live).

## هل source أصبح superset وظيفي للـ live؟ **نعم**
- tools.py + orchestrator.py = مطابقان لـ live (32 ملفًا identical).
- الـ 12 المتبقية المختلفة = live + UPG-2 (إضافات فوق سلوك live الحالي، لا حذف).
- الـ 30 NEW = وحدات UPG-2/Phase.
- لا سلوك live مفقود: classify/risk_class/bypass_approval/contract/all_contracts/ROUTES/DESTRUCTIVE_PATTERNS/دوال audit — كلها محفوظة.

## نتائج الاختبارات (كاملة PASS/FAIL/SKIP)
| suite | النتيجة |
|---|---|
| tests_agents (Phase C) | **16/16 PASS** ✅ |
| tests_capabilities (Phase B) | 9/9 PASS |
| tests_memory + tests_memory_isolation (Phase A) | 5/5 + 23/23 PASS |
| tests_tool_guard | 9/9 PASS |
| tests_approval_audit | 12/12 PASS |
| tests_workspace + tests_workspace_http | 19/19 + 9/9 PASS |
| tests_config_language | 6/6 PASS |
| tests_auth | 9/9 PASS |
| tests_security / upload_auth / enrollment | 12/12 + 9/9 + 6/6 PASS |
| tests_maps / voice_stability / realtime_tools | 17/17 + 16/16 + 25/25 PASS |
| tests_phaseD | 13/13 PASS |
| tests_instagram / microsoft / multi_email / telegram / youtube | 11 + 13 + 29 + 26 + 19 PASS |

**لا FAIL ولا SKIP.**

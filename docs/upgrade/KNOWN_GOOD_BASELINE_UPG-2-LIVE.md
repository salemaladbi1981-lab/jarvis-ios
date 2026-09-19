# KNOWN GOOD BASELINE — UPG-2-LIVE

التاريخ: 2026-09-19. هذه نقطة الرجوع الرسمية لأي مرحلة لاحقة (UPG-3 فما بعد).

## الهوية
| البند | القيمة |
|---|---|
| LIVE SOURCE SHA | `0d6eb831369ee0d665fd1c9957b14139b2a490d1` |
| TAG | `UPG-2-LIVE` (annotated، مرفوع إلى remote — peeled commit = 0d6eb83) |
| branch | `feat/master-build-v1` |
| LIVE FINGERPRINT | `b4fc08283d8443b9` (SHA256 لمانيفست 84 ملفًا) |
| DEPLOYMENT | PASS · ACCEPTANCE 23/23 · REGRESSIONS NONE · ROLLBACK NOT REQUIRED |

## المراجع (كلها محفوظة في المستودع)
- **post-deploy manifest**: `docs/upgrade/live_fingerprint_POSTDEPLOY_20260919.json` (84 ملفًا SHA256)
- **reconciliation report**: `docs/upgrade/RECONCILIATION_REPORT.md`
- **one-shot deployment plan**: `docs/upgrade/ONE_SHOT_DEPLOYMENT_PLAN.md`
- **pre-deploy baseline manifest**: `docs/upgrade/live_fingerprint_20260919.json` (+ `.md`)
- **rollback backup**: `/opt/data/workspace/jarvis-native/deploy-backup-20260919-121929/` (51 ملفًا pre-deploy)

## ما أُغلق
- **UPG-0** (تثبيت المصدر) · **UPG-1** (استقرار: صوت/موقع/لغة) · **UPG-2** (صلاحيات/ذاكرة/عزل + Restricted Profile enforcement) — **CLOSED**.

## الحالة الأمنية/التشغيلية المثبتة على live
- Restricted Profile `jarvis-agent` نشط: terminal/file/code_execution/skills/delegation = blocked؛ web/vision/image_gen فقط.
- multiplexing `[default, jarvis-agent]` + fail-closed (ملف شخصي غير صالح → 404).
- `JARVIS_HERMES_PROFILE=jarvis-agent` في backend `.env`.
- workspace isolation (4 مساحات) + approvals ملزمة + audit hash-chain + kill_switch + tool_guard.
- Phase A (memory) + Phase B (capabilities) + Phase C (agents) = 16/16 و9/9 و5/5+23/23 على live.

## قاعدة
**لا تغيير على الـlive خلال هذه الخطوة.** أي انحراف في مرحلة لاحقة يرجع إلى هذه النقطة حصرًا.

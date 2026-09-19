# Hermes Native Tool Enforcement — فحص المصدر الفعلي (مثبّت بالبصمة)

التاريخ: 2026-09-19.

## النسخة المفحوصة (مثبّتة)

| البند | القيمة |
|---|---|
| Hermes version | **0.21.0** (`pyproject.toml` سطر 5) |
| pyproject.toml SHA256 | `c70c8b52f6cc08a4e65f0fc1713c26814fd4f19811bc7e01de645009b2a76600` |
| api_server.py SHA256 | `6aec6687d47c81b3567e930882a499c5c5c041ecbe40e1d08f93038212401962` |
| api_server.py size/mtime | 362034 bytes / 2026-08-31 19:30:18 UTC |
| git commit | غير متاح (ليس git checkout — لا يوجد `.git` تحت `/opt/hermes`) |
| المسار | `/opt/hermes/gateway/platforms/api_server.py` |

## مسار التنفيذ الذي تتبعته (chat-completions)

1. **تسجيل المسار** — سطر `2247`: `("POST", "/v1/chat/completions", self._handle_chat_completions)`.
2. **الـ handler** — سطر `5046`: `_handle_chat_completions` يقرأ `messages` + `system_prompt` + رؤوس الجلسة (`X-Hermes-Session-Id`/`-Key`).
3. **الاستدعاء** — سطر `5290`-`5299`: `_compute_completion()` → `self._run_agent(user_message=…, ephemeral_system_prompt=…, session_id=…, **agent_overrides, route=…)` — **بلا أي معامل tools**.
4. **توقيع `_run_agent`** — سطر `7247`-`7276`: لا يوجد `tools` / `tool_choice` / `allowed_tools` / `toolset`. (تأكيد عددي: 0 تطابق لهذه الأسماء في التوقيع.)
5. **`tools`/`tool_choice`** — سطر `5310`-`5311`: يظهران **فقط** في `_make_request_fingerprint` (مفتاح idempotency للـ dedup)، لا تُقرأ من الطلب ولا تُنفَّذ.

## نتيجة NOT_SUPPORTED — نطاقها الدقيق

**غير مدعوم في هذه النسخة (0.21.0) على هذا الـ gateway (single-profile):**
- ❌ **per-request tool allowlist عبر `POST /v1/chat/completions`** (قائمة أدوات مسموحة لكل طلب) — لا يوجد معامل ولا قراءة لحقل `tools` ولا فرض.
- ❌ `tool_choice` / `allowed_tools` — لا يُفرض.
- ❌ تعطيل أدوات غير مصرّح بها per-request.
- ❌ interception/gateway قبل تنفيذ الأداة عبر هذا المسار.

**مفصول عنه — آليات تقييد أخرى موجودة في المصدر (وليست بديلًا عن allowlist لكل طلب):**

| الآلية | الحالة |
|---|---|
| `toolsets` (`/v1/toolsets`) | platform-level (ثابتة في config، سطر 4098-4138) — **ليست per-request** |
| Per-profile multiplexing (`/p/<profile>/v1/chat/completions`) | مدعوم في المصدر، لكن هذا الـ gateway **single-profile** (سطر 70-88: أي `/p/<other>/` يُرفض fail-closed) — يتطلب تمكين multiplexing + `multiplex_profile_allowlist` |
| `ephemeral_system_prompt` | prompt-level فقط (تعليمة فوق الـ core) — **ليس enforcement تقنيًا** |

## الحالة الصادقة

- `HERMES_NATIVE_TOOL_ENFORCEMENT` = **NOT_SUPPORTED** (نطاق: allowlist لكل طلب عبر chat-completions في 0.21.0).
- الإنفاذ الحالي = `request-level` (بوابة `enforce()` في agent_runner) + `prompt-level` (ephemeral_system_prompt) + `tool_guard` (حدود تنفيذ أدوات JARVIS الحساسة).
- **لا نعتمد prompt-level بديلًا عن المنع أثناء التنفيذ** — قرار سالم معتمد.

## الإغلاق المعتمد (الخيار 1): Restricted Hermes profile

التفاصيل التنفيذية في `docs/upgrade/RESTRICTED_PROFILE_PLAN.md`. يبقى UPG-2 مفتوحًا حتى اكتمال النشر + اختبارات الإنفاذ.

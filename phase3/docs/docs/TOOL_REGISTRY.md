# JARVIS — Tool Registry (typed contracts)

| tool_id | display_name | owners | risk | approval | timeout | idempotent |
|---|---|---|---|---|---|---|
| read-temperature | قراءة الحرارة | core_home | low | none | 10s | yes |
| read-light-state | قراءة الإضاءة | core_home | low | none | 10s | yes |
| get-service-health | صحة الخدمات | sys_server | low | none | 10s | yes |
| capability-status | حالة القدرات | sys_server | low | none | 10s | yes |
| unlock-door | فتح الباب | core_home | high | action-specific | 10s | no |

## Contract fields (every tool)
tool_id, display_name, owning_agent_ids, description, input_schema,
output_schema, risk_class, approval_rule, timeout_s, retry_policy, idempotent,
cancellable, audit_category.

## Rules
- Structured results only; never infer real success from prose.
- Mock/demo results explicitly flagged `mock: true`.
- High/medium risk tools refuse execution unless approval was resolved
  (gateway `bypass_approval` only set by the trusted backend after approval).

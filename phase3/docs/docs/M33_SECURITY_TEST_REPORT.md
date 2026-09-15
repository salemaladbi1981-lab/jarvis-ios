# JARVIS — M3.3 Security Test Report

## Results (tests.py)
| Check | Result |
|---|---|
| Privileged tool cannot bypass approval (gateway refuses) | PASS |
| Client cannot invoke arbitrary privileged tools | PASS (backend-only) |
| Approval binds to exact action+params | PASS |
| Expired/reused approval denied | PASS |
| Unknown destructive action deny-by-default | PASS |
| No provider secrets in repo source | PASS |

## Model
- Privileged execution lives in the trusted backend; client cannot bypass
  approval, change risk class, or forge approval.
- No permanent provider secret in Apple clients / git / logs.

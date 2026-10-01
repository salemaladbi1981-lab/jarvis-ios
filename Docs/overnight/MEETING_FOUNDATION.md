# Meeting foundation

Shared `JarvisState.swift` defines consent policy, lifecycle/coordinator, transcript segments, evidence-backed summaries/decisions/action items, opaque artifact references and a user/workspace-scoped storage protocol. `MeetingRecord.validate(for:)` rejects cross-scope records, invalid timestamps, duplicate segment IDs and findings without transcript evidence. A storage implementation must authenticate on the server and enforce ownership; these models alone are not an authorization boundary.

Home's meeting toolbar entry opens the same honest unavailable screen on iPhone and Mac. There is no capture provider, recording, seeded transcript, synthetic summary, or implicit local persistence. Silent observer means no spoken interruption, never invisible recording. Consent revocation transitions active capture state to stopped; a future capture adapter must stop the actual platform stream at that transition.

Activation still requires an official capture adapter, platform permissions, visible capture indication, participant consent, authenticated scoped backend storage, retention/deletion behavior, transcript import and evidence-grounded generation. The Meeting Agent must not be advertised as executable before those exist.

Executable regression evidence: `MeetingFoundationTests.swift` (19 policy/lifecycle cases) and `MeetingArtifactTests.swift` (4 serialization/isolation/evidence cases). `Tools/meeting_foundation_test.py` checks the routed unavailable UI and persistence contract.

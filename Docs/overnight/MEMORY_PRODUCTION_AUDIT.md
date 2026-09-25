# Production memory audit — 2026-09-20

## Verified in code and isolated tests

- Production Swift transcript routing does not use `MemoryStore.seeded`, `memoryAnswer`, or a second local spoken response. Seed construction is DEBUG-only.
- `ChatViewModel` uses the authenticated backend conversation path and sends its workspace header.
- Backend chat derives a stable conversation memory namespace from the server-owned conversation. The Hermes request carries that namespace and explicitly identifies the workspace.
- Narrow personal-recall questions (name, previous discussion) read backend memory evidence directly. A miss returns an explicit no-stored-information answer; it does not ask a model to guess.
- `jarvis_recall` reads persisted memory and message records. All conversation-log evidence requires both user and workspace ownership. Owner legacy USER.md and flat memory files are available only in PERSONAL.
- Voice sockets require an enrolled session. Tool identity fields override model arguments using the server-authenticated identity, including workspace and namespace.
- `tests_memory_production.py`: nine executable tests cover isolated real temporary stores, identity forgery, socket authorization, stable namespaces, no seeded fallback, and direct personal-question routing. `tests_memory_isolation.py` also passes.

## Deployment and physical verification still required

These checks verify repository code, not the currently deployed backend or its stored facts. Deploy backend authentication/receipt/memory changes together with the client build before acceptance testing. The client sends the existing enrolled session token; a device without a valid pairing must reconnect through connection settings.

Legacy Hermes `state.db` rows without explicit workspace ownership are deliberately excluded. Migrate those rows only after establishing their provenance. No production memory file, credential, or database was modified during this sprint.

Broader semantic memory questions still use Hermes under the scoped session namespace. The remote Hermes tool implementation and isolation require deployment-side verification; prompt instructions alone are not proof of remote enforcement.

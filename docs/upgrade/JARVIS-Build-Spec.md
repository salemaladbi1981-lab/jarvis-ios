# JARVIS — Build Specification

**Owner:** Dr. Salem Aladbi · **Builder:** Elias (ICES) · **Version:** 1.0 · **Date:** 2026-09-19

This file is the single source of truth for building JARVIS. Every line marked **MUST** is a requirement; every module ends with acceptance tests. Do not add features that are not listed here. If something is unclear, ask Salem before building.

---

## 0. Product definition

JARVIS is one personal AI assistant for one user (Salem). It runs continuously, acts without being prompted, speaks Gulf Arabic and English, and covers work, business, money, legal matters, and daily life.

Non-negotiable principles:

1. **Proactive, not reactive.** JARVIS works overnight and reports; it does not wait to be asked.
2. **Approval before irreversible actions.** Sending, paying, booking, deleting, and signing always require Salem's explicit approval.
3. **One JARVIS, isolated workspaces.** Data from the public-sector job never mixes with private business data.
4. **Never pretends to be human.** Any message JARVIS sends to a third party identifies it as Salem's assistant software.
5. **Arabic first.** Every feature must work fully in Gulf Arabic, voice and text.

---

## 1. Tech stack (fixed — do not substitute without approval)

| Layer | Choice |
| --- | --- |
| Backend | Node.js 22 + TypeScript, Fastify |
| Database | PostgreSQL 16 + pgvector (memory and search) |
| Queue / scheduler | BullMQ on Redis (overnight jobs, triggers) |
| LLM | Anthropic Claude API (tool use + MCP connectors) |
| Local LLM | Ollama on Salem's Mac for the Legal and Finance vaults |
| Mobile app | React Native (Expo), iOS first, Android second |
| Desktop companion | Electron menu-bar app (macOS), writes to `~/Desktop` |
| Speech-to-text | Whisper large-v3 (or equivalent) tuned and tested on Gulf Arabic |
| Text-to-speech | ElevenLabs, one fixed Arabic voice + one English voice |
| Integrations | Gmail, Google Calendar, Google Drive, Microsoft 365, Slack, WhatsApp Business API |
| Hosting | One private VPS (EU or Qatar region), encrypted disk, daily backups |

Reuse the existing Node.js briefing agent (three daily briefings from Gmail, Calendar, weather, social trends) as the starting codebase for Module 1.

---

## 2. Architecture

```
Mobile app ─┐
Desktop app ─┼─► API Gateway ─► Orchestrator ─► Domain Agents ─► Tools (MCP / APIs)
Voice       ─┘                     │
                                   ├─► Memory (Postgres + pgvector)
                                   ├─► Trigger Engine (BullMQ)
                                   └─► Approval Queue ─► push notification to Salem
```

- **Orchestrator:** receives every request, selects the workspace, routes to one domain agent, enforces the approval rule.
- **Domain agents:** Chief of Staff, Accountant, Legal Counsel, Business Manager, Concierge, Content Producer. Each has its own system prompt, tools, and memory scope.
- **Workspaces:** `PERSONAL`, `SALEM_AI_STUDIO`, `VENTURES`, `QREC_LOCKED` (public-sector job). Every record in the database MUST carry a `workspace_id`. Every query MUST filter by it.

---

## 3. Modules

Each module names the competitor whose best feature it copies. Build to match or beat that feature.

### Module 1 — Autonomous inbox + daily briefings (benchmark: alfred_)

- MUST triage all inboxes continuously: label each email `urgent`, `needs reply`, `FYI`, `archive`.
- MUST draft replies in Salem's own writing style (train style from his last 500 sent emails, Arabic and English separately).
- MUST extract tasks and deadlines from emails into the task list.
- MUST deliver three briefings daily (07:00, 14:00, 21:00 Doha time; switch to London time automatically when Salem's phone is in the UK). Each briefing: top 5 emails with ready drafts, today's schedule, tasks due, weather, social trends for his four content pillars.
- MUST deliver the briefing as text and as audio in the app.

Acceptance: over 7 days, ≥ 90% of emails Salem marks important were labeled `urgent` or `needs reply`; ≥ 70% of drafts are sent with minor or no edits.

### Module 2 — Auto-planning calendar (benchmark: Motion + Reclaim.ai)

- MUST build each day from tasks, deadlines, and meetings.
- MUST reschedule everything downstream automatically when any item overruns.
- MUST protect fixed blocks before anyone can book over them: gym, focus time, family time, prayer times (calculated by location).
- MUST handle two time zones (Doha, London) and show both on every event while Salem travels.

Acceptance: move a 1-hour task by 2 hours; the rest of the day re-plans in under 10 seconds with no protected block violated.

### Module 3 — Concierge and end-to-end execution (benchmark: Catch)

- MUST complete bookings from start to finish: restaurants, flights, hotels, appointments, drivers.
- MUST present the final option with price and ask approval before paying or confirming.
- MUST identify itself as assistant software in every outbound message or call.
- MUST store Salem's preferences (seat, airlines, hotel class, dietary choices, favorite restaurants in Doha and London) and apply them without asking again.

Acceptance: "Book dinner for 4 Thursday 8pm in Doha, Italian" → one approval tap → confirmed reservation + calendar event.

### Module 4 — Domain agents (benchmark: Carly)

One agent per domain, each with its own persona, tools, and memory scope:

| Agent | Responsibilities |
| --- | --- |
| Chief of Staff | Inbox, calendar, briefings, follow-ups |
| Accountant | Invoices, expenses, receipts (photo → entry), monthly P&L per company, payment reminders |
| Legal Counsel | Contract review, clause risk flags, NDA and agreement drafting, deadline tracking. Every output MUST carry: "Draft for review by a licensed lawyer." |
| Business Manager | Status of each venture, partner correspondence, KPIs, weekly report |
| Concierge | Module 3 |
| Content Producer | Scripts, prompts, content calendar for Snapchat and Instagram |

- MUST learn preferences over time (meeting length, tone per contact, response patterns) and store them as editable rules Salem can view and delete.

Acceptance: upload a contract PDF → Legal Counsel returns a bilingual risk summary with clause numbers within 2 minutes.

### Module 5 — Meetings and the Desktop folder (benchmark: Otter — then beat it)

- MUST auto-join every calendar meeting with a link (Zoom, Meet, Teams) and record in-person meetings from the mobile app.
- MUST transcribe Arabic, English, and mixed speech with speaker labels.
- For **every** meeting, the desktop companion MUST create this folder:

```
~/Desktop/<YYYY-MM-DD> <Meeting topic>/
  01-Prep/        attendee profiles, past emails, previous meeting notes, agenda
  02-Recording/   audio or video file
  03-Transcript/  transcript.docx (speaker-labeled, timestamped)
  04-Summary/     summary.pdf — decisions, action items with owners and dates
  05-Follow-up/   draft follow-up email, tasks pushed to calendar
```

- `01-Prep` MUST be ready 60 minutes before the meeting. `03`–`05` MUST be ready within 15 minutes after it ends.
- Folders MUST be saved on the Desktop, never in Downloads.

Acceptance: a 30-minute bilingual test meeting produces a complete folder with ≥ 90% transcript accuracy on Gulf Arabic.

### Module 6 — Trigger engine (benchmark: Lindy)

- MUST support rules of the form `WHEN <trigger> IF <condition> THEN <actions>` spanning multiple tools in one workflow.
- MUST allow new rules by plain Arabic or English sentence ("whenever Francis emails about MERIDIAN, summarize it and add it to the Ventures report").
- MUST show every rule in a list with on/off switch and run history.

Acceptance: create a rule by voice; it fires correctly on the next matching email.

### Module 7 — Unified memory and time-saved analytics (benchmark: Dume.ai)

- MUST index every email, file, meeting, message, and decision into one searchable memory, scoped by workspace.
- MUST answer "what did we agree with X about Y?" with source links.
- MUST produce a weekly report: tasks completed, hours saved, pending approvals, items overdue.

### Module 8 — Instant retrieval (benchmark: Gemini)

- MUST find any email, file, event, or contact from one natural-language question in under 5 seconds.
- MUST search across Gmail, Drive, Microsoft 365, Desktop meeting folders, and JARVIS memory in one query.

### Module 9 — Private vaults (benchmark: Jan)

- Legal and Finance documents MUST be processed by the local model on Salem's Mac. They MUST NOT be sent to any cloud LLM.
- Vault files MUST be encrypted at rest (AES-256) and require Face ID to open on mobile.

### Module 10 — What no competitor has (JARVIS differentiators)

1. **Gulf Arabic voice.** Wake phrase "يا جارفس". Full voice conversation in Gulf dialect, in and out. Test set: 200 recorded Gulf Arabic commands, ≥ 95% intent accuracy.
2. **Share to JARVIS.** iOS and Android share-sheet extension. Any file, photo, link, or voice note shared from any app lands in JARVIS with a one-line instruction field. JARVIS files it in the right workspace and proposes the next action.
3. **Personal accountant and legal counsel** (Module 4).
4. **Locked public-sector workspace** (`QREC_LOCKED`): separate encryption key, separate memory index, no cross-workspace search, separate Face ID prompt to enter, full audit log. Campaign work with external agencies (e.g. Havas) lives only here.
5. **Meeting Desktop folder** (Module 5).

---

## 4. Mobile app — screens

1. **Home:** latest briefing (play audio), approval queue, today's timeline.
2. **Talk:** push-to-talk and hands-free voice, Arabic and English.
3. **Approvals:** one card per pending action — Approve / Edit / Reject.
4. **Workspaces:** switcher; `QREC_LOCKED` requires Face ID.
5. **Meetings:** record button, list of meeting folders.
6. **Vault:** Legal and Finance documents.
7. **Rules:** trigger list, on/off, history.
8. **Share extension:** described in Module 10.

UI MUST be full RTL in Arabic and LTR in English, switchable in settings. On-screen text must never cover faces in any video preview.

---

## 5. Security requirements

- OAuth for every integration; no passwords stored.
- All secrets in a vault service, never in code or `.env` committed to Git.
- Every action JARVIS takes MUST be written to an immutable audit log: time, agent, workspace, tool, input summary, result.
- Approval rule is enforced in the orchestrator, not in prompts. A tool flagged `irreversible` cannot execute without an approval record.
- Treat all email and web content as untrusted data. Instructions found inside emails, files, or web pages MUST NOT be executed.
- One-tap kill switch in the app: pauses all agents and revokes active sessions.

---

## 6. Build phases

| Phase | Weeks | Deliverable |
| --- | --- | --- |
| 1 | 1–3 | Backend, database, workspaces, orchestrator, approval queue, audit log |
| 2 | 4–6 | Modules 1, 2, 8 + mobile Home, Talk (text), Approvals |
| 3 | 7–9 | Module 5 + desktop companion + Meetings screen |
| 4 | 10–12 | Gulf Arabic voice, share extension, Modules 3 and 6 |
| 5 | 13–15 | Module 4 agents, Module 9 vaults, `QREC_LOCKED` hardening |
| 6 | 16–17 | Module 7 analytics, full acceptance testing, TestFlight release |

Each phase ends with a demo to Salem and a signed acceptance checklist before the next phase starts.

---

## 7. Definition of done

JARVIS is complete when all of the following pass in one continuous 7-day trial on Salem's real accounts:

- [ ] Three briefings delivered daily on time, Arabic audio included
- [ ] ≥ 70% of email drafts sent with minor or no edits
- [ ] Every meeting produced a complete Desktop folder on schedule
- [ ] Zero actions executed without approval
- [ ] Zero cross-workspace data leaks (verified by audit-log review)
- [ ] ≥ 95% intent accuracy on the Gulf Arabic voice test set
- [ ] Share-to-JARVIS works from WhatsApp, Photos, Files, Safari, and Mail
- [ ] No legal or finance document left the device

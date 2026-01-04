# Oura Agent — Website First, Then iOS + Agents (Not Medical)

This repo is building a personal wellness assistant that uses **Oura data** (via OAuth) to generate **non-medical** insights and experiments. We are starting with a **React website** (easier to ship + satisfies Oura “Website/Privacy/Terms” requirements), then wiring the same backend into **iOS SwiftUI**.

## North Star
- **Oura data pipeline first** (OAuth + data fetch + caching).
- **Website first** (legal pages + OAuth entrypoint + Terms acceptance gate).
- Then **iOS app** as a client of the same backend.
- Then **deep research agent** and multi-agent orchestration.

---

## Non-negotiables
- **Not medical.** Never diagnose, treat, or claim clinical certainty.
  - Allowed phrasing: “suggests”, “may be consistent with”, “worth testing”, “correlates with”.
  - Disallowed: “diagnosis”, “you have X”, “treatment plan”, “clinically proven for you”.
- **Single user-facing voice.** Only the Synthesizer (later) produces user-visible prose.
- **Secrets never ship to clients.** OAuth client secret and refresh tokens stay on the backend.
- **Modular, readable code.** Small files, typed models, explicit interfaces, minimal magic.

---

## Repo layout
```
oura-agent/
web/ # React (Vite + TS) website (primary first milestone)
ios/ # SwiftUI app (later)
backend/ # FastAPI service + Oura OAuth + agents (in parallel, but website first)
shared/ # API contracts, shared schemas, docs
infra/ # deployment later
Privacy/ # existing privacy.md (currently contains Terms text too)
CLAUDE.md
```

---

# Current Priority: Website (React) first

## Why
Oura requires a **Website**, **Privacy Policy URL**, and **Terms of Service URL** for OAuth application registration. The fastest compliant solution is a small website with stable URLs and a Terms acceptance gate.

## Website stack (must use)
- React + TypeScript
- Vite
- React Router
- TailwindCSS (or simple CSS if necessary, but prefer Tailwind)
- `react-markdown` to render legal markdown files

## Website routes (required)
- `/` Home (landing)
- `/privacy` Privacy Policy (markdown-rendered)
- `/terms` Terms of Service (markdown-rendered)
- `/accept` Terms acceptance gate
- `/app` Protected app area (placeholder UI)
- `/app/connect` Connect Oura page
- `/app/welcome` Welcome page after OAuth redirect

## Terms acceptance gate (required behavior)
- Any visit to `/app/*` must redirect to `/accept` unless Terms are accepted.
- `/accept` must enforce **real acknowledgement**:
  - Show Terms content in a scrollable panel.
  - Disable “Accept/Continue” until the user scrolls to bottom.
  - Require checkbox: “I have read and accept the Terms of Service.”
  - Require checkbox: “I have read the Privacy Policy.”
  - Only enable Continue when both boxes are checked AND scrolled to bottom.
- Store acceptance in `localStorage`:
  - `termsAccepted: true`
  - `termsAcceptedAt: ISO timestamp`
  - `termsVersion: string` (e.g., `2026-01-04`)
- Preserve intended destination:
  - If user tries `/app/connect` without acceptance, redirect to `/accept?next=/app/connect`
  - After acceptance, redirect to `next`.

## Legal content source (required)
- The Terms of Service text is currently mixed inside: `Privacy/privacy.md`
- Create:
  - `web/src/content/privacy.md`
  - `web/src/content/terms.md`
- For now:
  - Copy the relevant Terms sections into `terms.md` (even if imperfect).
  - Keep privacy-only content in `privacy.md`.
  - We will refine wording later, but must be accurate and non-medical.

## Website structure (required)
Create `web/` with:
```
web/
src/
pages/ # Home, Privacy, Terms, Accept, AppHome, ConnectOura, Welcome
components/ # Header, Footer, MarkdownPage, TermsGate, LegalNotice
content/ # privacy.md, terms.md
lib/ # storage.ts, terms.ts (version), routes.ts
public/
.env.example # VITE_BACKEND_BASE_URL=http://localhost:8000

README.md # local run + build + config docs
```
## iOS friendliness (required)
- Large tap targets
- No hover-only UI
- Avoid fixed heights that break on mobile Safari
- Respect safe-area insets when needed
- Keep typography readable on iPhone

---

# Backend: Oura OAuth + Data (next spine, may be built in parallel)

## OAuth (required implementation approach)
Backend-owned **Authorization Code flow**.
- iOS and Web are clients; backend handles token exchange and stores refresh tokens securely.

Endpoints (planned / required soon):
- `GET /oura/connect/start` → returns `{ auth_url, state }`
- `GET /oura/connect/callback` → exchanges `code`, stores tokens, redirects to web `/app/welcome` (or returns JSON in dev)
- `POST /oura/disconnect` → revokes and deletes stored tokens

Rules:
- Validate `state` (CSRF protection)
- Refresh tokens are rotating; always store newest refresh token after refresh
- Never log raw token values
- Store secrets only in backend env vars

## Oura data “working” definition (MVP)
Oura integration is considered working when:
- OAuth connect completes end-to-end
- Backend can fetch last 14 days of daily summaries (sleep/readiness/activity)
- Token refresh happens automatically without re-login

---

# Agents (later milestone, but structure now)

## Backend package layout (target)
```
backend/app/
api/ # FastAPI routes (thin controllers)
core/ # config, logging, errors, utilities
oura/ # OAuth + API client + caching
agents/ # agent framework + concrete agents
orchestration/ # pipeline runner + synthesizer coordination
storage/ # DB models/repositories
schemas/ # pydantic API models
services/ # feature computation, time-series helpers
main.py
tests/
```

## Agent framework (class hierarchy)
- `AgentContext` (typed)
- `AgentResult` (typed: payload + confidence + evidence + warnings)
- `Agent` base class:
  - `name: str`
  - `depends_on: list[str]`
  - `run(ctx) -> AgentResult` (async OK)

Constraints:
- Only `OuraDataAgent` may do network calls (later).
- Only `SynthesizerAgent` may write user-facing prose.
- Everyone else outputs structured JSON/data.

---

# iOS (later milestone)
- SwiftUI app is a thin client of backend API.
- Uses async/await, Codable models.
- Does NOT store OAuth secrets or refresh tokens.
- Renders UI from structured cards, not by parsing prose.

---

# Claude Code workflow rules (important)
## Always do this
- Prefer **Plan Mode** for architectural work before editing:
  - `claude --permission-mode plan`
- Keep changes modular and small; avoid editing many unrelated files at once.
- Create/modify files in the declared structure (don’t invent new top-level folders).

## When implementing the website milestone
- Implement the React site inside `web/` exactly as described above.
- Ensure routes + TermsGate behavior match requirements.
- Create `web/README.md` with local run/build steps.
- Use `.env.example` for backend URL configuration.

## Tone & product posture (always)
- Non-medical, experiment-driven, uncertainty-aware.
- No diagnosis language, even internally in user-facing outputs.

---

# Definition of Done (Website Milestone)
- `/`, `/privacy`, `/terms`, `/accept`, `/app` routes exist and work.
- `/app/*` is protected behind Terms acceptance gate.
- Terms acceptance requires scroll-to-bottom + two checkboxes.
- Privacy and Terms content render from markdown files.
- “Connect Oura” page calls `GET {VITE_BACKEND_BASE_URL}/oura/connect/start` and redirects to returned `auth_url`.
- Looks good and is usable on iOS Safari.

---

# Definition of Done (Oura Data Milestone)
- Backend OAuth completes and tokens are stored server-side.
- Data fetch endpoints work (at least daily summaries).
- Web UI can initiate OAuth and land on a welcome page post-auth.

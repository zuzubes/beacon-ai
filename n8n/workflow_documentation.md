# Sector Brief Generation — n8n Workflow

`brief_generation_demo.json` — a chat-driven automation POC that lets a partner pick a sector
and get a partner-ready investment brief back in the same conversation, without touching a
terminal or notebook.

## What it does

1. **When chat message received** opens n8n's built-in chat widget.
2. **Config** holds the address and shared secret of the bridge server (see [Architecture](#architecture-and-why) below) — the only two values that change between runs.
3. **Get Sectors** calls the bridge server for the current list of sectors that have a computed
   `transfer_score` (currently 20, sourced from `outputs/signals/transfer_scores.csv`).
4. **Match Sector** (Code node) checks whether the user's message matches one of those sectors
   exactly (case-insensitive).
5. **Sector Selected?** branches:
   - No match → **Ask For Sector** replies with the sector list as a pick-from-this menu.
   - Match → **Generate Brief** calls the bridge server to run `src/generate_brief_for_sector.py`
     for that sector, which generates the brief via the OpenAI API, writes a timestamped copy to
     `outputs/briefs/`, and returns the markdown.
6. **Format Brief Output** sends that markdown back into the chat.

## Why n8n, for this round

n8n was chosen specifically to demo the idea quickly — a working, clickable proof that
"pick a sector → get a brief" is a real, chainable pipeline, without spending Round 1 time on a
custom front end. It's the fastest way to make the `src/briefs.py` pipeline something a
non-technical stakeholder can actually try.

It is **not** assumed to be the long-term product surface. Candidate directions for later rounds:
- An **MCP (Model Context Protocol) connection**, so the brief-generation tools plug directly
  into whatever assistant/IDE a partner already uses.
- A documented **API** (`/sectors`, `/brief` — the same shape the bridge server already exposes)
  that other internal tools or a future dashboard can call directly.
- Direct integration into **Slack, Telegram, or WhatsApp**, so partners ask for a brief inside a
  tool they're already in daily, instead of a dedicated chat widget.

n8n's role in this round is to prove the workflow shape (trigger → validate input → generate →
respond) cheaply, so whichever of those directions gets picked next round, the underlying
`src/` pipeline doesn't need to change — only the front door does.

## Architecture, and why

The workflow talks to a small local script, `src/bridge_server.py`, over an HTTP tunnel
(e.g. `cloudflared tunnel --url http://127.0.0.1:8000`), instead of running Python directly
inside n8n. Two things forced that design, both specific to this demo's hosting:

1. **The n8n instance used for this demo is a shared, managed instance** (not self-hosted by
   this project), and shared instances lock down `Execute Command` — the node that would let a
   workflow shell out to Python — because it would let any user on the instance run arbitrary
   shell commands on the shared server. That's a correct security default, not a bug.
2. **Even with that node enabled, it wouldn't help.** `Execute Command` runs on whatever machine
   hosts n8n. A managed instance runs on someone else's server, which doesn't have this repo,
   this `.venv`, or the `outputs/briefs/` folder the brief needs to be written into. Only a
   locally-run n8n could shell out to local Python directly.

The bridge server is the workaround for both: it's a plain HTTP server (`http.server`, no new
dependencies) exposing `GET /sectors` and `GET /brief?sector=<name>`, protected by a shared
`X-Bridge-Token` header (`BRIDGE_TOKEN` in `.env`). Running it locally and tunneling it out lets
a workflow on someone else's n8n instance still reach this laptop's Python code and filesystem.

## Limits vs. a production design

This is a demo-only architecture, and it should not be mistaken for how this would ship:

- **The bridge server and tunnel must both be running** for the workflow to work at all. If
  either is stopped, the chat fails. A production deployment wouldn't depend on someone's laptop
  being on.
- **The tunnel URL is ephemeral** — a fresh `cloudflared` quick tunnel prints a new URL every
  time it starts, so the `Config` node's `bridgeUrl` has to be updated by hand after every
  restart. A production setup would run behind a stable domain.
- **No retry, queueing, or concurrency handling.** The bridge server is a single-process
  `ThreadingHTTPServer` with no rate limiting — fine for one demo user clicking through a chat,
  not for multiple partners hitting it at once.
- **Auth is a single shared secret**, not per-user credentials or scoped access — adequate to
  stop a stranger who finds the tunnel URL from triggering paid OpenAI calls, not adequate for
  a real multi-tenant product.
- **No persistence beyond the filesystem.** Generated briefs are markdown files in
  `outputs/briefs/`; there's no database, no way to list past briefs from the chat, and nothing
  survives if the laptop's disk is wiped.
- **The sector list only covers sectors with a computed `transfer_score`** (20 of the ~69 in
  `data/processed/sector_year_features.csv`) — sectors without enough signal simply aren't
  offered, by design, not as a bug to fix later.

A production version would run the actual `src/` pipeline behind a real API (deployed
somewhere it doesn't depend on a laptop staying on), and have n8n — or whatever front door is
chosen next round (MCP, Slack, etc.) — call that API directly instead of a tunneled bridge.

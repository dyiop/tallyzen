# Convex memory — flip from local to real (earns the Convex power-up)

The `context` plugin runs on a **local JSON store by default** (works offline, no
setup). To switch the SAME tools to a real Convex deployment — which is what earns
the Convex partner power-up — do this once. The one step that can't be automated is
the login (it opens a browser).

## Setup (one time, ~5 min)
```bash
cd memory/convex
npm init -y
npm install convex
npx convex dev          # ← opens a browser to log in / create the deployment
                        #   (this is the step you must do yourself)
```
`npx convex dev` reads `schema.ts` + `memory.ts` here, creates the `memory` table,
deploys the `remember` mutation and `recall` query, and prints your deployment URL
(looks like https://<name>-<n>.convex.cloud). Keep it running (it watches for changes).

## Point the agents at it
The Convex Python client is needed on the Hermes side:
```bash
~/.hermes/hermes-agent/venv/bin/pip install convex
```
Then set the URL and restart the gateway so the plugin reloads in Convex mode:
```bash
export CONVEX_URL=https://<your-deployment>.convex.cloud
hermes gateway run --replace
```
That's it — `remember_invoice`, `remember_signal`, `get_company_context` etc. now
read/write real Convex. Everything else (tool names, agent prompts) is unchanged.

## How the plugin calls it
- write:  `client.mutation("memory:remember", { org, kind, data, ts })`
- read:   `client.query("memory:recall",   { org, kind, limit })`

## Verify
In the Convex dashboard (opened by `npx convex dev`) → Data → `memory` table: you'll
see rows appear as the agents store invoices and signals. Seed the company profile
either by leaving it in the plugin's `company_seed.json` (read locally) or by adding
a `companies` table later if you want it in Convex too.

## Note
A local store *labelled* Convex earns nothing. The power-up needs Convex genuinely
running with the agents writing to it — which is exactly what `CONVEX_URL` switches on.

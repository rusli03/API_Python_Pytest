# Coding Exercise — QA Automation Lead

**Test duration: 3 hours.** Please stop at 3 hours even if unfinished and tell us in the README what you would have done next. We are assessing design judgment.

## The scenario

You are joining a platform team that owns two small services:

- **Wallet service** (`wallet-service.openapi.yaml`) — holds a user's balance; supports credit, debit, and a transaction ledger.
- **Rewards service** (`rewards-service.openapi.yaml`) — a catalogue of rewards. Claiming a reward with a cost **debits the user's wallet by calling the Wallet service**. If the wallet has insufficient funds, the claim is rejected.

The two services are real, stateful, and talk to each other over HTTP.

### Running them locally

The mock is Python, but **your harness does not have to be** — you only need to
get these two services up and leave them running. Requires **Python 3.10+**
(`python3 --version`, or `py --version` on Windows).

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python mock_services.py
```

**Windows (PowerShell)**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python mock_services.py
```

If PowerShell blocks the activate script, run
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first.

Use the virtualenv. Installing into a system-wide Python needs admin rights and
will fail with a permissions error on most machines.

You should see:

```
Wallet  service: http://127.0.0.1:8081/docs
Rewards service: http://127.0.0.1:8082/docs
```

**This process stays in the foreground and does not return to the prompt — that
is normal. Leave it running and open a second terminal for your tests.** Stop it
with Ctrl-C.

Sanity check, from the second terminal:

```bash
curl http://127.0.0.1:8082/rewards
```

That should return the seeded reward catalogue. Swagger UI is at `/docs` on
either port — `http://127.0.0.1:8081/docs` and `http://127.0.0.1:8082/docs`.

Ports 8081 and 8082 must be free. If either is taken, uvicorn will exit with an
"address already in use" error; free the port and start again.

Each service exposes `POST /admin/reset` for test use. State is in memory and
lost on restart.

Time spent getting this running does not count against your 3 hours.

## What to build

1. **A minimal test harness**, in Java, Python, Go — your choice:
   - one API client per service,
   - one or two data builders (e.g. a way to get "a wallet funded with X"),
   - one fixture for common setup / teardown.
2. **Three (3) automated tests that exercise the cross-service flow.** Single-endpoint tests do not count. Both tests should verify the effect in *both* services.
3. **A short README** (half a page is fine) covering: how to run it, the design decisions you made and why, what you deliberately left out, and what you would do next with another day.

## What we are looking for

- A harness that a developer/QA on another team could pick up and write a third test with, without reading your test code first.
- Tests that are independent of each other and of run order. Running either one alone, or both in reverse order, or twice in a row, should pass.
- Assertions that prove the business outcome — not just that the HTTP call returned 2xx.
- Test names a product manager could read as a bug report title.
- Honest trade-offs in the README. "I hard-coded the base URL because…" is a fine sentence.

## What we are *not* looking for

- Volume. Two well-designed tests beat ten shallow ones.
- UI tests, load tests, or a CI pipeline.
- Docker, reporting dashboards, or a framework with plugin architecture.
- Any change to `mock_services.py`. Treat it as a service you do not own. If you believe it has a bug, note it in the README — that is a legitimate finding.

## Submitting

Send a zip or a link to a private repository. Include the README at the root. We will run your tests against the unmodified mock, then discuss your design with you in the next interview stage.
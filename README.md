# M365 Command Center

A read-only security dashboard for a Microsoft 365 / Entra ID tenant. It shows, on one
screen, what a security operator checks across five consoles: failed sign-ins, risky
users, service health, external mail forwarding (data exfiltration), and where devices
are signing in from.

It **never writes** to the tenant. That is enforced by a test, not just promised in this
README — see [Read-only, and how it's enforced](#read-only-and-how-its-enforced).

## The problem

Sign-in risk lives in Entra. Failed logons live in the audit logs. Service health is a
different blade. Mailbox forwarding rules are buried in Exchange. Device compliance is in
Intune. A small team ends up flipping between five consoles to answer one question —
*"is anything on fire right now?"* — and no one keeps all five open. This puts the signals
that matter on a single page that refreshes on its own.

## See it in 10 seconds — no tenant required

```bash
git clone https://github.com/earbona23/m365-command-center
cd m365-command-center
python -m app.server        # demo mode: synthetic data, no credentials
```

Open <http://127.0.0.1:8888>. Everything you see is **clearly labelled `DEMO DATA`** — it
is invented, it comes from no real tenant, and it exists so you can evaluate the tool
before wiring anything up.

![Dashboard in demo mode](docs/screenshot.png)

## Connecting a real tenant

```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml     # fill in tenant/client id; secret via env var
export M365CC_CLIENT_SECRET=...        # keep the secret out of the file
python -m app.server --live
```

`config.yaml` is git-ignored. No secret is ever written to the repo, and the dashboard's
`/api/config` endpoint has a test proving it never returns the secret to the browser.

### Permissions it asks for, and why each one

All **read-only, application (app-only)** Microsoft Graph permissions. Nothing here can
change the tenant.

| Permission | Powers | Why it's needed |
|---|---|---|
| `AuditLog.Read.All` | Failed sign-ins | The failed-login chart and top offenders |
| `IdentityRiskyUser.Read.All` | Risky users | The risk panel |
| `IdentityRiskEvent.Read.All` | Risk detections | Risk detail |
| `User.Read.All` | User inventory | User count, mailbox enumeration |
| `Device.Read.All` | Device inventory | Devices and their last sign-in city |
| `ServiceHealth.Read.All` | Service health | The service-status panel |
| `MailboxSettings.Read` | Forwarding rules | Detecting mail forwarded to external domains |

If a permission is missing, that **one panel** stays empty with a note; the rest of the
dashboard still works. It never fails as a whole because one grant is absent.

## Read-only, and how it's enforced

The Graph client (`app/graph.py`) exposes exactly two methods: `get()` and `get_all()`.
There is no `post`, `patch`, `put`, or `delete`. `tests/test_readonly_guarantee.py` walks
every file under `app/` and fails if a Graph write verb appears anywhere (the single OAuth
token request is the one documented exception, and it touches no tenant data). Add a write
and CI goes red before it ever reaches a tenant.

## How it works

- `app/demo/` — deterministic synthetic tenant, so the suite runs and the demo shows
  without a real tenant.
- `app/collectors/` — one read-only function per data source. Each is tested against a
  fake Graph client, so `pytest` needs no tenant and no network.
- `app/server.py` — standard-library HTTP server (no web framework: less to attack, less
  to install). Binds to `127.0.0.1` by default and serves the dashboard plus `/api/*` JSON.
- `dashboard/index.html` — self-contained. No external scripts, no CDN, charts drawn as
  inline SVG. It works offline and adds no third-party supply chain.

## A word on privacy

Device location is shown at **city level, derived from sign-in logs** — the granularity
Entra actually provides. This tool deliberately does **not** collect or display precise
GPS coordinates of employee devices: that is personal monitoring with consent and legal
implications well beyond a security dashboard.

## Limitations — what this does not do

- It is a **read-only viewer**, not a SIEM. It does not store history, correlate events
  over time, or alert. For that, use Sentinel; this complements it, it doesn't replace it.
- Detections are simple and honest: external forwarding is flagged by comparing the
  forwarding domain to the user's own. It will miss forwarding done through inbox rules or
  connectors, and it does not claim otherwise.
- `--live` has been built against the documented Graph shapes and unit-tested with mocked
  responses. Validate it against your own tenant before relying on it operationally.
- Do not expose it to the internet without putting authentication in front of it. A SOC
  dashboard reachable from the internet is itself the leak. It warns you if you bind it
  beyond localhost.

## Contributing

New collectors are welcome — keep them read-only, add a mocked test, and the read-only
guarantee test will hold the line. Run `pytest -q` and `ruff check .` before a PR.

## License

MIT — see [LICENSE](LICENSE).

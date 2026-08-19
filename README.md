# Kelo

![WIP](https://img.shields.io/badge/status-WIP-yellow)

A personal archive for bills, invoices, and important house/car documents.

The intended pipeline: watch a mailbox (any IMAP/OAuth provider) for PDFs from known senders, extract structured data (amount, supplier, due date, consumption), store a row in a document store with the PDF attached, and flag amount mismatches (subtotals vs total, or a spike vs history).

Today that means n8n for automation and Notion for storage. Both can be replaced later.

Runtime state lives in a Docker volume (SQLite). Workflow JSON in `workflows/` is the Git copy of those automations.

## Prerequisites

- Docker Desktop on Mac, or Docker Engine with Compose on a VPS

## Start

```bash
cp .env.example .env
# Replace N8N_ENCRYPTION_KEY in .env:
openssl rand -hex 32
```

Paste the generated value into `N8N_ENCRYPTION_KEY`, then:

```bash
docker compose up -d
```

Open http://localhost:5678 and create the owner account.

## Persistence and source control

n8n stores workflows and credentials in SQLite inside the `n8n_data` volume. That volume survives `docker compose down` and image rebuilds.

After you change a workflow in the UI, export JSON into Git and commit:

```bash
docker compose exec n8n n8n export:workflow --backup --output=/workflows
git add workflows/*.json
git commit -m "Export n8n workflows."
```

`--backup` writes one JSON file per workflow.

## New machine

1. Copy the repo, create `.env` from `.env.example`, set a new `N8N_ENCRYPTION_KEY` (or reuse the old key only if you also migrate the volume).
2. `docker compose up -d`
3. If `workflows/` contains JSON files:

```bash
docker compose exec n8n n8n import:workflow --separate --input=/workflows
```

Skip import when the folder only has `.gitkeep`. Re-enter credentials in the UI after import; they are not in the JSON.

## VPS

In `.env` on the server set:

- `N8N_BIND_HOST=0.0.0.0` until a reverse proxy exists
- `N8N_HOST` to the hostname or public IP
- `N8N_EDITOR_BASE_URL` and `WEBHOOK_URL` to the public URL (trailing slash)

Do not commit `.env`. Keep `N8N_SECURE_COOKIE=false` while serving HTTP; set it to `true` when HTTPS is in front of n8n.

## Encryption key

If you lose both the volume and `N8N_ENCRYPTION_KEY`, saved credentials cannot be recovered. JSON in Git rebuilds workflow graphs, not OAuth tokens.

## Update n8n

Change the image tag in `docker-compose.yml` (currently `2.35.3`), then:

```bash
docker compose pull
docker compose up -d
```

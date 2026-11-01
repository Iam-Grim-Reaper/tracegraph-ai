# Coolify deployment: TraceGraph AI backend

**Status:** Deployment configuration prepared, **not yet tested on a VPS**. Keep this PR unmerged until the server deployment is verified. Coolify self-hosted software is free; VPS, domains, off-server backups and Gemini usage may cost money.

## Architecture

Keep the existing Next.js frontend on Vercel. Deploy the Git-tracked [compose.coolify.yml](../compose.coolify.yml) as a Coolify Docker Compose **Application**, not a Docker Compose Empty Service. The stack builds the existing `backend/Dockerfile` and runs:
- `api`: FastAPI + LangGraph + PyTorch CrossEncoder, internal port 8080.
- `qdrant`: private vector database with API-key authentication, data in `qdrant-data`.
- `neo4j`: private graph database, data in `neo4j-data`, logs in `neo4j-logs`.
- `graph-extraction-cache`: persistent graph extraction cache for the API.

No database ports are published to the host; only the FastAPI service should receive a public HTTPS domain.

## 1. Get a Linux server and install free self-hosted Coolify

Choose an Ubuntu 24.04 LTS **amd64/x86_64** VPS with SSH. For this project, budget approximately **4 vCPU, 16 GB RAM, 80–100 GB SSD** as a starting estimate, not a measured requirement. Do not choose arm64 before validating the repository's CPU PyTorch wheel and model build. Coolify's own installation minimum (2 CPU, 2 GB RAM, 10 GB disk) is **not** enough to judge this full stack.

Follow [Coolify's official installation instructions](https://coolify.io/docs/start-with-self-hosted). On the Linux server, review the installer and run as root/sudo:

```bash
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash
```

Access the new dashboard at `http://SERVER_IP:8000`, create the admin account promptly, then secure dashboard access with HTTPS. Back up `/data/coolify/source/.env`. Use SSH keys and a firewall. Permit SSH, 80 and 443, and restrict 8000 after setup. **Never expose 6333, 6334, 7474 or 7687 to the public internet.**

## 2. Deploy from GitHub in Coolify

1. Create a project and environment in Coolify and select **Application** from the public repository `Iam-Grim-Reaper/tracegraph-ai`.
2. Select the **Docker Compose** build strategy; repository root `/`; Compose file `/compose.coolify.yml`. Do **not** enable Raw Compose.
3. In the Application's **Domains** section, assign an HTTPS hostname to service `api` and internal port **8080**. Follow Coolify's documented domain format, e.g. `https://api.example.com:8080` (the suffix denotes internal container port; users still connect via normal HTTPS).
4. In resource Environment Variables, provide each required secret/setting below. Never put real API keys or passwords in GitHub.

| Environment variable | Value |
|---|---|
| `FRONTEND_URL` | `https://tracegraph-ai.vercel.app` (verify actual production frontend hostname, no trailing slash) |
| `CORS_ALLOWED_ORIGINS` | Same frontend origin, or a comma-separated list of exact allowed origins |
| `GEMINI_API_KEY` | Your Gemini API key |
| `QDRANT_API_KEY` | A long, unique random token (`openssl rand -hex 32`) |
| `NEO4J_PASSWORD` | A strong, unique random password (avoid `/` and characters needing Compose escaping) |

The Compose file defines the private database hostnames automatically. Keep `PUBLIC_UPLOADS_ENABLED=false` during public testing.

## 3. Verify the backend before connecting the frontend

Deploy and review logs and image build size. The existing Dockerfile downloads and bakes the model into the image; this requires memory, CPU, storage, and outbound network access during build.

- `GET https://YOUR_API_HOST/health` — liveness only.
- `GET https://YOUR_API_HOST/ready` — readiness/configuration check. **It currently does not execute real database queries**, so a 200 does not establish end-to-end correctness.
- `GET https://YOUR_API_HOST/api/documents` — should list ready indexed documents. Newly created volumes are EMPTY.
- After indexing protected test documents, verify streamed chat, Qdrant retrieval, Neo4j graph retrieval, and answer verification.

**Security:** Public `/api/chat` can consume paid Gemini tokens without authentication. Do not publish it for unrestricted access until you add authentication, request quotas, and rate limiting. Use private access controls while staging. Public uploads are deliberately disabled.

## 4. Connect existing Vercel frontend

In Vercel project's Environment Variables, set:
- `NEXT_PUBLIC_API_URL=https://YOUR_API_HOST`
- `NEXT_PUBLIC_UPLOADS_ENABLED=false`

Redeploy the frontend: these NEXT_PUBLIC variables are embedded at build time. Never put Gemini, Qdrant, or Neo4j secrets in NEXT_PUBLIC variables.

## 5. Persistence, migration, backup

Compose named volumes survive routine container restarts and redeployments. They do **not** protect against deletion of the server, disk failures, or deleting volumes. Configure off-server encrypted backups and test restore.

The new Qdrant/Neo4j volumes do **not** contain previous localhost or managed-cloud datasets. Plan a supported backup/restore from the prior databases or reindex documents in a protected environment. Back up before image upgrades; review migration compatibility.

The backend ingests documents synchronously, so large ingestion tasks can occupy an API worker and incur Gemini costs. Test modest data first.

## Official references

- [Install Coolify](https://coolify.io/docs/start-with-self-hosted)
- [Git-linked Docker Compose](https://coolify.io/docs/applications/builds/docker-compose)
- [Qdrant security](https://qdrant.tech/documentation/security/)
- [Neo4j Docker](https://neo4j.com/docs/operations-manual/current/docker/introduction/)

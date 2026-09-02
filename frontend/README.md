# TraceGraph frontend

The Next.js interface for TraceGraph.

- `/` is the hero-only product landing page.
- `/app` is the document workspace, including catalog, upload, streaming
  execution, answers, and evidence inspection.

## Local development

```bash
npm ci
npm run dev
```

The workspace reads `NEXT_PUBLIC_API_URL` and defaults to
`http://127.0.0.1:8000` when it is not set.

## Validation

```bash
npm run lint
npm run build
```

## Vercel deployment

Deploy this directory as a Vercel Next.js project with `npm run build`.
Set these safe, browser-visible Vercel environment variables:

- `NEXT_PUBLIC_API_URL` — Railway backend HTTPS origin.
- `NEXT_PUBLIC_UPLOADS_ENABLED=false` — disables the public-demo upload UI.

For local development, use `NEXT_PUBLIC_UPLOADS_ENABLED=true` in ignored
`.env.local`. Do not set backend credentials in Vercel.

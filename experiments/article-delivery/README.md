# Article delivery prototype — NOT production-ready

This experiment does not change Cloudflare routes, Pages output, article data, or any URLs.

## Scope
- `worker.mjs` accepts GET/HEAD for `/en/news/<slug>/` and `/hi/news/<slug>/`.
- Fetches already generated article HTML from the public repository's committed `dist/` tree.
- Returns HTML (not client-only JavaScript), allowing SEO markup to remain present.
- Caches HTML for 5 minutes. Images/CSS referenced by the HTML must still be served separately.

## Important limitations
- GitHub raw is **not a production content origin** and may rate-limit or change availability. It cannot guarantee one-year uptime or speed.
- Worker free-tier request quotas apply, including cache hits that invoke the Worker.
- Existing Pages build still exceeds 20,000 files; this prototype does NOT fix deployments yet.
- Do not remove any `dist` HTML or image files, activate routes, or alter sitemap/redirects until a durable origin is tested and backed up.
- Test sample canonical article URLs, redirects, English/Hindi, images, cache behavior, 404s, mobile performance, SEO markup, and failure modes in an isolated preview before any migration.
- Production migration requires a storage origin with a tested cost/usage budget and rollback plan.

## Safe rollback
Delete the experiment files. No production traffic is routed to this code.

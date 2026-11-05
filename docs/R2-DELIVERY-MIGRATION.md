# R2 delivery migration — review and staging required

This branch is **not a verified production migration**. Do not merge it or activate production routing solely because unit tests pass. No Cloudflare settings have been changed from this workspace.

## Baseline and preservation

The supplied successful image-backup run was checked through GitHub: job `127041798059` completed successfully. PR #6 is an open, non-mergeable draft; its current Worker still uses raw GitHub and accepts only the old ID-shaped route. It is not a production origin and has not been merged into this implementation.

The audited main snapshot is `69c76b6ed33462a901059c8a61a486a17a294e35`. Its tracked `dist/` contains 20,983 files. Rebuilding that checkout produces **22,075 files**, rather than the prompt's earlier 21,543. The updated directory records generate additional car profiles; stale profiles and redirect stubs were also retained by the old build.

| Item | Reproduced old build | Clean full render | Proposed Pages package |
| --- | ---: | ---: | ---: |
| Files | 22,075 | 19,672 | 17 |
| HTML files | 19,828 | 17,425 | 3 |
| Per-URL redirect stubs | 2,403 | 0 | 0 |
| `/images/` files | 2,233 | 2,233 | 0 |
| Server-side legacy aliases | 2,000 rules + 2,403 stubs | 4,402 R2 route entries | Root/sitemap redirects only |
| Logical published articles | 2,187 | 2,187 | Delivered through R2 |
| Original source post JSON files | 2,194 | 2,194 | Kept in source repository |
| Indexable canonical sitemap pages | 7,785 | 7,785 | Same public URLs |

The clean render preserves eight historical car/phone profiles which no longer regenerate from current records. Their exact HTML is retained under `content/historical-pages/`. Six image files which no longer regenerate are retained under `content/legacy-images/`. All other original images remain in `content/featured/`; generated illustrations regenerate from article inputs. **All 2,233 output image files were compared byte-for-byte with the reproduced old build and matched**, totaling 281,004,661 bytes.

`content/published-url-inventory.json` records 24,057 existing scoped page, image and redirect URLs. Both language routes and legacy ID aliases are checked against every release. Seven duplicate source imports keep their source JSON and receive canonical redirects; no source article was deleted. Nine existing Hindi URLs contain the English fallback and retain their existing English canonical/noindex behavior; the system does not invent translations.

`dist/` and Python bytecode are removed from Git tracking, not treated as original content. Git history retains the old generated tree. Pending drafts, source posts, source images, directories, original repository archives, and PR #6 remain untouched.

## Architecture and generator cleanup

- `scripts/build.py --render-only` always creates a fresh, fixed `build/rendered/` directory. It is a migration input, never a deployable Pages directory. The default static build retains the 19,000-file guard and refuses an oversized package before replacing the old artifact.
- `OutputWriter` gives every path one owner, skips identical writes, rejects conflicting content, and reports the responsible generator. Redundant early CSS, JS, homepage and temporary sitemap writes were removed.
- Legacy redirects become a flattened route map and real HTTP 301 responses. No per-alias HTML stubs are generated for R2 delivery. The old standalone static fallback is retained only for an explicit static build/rollback; it cannot pass the asset guard at today's scale.
- One immutable R2 content object serves equivalent bodies. The 2,233 legacy image URLs map to 2,168 distinct existing image objects. Original R2 keys are reused when their checksum matches; changed/new media uses immutable checksum keys. Existing remote objects are never deleted.
- Releases use 256 deterministic URL hash shards. A small immutable release manifest selects those shards. Each URL points to an immutable body or a real redirect. Missing keys return 404; missing/corrupt release objects return 503. Both failures are uncached.
- Root assets, robots, verification files, sitemap files, ads, branding, CSS and JavaScript stay on Pages. The existing root redirect remains a 301 to `/en/`. Previously published `news-sitemap-1.xml`/`-2.xml` URLs either remain current shards or redirect to the current news sitemap.
- Production Worker routes are exactly `/en/*`, `/hi/*`, `/images/*`, and the slashless `/en` and `/hi`. There is no global Pages middleware or route matching CSS/JS/robots/sitemaps. All language HTML is in scope because directories, article pagination and archive pages also grow. This avoids merely shifting the 20,000-file failure to pagination next year.
- Old article related links are anchored to earlier coverage; publishing a new story no longer rewrites every old article's global trending block. The homepage retains current trending coverage and the four-hour discovery workflow.
- `SOURCE_DATE_EPOCH` pins the build clock. A clean repeated render must produce exactly the same release package. Content corrections and image backfills intentionally produce new immutable objects.
- Normal sitemap output shards at 45,000 URLs; News sitemaps retain their 1,000-entry limit. The SEO auditor understands both sitemap indexes and individual sitemap files.

## Publishing and monitoring

The 48 categories, two-post/category target, `7 */2 * * *` publishing schedule, `23 */4 * * *` trending discovery schedule, worldwide discovery, original-image logic, backfill, and directory/notice workflows remain. Source workflows commit only source/progress. The release workflow owns builds, uploads and deployment, so official-notice polling and image backfills do not repeatedly build and commit the full website.

A saved-draft fairness bug was fixed: twenty saved drafts in one category cannot take the first twenty processing slots. Saved drafts are prioritized **within** each category and categories rotate. Run summaries explicitly report every category's unmet target. Providers, evidence and quotas can still prevent a target; neither tests nor this branch demonstrate a successful live 96-post batch. The repository's latest persisted report showed 14 cricket posts and unavailable AI providers. No provider keys are available in this workspace, and no paid AI services were added or quotas raised.

Automatic deployment remains OFF until `DELIVERY_ENABLED=true` is deliberately set after the initial verified migration. A normal source push triggers releases; scheduled bot pushes are handled by the news workflow's completion event. Backfills and directory changes arrive with the next two-hour release. There is no extra scheduled polling job.

Build summaries report files, bytes, extensions, generator counts and growth. A greater-than-15% count increase names the generators responsible. Policy checks reject deployment output/bytecode in Git, obsolete experimental checkout references, guard bypasses, duplicate workflows, global middleware and workflows which commit `dist/`. Deployment root assets and scoped output types are allowlisted; unexpected caches, manifests, intermediate artifacts and new directories fail packaging. The old manual static rebuild, independent image polling and obsolete image-safety workflows were replaced by delivery CI/release checks. Dormant historical source code was not deleted merely for being unused by this migration.

Uploads use four bounded workers, bounded retries, connect/read timeouts and checksum/length verification. A failed upload cannot retain a successful receipt. Previously byte-verified immutable objects use a verification index plus a current bucket listing to avoid millions of redundant HEADs. Every new/changed public object is also fetched through the staging Worker before promotion. New uploads are HEAD- and GET-verified; `--deep-verify` rechecks unchanged bytes. An externally changed object fails Worker metadata checks, and staging HTTP checks validate served bytes. No object deletion or lifecycle rule is created.

## Verified quotas and 12-month forecast

Official references checked on 5 November 2026:

- https://developers.cloudflare.com/r2/pricing/ — Standard storage: 10 GB-month/month; 1 million Class A operations/month; 10 million Class B operations/month; free egress. Other buckets and applications share the account allowances.
- https://developers.cloudflare.com/workers/platform/pricing/ — Free Workers: 100,000 requests/day and 10 ms CPU/invocation. Cache hits still invoke the Worker and count. A paid account's existing billing is a separate account setting; this code does not switch plans.
- https://developers.cloudflare.com/pages/configuration/redirects/ — 2,000 static + 100 dynamic Pages redirect rules. Cloudflare Pages cannot proxy an external R2 origin with `_redirects`.
- https://developers.cloudflare.com/r2/platform/limits/ — `r2.dev` is not a production delivery endpoint. This implementation uses the private R2 binding.

At the requested target, 48 × 2 × 12 = **1,152 posts/day**, or **420,480 posts/year**. Current measured average image size is 125,842 bytes and average article HTML is 30,227 bytes per language. At one image and two languages per new article:

| Lower-bound growth | Approximate 12 months |
| --- | ---: |
| New image storage | 52.9 GB |
| New English + Hindi article HTML | 25.4 GB |
| Total new primary content | 78.3 GB |
| New language HTML routes | 840,960 |
| Pages file growth from those article/image routes | 0 |

These are decimal GB, not a claim that directories, index shards, corrections, retained releases or backfills are free. They add more storage. With the current baseline, the 8 GB **bucket safety threshold** is reached in roughly 34 days at this full target, sooner with revisions or larger images. A 10 GB allowance would also be exceeded long before a year. **The requirements “this volume”, “retain all content and rollback versions”, and “₹0 for a year on this R2 account” cannot all be guaranteed simultaneously.** No publishing frequency or category was reduced to conceal this limit.

The uploader lists current bucket objects and refuses all new writes if existing storage + proposed new immutable objects + verification-index growth exceed 8,000,000,000 bytes. It never silently enables billing or deletes history to fit. This is a bucket guard, not an account-wide billing cap: current other-bucket storage and actual monthly API usage must be checked in Cloudflare before activation. Worker traffic volume/CPU and cache behavior require real staging measurements. At 100,000 HTML/image requests/day, the Free Worker cap is reached even if R2 is entirely cached. The verified-index/list strategy keeps upload verification operations proportional to new objects plus bucket listing, rather than HEAD-checking all history every two hours.

## Staging, exact missing setup and production authorization

Existing R2 secrets used by the successful backup are `CF_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`. The delivery workflow requires a `CLOUDFLARE_API_TOKEN` with Workers Scripts Edit and Cloudflare Pages Edit scoped to this account, plus repository variable `CLOUDFLARE_PAGES_PROJECT` containing the **actual existing Pages project name**. Do not paste credentials into chat or source files.

Staging uses `cloudflare-staging`, no production routes, a separate staging Worker and a Pages preview branch. On this draft PR, adding label `r2-stage-approved` starts a staging-only run from the PR head; fork PRs cannot use this path. This supports testing before merge. A manual dispatch from the branch also checks out the selected ref when available. Initial staging requests every recorded page/redirect/image URL and checks HTTP status, image/HTML bytes, MIME, canonical-compatible HTML, HEAD, ETag, 404 and method handling. Preview responses receive `X-Robots-Tag: noindex`; production article bodies and canonical markup remain unchanged.

Before production promotion, separately obtain owner authorization, verify account-wide free-tier headroom, and configure `cloudflare-production` approval controls. Add `CF_ZONE_ID` as a repository variable and give the production token Zone Workers Routes Edit. Disable Git-triggered **Pages** production builds (the central release workflow replaces them). Do not disable the news/trending GitHub schedules. Capture current Pages/Worker configuration and retain the previous production deployment.

Root CSS, JS and branding must match the current production bytes at cutover. A simultaneous UI-asset change is refused and requires a separate compatible staged asset rollout; normal news/content releases do not change these assets.

Initial promotion requires exhaustive staging verification for the exact release, a matching remote upload receipt, explicit routing authorization in the protected production job, a successful previous Pages rollback target, and no route owned by another Worker. It snapshots rollback state, activates the five scoped routes, deploys the small Pages package, and smoke-tests production. Failure automatically restores the prior Pages deployment and release, or removes only newly added owned routes on a first migration. It never deletes article data, images or R2 objects.

After initial production has passed, set `DELIVERY_INITIAL_VERIFIED=true`, then `DELIVERY_ENABLED=true` to authorize subsequent automatic two-hour releases. Staging stays isolated from production. Do not set these flags merely to get past a failing verification.

## Rollback and maintenance

The release artifact includes `rollback.json`, verification receipts, file counts and the old release ID. R2 objects and manifests are immutable; selecting the previous release ID restores its original content, including changed images. Restore the previous successful Pages production deployment for matching root assets. The rollback code affects only the five known routes and preserves all unrelated Workers/routes. A first-cutover rollback removes newly created owned routes and returns traffic to the retained old Pages deployment. Previous successful production deployments remain available in Cloudflare; preview deployments are not production rollback targets.

If rollback itself fails, the original deployment is not declared verified; inspect the retained snapshot and use Cloudflare's production rollback UI. Live rollback has not been exercised from this workspace. Unit tests cover first-cutover route removal, previous-release restoration and retained remote objects.

No continuous polling, automatic remote cleanup, automatic lifecycle deletion or paid plan switch is installed. Storage guard failures require a deliberate retention/budget/hosting decision; they cannot be solved by fabricating news, deleting original content or hiding a quota breach.

## Verification limits

Offline preservation checks cover every one of the 24,057 baseline scoped URLs, source IDs and 2,233 image paths. SEO checks cover all 7,785 canonical URLs. Unit/Worker tests cover upload retries, corruption, receipts, deduplication, redirects, future-route isolation, build cleanup, sitemap growth, fair queues, rollback selection and route scope. Reproducible rendering is checked with the same source clock.

Actual staging upload, exhaustive HTTP validation, mobile/browser rendering, Cloudflare account usage, production deployment duration, live rollback, live propagation and a future provider-backed publishing run still require connected Cloudflare/GitHub Actions access. File-count projections or mock receipts are never reported as a verified production deployment.

Local validation completed: 210 Python tests ran (209 passed, one existing Chromium integration test skipped because the optional browser is not installed), 10 Node Worker tests passed, 7,785 canonical pages passed the SEO audit, all 24,057 baseline scoped URLs passed preservation checks, and two renders with the same source clock produced byte-identical release packages. The measured clean render took 46.382 seconds on this workspace. Baseline and real deployment durations were not measured.


## Connected Cloudflare staging handoff

A connected Cloudflare session can deploy the staging Worker and Pages preview without exporting its OAuth credential to GitHub. Label `r2-stage-data` enables a bounded preparation job only after architecture CI passes. It uses the existing R2 S3 secrets to copy and byte-verify immutable content, then publishes one immutable, checksum-checked capsule containing the 17 public Pages files and a compressed URL/checksum inventory. Nothing in the capsule is a credential. Original R2 images and source files remain intact; no route or production release is activated by this job.

The connected API can retrieve this capsule and provision a preview deployment. Full public URL checks then run against that exact release. This is an interactive migration handoff; unattended Wrangler deployment still requires the separately scoped GitHub deployment secret described above. The old one-off access diagnostic is retired once connected account access has been verified.


### Initial audit request bounds and owner setup

Initial deep verification uses eight bounded workers, a 120-minute CI ceiling and progress every 256 objects. A GET verifies SHA-256, length and checksum metadata together, avoiding redundant HEAD requests. New keys use atomic `If-None-Match: *`; a conflicting write (including a timeout after commit) is read and verified, never overwritten. Regression tests cover conflicting races and uncertain successful uploads. Cloudflare documents atomic conditional writes at https://developers.cloudflare.com/r2/api/s3/extensions/#conditional-operations-in-putobject.

The connected audit identified the active zone ID as `f4734194c8d271464724ac105f46bf4c`. The owner must save repository variable `CF_ZONE_ID` with this value for later production snapshot/routing/rollback, and `CLOUDFLARE_PAGES_PROJECT=globaltech-daily`. The GitHub plugin cannot write repository secrets or variables. Save the token directly in repository Actions secrets as `CLOUDFLARE_API_TOKEN`; never put it in chat or Git. Restrict its account resources to this account and zone resources to globewiredaily.org. Required account permissions: Cloudflare Pages Edit and Workers Scripts Edit. Production also requires Zone Read (Wrangler resolves the zone name) and Workers Routes Edit for this zone. Existing R2 S3 credentials remain unchanged. These permissions do not authorize production cutover by themselves; staging and explicit owner routing approval are still required.

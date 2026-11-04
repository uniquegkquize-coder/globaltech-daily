# AI Session Checkpoint — GlobeWireDaily audit and repair

Is file ka maqsad: koi bhi agla AI session yahan se kaam resume kar sake.
Last updated: 2026-11-04 (session 2, trending queue restructure added).

## Current branch and commits

Branch: fix/cf-usage-audit-and-trending-syntax (main se aage, PUSH NAHI kiya)

Commits (purane se naye):
1. 9dae4e0ec2 Fix literal newline-continuation syntax errors in trending_watch
2. 6d398f8ff4 Add regression guards for Pages static contract and script syntax
3. 07dedec7a5 Rebuild dist to publish articles stuck behind the syntax outage
4. 44d85183a5 Fix daily IndexNow notification failures caused by Cloudflare UA blocking
5. a2172742f7 Restore fair per-category rotation in the publication queue
6. 1dc48b7d25 Report publish outcome and category coverage in the job summary
7. 1079d23078 Add session checkpoint for AI handoff
8. (naya) Queue-based trending architecture: discovery deploy trigger nahi karta

## Trending queue restructure (Phase 6, is session me kiya)

- trending-watch.yml cron: 15-min (2,17,32,47) se '23 */4 * * *' (har 4 ghante).
- trending_watch.py: persist_post() added — TREND_QUEUE_MODE=1 par finished
  bilingual article content/posts ki jagah .cache/trending-drafts/<id>.json
  me likhta hai. Trending workflow ab git commit/push/build kuch bhi nahi
  karta → trending discovery akela Cloudflare deployment trigger NAHI karta.
- trending-watch.yml cache save/restore ab .cache/trending-drafts bhi
  cover karta hai (key prefix trending-watch-main-).
- news-auto.yml (2-hour publishing): cache/restore (restore-keys:
  trending-watch-main-) + 'Ingest trending drafts' step (scripts/
  ingest_trending_drafts.py) compileall se pehle.
- scripts/ingest_trending_drafts.py: update drafts (id live posts me hai)
  sirf tab overwrite karta hai jab draft.updated_at newer ho; new drafts
  content/pending/<id>.json me queue hote hain. Idempotent.
- Post-id consistency verified: trending digest(url)[:12] == collect
  sha256(url)[:12], isliye pending file direct match hoti hai.
- collect.py saved_drafts scan: pehle complete bilingual drafts skip hote
  the (ready_en==ready_hi:continue) — ab ready_en OR ready_hi dono ko
  first AI slots milte hain. Regression test updated.
- Tests: tests/test_trending_queue.py (7 tests: queue mode, legacy mode,
  ingest new/update/stale/invalid, workflow schedule assertions regex se —
  pyyaml CI me nahi hai isliye).

## Verified aur fixed bugs

- scripts/trending_watch.py lines 125 aur 230: literal backslash-n merged
  statements (SyntaxError). Isse Trending Watch har 15 min fail ho raha tha
  aur Auto News ka compileall gate ruka hua tha. Fix + syntax canary test.
- dist/_redirects kabhi 1-line stub ban gaya tha (partial publish bug).
  Regression test: tests/test_cloudflare_static_contract.py.
- indexnow.yml: Cloudflare default Python-urllib UA ko 403 deta hai
  (verified locally: same URL, sirf UA farak). Named bot UA added; live
  simulation pass (key verify + news-sitemap 934 URLs parsed).
- collect.py final queue sort story_priority globally laga raha tha, jisse
  hot category cluster hoti thi (evidence: news-run-status.json 2026-11-04:
  published 23, apps-software=20, 46 categories zero, time_limit_reached).
  fair_publication_order() ab stable sort se interleaving bachata hai.
  Tests: tests/test_category_fairness.py (3 tests).

## Test commands

- Full suite: python -m unittest discover -s tests
  (Termux par 1 error expected: test_website_leads... /tmp read-only —
  environment-only, CI ubuntu par pass. 2 skips bhi env-related.)
- Contract tests: python -m unittest tests.test_cloudflare_static_contract
- Fairness: python -m unittest tests.test_category_fairness
- Full production build: SITE_URL=https://globewiredaily.org python scripts/build.py
  (local Termux ~6 min; 2048 posts; SEO_REDIRECTS 2000 server + 2125 html fallback)

## Verified architecture facts (do not re-litigate)

- NO Cloudflare Workers/Functions/_worker.js/_routes.json/wrangler.toml/
  middleware/service-worker kabhi repo me the (poori git history scanned).
  Site pure static hai; Pages static requests par billing nahi hoti.
- Deploy mechanism: Cloudflare Pages Git integration — har push to main =
  ek CF build (build command: python scripts/build.py, output: dist).
- Categories: 48 (news_config.CATEGORIES). MIN_POSTS_PER_CATEGORY=2,
  POSTS_PER_RUN=100, news-auto cron 7 */2 * * * (preserve kiya gaya).
- Image pipeline already compliant: og:image/twitter:image/JSON-LD
  extraction, dimension gates (600x320), licensed attribution metadata,
  retry_after 6h cooldowns, persistent backfill cursors, modes
  mixed/directory/new/all. Phase 4/5 ke liye koi code change zaroori nahi.
- providers_ready() empty-key providers ko skip karta hai (OPENAI_API_KEY
  repo variable me blank hai — gemini primary hai; openai fallback kabhi
  try hi nahi hoga jab tak key set na ho. User ko bata dena.)

## Open items (user approval ya dashboard access chahiye)

1. CF Pages build frequency: 7-day window me 1010 commits; har push = build.
   Free plan 500 builds/month. Optimization options (approval pending):
   official-notices ka full rebuild+push har 15 min ko data-only push +
   coalesced rebuild banana; ya CF dashboard me build schedule review.
2. Repo weight: .git pack 1.38 GB (content/featured JPEG history).
   History rewrite DESTRUCTIVE hai — kabhi bina approval mat karna.
   Future-safe option: image dedupe + compressed variants.
3. Redirect fallback growth: SEO_REDIRECTS html_redirects 2111 -> 2125
   (har build me badh raha hai); dist 18k files, Pages 20k file limit ke
   kareeb. Monitoring metric hai; hard-fail test mat banana.
4. /images/* cache 86400s rakha hai kyunki image filename post-id based hai
   aur image upgrades same filename par ho sakti hain (stale risk).
5. OPENAI_API_KEY blank hai (repo variable). Chaaho to set kar do, warna
   provider chain gemini->openrouter->groq hi chalega (already graceful).

## Evidence locations

- Workflow run stats: gh run list --workflow <name> --limit 15
- news-run-status.json / news-coverage-status.json (content/)
- Category coverage: content/news-coverage-status.json (categories_below_minimum)
- Source diagnostics: collect.py run logs "SOURCE DIAGNOSTICS BEGIN/END"

## Next session suggestions (priority order)

1. User approval ke baad branch merge/push.
2. official-notices rebuild coalescing design + test (Phase 6/8).
3. Discovery queue pruning policy review (content/pending 112 MB).
4. GITHUB_STEP_SUMMARY ko directory-guides/image-backfill me bhi add karna.

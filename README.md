# GlobeWire Daily

Bilingual source-grounded publishing on Cloudflare Pages and R2.

The repository has outgrown the static Pages file limit. Read [the migration audit, staging requirements, verified limits and rollback procedure](docs/R2-DELIVERY-MIGRATION.md) before deploying this branch. Production routing is not activated by this draft.

- Source posts: `content/posts/`; saved drafts: `content/pending/`; original photos: `content/featured/`.
- News target: two posts per configured category, every two hours. Trending discovery: every four hours. Provider/source shortfalls are reported.
- Local validation: `pip install -r requirements.txt`, `python scripts/build.py --render-only`, `python -m unittest discover -s tests`, `node --test tests/delivery-worker.test.mjs`.
- R2 preparation: `python scripts/delivery_package.py`, then `python scripts/verify_delivery.py`. No upload occurs without explicit `--upload`; the release workflow performs staging checks before production promotion.
- Never commit `dist/`, `build/`, bytecode, caches or secrets. Never delete published source articles or original images to fit a hosting limit.

Automatic delivery stays disabled until the initial staged migration and production authorization are complete. This architecture removes the Pages file-count growth problem; the requested publishing volume cannot be promised free for a year within R2's verified storage allowance.

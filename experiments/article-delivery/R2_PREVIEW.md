# R2 article delivery: isolated preview

This is NOT deployed. It adds no Cloudflare routes and changes no Pages build, articles, media, redirects or automation.

## Storage contract
Use a private R2 bucket binding named `ARTICLE_HTML_BUCKET`. An existing generated file `dist/en/news/sports/example/index.html` must be uploaded with key `en/news/sports/example/index.html`. Repeat for Hindi and every category. Do not delete the original files during preview. R2 storage and operation quotas must be checked against current Cloudflare pricing; free usage is not guaranteed indefinitely.

## Preview validation
1. Deploy only `r2-preview.mjs` to an isolated workers.dev preview, with no production route.
2. Upload a small set of unchanged existing article HTML files to R2 under matching keys.
3. Test GET and HEAD for EN/HI, different categories, unknown articles (404), unsupported paths (404), and unsupported methods (405).
4. Compare canonical, hreflang, structured data, links, image/CSS URLs, HTTP status, cache response and mobile speed against the existing Pages articles.
5. Confirm missing R2 binding returns 503; simulate R2 failure and confirm 503. Validate that no private or unpublished content is uploaded.
6. Estimate requests/day, R2 storage/operations, Worker requests, and cache hit rate for at least a representative sample. Worker is invoked even on cache hits; free quota exhaustion is possible.
7. Record rollback: remove any preview route/binding and revert to existing Pages delivery.

## Before production migration
- Create a repeatable resumable R2 uploader with checksums, versioned manifest, and full backup.
- Confirm **all** published HTML exists in R2 before excluding any generated HTML from Pages.
- Ensure the Pages build stays under the 20,000-file limit, including growth forecasts and image/static assets.
- Verify sitemap URLs, existing redirects, search-engine crawling, 404 behavior, image delivery, and deployment rollback.
- Production routing must be explicitly approved after preview and quota checks. Never enable a broad route before all article keys are uploaded.

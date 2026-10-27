GlobalTech Daily — Starter ZIP
1. Upload ZIP contents to a GitHub repository (keep .github folder).
2. Connect GitHub repo to Cloudflare Pages. Build command: python scripts/build.py; output directory: dist. Set SITE_URL environment variable to https://YOURNAME.pages.dev.
3. GitHub Settings > Secrets and variables > Actions: add GEMINI_API_KEY as a secret; AUTO_POST=true as a variable. Default OFF. Settings > Actions > General: set workflow permissions to read/write.
4. Actions > Automatic news > Run workflow. Scheduled daily at 02:17 UTC; free limits may result in fewer than 10 posts.
5. Manual posting: create JSON in content/posts/ with keys id, en_title, hi_title, en_body, hi_body, source. Edit or delete with GitHub web editor; Cloudflare redeploys automatically.
6. Submit /sitemap.xml to Google Search Console. Add genuine publisher identity, privacy details, licensed images, structured data, affiliate disclosures and AdSense only after approval.
IMPORTANT: Source-backed does NOT mean independently verified. Automated publishing can be wrong. No Google Discover, AdSense or earnings guarantee. This is a functional starter, not a production-ready verified newsroom or integrated CMS.

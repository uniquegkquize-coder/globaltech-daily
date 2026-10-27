GlobalTech Daily: category + source + long-form upgrade
=====================================================
This is a PATCH ZIP. Unzip into the existing repository root, not into dist/.
It does not include or delete your existing content/posts or content/featured.

Changes:
- Categories: technology, government-schemes, sarkari-naukri, bilingual pages.
- Curated source discovery from official RSS feeds (feeds can fail/change).
- Source-grounded minimum 3000 words PER language. Posts below threshold skipped.
- Discovers compatible Gemini text models; tries fallback models only as needed.
- Existing image pipeline attempts Gemini images, and locally generated conceptual illustrations remain fallback.
- NewsArticle schema, News sitemap, AI Tools retained.
- Removes automatic old-post archiving step from Actions.

IMPORTANT: The 3000-word minimum is STRICT. Many official announcements cannot support 3000 verified words; these will be skipped. This is intentional to prevent hallucinated/padded content. Long bilingual responses can exceed model output limits, resulting in zero posts. Government RSS endpoints are best-effort; verify actual feed accessibility in Actions logs. No claim of live API testing.

Codespaces:
  unzip -o GlobalTech_Daily_Categories_3000_Word_Upgrade.zip
  python -m pip install -r requirements.txt
  python -m compileall -q scripts
  python scripts/build.py
  git add scripts/collect.py scripts/build.py scripts/generate_images.py .github/workflows/news-auto.yml
  git commit -m 'Add government schemes and jobs categories with verified longform gate'
  git pull --rebase --autostash origin main
  git push origin main

Note: A GitHub workflow may have more changes than the ZIP; inspect git diff before committing. Set AUTO_POST=true and GEMINI_API_KEY in repo settings as before. Cloudflare Pages should publish dist/ from the repository. Do not delete existing posts.

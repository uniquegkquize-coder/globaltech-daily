# GlobeWire Daily SEO recovery

`.github/workflows/seo-recovery.yml` runs the production audit at 05:53, 11:53, 17:53 and 23:53 IST once the workflow is on the default branch. Pull requests run the test suite and render an isolated Oracle-style candidate for validation. The audit uploads reports to the Actions run. It replaces the weekly CTR job, whose script and test files were absent.

The live report checks the apex and www redirects, robots directives, sitemap XML and news shards, and a rotating sample of canonical article URLs in both languages. The checkpoint stores only the crawl cursor. The source report lists duplicate groups using the publisher's story identity and category candidates using the existing editorial routing rules. Use those lists to review cases where content or taxonomy needs editorial judgment. Existing publication, deduplication, category and Oracle release jobs retain their own triggers and permissions.

## Search Console

Add a Google service account to the Search Console property `sc-domain:globewiredaily.org` with read access and enable the Search Console API for its Google Cloud project. Add its JSON credentials as the repository Actions secret `SEO_GSC_SERVICE_ACCOUNT_JSON`. Generate a Fernet key locally with `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'` and save it locally and as the repository Actions secret `SEO_GSC_REPORT_KEY`. The public repository's Actions logs and cache omit Search Console data. The artifact `search-console.json.fernet` holds the encrypted report.

After downloading the artifact, set `SEO_GSC_REPORT_KEY` locally and decrypt it with the following command. The report includes two settled seven-day windows, sampled URL Inspection results and article query-page pairs with at least 50 impressions and low CTR for their average position. The position bands are triage thresholds. Confirm the query intent and review the article before changing its SEO title or description.

```bash
python -c 'from cryptography.fernet import Fernet; from pathlib import Path; import os; Path("search-console.json").write_bytes(Fernet(os.environ["SEO_GSC_REPORT_KEY"].encode()).decrypt(Path("search-console.json.fernet").read_bytes()))'
```

Google Search Console data from October 13–November 9, 2026 informed the initial edits to Manjimup Working Holiday visas, Blinkit Cracker Joy, the UK digital landline switchover, MyJio data codes and West Bengal's Krishak Bandhu scheme. Their article IDs and URL inputs are preserved. Check the same query-page pairs after four settled weeks and compare CTR alongside average position and impressions.

## Local verification

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests
python scripts/build.py --render-only
git ls-tree -r --name-only HEAD -- dist > /tmp/globewire-legacy-files.txt
python scripts/audit_built_seo.py build/rendered --inventory content/published-url-inventory.json \
  --legacy-files /tmp/globewire-legacy-files.txt
python scripts/seo_recovery.py --output /tmp/globewire-seo-audit
```

The Oracle render uses `build/rendered` and the existing origin redirect manifest. The build report separately lists inventory URLs served by the tracked legacy layer, including old directory pages and images. Keep the Pages output and its existing asset guard separate from the Oracle candidate.

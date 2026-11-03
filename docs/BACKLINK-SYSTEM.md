# GlobeWire Daily editorial backlink system

## Scope and running it

This system researches possible editorial references, prepares review-only drafts,
and verifies source pages. It never posts backlinks, submits forms, creates
accounts, or sends email. There is no sending implementation or Gmail connection.
A candidate, draft or contact address is not an acquired backlink.

Daily at **01:43 UTC / 07:13 India time** the independent workflow researches at
most 30 candidates with a 480-second research budget. Mondays also verify imported
links (180-second budget) and save an immutable ISO-week snapshot. Manual dispatch
can request weekly verification. Tests also run on implementation pushes; research
runs only on main for schedule/dispatch. Scheduled runs begin only after merge.
GitHub can delay scheduled executions; free-runner availability is not guaranteed.

```
python -m scripts.backlinks.run --limit 30 --seconds 480
python -m scripts.backlinks.run --limit 30 --seconds 480 --weekly
python -m unittest discover -s tests -p test_backlinks.py -v
```

Dependencies: requests and BeautifulSoup, already used by the site. The dedicated
workflow installs PyYAML for workflow structure checks. Research outputs are
persisted on `backlink-data`, not main, with reports attached to each Actions run.
The code is checked out from main; only data is restored from backlink-data.
No news collection/build scripts are invoked by this workflow. Pushes of research
data do not modify or publish the website. Current site resource pages are rendered
through the existing build function when the site next builds after merge.

## Discovery, quality and growth

Candidate URLs come from existing public source lists, the actual source URLs of
stored posts, official college URLs already recorded with source provenance, and
`search-import.json`. Contact pages are discovered from real links, never guessed.
Public editorial/resource links can expand discovery. There is no Google Search
scraping. Initial search leads were found through the permitted search tool.

The **300** target refers to successfully researched, relevant prospects over time,
not 300 guaranteed placements. Candidate counts, successful research and provisional
qualified prospects are separate. Unavailable/robots-blocked domains stay candidates
with error reasons. Oldest attempted candidates rotate first; a domain is checked
at most once per day. Domains are normalized (www collapsed, subdomains retained).
The queue is bounded during expansion, with no paid APIs or secrets required.
Terms and editorial suitability must be reviewed before outreach. Robots rules are
honored on each hop; unknown robots access fails closed. A contact address does not
imply consent, suitability or an invitation to a link pitch.

Heuristic weights:

| Component | Max | Observable evidence |
|---|---:|---|
| Topical relevance | 30 | Topic detected from page or sourced category |
| Editorial credibility | 25 | Policy/about link 10; byline 10; article markup 5 |
| Content/audience signals | 20 | 300 words 10; 1,000 words 10; audience unknown |
| Placement suitability | 15 | Contact page 5; editorial invitation text 10 |
| Spam screening | 10 | No detected link-selling/reciprocal scheme signal |

Scores >=70 are provisional qualified research leads, subject to manual review.
Missing evidence earns zero. These are not DA, Google authority or traffic scores.
A heuristic cannot reliably identify every PBN/link farm; reject these in review.
Detected schemes disqualify a prospect regardless of total score. No automatic
reciprocal/paid placements are offered. Third-party publisher editorial standards
also apply: for example TechRadar Pro Perspectives explicitly rejects AI-written
submissions; its submission page is recorded as a lead, not permission to submit
these automated drafts or republish a GlobeWire article there.

## Imports and review queue

Edit these files **on backlink-data once it exists**, otherwise the initial files
on the implementation branch. Data branch contents override initial main data.

`search-import.json`: list of public URLs with provenance, optional category:

```json
[{"url":"https://publisher.example/editorial/","category":"tech-ai","discovered_from":"public search URL / research note"}]
```

The example is a schema example, not a real prospect. Category keys are tech-ai,
cars-bikes, mobiles, education, jobs-exams, sports, entertainment, travel,
defence-world, regional. Do not add fabricated contacts or pre-qualified scores.

`submissions.json`: actual known source/target pairs, optionally editorial or profile:

```json
[{"source_url":"https://publisher.example/existing-story/","target_url":"https://globewiredaily.org/en/","placement_type":"editorial"}]
```

No live backlink is implied by this example. Default placement type is unknown.
Self-created profiles must be labelled `profile`, not editorial. `drafts.json`
contains personalized messages, contact candidates, a null recipient and null
sent_at. One draft per domain prevents duplicate outreach. Before any manual send,
review the target's facts, originality and relevance; check the recipient's purpose,
editorial rules and applicable anti-spam requirements; approve an exact recipient
list explicitly. No sending step exists here, so sent count remains zero. Existing
review decisions/draft IDs are preserved when research refreshes.

## Verification and reports

`backlinks.json` distinguishes live, changed, removed, not_found, inaccessible and
rejected internal/target URLs. Exact normalized path and query are required; another
GlobeWire link is "changed", not a match. Every observed matching anchor has its
rel attributes and HTML placement recorded. Source redirects are checked and a
redirect into GlobeWire cannot count as external. First-seen is first observation,
not a claim about the original link publication date. Inaccessible pages are not
counted as live or automatically classified as lost.

`summary.json`, `REPORT.md`, CSV exports and `history/YYYY-Www.json` provide totals,
new links within seven days, current lost links, referring hostnames, per-anchor
rel distribution, target/category counts and declared placement types. Domains
are hostnames rather than registrable domains; public suffix grouping isn't claimed.
The best target list ranks observed link counts, not traffic or conversions.

`search-performance-baseline.json` stores the real available Search Console rows
and date range. The connector exposes Search Analytics, not the Links report. There
is no historical backlink inventory, competitor backlink database, API credential
or Search Console weekly refresh configured. Performance trends are independent
observations and never attributed causally to this system. Missing integrations
are limitations, not successes. A future approved export can update that baseline.

## Reference content

`link_resources.py` adds English/Hindi searchable, selectable comparison tables for
colleges (course-level eligibility/annual fee/basis), cars, motorcycles and phones;
a stored official exam-notice tracker; a task-based AI tool comparison; and a
publication-time defence coverage timeline. Source URLs and stored check dates are
retained. Missing values are marked, never invented. The defence timeline does
not pretend publication times are event dates. There is no invented benchmark,
research statistic, live price, admission deadline or current availability claim.
The pages use the site's shell, CollectionPage structured data, canonical/hreflang,
footer links and final sitemap reconciliation. Existing source-record accuracy is
not independently re-audited for every record by this backlink task.

## Competitor/resource review, 3 November 2026

No competitor backlink inventory is accessible. The following are current
first-party page observations and editorial opportunities, not measured backlink
gaps or Google ranking comparisons:

| Area | Sample reviewed | Observation / realistic next step |
|---|---|---|
| News/defence | https://news.ssbcrack.com/contact/ | Invites relevant defence story ideas; one review-only reference pitch prepared, no submission. |
| Tech | https://www.techradar.com/pro/perspectives-how-to-submit | Requires unique, exclusive, non-promotional expert submissions and prohibits AI-written submissions; automation must not submit there. |
| Cars | https://www.cardekho.com/mahindra/thar | Model/variant/specification and comparison navigation; comparable records need model-year/market basis. No outreach permission inferred. |
| Gadgets | https://www.gadgets360.com/vivo-x-fold-5-price-in-india-133304 | Product specifications and category comparison navigation; provide source-linked fields rather than unqualified live prices. |
| Education | https://www.collegedekho.com/colleges/parul-university | Course, fee, admission and placement sections; our comparison retains course-level fee basis and primary citations instead of copying claims. |
| Jobs | https://employmentnews.gov.in/NewEmp/AboutUs.aspx | Official employment publication with career/editorial sections; source official notices, not invented deadlines. |
| Entertainment | https://www.comingsoon.net/feed | Successfully read public entertainment content; no editorial contact discovered in sample, so no draft. |
| Travel | https://travelbizmonitor.com/submit-article/ | Invites editorial articles; lacks a sufficiently specific current target match, so no draft. |
| Regional | https://gogorakhpur.com/contact-gogorakhpur/ | Search found a local editorial contact page; direct research was inaccessible and remains an unqualified candidate. |

The first release researched 10 prospects successfully from live public pages,
with 5 scoring at least 70 provisionally, and 1 draft. The broader candidate pool
is 359 real recorded hostnames; it is not 359 qualified opportunities. No external
page with a GlobeWire link has been confirmed. Live negative-control verification
was inaccessible in this environment; positive/removed/changed/nofollow examples
are covered by deterministic fixtures, not claimed as acquired links.

The local environment requires opt-in proxy-side DNS resolution for permitted
outbound research (`BACKLINK_PROXY_DNS=1`). It does not bypass robots or HTTP
restrictions. Standard GitHub runners use strict public-address DNS validation.
Live sitemap reads through the restricted research fetcher fell back explicitly
to generated repository sitemaps. The site did respond HTTP 200 to a separate
header request; this is not presented as a successful live sitemap crawl.
Browser visual testing was unavailable because Chromium is not installed. Build,
HTML/JSON-LD/link checks and unit tests passed; interactive browser behavior is
covered by source inspection only. `targets.json` is a regenerated ignored cache.

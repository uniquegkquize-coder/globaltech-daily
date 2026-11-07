"""Refresh mutable directory facts independently of static specifications."""
from urllib.parse import urlparse

MUTABLE = {'price', 'fees', 'courses', 'variants', 'price_basis', 'price_valid_until', 'availability',
           'mrp_inr', 'secondary_selling_price_inr', 'secondary_price_basis'}


def refresh_fields(kind):
    return {'fees', 'courses'} if kind == 'colleges' else {'price', 'variants', 'availability'}


def refresh_sources(kind, entry):
    """Revisit known fee/offer pages, not just the static specification brochure."""
    urls = []
    for key, evidence in entry.get('field_sources', {}).items():
        if key in MUTABLE and isinstance(evidence, dict):
            urls.append(evidence.get('url', ''))
    for key in ('courses', 'variants'):
        for row in entry.get(key, []):
            if isinstance(row, dict):
                urls.append(row.get('source_url', ''))
    urls.extend(entry.get(k, '') for k in ('official_url', 'source_url', 'evidence_url'))
    result = []
    for url in urls:
        parsed = urlparse(str(url))
        if parsed.scheme not in ('https', 'http') or not parsed.hostname:
            continue
        if parsed.hostname in {'wikidata.org', 'www.wikidata.org'} or parsed.path.lower().endswith('.pdf'):
            continue
        if url not in result:
            result.append(url)
    return result


def protect_reviewed(existing, additions):
    """Static reviewed specifications stay locked; newly sourced prices can change."""
    sourced = additions.get('field_sources', {})
    for key in ('courses','variants'):
        if isinstance(existing.get(key),list) and key in additions and not isinstance(additions[key],list):
            additions.pop(key)
            sourced.pop(key,None)
    protected = set(existing.get('reviewed_fields', [])) - {'field_sources','source_url','evidence_url','official_url'}
    protected -= {k for k in MUTABLE if k in additions and isinstance(sourced.get(k), dict) and sourced[k].get('url')}
    for key in protected:
        additions.pop(key, None)
    if protected:
        for key in ('source_url','evidence_url','official_url'):
            additions.pop(key, None)
        additions['field_sources'] = {k: v for k, v in sourced.items() if k not in protected}
    return additions


def merge_rows(previous, incoming):
    """Replace refreshed source snapshots; retain rows from unvisited pages.

    This also removes obsolete numeric fee columns when a source changes its
    labels or programme title, instead of showing old and new fees together.
    """
    sources = {r.get('source_url') for r in incoming if isinstance(r,dict) and r.get('source_url')}
    combined = [r for r in previous if not isinstance(r,dict) or r.get('source_url') not in sources]
    def identity(row):
        if not isinstance(row, dict):
            return None
        name = next((str(row[k]).casefold() for k in ('course','courses','programme','programmes','variant') if row.get(k)), '')
        if not name:
            return None
        return (name, row.get('source_url', ''), row.get('entry_mode', ''),
                row.get('duration', ''), row.get('academic_year', ''), row.get('market', ''))
    for row in incoming:
        key = identity(row)
        index = next((i for i, old in enumerate(combined) if key is not None and identity(old) == key), None)
        if index is not None:
            combined[index] = {**combined[index], **row}
        elif row not in combined:
            combined.append(row)
    return combined[:300]

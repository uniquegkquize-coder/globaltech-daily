"""Conservative presentation repairs shared by publishing and static builds."""
import re


def aligned_hindi_title(english, hindi):
    """Preserve an explicitly future Indian launch in the translated headline."""
    future = re.search(r'\b(?:to launch|preparing to launch|expected to launch|set to launch)\b', english, re.I)
    if future and re.search(r'\bin India\b', english, re.I):
        hindi = re.sub(r'भारत में लॉन्च(?=\s*(?:[–—:।]|$))', 'भारत में लॉन्च की तैयारी', hindi)
    return hindi


def normalize_post(post):
    """Return a copy; preserve saved records, article slugs and category history."""
    try:
        from .news_config import route_category
    except ImportError:
        from news_config import route_category
    result = dict(post)
    if (not post.get('manual_category_mode') and not post.get('directory_kind')
            and post.get('content_type') != 'evergreen_directory_guide'):
        old = post.get('category', 'technology')
        new = route_category(post.get('en_title') or post.get('source_title', ''), old, post.get('source', ''))
        if new != old:
            result['previous_categories'] = sorted(set(post.get('previous_categories', [])) | {old})
            result['category'] = new
    for field in ('hi_title', 'hi_seo_title'):
        if post.get(field):
            result[field] = aligned_hindi_title(str(post.get('en_title', '')), str(post[field]))
    return result

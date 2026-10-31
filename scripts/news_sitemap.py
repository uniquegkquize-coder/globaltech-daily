"""Generate bounded Google News sitemaps without dropping recent articles."""
import datetime as dt
from xml.sax.saxutils import escape


def write_news_sitemap(out, site, posts, article_path, title, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    entries = []
    for post in posts:
        try:
            published = dt.datetime.fromisoformat(post['date'].replace('Z', '+00:00'))
            if published.tzinfo is None:
                continue
            age = (now - published).total_seconds()
            if not 0 <= age <= 172800:
                continue
        except (ValueError, KeyError, TypeError):
            continue
        for lang in ('en', 'hi'):
            entries.append('<url><loc>' + escape(site + article_path(post, lang))
                + '</loc><news:news><news:publication><news:name>GlobeWire Daily</news:name>'
                + '<news:language>' + lang + '</news:language></news:publication>'
                + '<news:publication_date>' + escape(post['date']) + '</news:publication_date>'
                + '<news:title>' + escape(title(post, lang)) + '</news:title></news:news></url>')
    header = '<?xml version="1.0" encoding="UTF-8"?>'
    urlset = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">'
    active = set()
    if len(entries) <= 1000:
        root = header + urlset + ''.join(entries) + '</urlset>'
    else:
        children = []
        for start in range(0, len(entries), 1000):
            name = f'news-sitemap-{start // 1000 + 1}.xml'
            active.add(name)
            (out / name).write_text(header + urlset + ''.join(entries[start:start + 1000]) + '</urlset>', encoding='utf-8')
            children.append('<sitemap><loc>' + escape(site + '/' + name) + '</loc></sitemap>')
        root = header + '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(children) + '</sitemapindex>'
    (out / 'news-sitemap.xml').write_text(root, encoding='utf-8')
    for path in out.glob('news-sitemap-[0-9]*.xml'):
        if path.name not in active:
            path.unlink()

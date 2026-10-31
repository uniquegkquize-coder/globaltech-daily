"""Bounded direct discovery for launches; search engines remain a fallback.
Sources supply leads for original reporting, never permission to copy articles.
"""
NATIVE_FEEDS=[
 ('https://www.firstshowing.net/feed/','movies-entertainment','firstshowing.net'),
 ('https://www.comingsoon.net/feed','movies-entertainment','comingsoon.net'),
 ('https://www.motor1.com/rss/news/all/','automobiles','motor1.com'),
 ('https://www.carscoops.com/feed/','automobiles','carscoops.com'),
 ('https://insideevs.com/rss/news/all/','automobiles','insideevs.com'),
 ('https://www.gsmarena.com/rss-news-reviews.php3','technology','gsmarena.com'),
 ('https://www.androidauthority.com/feed/','technology','androidauthority.com'),
 ('https://www.sammobile.com/feed/','technology','sammobile.com'),
 ('https://9to5google.com/feed/','technology','9to5google.com'),
 ('https://variety.com/feed/','movies-entertainment','variety.com'),
 ('https://deadline.com/feed/','movies-entertainment','deadline.com'),
 ('https://www.hollywoodreporter.com/feed/','movies-entertainment','hollywoodreporter.com'),
 ('https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml','movies-entertainment','bbc.co.uk'),
]
# CarDekho and IMDb returned 403 in verification. Keep them in search
# discovery only; do not repeatedly fetch their blocked listing pages.
PAGES=[
 ('https://www.androidpolice.com/','technology','androidpolice.com'),
 ('https://www.firstshowing.net/','movies-entertainment','firstshowing.net'),
 ('https://www.comingsoon.net/hub/movie-news','movies-entertainment','comingsoon.net'),
 ('https://about.netflix.com/en/news','movies-entertainment','about.netflix.com'),
 ('https://www.autocarindia.com/car-news','automobiles','autocarindia.com'),
 ('https://www.carscoops.com/','automobiles','carscoops.com'),
 ('https://www.motor1.com/news/','automobiles','motor1.com'),
 ('https://www.gadgets360.com/mobiles/news','technology','gadgets360.com'),
 ('https://www.gsmarena.com/news.php3','technology','gsmarena.com'),
 ('https://news.samsung.com/global/','technology','news.samsung.com'),
 ('https://www.apple.com/newsroom/','technology','apple.com'),
 ('https://www.netflix.com/tudum/topics/news','movies-entertainment','netflix.com'),
 ('https://www.sonypictures.com/movies','movies-entertainment','sonypictures.com'),
 ('https://variety.com/v/film/','movies-entertainment','variety.com'),
 ('https://deadline.com/v/film/','movies-entertainment','deadline.com'),
 ('https://apnews.com/hub/entertainment','movies-entertainment','apnews.com'),
]
SEARCH_SOURCES=[
 ('phonearena.com','mobile-launches','smartphone launch specifications price'),
 ('androidpolice.com','mobile-launches','new phone launch specifications'),
 ('cardekho.com','car-launches','new car launch price mileage'),
 ('motor1.com','car-launches','new car debut price specifications'),
 ('carscoops.com','car-launches','new model unveiled price'),
 ('insideevs.com','car-launches','new electric car launch range'),
 ('gadgets360.com','mobile-launches','smartphone launched price specifications'),
 ('androidauthority.com','mobile-launches','phone launch price specifications'),
 ('sammobile.com','mobile-launches','Galaxy phone launch specifications'),
 ('9to5google.com','mobile-launches','Pixel phone launch price'),
 ('imdb.com','movie-releases','movie release date trailer'),
 ('netflix.com','movie-releases','tudum movie release date'),
 ('sonypictures.com','movie-releases','movie theatrical release trailer'),
 ('hollywoodreporter.com','movie-releases','movie release date trailer'),
 ('apnews.com','controversies','entertainment controversy allegations response'),
 ('reuters.com','controversies','public dispute controversy response'),
 ('variety.com','controversies','film controversy backlash response'),
 ('hollywoodreporter.com','controversies','controversy allegations response'),
]

# Publishers expose article copy through different containers. No login,
# paywall, CAPTCHA, blocked-response or alternate-route bypass is attempted.
ARTICLE_SELECTORS=(
 '.content_text', '.content-text', '.news-text', '#review-body', '.review-body', '.entry', '.postContent', '.post-content',
 '.article__body', '.article-body', '.article__content', '.article-content',
 '.story_details', '.story__content', '.entry-content',
 '[data-component="text-block"]', '[data-testid="paragraph"]',
)

def structured_article_data(soup):
    import json
    bodies=[];dates=[]
    def visit(obj,depth=0):
        if depth>12:return
        if isinstance(obj,list):
            for value in obj:visit(value,depth+1)
        elif isinstance(obj,dict):
            # Restrict extraction to actual Article schema objects.
            kind=obj.get('@type','')
            if not isinstance(kind,list):kind=[kind] if isinstance(kind,str) else []
            if any(str(k).endswith('Article') or k in ('Report','BlogPosting') for k in kind):
                if isinstance(obj.get('articleBody'),str):bodies.append(obj['articleBody'])
                if isinstance(obj.get('datePublished'),str):dates.append(obj['datePublished'])
            for value in obj.values():
                if isinstance(value,(dict,list)):visit(value,depth+1)
    for script in soup.select('script[type="application/ld+json"]'):
        try:visit(json.loads(script.string or script.get_text() or '{}'))
        except (ValueError,TypeError,RecursionError):continue
    return bodies,dates

def content_candidates(soup,clean):
    values=[]
    for selector in ARTICLE_SELECTORS:
        for node in soup.select(selector)[:4]:
            paras=[clean(p.get_text(' ',strip=True)) for p in node.find_all(['p','h2','h3','li'])]
            if node.name=='p':paras=[clean(node.get_text(' ',strip=True))]
            paras=list(dict.fromkeys(p for p in paras if len(p)>35))
            if paras:values.append('\n'.join(paras))
    # Some publishers use nonsemantic wrappers. Only use public paragraphs
    # when the page explicitly declares itself an article, never a listing.
    if soup.select_one('meta[property="og:type"][content="article"]') and max((len(v.split()) for v in values),default=0)<65:
        paragraphs=[clean(p.get_text(' ',strip=True)) for p in soup.find_all('p')]
        paragraphs=list(dict.fromkeys(p for p in paragraphs if len(p)>60))[:25]
        if paragraphs:values.append('\n'.join(paragraphs))
    return values

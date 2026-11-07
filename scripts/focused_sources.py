"""Bounded direct discovery for launches; search engines remain a fallback.
Sources supply leads for original reporting, never permission to copy articles.
"""
NATIVE_FEEDS=[
 ('https://www.apple.com/newsroom/rss-feed.rss','technology','apple.com'),
 ('https://news.samsung.com/global/feed','technology','news.samsung.com'),
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

# Regional RSS and named local publishers supplement broad search discovery.
LOCAL_FEEDS=[
 ("https://www.amarujala.com/rss/gorakhpur.xml","india-news","amarujala.com"),
 ("https://www.amarujala.com/rss/kushinagar.xml","india-news","amarujala.com"),
 ("https://www.amarujala.com/rss/deoria.xml","india-news","amarujala.com"),
 ("https://www.amarujala.com/rss/basti.xml","india-news","amarujala.com"),
 ("https://www.amarujala.com/rss/sant-kabir-nagar.xml","india-news","amarujala.com"),
 ("https://www.amarujala.com/rss/maharajganj.xml","india-news","amarujala.com"),
 ("https://www.amarujala.com/rss/lucknow.xml","india-news","amarujala.com"),
 ("https://www.amarujala.com/rss/varanasi.xml","india-news","amarujala.com"),
 ("https://www.amarujala.com/rss/kanpur.xml","india-news","amarujala.com"),
 ("https://www.amarujala.com/rss/uttar-pradesh.xml","india-news","amarujala.com"),
 ("https://www.amarujala.com/rss/uttarakhand.xml","india-news","amarujala.com"),
 ("https://www.amarujala.com/rss/bihar.xml","india-news","amarujala.com"),
 ("https://www.amarujala.com/rss/madhya-pradesh.xml","india-news","amarujala.com"),
 ("https://www.amarujala.com/rss/rajasthan.xml","india-news","amarujala.com"),
 ("https://www.amarujala.com/rss/haryana.xml","india-news","amarujala.com"),
 ("https://www.amarujala.com/rss/punjab.xml","india-news","amarujala.com"),
 ("https://feeds.bbci.co.uk/news/england/rss.xml","world-news","bbc.co.uk"),
 ("https://feeds.bbci.co.uk/news/scotland/rss.xml","world-news","bbc.co.uk"),
 ("https://feeds.bbci.co.uk/news/wales/rss.xml","world-news","bbc.co.uk"),
 ("https://feeds.bbci.co.uk/news/northern_ireland/rss.xml","world-news","bbc.co.uk"),
 ("https://www.theguardian.com/uk-news/rss","world-news","theguardian.com"),
 ("https://www.theguardian.com/us-news/rss","world-news","theguardian.com"),
 ("https://www.theguardian.com/australia-news/rss","world-news","theguardian.com"),
 ("https://www.aljazeera.com/xml/rss/all.xml","world-news","aljazeera.com"),
]
LOCAL_SEARCH_SOURCES=[
 ("livehindustan.com","IN","hi","hi"),
 ("jagran.com","IN","hi","hi"),
 ("bhaskar.com","IN","hi","hi"),
 ("hindi.news18.com","IN","hi","hi"),
 ("inextlive.com","IN","hi","hi"),
 ("dainikgorakhpur.com","IN","hi","hi"),
 ("indianexpress.com","IN","en-IN","en"),
 ("hindustantimes.com","IN","en-IN","en"),
 ("thehindu.com","IN","en-IN","en"),
 ("deccanherald.com","IN","en-IN","en"),
 ("onmanorama.com","IN","en-IN","en"),
 ("newindianexpress.com","IN","en-IN","en"),
 ("patch.com","US","en-US","en"),
 ("apnews.com","US","en-US","en"),
 ("bbc.com","GB","en-GB","en"),
 ("theguardian.com","GB","en-GB","en"),
 ("cbc.ca","CA","en-CA","en"),
 ("abc.net.au","AU","en-AU","en"),
 ("rnz.co.nz","NZ","en-NZ","en"),
 ("stuff.co.nz","NZ","en-NZ","en"),
 ("groundup.org.za","ZA","en-ZA","en"),
 ("news24.com","ZA","en-ZA","en"),
 ("nation.africa","KE","en-KE","en"),
 ("standardmedia.co.ke","KE","en-KE","en"),
 ("premiumtimesng.com","NG","en-NG","en"),
 ("ghanaweb.com","GH","en-GH","en"),
 ("dawn.com","PK","en-PK","en"),
 ("thedailystar.net","BD","en-BD","en"),
 ("kathmandupost.com","IN","en-IN","en"),
 ("rappler.com","PH","en-PH","en"),
 ("inquirer.net","PH","en-PH","en"),
 ("malaymail.com","MY","en-MY","en"),
 ("antaranews.com","ID","id","id"),
 ("kompas.com","ID","id","id"),
 ("bangkokpost.com","TH","en","en"),
 ("france24.com","FR","fr","fr"),
 ("dw.com","DE","de","de"),
 ("elpais.com","ES","es","es"),
 ("g1.globo.com","BR","pt-BR","pt-419"),
 ("japantimes.co.jp","JP","en","en"),
]
NATIVE_FEEDS.extend(LOCAL_FEEDS)

# CarDekho and IMDb returned 403 in verification. Keep them in search
# discovery only; do not repeatedly fetch their blocked listing pages.
PAGES=[
 ('https://www.bikewale.com/news/','automobiles','bikewale.com'),
 ('https://www.autocarindia.com/bike-news','automobiles','autocarindia.com'),
 ('https://www.androidpolice.com/','technology','androidpolice.com'),
 ('https://www.firstshowing.net/','movies-entertainment','firstshowing.net'),
 ('https://www.comingsoon.net/hub/movie-news','movies-entertainment','comingsoon.net'),
 ('https://about.netflix.com/en/newsroom','movies-entertainment','about.netflix.com'),
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
 ('bikewale.com','automobiles','motorcycle scooter launch specifications price'),
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
 '[itemprop="articleBody"]', 'article',
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

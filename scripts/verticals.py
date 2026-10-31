"""International coverage registry and source-grounded reporting requirements."""
CATEGORIES={
 'cricket':('Cricket','क्रिकेट'), 'car-launches':('Car Launches, Prices & Mileage','कार लॉन्च, कीमत और माइलेज'),
 'mobile-launches':('Mobile Launches & Specifications','मोबाइल लॉन्च और स्पेसिफिकेशन'),
 'movie-releases':('Movie Releases & Trailers','फिल्म रिलीज और ट्रेलर'),
 'celebrity-news':('Actors & Celebrity News','एक्टर और सेलिब्रिटी'),
 'entertainment-rumours':('Entertainment Rumours','मनोरंजन की अपुष्ट खबरें'),
 'controversies':('Public Controversies','सार्वजनिक विवाद'), 'social-media':('TikTok, Instagram & Social Media','टिकटॉक, इंस्टाग्राम और सोशल मीडिया'),
 'defence':('Defence & Armed Forces','रक्षा और सेनाएँ'), 'conflict-news':('War & Conflict News','युद्ध और संघर्ष'),
 'military-tech':('Military Vehicles & Technology','सैन्य वाहन और टेक्नोलॉजी'),
 'tourism':('Tourism & Destinations','पर्यटन और घूमने की जगहें'),
 'travel-packages':('Tour Packages & Travel Offers','टूर पैकेज और ट्रैवल ऑफर्स'),
 'study-abroad':('Study Abroad','विदेश में पढ़ाई'), 'visas-immigration':('Visas & Immigration Updates','वीजा और इमिग्रेशन'),
 'freebies':('Freebies & Free Offers','फ्रीबीज़ और मुफ्त ऑफर्स'),
 'ev-clean-energy':('EVs & Clean Energy','ईवी और क्लीन एनर्जी'), 'space-news':('Space & Astronomy','अंतरिक्ष और खगोल विज्ञान'),
}
PATTERNS={
 'cricket':r'\b(?:cricket|ipl|t20|odi|ashes|icc|bcci|wicket|batting|bowling)\b|क्रिकेट|विकेट',
 'car-launches':r'\b(?:launch|unveil|debut|specification|mileage|fuel economy|variant|price|pricing)\b|लॉन्च|माइलेज|कीमत',
 'mobile-launches':r'(?=.*\b(?:phone|smartphone|iphone|galaxy|pixel|oneplus|xiaomi)\b)(?=.*\b(?:launch|price|specifications?|unveil|release|camera|battery)\b)|मोबाइल लॉन्च',
 'entertainment-rumours':r'rumou?r|unconfirmed|reportedly.*(?:cast|film|actor|dating)|अफवाह|अपुष्ट',
 'movie-releases':r'\b(?:movie|film|cinema|trailer|box office)\b.*\b(?:release|launch|premiere|debut|trailer)\b|फिल्म रिलीज|ट्रेलर',
 'celebrity-news':r'\b(?:actor|actress|celebrity|celebrities|bollywood|hollywood star)\b|अभिनेता|अभिनेत्री|सेलिब्रिटी',
 'controversies':r'controversy|controversial|backlash|public dispute|विवाद|विवादित',
 'social-media':r'\b(?:tiktok|instagram|facebook|youtube|threads|snapchat|social media|creator economy)\b|टिकटॉक|इंस्टाग्राम',
 'military-tech':r'\b(?:armou?r|tank|fighter jet|warship|military vehicle|missile defence|air defence|naval ship)\b|सैन्य वाहन|लड़ाकू विमान|युद्धपोत',
 'conflict-news':r'\b(?:ceasefire|invasion|conflict|war zone|peace talks|airstrike|battlefield)\b|युद्ध|संघर्ष|युद्धविराम',
 'defence':r'\b(?:defence|defense|army|navy|air force|armed forces|pentagon|nato)\b|सेना|नौसेना|रक्षा मंत्रालय',
 'study-abroad':r'study abroad|international students?|student visa|overseas education|विदेश.*पढ़ाई|विदेश.*शिक्षा',
 'visas-immigration':r'\b(?:visa|immigration|entry requirement|passport rule)\b|वीजा|इमिग्रेशन',
 'travel-packages':r'tour package|holiday package|vacation package|travel deal|टूर पैकेज|यात्रा पैकेज',
 'tourism':r'\b(?:tourism|tourist|destination|sightseeing|travel guide|national park)\b|पर्यटन|पर्यटक|घूमने',
 'freebies':r'\b(?:freebie|freebies|free sample|free trial|free giveaway|free game)\b|मुफ्त ऑफर|फ्रीबी',
 'ev-clean-energy':r'electric vehicle|clean energy|ev charging|renewable energy|इलेक्ट्रिक वाहन|स्वच्छ ऊर्जा',
 'space-news':r'\b(?:nasa|esa|isro|space telescope|spacecraft|astronaut|exoplanet|rocket launch)\b|अंतरिक्ष|खगोल',
}
SCOPES={
 'car-launches':{'automobiles','car-launches','ev-clean-energy'},
 'entertainment-rumours':{'movies-entertainment','movie-releases','celebrity-news','entertainment-rumours'},
 'celebrity-news':{'movies-entertainment','movie-releases','celebrity-news'},
 'movie-releases':{'movies-entertainment','movie-releases','celebrity-news'},
}
SOURCES=[
 ('icc-cricket.com','cricket','cricket news'),('espncricinfo.com','cricket','cricket latest'),('bbc.com','cricket','cricket'),
 ('global.toyota','car-launches','new model specifications price'),('hyundai.news','car-launches','new model launch specifications'),('media.ford.com','car-launches','vehicle launch'),('autocarindia.com','car-launches','launch price mileage'),('caranddriver.com','car-launches','new car specifications'),
 ('news.samsung.com','mobile-launches','Galaxy launch specifications'),('apple.com','mobile-launches','newsroom iPhone launch'),('blog.google','mobile-launches','Pixel phone specifications'),('gsmarena.com','mobile-launches','phone launch price specifications'),
 ('variety.com','movie-releases','film release trailer'),('deadline.com','movie-releases','movie release'),
 ('hollywoodreporter.com','celebrity-news','actor interview'),('people.com','celebrity-news','actor news'),
 ('deadline.com','entertainment-rumours','casting reportedly'),('variety.com','entertainment-rumours','casting talks'),
 ('bbc.com','controversies','public controversy'),('theguardian.com','controversies','public dispute'),
 ('newsroom.tiktok.com','social-media','TikTok news'),('about.fb.com','social-media','Instagram creator update'),('blog.youtube','social-media','creator news'),
 ('nato.int','defence','news'),('gov.uk','defence','Ministry Defence news'),('pib.gov.in','defence','Ministry Defence'),('defensenews.com','defence','military'),
 ('un.org','conflict-news','ceasefire peace conflict'),('bbc.com','conflict-news','war ceasefire'),('aljazeera.com','conflict-news','conflict'),
 ('army.mil','military-tech','vehicle technology'),('navy.mil','military-tech','ship technology'),('af.mil','military-tech','aircraft technology'),('janes.com','military-tech','defence technology'),
 ('visitbritain.org','tourism','tourism destination'),('japan.travel','tourism','travel destination'),('tourism.australia.com','tourism','tourism news'),('untourism.int','tourism','tourism news'),
 ('intrepidtravel.com','travel-packages','tour offer'),('gadventures.com','travel-packages','travel tour offer'),('tui.com','travel-packages','holiday offer'),
 ('educationusa.state.gov','study-abroad','international study application'),('study-uk.britishcouncil.org','study-abroad','study UK application scholarship'),('studyaustralia.gov.au','study-abroad','student application'),('daad.de','study-abroad','study Germany scholarship'),
 ('gov.uk','visas-immigration','student visa update'),('travel.state.gov','visas-immigration','student visa update'),('canada.ca','visas-immigration','study permit update'),('immi.homeaffairs.gov.au','visas-immigration','visa student update'),
 ('store.epicgames.com','freebies','free games'),('gog.com','freebies','giveaway'),('freekaamaal.com','freebies','free samples'),('desidime.com','freebies','free offers'),
 ('electrek.co','ev-clean-energy','electric vehicles'),('energy.gov','ev-clean-energy','clean energy'),('science.nasa.gov','space-news','space news'),('esa.int','space-news','space news'),
]
DIRECT=[('https://www.icc-cricket.com/news','cricket','icc-cricket.com'),('https://news.samsung.com/global/','mobile-launches','news.samsung.com'),('https://about.fb.com/news/','social-media','about.fb.com'),('https://newsroom.tiktok.com/','social-media','newsroom.tiktok.com'),('https://www.nato.int/','defence','nato.int'),('https://educationusa.state.gov/your-5-steps-us-study','study-abroad','educationusa.state.gov')]
TRUSTED_ENTERTAINMENT=('variety.com','deadline.com','hollywoodreporter.com','people.com','bbc.com','bbc.co.uk','theguardian.com','news.abplive.com')
REQUIREMENTS={
 'car-launches':'Cover model and market/country, launch versus announcement, variant-wise price with currency and ex-showroom/on-road distinction, engine or battery, transmission, power, safety and availability. Report mileage/range ONLY with stated test cycle (ARAI/WLTP/EPA) and units. Separate manufacturer claims from independently measured results. Mark absent facts as not announced; never estimate missing specifications.',
 'mobile-launches':'Cover confirmed model, launch country/date, variant-wise local price/currency, display, chipset, RAM/storage, cameras, battery, charging, software support, availability and official product link. Distinguish announced, preorder, on-sale and leaked specifications. Never combine different regional variants.',
 'movie-releases':'Cover film title, original language, confirmed release date by country, theatrical versus streaming release, credited cast/director, official trailer/distributor links and release-date uncertainty. Do not invent runtimes, ratings, OTT partners or box-office totals.',
 'cricket':'Cover teams, competition, venue, match date and time zone, format and source-confirmed result/score. Distinguish scheduled, live and completed matches. Never invent live scores, injuries or team selections.',
 'entertainment-rumours':'Use only attributable reporting from established entertainment publications. Put Reported/Unconfirmed or अपुष्ट in the headline and opening when not officially confirmed. Explain what is and is not confirmed. Do not publish private-person gossip or uncorroborated accusations of serious wrongdoing, intimate conduct or health matters.',
 'controversies':'Attribute allegations and responses precisely, distinguish accusation from finding, and include relevant denials where the source provides them. Do not convert social-media speculation into facts or fabricate a response.',
 'social-media':'Explain official platform feature/policy, eligible countries/accounts, rollout versus general availability, creator/user impact and original announcement links. Do not invent earnings or imply availability in restricted markets.',
 'defence':'Report public, high-level defence news and clearly attribute official claims. No tactical targeting guidance, weapon construction instructions, operational vulnerabilities or unverified casualty claims.',
 'conflict-news':'Attribute disputed claims, label unverified reports, state event date and location, distinguish official claims from independently established facts, and avoid real-time tactical targeting details. Never fabricate casualty counts.',
 'military-tech':'Describe publicly released platform/armour/vehicle specifications at a news-explainer level, procurement context and source. Avoid weapon construction, targeting instructions and exploitable operational details.',
 'tourism':'Cover destination/country, seasonal considerations, practical transport context and official tourism/advisory links. Distinguish evergreen guidance from a new announcement and never guarantee safety or entry.',
 'travel-packages':'State operator, destination, duration, departure market, currency, per-person versus total price, occupancy, inclusions/exclusions, travel dates, booking expiry and official booking/terms link only when supplied. Mark missing details unknown. Do not represent an unverified or expired offer as active.',
 'study-abroad':'Cover country/program/intake, eligibility, required documents, language tests, official application process, tuition/currency, funding and visa-authority links where verified. Say what varies by institution. Never guarantee admission, scholarship or visa; do not invent fees or deadlines.',
 'visas-immigration':'Use the issuing government authority as the source for procedural changes, identify affected nationalities, effective date and official guidance. Do not invent legal requirements, fees, processing times or guarantees.',
 'freebies':'State merchant, country, eligibility, exact free item, stock/date restrictions, shipping/other costs, trial auto-renewal terms and official redemption link only if verified. Distinguish free from paid membership or purchase-required promotions. Never call an unverified offer live.',
 'deals-offers':'State merchant, market, currency, product/variant, verified price, eligibility, coupon terms, expiry and official store link. Never invent discount percentages, compare unsupported reference prices or imply current availability without dated evidence.',
}

def requirements(category):
    if category=='celebrity-news':return REQUIREMENTS['entertainment-rumours'].replace('Put Reported/Unconfirmed or अपुष्ट in the headline and opening when not officially confirmed.','Label any unconfirmed claim clearly.')
    return REQUIREMENTS.get(category,'')


def unconfirmed_story(title):
    import re
    text=str(title)
    # The title of Neil Simon’s play Rumors is not an unconfirmed report.
    if re.search(r"neil simon|नील साइमन",text,re.I):return False
    return bool(re.search(r"rumou?r|unconfirmed|अफवाह|अपुष्ट",text,re.I))

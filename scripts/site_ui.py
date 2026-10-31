"""Shared navigation layout and Hindi interface labels."""
MENU_CSS = '''
/* Anchor the desktop dropdown inside the rightmost header column. */
@media(min-width:1000px){
 .top .wrap{grid-template-columns:auto minmax(0,1fr) auto!important}
 .top .wrap .category-menu{justify-self:end;margin-left:0}
}
.top .wrap .category-menu .nav-more[open] .nav-more-list{
 right:0!important;left:auto!important;width:min(400px,calc(100vw - 32px))!important;
 overflow-x:hidden!important;box-sizing:border-box;
}
@media(max-width:999px){
 .top .wrap{display:flex!important;flex-wrap:wrap;gap:10px;padding-top:12px;padding-bottom:10px}
 .top .wrap .logo{order:1}
 .top .wrap .category-menu{order:2;margin-left:auto}
 .top .wrap nav[aria-label="Primary"]{order:3;flex:0 0 100%;min-width:0;margin-top:0;overflow-x:auto!important;flex-wrap:nowrap!important}
 .top .wrap nav[aria-label="Primary"] a{flex:none}
 .top .wrap .category-menu .nav-more[open] .nav-more-list{
  position:fixed!important;left:12px!important;right:12px!important;top:126px!important;
  width:auto!important;max-width:none!important;max-height:calc(100dvh - 142px)!important;
  overflow-y:auto!important;overscroll-behavior:contain;z-index:99999!important;
 }
}
'''

HI = {
 'Worldwide news, movies, entertainment, technology, business, sports and useful explainers.': 'दुनिया, मनोरंजन, टेक्नोलॉजी, कारोबार और खेल की खबरें व उपयोगी जानकारी।',
 'WORLDWIDE NEWS & EXPLAINERS': 'दुनियाभर की खबरें और आसान जानकारी',
 'Explore AI tools': 'AI टूल्स खोजें', 'Our approach': 'हमारा तरीका',
 'Read original sources. Check dates. Explain what matters. Corrections welcome.': 'मूल स्रोत और तारीख जांचें। जरूरी बात आसान भाषा में समझें। सुधार के सुझावों का स्वागत है।',
 'Independent bilingual news and explainers, with clear sourcing, corrections and transparent editorial standards.': 'हिंदी और अंग्रेजी में खबरें व जानकारी, स्पष्ट स्रोतों, सुधार की व्यवस्था और पारदर्शी संपादकीय मानकों के साथ।',
 'About': 'हमारे बारे में', 'Privacy': 'गोपनीयता', 'Contact': 'संपर्क',
 'Editorial': 'संपादकीय नीति', 'Corrections': 'सुधार', 'Affiliate': 'एफिलिएट जानकारी', 'Tools': 'टूल्स',
 'Assistant': 'सहायक', 'Research': 'रिसर्च', 'Developer': 'डेवलपर', 'Design': 'डिजाइन',
 'Writing, reasoning and coding': 'लेखन, तर्क और कोडिंग',
 'Multimodal AI assistant': 'टेक्स्ट, चित्र और अन्य माध्यमों के लिए AI सहायक',
 'Writing and analysis': 'लेखन और विश्लेषण',
 'Research with linked sources': 'स्रोतों के लिंक के साथ रिसर्च',
 'Research from your own sources': 'अपने दस्तावेजों और स्रोतों पर रिसर्च',
 'Experiment with Gemini models': 'Gemini मॉडल के साथ प्रयोग',
 'Explore models and datasets': 'मॉडल और डेटासेट खोजें',
 'Visual content design': 'चित्र और विजुअल डिजाइन',
}


def label(text, lang):
    return HI.get(text, text) if lang == 'hi' else text

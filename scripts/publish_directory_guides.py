"""Publish two source-attributed evergreen directory explainers per run.
These are dated guides, NOT newly launched products or fresh breaking news.
"""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
POSTS=ROOT/'content'/'posts'
KINDS=('colleges','phones','cars','bikes')
CATEGORY={'colleges':'education','phones':'gadgets','cars':'automobiles','bikes':'automobiles'}
SUBJECT={'colleges':'college','phones':'phone','cars':'car','bikes':'motorcycle'}
LABEL={'colleges':'college admissions','phones':'smartphone specifications','cars':'car specifications','bikes':'motorcycle specifications'}

def read(path):
    try:
        value=json.loads(path.read_text(encoding='utf-8'))
        return value if isinstance(value,dict) else {}
    except (OSError,ValueError):
        return {}

def candidates():
    records=read(ROOT/'content'/'directory-records.json')
    details=read(ROOT/'content'/'directory-details.json')
    for kind in KINDS:
        seen=set()
        for name,entry in (details.get(kind) or {}).items():
            if not isinstance(entry,dict):continue
            source=entry.get('official_url') or entry.get('source_url')
            if source and source.startswith('https://'):
                seen.add(name.casefold())
                yield kind,name,entry,source
        for entry in records.get(kind,[]):
            if not isinstance(entry,dict):continue
            name=str(entry.get('name','')).strip()
            if not name or name.casefold() in seen:continue
            source=entry.get('official_url') or entry.get('source_url')
            if source and source.startswith('https://'):
                seen.add(name.casefold())
                yield kind,name,entry,source

def article(kind,name,entry,source):
    now=dt.datetime.now(dt.timezone.utc).isoformat()
    country=entry.get('country') or 'not recorded'
    fields=[(k.replace('_',' ').title(),str(v)) for k,v in entry.items()
            if k not in ('source','source_url','official_url','retrieved_at','name','country')
            and isinstance(v,(str,int,float)) and str(v).strip()]
    facts='\n'.join('- **'+k+':** '+v for k,v in fields[:15]) or '- Detailed specifications are not yet available from this source.'
    topic=SUBJECT[kind]
    intro=f'{name} is listed in our worldwide {topic} directory. Country or market recorded: {country}. This is an evergreen reference guide, not a new launch or a claim that the institution or product was recently announced.'
    sections={
      'colleges':('How to check courses and eligibility','Find the current programme catalogue on the institution website. Compare prerequisites, required qualifications, language tests, admission tests, application deadlines and international-student conditions.','Fees, scholarships and placement reports','Fees depend on course, intake, residency and academic year. Request official fee schedules and audited programme-level placement or graduate-outcome reports; no unverified salary or placement figures are claimed.','Application checklist','Choose a course, verify recognition and eligibility, prepare transcripts and tests, check scholarship deadlines, apply via the official admissions portal and retain confirmation.'),
      'phones':('How to compare specifications','Check the exact regional model, chipset, screen, battery capacity, charging standards, camera hardware, storage, network bands and promised software updates against manufacturer documentation.','Price and availability','Prices vary by market, storage option, taxes and date. Confirm the live selling price, warranty, launch status and availability with the manufacturer or authorized retailer.','Buyer checklist','Check regional warranty, supported networks, return policy, update commitments, accessories and repair availability before purchase.'),
      'cars':('How to compare models and variants','Verify model year, trim, engine or battery, transmission, safety equipment, homologated mileage or range, independent crash-test results and service coverage.','Price and running costs','Check local ex-showroom or MSRP pricing separately from registration, taxes, insurance, fuel or charging, maintenance and financing. No live price is implied.','Buyer checklist','Request an official variant brochure, test drive, compare total ownership cost, inspect warranty terms and confirm delivery estimates.'),
      'bikes':('How to compare models and variants','Verify displacement or battery capacity, torque, power, brakes and ABS, weight, seat height, certified mileage or range and variant differences.','Price and running costs','Check current market-specific ex-showroom pricing, registration, insurance, maintenance intervals, fuel economy and warranty.','Buyer checklist','Arrange a test ride, compare ergonomic fit and safety equipment, check parts availability and confirm authorized dealer support.')
    }[kind]
    a,b,c,d,e,f=sections
    body=(f'## Overview\n\n{intro}\n\n## Source-listed information\n\n{facts}\n\n'
          f'## {a}\n\n{b}\n\n## {c}\n\n{d}\n\n## {e}\n\n{f}\n\n'
          f'## Verification and limitations\n\nThis profile is based on a source directory record. '
          f'An empty field means the information was not verified, not that a feature or course is unavailable. '
          f'Figures and specifications may change by country, variant and date. '
          f'Always confirm on the [source page]({source}) before applying or buying. '
          f'Published as a reference guide on {now[:10]}, not as breaking news.')
    if kind=='colleges':
        location=', '.join(str(entry.get(k,'')) for k in ('city','region','country') if entry.get(k)) or 'Not verified'
        extra=(f'## College location and profile\n\nLocation: {location}. Institution type: {entry.get("type") or "Not verified"}. Accreditation: {entry.get("accreditation") or "Not verified"}.\n\n'
               f'## Courses offered\n\n{entry.get("programmes") or "See official course catalogue"}\n\n'
               f'## Admission and eligibility\n\n{entry.get("admissions") or "Check official admission criteria"}\n\n'
               f'## Course fees\n\n{entry.get("fees") or "Current course-wise fees not verified"}\n\n'
               f'## Placements\n\n{entry.get("placement") or "Programme-wise placements not verified"}\n\n')
        body=body.replace('## Source-listed information',extra+'## Source-listed information')
    hi=(f'## परिचय\n\n{name} हमारी वैश्विक {LABEL[kind]} डायरेक्टरी में दर्ज है। देश/बाजार: {country}। '
        f'यह जानकारी देने वाली गाइड है, नई लॉन्च या ताज़ा घटना की खबर नहीं।\n\n'
        f'## स्रोत में दर्ज विवरण\n\n{facts}\n\n'
        f'## जरूरी जाँच\n\n{b}\n\n{d}\n\n{f}\n\n'
        f'## सत्यापन\n\nआवेदन या खरीद से पहले [आधिकारिक या संदर्भ स्रोत]({source}) पर फीस, कीमत, मॉडल, पात्रता और उपलब्धता जाँचें। '
        f'बिना सत्यापन के कोई नया दावा नहीं किया गया है।')
    key=hashlib.sha256(('directory-guide:'+kind+':'+name.casefold()).encode()).hexdigest()[:24]
    return key,{'id':key,'en_title':f'{name}: {LABEL[kind].title()}, Facts and Verification Guide',
                'hi_title':f'{name}: विवरण, पात्रता/स्पेसिफिकेशन और सत्यापन गाइड',
                'en_body':body,'hi_body':hi,'en_meta':f'Explore sourced {LABEL[kind]} for {name}; verify details before making a decision.',
                'hi_meta':f'{name} के स्रोत आधारित विवरण और जरूरी जाँच।',
                'en_keywords':f'{name}, {LABEL[kind]}, official source, comparison',
                'hi_keywords':f'{name}, जानकारी, तुलना, आधिकारिक स्रोत',
                'source':source,'source_title':f'{name} reference directory',
                'date':now,'category':CATEGORY[kind],'image_kind':'none',
                'content_type':'evergreen_directory_guide'}

def sufficient(kind,entry):
    """Publish useful source-backed profiles even if optional details are missing.

    Unknown fees, admission requirements and specifications are explicitly labelled
    as unverified in the article. Never invent missing figures.
    """
    source=entry.get('official_url') or entry.get('source_url') or ''
    if not str(source).startswith('https://'):
        return False
    fields={
      'colleges':('programmes','admissions','fees','placement','accreditation','city','region','country'),
      'phones':('display','processor','battery','ram','storage'),
      'cars':('powertrain','variants','price','mileage'),
      'bikes':('engine','power','torque','price','mileage')
    }[kind]
    known=sum(bool(str(entry.get(field,'')).strip()) and
              str(entry.get(field,'')).strip().lower() not in
              ('unknown','n/a','not available','—','none')
              for field in fields)
    # Require actual descriptive facts, not merely a Wikidata name and country.
    if kind=='colleges':
        descriptive=sum(bool(str(entry.get(field,'')).strip()) for field in
                        ('programmes','admissions','fees','placement','accreditation'))
        return known>=3 and descriptive>=1
    return known>=2

def main():
    POSTS.mkdir(parents=True,exist_ok=True)
    items={k:[] for k in KINDS}
    for kind,name,entry,source in candidates():
        if not sufficient(kind,entry):
            continue
        key,post=article(kind,name,entry,source)
        if not (POSTS/(key+'.json')).exists():
            items[kind].append((key,post))
    # Keep curated records first; deterministic ordering avoids reordering on every run.
    # Existing published IDs are skipped above, so each run can advance to new entities.
    shortage={kind:max(0,2-len(group)) for kind,group in items.items() if len(group)<2}
    published=0
    for kind in KINDS:
        for key,post in items[kind][:2]:
            (POSTS/(key+'.json')).write_text(json.dumps(post,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            print('Prepared verified directory guide:',kind,post['en_title'],flush=True)
            published+=1
    print('Directory publishing summary:',published,'of 8 new guides; missing verified candidates:',shortage,flush=True)
    (ROOT/'content'/'directory-guide-status.json').write_text(
        json.dumps({'published':published,'target':8,'missing':shortage,'date':dt.datetime.now(dt.timezone.utc).isoformat()},indent=2)+'\n',encoding='utf-8')
    # Missing source facts are recorded, never fabricated. Other categories can publish.

if __name__=='__main__':main()

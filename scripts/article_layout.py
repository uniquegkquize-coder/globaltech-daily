"""Accessible article presentation, without inventing or rewriting source facts."""
import html
import math
import re
from notice_details import inline


def plain(text):
    text = re.sub(r'\[([^\]]+)\]\([^\s]+\)', r'\1', str(text))
    return re.sub(r'\s+', ' ', re.sub(r'[#*`]', '', text)).strip()


def excerpt(raw, provided=''):
    """Use prose only; never cut through Markdown or a specification row."""
    candidates = [provided] if provided else re.split(r'\n\s*\n', str(raw))
    for value in candidates:
        if not value or re.match(r'^\s*(?:#|[-*] |\d+\. |\|)', value):
            continue
        value = plain(value)
        if len(value) > 360:
            value = value[:357].rsplit(' ', 1)[0].rstrip('.,;:') + '…'
        return value
    return ''


def clean_value(value):
    return re.sub(r'\[\s*edit\s*\]', '', str(value), flags=re.I).strip()


def guide_body(raw):
    """Migrate legacy generated field dumps into labelled, deduplicated tables.

    Keep variant names/units intact. Navigation sections from scraped infoboxes
    and empty edit controls are not product specifications.
    """
    blocks = re.split(r'(?m)(?=^## )', str(raw))
    facts = []; seen = set(); values = set(); kept = []; insertion = None
    for block in blocks:
        heading = block.split('\n', 1)[0].lower()
        if re.match(r'## (?:source-listed information|स्रोत में दर्ज विवरण)', heading):
            insertion = len(kept)
            for label, value in re.findall(r'^- \*\*(.+?):\*\* (.+)$', block, re.M):
                value = clean_value(value)
                if value:
                    facts.append((label, value)); seen.add(label.casefold()); values.add(value)
            continue
        if heading.startswith('## specification rows'):
            for label, value in re.findall(r'; label: (.*?); value: (.*?)(?:; source url:|$)', block, re.M):
                label = clean_value(label); value = clean_value(value)
                if not value or value in values or label.casefold() in seen or re.search(r'other|software|vte', label, re.I):
                    continue
                facts.append((label, value)); seen.add(label.casefold()); values.add(value)
            continue
        # Other structured collections (courses, variants, engines) keep all
        # substantive cells, but remove repeated field names / raw URL dumps.
        if heading in ('## engines', '## variants', '## placement statistics', '## source-listed course details', '## कोर्स, फीस और पात्रता'):
            rows = []
            for line in block.splitlines()[1:]:
                if not line.startswith('- '): continue
                pairs = [s.split(': ', 1) for s in line[2:].split('; ') if ': ' in s]
                pairs = [(k, clean_value(v)) for k,v in pairs if k not in ('source url','source_url','section') and clean_value(v)]
                if pairs: rows.append(pairs)
            if rows:
                keys = list(dict.fromkeys(k for row in rows for k,v in row))
                block = block.split('\n')[0]+'\n\n'+markdown_table(keys, [[dict(row).get(k,'—') for k in keys] for row in rows])+'\n\n'
        kept.append(block)
    if facts:
        heading = 'स्रोत में दर्ज विवरण' if re.search(r'[\u0900-\u097f]', str(raw)[:100]) else 'Source-listed specifications'
        table = '## '+heading+'\n\n'+markdown_table(['Field','Source-listed detail'], facts)+'\n\n'
        kept.insert(insertion if insertion is not None else 1, table)
    result = ''.join(kept)
    result = re.sub(r' Country or market recorded: not recorded\.', '', result)
    result = result.replace('देश/बाजार: not recorded। ', '')
    for en, hi in {'smartphone specifications':'मोबाइल स्पेसिफिकेशन', 'college admissions':'कॉलेज एडमिशन', 'car specifications':'कार स्पेसिफिकेशन', 'motorcycle specifications':'बाइक स्पेसिफिकेशन'}.items():
        result = result.replace('वैश्विक '+en+' डायरेक्टरी', 'वैश्विक '+hi+' डायरेक्टरी')
    if re.search(r'[\u0900-\u097f]', str(raw)[:100]):
        translations = {
            'Check the exact regional model, chipset, screen, battery capacity, charging standards, camera hardware, storage, network bands and promised software updates against manufacturer documentation.':'निर्माता के दस्तावेजों से सही क्षेत्रीय मॉडल, चिपसेट, स्क्रीन, बैटरी, चार्जिंग, कैमरा, स्टोरेज, नेटवर्क बैंड और सॉफ्टवेयर अपडेट की जानकारी मिलाएँ।',
            'Prices vary by market, storage option, taxes and date. Confirm the live selling price, warranty, launch status and availability with the manufacturer or authorized retailer.':'कीमत बाजार, स्टोरेज, टैक्स और तारीख के अनुसार बदलती है। मौजूदा कीमत, वारंटी और उपलब्धता निर्माता या अधिकृत विक्रेता से जाँचें।',
            'Check regional warranty, supported networks, return policy, update commitments, accessories and repair availability before purchase.':'खरीदने से पहले स्थानीय वारंटी, नेटवर्क सपोर्ट, वापसी नीति, अपडेट, एक्सेसरीज और मरम्मत की उपलब्धता जाँचें।',
            'Find the current programme catalogue on the institution website. Compare prerequisites, required qualifications, language tests, admission tests, application deadlines and international-student conditions.':'संस्थान की वेबसाइट पर वर्तमान कोर्स सूची देखें। योग्यता, भाषा और प्रवेश परीक्षा, आवेदन की अंतिम तारीख और अंतरराष्ट्रीय छात्रों की शर्तें जाँचें।',
            'Fees depend on course, intake, residency and academic year. Request official fee schedules and audited programme-level placement or graduate-outcome reports; no unverified salary or placement figures are claimed.':'फीस कोर्स, सत्र और छात्र की श्रेणी के अनुसार बदलती है। आधिकारिक फीस सूची और कोर्स के प्लेसमेंट परिणाम माँगें। बिना सत्यापन वाले वेतन या प्लेसमेंट आँकड़ों को पक्का न मानें।',
            'Choose a course, verify recognition and eligibility, prepare transcripts and tests, check scholarship deadlines, apply via the official admissions portal and retain confirmation.':'कोर्स चुनें, मान्यता और पात्रता जाँचें, दस्तावेज और परीक्षाएँ तैयार करें। छात्रवृत्ति की अंतिम तारीख देखें, आधिकारिक पोर्टल से आवेदन करें और पुष्टि सुरक्षित रखें।',
            'Verify model year, trim, engine or battery, transmission, safety equipment, homologated mileage or range, independent crash-test results and service coverage.':'मॉडल वर्ष, वेरिएंट, इंजन या बैटरी, ट्रांसमिशन, सुरक्षा सुविधाएँ, प्रमाणित माइलेज या रेंज, क्रैश टेस्ट और सर्विस नेटवर्क जाँचें।',
            'Check local ex-showroom or MSRP pricing separately from registration, taxes, insurance, fuel or charging, maintenance and financing. No live price is implied.':'स्थानीय एक्स-शोरूम कीमत के साथ रजिस्ट्रेशन, टैक्स, बीमा, ईंधन या चार्जिंग, रखरखाव और फाइनेंस का खर्च अलग से जाँचें। यहाँ लाइव कीमत का दावा नहीं है।',
            'Request an official variant brochure, test drive, compare total ownership cost, inspect warranty terms and confirm delivery estimates.':'आधिकारिक वेरिएंट ब्रोशर माँगें, टेस्ट ड्राइव लें और कुल खर्च की तुलना करें। वारंटी की शर्तें और डिलीवरी का समय जाँचें।',
            'Verify displacement or battery capacity, torque, power, brakes and ABS, weight, seat height, certified mileage or range and variant differences.':'इंजन या बैटरी क्षमता, टॉर्क, पावर, ब्रेक और ABS, वजन, सीट की ऊँचाई, प्रमाणित माइलेज या रेंज और वेरिएंट के अंतर जाँचें।',
            'Check current market-specific ex-showroom pricing, registration, insurance, maintenance intervals, fuel economy and warranty.':'वर्तमान स्थानीय एक्स-शोरूम कीमत, रजिस्ट्रेशन, बीमा, सर्विस अंतराल, माइलेज और वारंटी जाँचें।',
            'Arrange a test ride, compare ergonomic fit and safety equipment, check parts availability and confirm authorized dealer support.':'टेस्ट राइड लें, बैठने की सुविधा और सुरक्षा उपकरणों की तुलना करें। पार्ट्स की उपलब्धता और अधिकृत डीलर की सहायता जाँचें।',
        }
        for en, hi in translations.items(): result = result.replace(en, hi)
    match = re.search(r'([^\n]+?) is listed in our worldwide (phone|car|motorcycle|college) directory\.', result)
    if match:
        name, kind = match.groups()
        focus = {'phone':'display, performance, battery and camera details', 'car':'powertrain, dimensions and variant details', 'motorcycle':'engine, performance and ownership details', 'college':'courses, admission requirements and fee information'}[kind]
        old = match[0] + ' This is an evergreen reference guide, not a new launch or a claim that the institution or product was recently announced.'
        result = result.replace(old, f'Explore {name}: source-listed {focus}, followed by practical checks before making a decision. This is a reference guide, not a new-launch report.')
    return result


def markdown_table(headers, rows):
    def cell(v): return str(v).replace('|', '&#124;').replace('\n', ' ')
    return '\n'.join('| '+' | '.join(cell(v) for v in row)+' |' for row in [headers, ['---']*len(headers), *rows])


def render(raw, lang='en'):
    """Safe supported Markdown, with semantic tables/lists and stable anchors."""
    parts=[]; headings=[]; used=set(); lines=str(raw).splitlines(); i=0
    def cells(line): return [x.strip().replace('&#124;', '|') for x in line.strip().strip('|').split('|')]
    while i < len(lines):
        line=lines[i].strip()
        if not line: i+=1; continue
        m=re.match(r'^#{1,3}\s+(.+)$', line)
        if m:
            level=3 if line.startswith('### ') else 2
            base='section-'+(re.sub(r'[^\w-]+','-',plain(m[1]).lower(),flags=re.U).strip('-') or 'details')
            ident=base; n=2
            while ident in used: ident=base+'-'+str(n); n+=1
            used.add(ident); headings.append((ident,plain(m[1]),level))
            parts.append(f'<h{level} id="{html.escape(ident)}">{inline(m[1])}</h{level}>'); i+=1; continue
        if '|' in line and i+1<len(lines) and re.fullmatch(r'[\s|:\-]+',lines[i+1]) and '-' in lines[i+1]:
            headers=cells(line); rows=[]; i+=2
            while i<len(lines) and '|' in lines[i] and lines[i].strip():
                row=cells(lines[i]); rows.append((row+['']*len(headers))[:len(headers)]); i+=1
            caption='Source-listed details' if lang=='en' else 'स्रोत में दर्ज जानकारी'
            cls='facts-table' if len(headers)==2 else 'data-table'
            table='<div class="article-table" tabindex="0" role="region" aria-label="'+caption+'"><table class="'+cls+'"><caption>'+caption+'</caption><thead><tr>'+''.join('<th scope="col">'+inline(h)+'</th>' for h in headers)+'</tr></thead><tbody>'
            for row in rows:
                table+='<tr>'+''.join(('<th scope="row">' if k==0 else '<td>')+inline(v)+('</th>' if k==0 else '</td>') for k,v in enumerate(row))+'</tr>'
            parts.append(table+'</tbody></table></div>'); continue
        item=re.match(r'^(?:([-*]) |(\d+)\. )(.+)',line)
        if item:
            ordered=bool(item[2]); tag='ol' if ordered else 'ul'; items=[]
            start=' start="'+item[2]+'"' if ordered and item[2]!='1' else ''
            while i<len(lines):
                match=re.match(r'^(?:([-*]) |(\d+)\. )(.+)',lines[i].strip())
                if not match or bool(match[2])!=ordered: break
                items.append('<li>'+inline(match[3])+'</li>'); i+=1
            parts.append('<'+tag+start+'>'+''.join(items)+'</'+tag+'>'); continue
        if line.startswith('> '):
            quote=[]
            while i<len(lines) and lines[i].strip().startswith('> '): quote.append(lines[i].strip()[2:]); i+=1
            parts.append('<blockquote><p>'+inline(' '.join(quote))+'</p></blockquote>'); continue
        paragraph=[line]; i+=1
        while i<len(lines) and lines[i].strip() and not re.match(r'^(?:#|[-*] |\d+\. |>|\|)',lines[i].strip()):
            paragraph.append(lines[i].strip()); i+=1
        parts.append('<p>'+inline(' '.join(paragraph))+'</p>')
    toc=''
    if len(headings)>=2:
        label='In this article' if lang=='en' else 'इस लेख में'
        toc='<nav class="article-toc" aria-label="'+label+'"><strong>'+label+'</strong><ol>'+''.join('<li class="toc-level-'+str(level)+'"><a href="#'+html.escape(ident)+'">'+html.escape(text)+'</a></li>' for ident,text,level in headings)+'</ol></nav>'
    minutes=max(1,math.ceil(len(plain(raw).split())/(180 if lang=='hi' else 220)))
    return ''.join(parts),toc,minutes


CSS = '''
.article.readable-article{max-width:900px;overflow:visible}.readable-article .story{max-width:70ch;font-size:18px;line-height:1.8;color:#22334b;overflow-wrap:anywhere}.readable-article .story p{line-height:inherit;margin-bottom:1.25em}.readable-article h1{max-width:25ch;text-wrap:balance}.readable-article .story h2{border-top:1px solid #e0e8f1;padding-top:24px;margin-top:38px}.story h2[id],.story h3[id]{scroll-margin-top:24px}.story li{margin:.6em 0}.story ol,.story ul{padding-inline-start:1.5em}.story blockquote{border-left:4px solid #079aa3;padding:12px 20px;margin:24px 0;background:#f2f8fa}.article-toc{display:block;background:#f5f8fc;border:1px solid #dce5f1;border-radius:12px;padding:18px 22px;margin:24px 0}.article-toc strong{font-size:16px}.article-toc ol{display:grid;grid-template-columns:1fr 1fr;gap:6px 24px;margin:12px 0 0;padding-left:20px}.article-toc li{font-size:14px;line-height:1.5}.article-toc a{display:block;color:#155b8b;padding:4px 0;text-decoration:underline;text-underline-offset:3px}.article-toc .toc-level-3{font-size:13px}.article-table{overflow-x:auto;max-width:100%;border:1px solid #dce5ef;border-radius:12px;margin:22px 0;background:#fff}.article-table table{border-collapse:collapse;width:100%;font-size:15px;line-height:1.65;text-align:left}.article-table caption{text-align:left;padding:10px 16px;background:#eaf3f8;font-size:13px;font-weight:700}.article-table th,.article-table td{padding:13px 16px;border-bottom:1px solid #e1e8ef;vertical-align:top;overflow-wrap:anywhere}.article-table thead{background:#f5f8fc}.article-table tbody th{width:28%;font-weight:650;color:#183d59}.article-table tr:last-child>*{border-bottom:0}.article-table tr:nth-child(even){background:#f8fafc}.readable-article .summary{font-size:17px;line-height:1.7;margin:20px 0}.reading-meta{font-size:13px;color:#586d82;margin-top:-8px}.context-links{display:block;border-left:3px solid #0c8a96;background:#f3f9fb;padding:16px 20px;margin:28px 0}.context-links strong{display:block;font-size:14px;margin-bottom:8px}.context-links a{display:block;margin:7px 0;font-size:15px;line-height:1.6}.guide-context{font-size:14px;background:#fff8e9;padding:12px 16px;border-radius:8px;margin:20px 0}.readable-article a:focus-visible,.article-table:focus-visible{outline:3px solid #0b8994;outline-offset:3px}.readable-article .breadcrumbs{line-height:1.6}.readable-article .related-card span{font-size:15px!important}.article-toc a:hover{text-decoration-thickness:2px}@media(max-width:600px){.readable-article .story{font-size:17px;line-height:1.8}.article-toc{padding:16px}.article-toc ol{grid-template-columns:1fr;gap:2px}.article-table .facts-table thead{display:none}.facts-table tbody,.facts-table tr,.facts-table th,.facts-table td{display:block;width:100%!important}.article-table .facts-table tbody th{padding-bottom:3px;border-bottom:0;background:#eef4f8}.article-table .facts-table td{padding-top:8px}.article-table th,.article-table td{padding:12px}.article-table .data-table{min-width:560px}.readable-article .related{grid-template-columns:1fr}.readable-article h1{font-size:30px}.readable-article .summary{font-size:16px}.guide-context{font-size:13px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@media (max-width: 480px) {
  [data-adsterra-slot] {
    width: min(320px, 100vw);
    margin-inline: calc((100% - min(320px, 100vw)) / 2);
  }
}
'''

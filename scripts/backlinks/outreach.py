"""Prepare review-only messages. This module has NO email sending capability."""
from .common import *

def choose(row,targets):
 options=[t for t in targets if t['category']==row['category'] and t['words']>=250 and t['language']==row.get('language','en')]
 query=tokens(row.get('name','')+' '+row.get('topic_excerpt',''))
 ranked=sorted(options,key=lambda t:(len(query&tokens(t['title'])),t['evergreen']),reverse=True)
 if not ranked or len(query&tokens(ranked[0]['title']))<2: return None
 return ranked[0]
def draft(row,target):
 ident=uid(row['domain']+'|'+target['url'])
 reason=f"Your public page ‘{row['name']}’ and this resource both cover {', '.join(sorted(tokens(row['name']+' '+row.get('topic_excerpt',''))&tokens(target['title']))[:5])}."
 if row.get('language')=='hi':
  subject=f"आपके पाठकों के लिए संदर्भ: {target['title']}"
  body=f"नमस्कार {row['name']} की संपादकीय टीम,\n\n{reason}\n\nGlobeWire Daily का यह संदर्भ आपके संबंधित लेखों के पाठकों के लिए उपयोगी हो सकता है: {target['title']}\n{target['url']}\n\nउपयोगिता और तथ्यों की समीक्षा के बाद ही इसे संदर्भ मानें। संपादकीय चयन आपका है। कोई भुगतान या बदले में लिंक का प्रस्ताव नहीं है।\n\nविजय\nGlobeWire Daily\ncontact@globewiredaily.org"
 else:
  subject=f"Reader reference for {row['name'][:65]}: {target['title'][:100]}"
  body=f"Hello {row['name']} editorial team,\n\n{reason}\n\nI help publish GlobeWire Daily. Our resource ‘{target['title']}’ may give readers of your related coverage an additional reference:\n{target['url']}\n\nPlease assess its facts and usefulness before considering a citation. Any inclusion is entirely your editorial decision; there is no payment or reciprocal-link proposal.\n\nVijay\nGlobeWire Daily\ncontact@globewiredaily.org"
 return {'id':ident,'prospect_id':row['id'],'domain':row['domain'],'recipient_candidates':row.get('public_emails',[]),'recipient':None,'subject':subject,'body':body,'target_url':target['url'],'reason':reason,'created_at':day(),'status':'needs_editorial_and_recipient_review','sent_at':None,'approval':None}
def run():
 rows=read('prospects.json',[]); targets=read('targets.json',[]); drafts=read('drafts.json',[])
 # One unsent outreach preparation per domain, including across target changes.
 used={d['domain'] for d in drafts}
 for row in rows:
  if not row.get('qualified') or row['domain'] in used or not row.get('contact_page') or not row.get('evidence',{}).get('editorial_invitation'): continue
  t=choose(row,targets)
  if not t: continue
  d=draft(row,t); drafts.append(d); used.add(row['domain'])
  row.update({'draft_id':d['id'],'outreach_status':'draft_review','suggested_target':t['url'],'editorial_reason':d['reason']})
 save('drafts.json',drafts); save('prospects.json',rows); return drafts
if __name__=='__main__': run()

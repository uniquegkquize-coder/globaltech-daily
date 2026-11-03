"""Observable heuristic: missing evidence earns zero; no inferred traffic or DA."""
from .common import *

def score(row):
 e=row.get('evidence',{})
 parts={'topical_relevance':30 if e.get('topical') else 0,
        'editorial_credibility':10*bool(e.get('policy_page'))+10*bool(e.get('byline'))+5*bool(e.get('article_markup')),
        'content_signals':10*(e.get('words',0)>=300)+10*(e.get('words',0)>=1000),
        'placement_suitability':5*bool(row.get('contact_page'))+10*bool(e.get('editorial_invitation')),
        'spam_screening':0 if e.get('spam_risk') else 10}
 # Content length is only an observable signal; actual audience remains unknown.
 return {**row,'score_breakdown':parts,'quality_score':sum(parts.values()),'qualified':sum(parts.values())>=70 and not e.get('spam_risk',False),'rejection_reason':'spam-risk signal; manual review required' if e.get('spam_risk') else ''}
def run():
 rows=[score(r) for r in read('prospects.json',[])]; save('prospects.json',rows); return rows
if __name__=='__main__': run()

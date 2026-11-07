"""Rebuild compact GeoNames locality names. Developer-only dependencies:
python -m pip install geonamescache==3.0.2 pycountry
The publisher runtime reads the checked-in gzip with Python's standard library.
"""
from collections import defaultdict
import datetime as dt
import gettext
import gzip
from importlib.metadata import version
import json
from pathlib import Path
import geonamescache
import pycountry
from types import SimpleNamespace

def main():
 gc=geonamescache.GeonamesCache(min_city_population=500)
 info=gc.get_countries();places=defaultdict(set)
 iso={row.alpha_2:row for row in pycountry.countries}
 iso['XK']=SimpleNamespace(name=info['XK']['name'])
 for row in gc.get_cities().values():
  if row['countrycode'] in iso:places[row['countrycode']].add(row['name'])
 countries={}
 for code,country in sorted(iso.items()):
  record=info.get(code,{})
  language=record.get('languages','en').split(',')[0].split('-')[0]
  translation=gettext.translation('iso3166-1',pycountry.LOCALES_DIR,languages=[language],fallback=True)
  countries[code]={'name':record.get('name',country.name),
                   'local_name':translation.gettext(country.name),
                   'languages':record.get('languages','en'),'places':sorted(places[code])}
 data={'source':'GeoNames via geonamescache '+version('geonamescache'),
       'license':'GeoNames CC-BY-4.0; country translations iso-codes LGPL-2.1-or-later',
       'url':'https://www.geonames.org/','translation_source':'iso-codes via pycountry',
       'scope':'ISO 3166-1 records plus Kosovo (XK); cities500 names, not every settlement',
       'countries':countries}
 target=Path(__file__).resolve().parents[1]/'data/world_localities.json.gz'
 target.parent.mkdir(parents=True,exist_ok=True)
 target.write_bytes(gzip.compress(json.dumps(data,ensure_ascii=False,separators=(',',':')).encode(),mtime=0))
 print(json.dumps({'countries':len(countries),'place_names':sum(len(row['places']) for row in countries.values()),'bytes':target.stat().st_size}))

if __name__=='__main__':main()

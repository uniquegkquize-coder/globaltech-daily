# Worldwide locality search registry

GeoNames geographic names: https://www.geonames.org/
Source export documentation: https://download.geonames.org/export/dump/readme.txt
License: Creative Commons Attribution 4.0, https://creativecommons.org/licenses/by/4.0/

The compressed file is a transformed extract of GeoNames cities500 distributed in
geonamescache 3.0.2. Only country codes, country names, languages and unique place
names are retained. Alternate names, coordinates and population fields are removed;
place names are sorted and deduplicated within each country. Kosovo (XK) is included
as a separate geographic search entry; obsolete CS and AN entries are excluded.
Country/territory codes and grouping do not express a position on political status.

Country-name translations come from the iso-codes dataset through pycountry 26.2.16.
Its LGPL 2.1 license is reproduced in ISO_CODES_LICENSE.txt.
Sources: https://github.com/pycountry/pycountry and
https://salsa.debian.org/iso-codes-team/iso-codes

Rebuild with scripts/build_world_localities.py after installing its documented
developer dependencies. The newsroom runtime needs no GeoNames account, API key,
pycountry or geonamescache package; it reads the checked-in gzip using Python.

Scope: 250 country/territory search entries and 207,383 unique place names.
The source includes places over 500 inhabitants and administrative seats according
to its upstream definition. It is not a list of every village. Four entries have
no place names and use country-level searches. Gazetteer data is supplied as is.

These are geographic discovery definitions, not verified publisher listings or
evidence that each place has been crawled. The main collector rotates 32 country
queries per run, including country/locality searches, within a 25-second budget.
The trending collector rotates 12 queries per 4-hour cycle. Newly found publisher
hosts must match the original source in Google News RSS metadata; reporting still
requires readable article text. No publisher restriction is bypassed.

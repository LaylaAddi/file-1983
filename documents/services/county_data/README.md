`us_city_county.json` is a city/state → county lookup table built from the
[US-Cities-Database](https://github.com/kelvins/US-Cities-Database) project
(MIT License, Copyright (c) 2017 Kelvin S. do Prado), reduced to a flat
`{state_code: {city_lowercase: county_name}}` mapping for fast static lookups.

`us_zip_county.json` is a ZIP → county lookup table built from
[us-state-county-zip](https://github.com/scpike/us-state-county-zip)
(derived from US Census ZCTA data), reduced to a flat
`{zip: {county, state}}` mapping. ZIP-based lookups also cover
unincorporated communities (no formal city government, so they're missing
from `us_city_county.json`) that still have their own ZIP code — e.g.
Van Wert, GA, an unincorporated community in Polk County sharing ZIP 30153
with Rockmart.

Used by `documents/services/county_lookup_service.py` to correct GPT's
free-text county guess (which has no real data behind it and is unreliable
for small/obscure or unincorporated places) against an authoritative
source — the same static-data-first approach used by
`court_lookup_service.py` for federal districts. ZIP is checked first when
available since it has broader coverage; city+state is the fallback.

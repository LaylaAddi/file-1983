`us_city_county.json` is a city/state → county lookup table built from the
[US-Cities-Database](https://github.com/kelvins/US-Cities-Database) project
(MIT License, Copyright (c) 2017 Kelvin S. do Prado), reduced to a flat
`{state_code: {city_lowercase: county_name}}` mapping for fast static lookups.

Used by `documents/services/county_lookup_service.py` to correct GPT's
free-text county guess (which has no real data behind it and is unreliable
for small/obscure towns) against an authoritative source — the same
static-data-first approach used by `court_lookup_service.py` for federal
districts.

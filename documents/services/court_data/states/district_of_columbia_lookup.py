from .base_state_lookup import BaseStateLookup

class DistrictOfColumbiaLookup(BaseStateLookup):
    STATE_CODE = 'DC'
    STATE_NAME = 'District of Columbia'
    IS_SINGLE_DISTRICT = True

    DISTRICTS = {
        'district': {
            'name': 'United States District Court for the District of Columbia',
            'cities': ['washington', 'dc', 'washington dc']
        }
    }
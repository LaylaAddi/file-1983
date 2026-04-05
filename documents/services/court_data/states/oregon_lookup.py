from .base_state_lookup import BaseStateLookup

class OregonLookup(BaseStateLookup):
    STATE_CODE = 'OR'
    STATE_NAME = 'Oregon'
    
    DISTRICTS = {
        'district': {
            'name': 'United States District Court for the District of Oregon',
            'cities': ['portland', 'eugene', 'salem', 'gresham', 'hillsboro', 'bend', 'beaverton', 'medford']
        }
    }
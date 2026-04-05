from .base_state_lookup import BaseStateLookup

class ArizonaLookup(BaseStateLookup):
    STATE_CODE = 'AZ'
    STATE_NAME = 'Arizona'
    
    DISTRICTS = {
        'district': {
            'name': 'United States District Court for the District of Arizona',
            'cities': ['phoenix', 'tucson', 'mesa', 'chandler', 'scottsdale', 'glendale', 'gilbert', 'tempe']
        }
    }
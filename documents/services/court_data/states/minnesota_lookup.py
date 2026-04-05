from .base_state_lookup import BaseStateLookup

class MinnesotaLookup(BaseStateLookup):
    STATE_CODE = 'MN'
    STATE_NAME = 'Minnesota'
    
    DISTRICTS = {
        'district': {
            'name': 'United States District Court for the District of Minnesota',
            'cities': ['minneapolis', 'st paul', 'rochester', 'duluth', 'bloomington', 'brooklyn park', 'plymouth', 'st cloud']
        }
    }
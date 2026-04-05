from .base_state_lookup import BaseStateLookup

class NorthDakotaLookup(BaseStateLookup):
    STATE_CODE = 'ND'
    STATE_NAME = 'North Dakota'
    
    DISTRICTS = {
        'district': {
            'name': 'United States District Court for the District of North Dakota',
            'cities': ['fargo', 'bismarck', 'grand forks', 'minot', 'west fargo', 'williston', 'dickinson', 'mandan']
        }
    }
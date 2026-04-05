from .base_state_lookup import BaseStateLookup

class NewJerseyLookup(BaseStateLookup):
    STATE_CODE = 'NJ'
    STATE_NAME = 'New Jersey'
    
    DISTRICTS = {
        'district': {
            'name': 'United States District Court for the District of New Jersey',
            'cities': ['newark', 'jersey city', 'paterson', 'elizabeth', 'trenton', 'camden', 'passaic', 'union city']
        }
    }
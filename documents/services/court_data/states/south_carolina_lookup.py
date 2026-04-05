from .base_state_lookup import BaseStateLookup

class SouthCarolinaLookup(BaseStateLookup):
    STATE_CODE = 'SC'
    STATE_NAME = 'South Carolina'
    
    DISTRICTS = {
        'district': {
            'name': 'United States District Court for the District of South Carolina',
            'cities': ['columbia', 'charleston', 'north charleston', 'mount pleasant', 'rock hill', 'greenville', 'summerville', 'sumter']
        }
    }
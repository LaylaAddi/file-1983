from .base_state_lookup import BaseStateLookup

class MassachusettsLookup(BaseStateLookup):
    STATE_CODE = 'MA'
    STATE_NAME = 'Massachusetts'
    
    DISTRICTS = {
        'district': {
            'name': 'United States District Court for the District of Massachusetts',
            'cities': ['boston', 'worcester', 'springfield', 'lowell', 'cambridge', 'new bedford', 'brockton', 'quincy']
        }
    }
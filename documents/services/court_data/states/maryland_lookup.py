from .base_state_lookup import BaseStateLookup

class MarylandLookup(BaseStateLookup):
    STATE_CODE = 'MD'
    STATE_NAME = 'Maryland'
    
    DISTRICTS = {
        'district': {
            'name': 'United States District Court for the District of Maryland',
            'cities': ['baltimore', 'frederick', 'rockville', 'gaithersburg', 'bowie', 'hagerstown', 'annapolis', 'college park']
        }
    }
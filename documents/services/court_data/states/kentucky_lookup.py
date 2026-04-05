from .base_state_lookup import BaseStateLookup

class KentuckyLookup(BaseStateLookup):
    STATE_CODE = 'KY'
    STATE_NAME = 'Kentucky'
    
    DISTRICTS = {
        'eastern': {
            'name': 'United States District Court for the Eastern District of Kentucky',
            'cities': ['lexington', 'frankfort', 'richmond', 'somerset', 'pikeville', 'hazard', 'london', 'corbin']
        },
        
        'western': {
            'name': 'United States District Court for the Western District of Kentucky',
            'cities': ['louisville', 'bowling green', 'owensboro', 'paducah', 'hopkinsville', 'elizabethtown', 'henderson', 'madisonville']
        }
    }
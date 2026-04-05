from .base_state_lookup import BaseStateLookup

class MississippiLookup(BaseStateLookup):
    STATE_CODE = 'MS'
    STATE_NAME = 'Mississippi'
    
    DISTRICTS = {
        'northern': {
            'name': 'United States District Court for the Northern District of Mississippi',
            'cities': ['jackson', 'tupelo', 'oxford', 'columbus', 'clarksdale', 'greenville', 'starkville', 'cleveland']
        },
        
        'southern': {
            'name': 'United States District Court for the Southern District of Mississippi',
            'cities': ['gulfport', 'biloxi', 'hattiesburg', 'meridian', 'pascagoula', 'laurel', 'natchez', 'mccomb']
        }
    }
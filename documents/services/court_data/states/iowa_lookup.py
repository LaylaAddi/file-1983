from .base_state_lookup import BaseStateLookup

class IowaLookup(BaseStateLookup):
    STATE_CODE = 'IA'
    STATE_NAME = 'Iowa'
    
    DISTRICTS = {
        'northern': {
            'name': 'United States District Court for the Northern District of Iowa',
            'cities': ['cedar falls', 'waterloo', 'dubuque', 'mason city', 'fort dodge', 'charles city', 'oelwein', 'decorah']
        },
        
        'southern': {
            'name': 'United States District Court for the Southern District of Iowa',
            'cities': ['des moines', 'cedar rapids', 'davenport', 'sioux city', 'iowa city', 'west des moines', 'council bluffs', 'ames']
        }
    }
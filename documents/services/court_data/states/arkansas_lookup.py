from .base_state_lookup import BaseStateLookup

class ArkansasLookup(BaseStateLookup):
    STATE_CODE = 'AR'
    STATE_NAME = 'Arkansas'
    
    DISTRICTS = {
        'eastern': {
            'name': 'United States District Court for the Eastern District of Arkansas',
            'cities': ['little rock', 'north little rock', 'pine bluff', 'jonesboro', 'searcy', 'helena', 'forrest city', 'west memphis']
        },
        
        'western': {
            'name': 'United States District Court for the Western District of Arkansas',
            'cities': ['fayetteville', 'fort smith', 'springdale', 'rogers', 'bentonville', 'hot springs', 'texarkana', 'russellville']
        }
    }
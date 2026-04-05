from .base_state_lookup import BaseStateLookup

class ConnecticutLookup(BaseStateLookup):
    STATE_CODE = 'CT'
    STATE_NAME = 'Connecticut'
    
    DISTRICTS = {
        'district': {
            'name': 'United States District Court for the District of Connecticut',
            'cities': ['bridgeport', 'new haven', 'hartford', 'stamford', 'waterbury', 'norwalk', 'danbury', 'new britain']
        }
    }
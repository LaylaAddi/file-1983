from .base_state_lookup import BaseStateLookup

class KansasLookup(BaseStateLookup):
    STATE_CODE = 'KS'
    STATE_NAME = 'Kansas'
    
    DISTRICTS = {
        'district': {
            'name': 'United States District Court for the District of Kansas',
            'cities': ['wichita', 'overland park', 'kansas city', 'topeka', 'olathe', 'lawrence', 'shawnee', 'salina']
        }
    }
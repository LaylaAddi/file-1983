from .base_state_lookup import BaseStateLookup

class NebraskaLookup(BaseStateLookup):
    STATE_CODE = 'NE'
    STATE_NAME = 'Nebraska'
    
    DISTRICTS = {
        'district': {
            'name': 'United States District Court for the District of Nebraska',
            'cities': ['omaha', 'lincoln', 'bellevue', 'grand island', 'kearney', 'fremont', 'hastings', 'north platte']
        }
    }
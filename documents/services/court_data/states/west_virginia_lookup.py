from .base_state_lookup import BaseStateLookup

class WestVirginiaLookup(BaseStateLookup):
    STATE_CODE = 'WV'
    STATE_NAME = 'West Virginia'
    
    DISTRICTS = {
        'northern': {
            'name': 'United States District Court for the Northern District of West Virginia',
            'cities': ['morgantown', 'wheeling', 'fairmont', 'clarksburg', 'bridgeport', 'buckhannon', 'grafton', 'kingwood']
        },
        
        'southern': {
            'name': 'United States District Court for the Southern District of West Virginia',
            'cities': ['charleston', 'huntington', 'parkersburg', 'beckley', 'martinsburg', 'lewisburg', 'bluefield', 'princeton']
        }
    }
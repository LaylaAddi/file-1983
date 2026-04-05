from .base_state_lookup import BaseStateLookup

class WyomingLookup(BaseStateLookup):
    STATE_CODE = 'WY'
    STATE_NAME = 'Wyoming'
    IS_SINGLE_DISTRICT = True

    DISTRICTS = {
        'district': {
            'name': 'United States District Court for the District of Wyoming',
            'cities': ['cheyenne', 'casper', 'laramie', 'gillette', 'rock springs', 'sheridan', 'green river', 'evanston']
        }
    }
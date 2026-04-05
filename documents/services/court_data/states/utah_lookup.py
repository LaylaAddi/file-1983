from .base_state_lookup import BaseStateLookup

class UtahLookup(BaseStateLookup):
    STATE_CODE = 'UT'
    STATE_NAME = 'Utah'
    IS_SINGLE_DISTRICT = True

    DISTRICTS = {
        'district': {
            'name': 'United States District Court for the District of Utah',
            'cities': ['salt lake city', 'west valley city', 'provo', 'west jordan', 'orem', 'sandy', 'ogden', 'st george']
        }
    }
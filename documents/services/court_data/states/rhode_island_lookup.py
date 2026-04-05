from .base_state_lookup import BaseStateLookup

class RhodeIslandLookup(BaseStateLookup):
    STATE_CODE = 'RI'
    STATE_NAME = 'Rhode Island'
    IS_SINGLE_DISTRICT = True

    DISTRICTS = {
        'district': {
            'name': 'United States District Court for the District of Rhode Island',
            'cities': ['providence', 'warwick', 'cranston', 'pawtucket', 'east providence', 'woonsocket', 'newport', 'central falls']
        }
    }
from .base_state_lookup import BaseStateLookup

class MaineLookup(BaseStateLookup):
    STATE_CODE = 'ME'
    STATE_NAME = 'Maine'
    IS_SINGLE_DISTRICT = True

    DISTRICTS = {
        'district': {
            'name': 'United States District Court for the District of Maine',
            'cities': ['portland', 'lewiston', 'bangor', 'south portland', 'auburn', 'biddeford', 'sanford', 'augusta']
        }
    }
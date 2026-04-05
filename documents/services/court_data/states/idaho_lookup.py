from .base_state_lookup import BaseStateLookup

class IdahoLookup(BaseStateLookup):
    STATE_CODE = 'ID'
    STATE_NAME = 'Idaho'
    IS_SINGLE_DISTRICT = True

    DISTRICTS = {
        'district': {
            'name': 'United States District Court for the District of Idaho',
            'cities': ['boise', 'nampa', 'meridian', 'idaho falls', 'pocatello', 'caldwell', 'coeur d\'alene', 'twin falls']
        }
    }
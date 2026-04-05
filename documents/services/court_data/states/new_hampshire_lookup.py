from .base_state_lookup import BaseStateLookup

class NewHampshireLookup(BaseStateLookup):
    STATE_CODE = 'NH'
    STATE_NAME = 'New Hampshire'
    IS_SINGLE_DISTRICT = True

    DISTRICTS = {
        'district': {
            'name': 'United States District Court for the District of New Hampshire',
            'cities': ['manchester', 'nashua', 'concord', 'derry', 'rochester', 'salem', 'dover', 'merrimack']
        }
    }
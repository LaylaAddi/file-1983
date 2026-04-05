from .base_state_lookup import BaseStateLookup

class VermontLookup(BaseStateLookup):
    STATE_CODE = 'VT'
    STATE_NAME = 'Vermont'
    IS_SINGLE_DISTRICT = True

    DISTRICTS = {
        'district': {
            'name': 'United States District Court for the District of Vermont',
            'cities': ['burlington', 'south burlington', 'rutland', 'barre', 'montpelier', 'winooski', 'st albans', 'brattleboro']
        }
    }
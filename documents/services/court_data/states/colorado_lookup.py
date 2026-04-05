from .base_state_lookup import BaseStateLookup

class ColoradoLookup(BaseStateLookup):
    STATE_CODE = 'CO'
    STATE_NAME = 'Colorado'
    
    DISTRICTS = {
        'district': {
            'name': 'United States District Court for the District of Colorado',
            'cities': ['denver', 'colorado springs', 'aurora', 'fort collins', 'lakewood', 'thornton', 'arvada', 'westminster']
        }
    }
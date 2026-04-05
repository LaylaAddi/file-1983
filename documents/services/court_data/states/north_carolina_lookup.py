from .base_state_lookup import BaseStateLookup

class NorthCarolinaLookup(BaseStateLookup):
    STATE_CODE = 'NC'
    STATE_NAME = 'North Carolina'
    
    DISTRICTS = {
        'eastern': {
            'name': 'United States District Court for the Eastern District of North Carolina',
            'cities': [
                'raleigh', 'durham', 'fayetteville', 'wilmington', 'greenville',
                'rocky mount', 'wilson', 'goldsboro', 'new bern', 'elizabeth city'
            ]
        },
        
        'middle': {
            'name': 'United States District Court for the Middle District of North Carolina',
            'cities': [
                'greensboro', 'winston-salem', 'high point', 'burlington', 'asheboro',
                'eden', 'thomasville', 'kernersville', 'graham', 'reidsville'
            ]
        },
        
        'western': {
            'name': 'United States District Court for the Western District of North Carolina',
            'cities': [
                'charlotte', 'asheville', 'gastonia', 'hickory', 'statesville',
                'concord', 'kannapolis', 'salisbury', 'morganton', 'shelby'
            ]
        }
    }
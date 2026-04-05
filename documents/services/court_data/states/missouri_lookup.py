from .base_state_lookup import BaseStateLookup

class MissouriLookup(BaseStateLookup):
    STATE_CODE = 'MO'
    STATE_NAME = 'Missouri'
    
    DISTRICTS = {
        'eastern': {
            'name': 'United States District Court for the Eastern District of Missouri',
            'cities': ['st louis', 'st charles', 'florissant', 'chesterfield', 'st peters', 'university city', 'ballwin', 'kirkwood']
        },
        
        'western': {
            'name': 'United States District Court for the Western District of Missouri',
            'cities': ['kansas city', 'springfield', 'independence', 'columbia', 'lee\'s summit', 'o\'fallon', 'st joseph', 'blue springs']
        }
    }
from .base_state_lookup import BaseStateLookup

class FloridaLookup(BaseStateLookup):
    """Federal district court lookup for Florida state."""
    
    STATE_CODE = 'FL'
    STATE_NAME = 'Florida'
    
    DISTRICTS = {
        'northern': {
            'name': 'United States District Court for the Northern District of Florida',
            'cities': [
                'tallahassee', 'pensacola', 'gainesville', 'panama city', 'marianna'
            ]
        },
        
        'middle': {
            'name': 'United States District Court for the Middle District of Florida',
            'cities': [
                'tampa', 'orlando', 'jacksonville', 'st petersburg', 'clearwater',
                'lakeland', 'ocala', 'fort myers'
            ]
        },
        
        'southern': {
            'name': 'United States District Court for the Southern District of Florida',
            'cities': [
                'miami', 'fort lauderdale', 'west palm beach', 'hollywood', 'coral gables',
                'hialeah', 'pompano beach', 'boca raton', 'key west'
            ]
        }
    }
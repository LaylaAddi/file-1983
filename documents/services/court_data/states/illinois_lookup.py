from .base_state_lookup import BaseStateLookup

class IllinoisLookup(BaseStateLookup):
    """Federal district court lookup for Illinois state."""
    
    STATE_CODE = 'IL'
    STATE_NAME = 'Illinois'
    
    DISTRICTS = {
        'northern': {
            'name': 'United States District Court for the Northern District of Illinois',
            'cities': [
                'chicago', 'rockford', 'aurora', 'joliet', 'naperville',
                'elgin', 'waukegan', 'cicero', 'arlington heights', 'evanston'
            ]
        },
        
        'central': {
            'name': 'United States District Court for the Central District of Illinois',
            'cities': [
                'springfield', 'peoria', 'decatur', 'champaign', 'urbana',
                'bloomington', 'normal', 'quincy', 'danville'
            ]
        },
        
        'southern': {
            'name': 'United States District Court for the Southern District of Illinois',
            'cities': [
                'east st louis', 'belleville', 'alton', 'carbondale',
                'marion', 'mount vernon', 'centralia'
            ]
        }
    }
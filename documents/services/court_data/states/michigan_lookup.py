from .base_state_lookup import BaseStateLookup

class MichiganLookup(BaseStateLookup):
    """Federal district court lookup for Michigan state."""
    
    STATE_CODE = 'MI'
    STATE_NAME = 'Michigan'
    
    DISTRICTS = {
        'eastern': {
            'name': 'United States District Court for the Eastern District of Michigan',
            'cities': [
                'detroit', 'warren', 'sterling heights', 'ann arbor', 'livonia',
                'dearborn', 'westland', 'troy', 'farmington hills', 'pontiac'
            ]
        },
        
        'western': {
            'name': 'United States District Court for the Western District of Michigan',
            'cities': [
                'grand rapids', 'kalamazoo', 'lansing', 'battle creek', 'wyoming',
                'kentwood', 'portage', 'holland', 'east lansing', 'muskegon'
            ]
        }
    }
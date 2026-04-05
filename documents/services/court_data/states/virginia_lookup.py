from .base_state_lookup import BaseStateLookup

class VirginiaLookup(BaseStateLookup):
    STATE_CODE = 'VA'
    STATE_NAME = 'Virginia'
    
    DISTRICTS = {
        'eastern': {
            'name': 'United States District Court for the Eastern District of Virginia',
            'cities': [
                'virginia beach', 'norfolk', 'chesapeake', 'richmond', 'newport news',
                'alexandria', 'hampton', 'portsmouth', 'suffolk', 'arlington'
            ]
        },
        
        'western': {
            'name': 'United States District Court for the Western District of Virginia',
            'cities': [
                'roanoke', 'lynchburg', 'charlottesville', 'danville', 'harrisonburg',
                'bristol', 'martinsville', 'staunton', 'waynesboro', 'blacksburg'
            ]
        }
    }
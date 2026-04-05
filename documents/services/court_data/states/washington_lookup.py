from .base_state_lookup import BaseStateLookup

class WashingtonLookup(BaseStateLookup):
    STATE_CODE = 'WA'
    STATE_NAME = 'Washington'
    
    DISTRICTS = {
        'eastern': {
            'name': 'United States District Court for the Eastern District of Washington',
            'cities': ['spokane', 'yakima', 'richland', 'kennewick', 'pasco', 'walla walla', 'wenatchee', 'moses lake']
        },
        
        'western': {
            'name': 'United States District Court for the Western District of Washington',
            'cities': ['seattle', 'tacoma', 'spokane', 'vancouver', 'bellevue', 'kent', 'everett', 'renton']
        }
    }
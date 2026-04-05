from .base_state_lookup import BaseStateLookup

class IndianaLookup(BaseStateLookup):
    STATE_CODE = 'IN'
    STATE_NAME = 'Indiana'
    
    DISTRICTS = {
        'northern': {
            'name': 'United States District Court for the Northern District of Indiana',
            'cities': ['fort wayne', 'south bend', 'gary', 'hammond', 'muncie', 'anderson', 'elkhart', 'mishawaka']
        },
        
        'southern': {
            'name': 'United States District Court for the Southern District of Indiana',
            'cities': ['indianapolis', 'evansville', 'bloomington', 'carmel', 'fishers', 'noblesville', 'greenwood', 'lawrence']
        }
    }
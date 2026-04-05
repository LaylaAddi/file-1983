from .base_state_lookup import BaseStateLookup

class AlabamaLookup(BaseStateLookup):
    STATE_CODE = 'AL'
    STATE_NAME = 'Alabama'
    
    DISTRICTS = {
        'northern': {
            'name': 'United States District Court for the Northern District of Alabama',
            'cities': ['birmingham', 'huntsville', 'decatur', 'gadsden', 'anniston', 'cullman', 'jasper', 'albertville']
        },
        
        'middle': {
            'name': 'United States District Court for the Middle District of Alabama',
            'cities': ['montgomery', 'tuscaloosa', 'auburn', 'opelika', 'selma', 'troy', 'dothan', 'enterprise']
        },
        
        'southern': {
            'name': 'United States District Court for the Southern District of Alabama',
            'cities': ['mobile', 'baldwin', 'prichard', 'daphne', 'fairhope', 'foley', 'gulf shores', 'orange beach']
        }
    }
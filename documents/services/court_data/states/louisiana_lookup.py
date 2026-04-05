from .base_state_lookup import BaseStateLookup

class LouisianaLookup(BaseStateLookup):
    STATE_CODE = 'LA'
    STATE_NAME = 'Louisiana'
    
    DISTRICTS = {
        'eastern': {
            'name': 'United States District Court for the Eastern District of Louisiana',
            'cities': ['new orleans', 'metairie', 'kenner', 'slidell', 'harvey', 'marrero', 'chalmette', 'gretna']
        },
        
        'middle': {
            'name': 'United States District Court for the Middle District of Louisiana',
            'cities': ['baton rouge', 'lafayette', 'lake charles', 'hammond', 'zachary', 'baker', 'central', 'gonzales']
        },
        
        'western': {
            'name': 'United States District Court for the Western District of Louisiana',
            'cities': ['shreveport', 'monroe', 'alexandria', 'ruston', 'natchitoches', 'minden', 'winnfield', 'pineville']
        }
    }
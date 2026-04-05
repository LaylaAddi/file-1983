from .base_state_lookup import BaseStateLookup

class CaliforniaLookup(BaseStateLookup):
    """Federal district court lookup for California state."""
    
    STATE_CODE = 'CA'
    STATE_NAME = 'California'
    
    DISTRICTS = {
        'northern': {
            'name': 'United States District Court for the Northern District of California',
            'cities': [
                'san francisco', 'oakland', 'san jose', 'berkeley', 'fremont',
                'hayward', 'sunnyvale', 'santa clara', 'vallejo', 'fairfield',
                'concord', 'richmond', 'antioch', 'daly city', 'san mateo'
            ]
        },
        
        'eastern': {
            'name': 'United States District Court for the Eastern District of California',
            'cities': [
                'sacramento', 'fresno', 'stockton', 'modesto', 'salinas',
                'visalia', 'bakersfield', 'chico', 'redding', 'merced'
            ]
        },
        
        'central': {
            'name': 'United States District Court for the Central District of California',
            'cities': [
                'los angeles', 'long beach', 'anaheim', 'santa ana', 'riverside',
                'irvine', 'glendale', 'huntington beach', 'santa clarita', 'garden grove',
                'oceanside', 'torrance', 'orange', 'fullerton', 'pasadena'
            ]
        },
        
        'southern': {
            'name': 'United States District Court for the Southern District of California',
            'cities': [
                'san diego', 'chula vista', 'oceanside', 'escondido', 'carlsbad',
                'el cajon', 'vista', 'san marcos', 'encinitas', 'national city'
            ]
        }
    }
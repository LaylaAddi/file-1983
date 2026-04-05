from .base_state_lookup import BaseStateLookup

class WisconsinLookup(BaseStateLookup):
    STATE_CODE = 'WI'
    STATE_NAME = 'Wisconsin'
    
    DISTRICTS = {
        'eastern': {
            'name': 'United States District Court for the Eastern District of Wisconsin',
            'cities': ['milwaukee', 'madison', 'green bay', 'kenosha', 'racine', 'appleton', 'waukesha', 'oshkosh']
        },
        
        'western': {
            'name': 'United States District Court for the Western District of Wisconsin',
            'cities': ['eau claire', 'la crosse', 'janesville', 'beloit', 'stevens point', 'wausau', 'superior', 'prairie du chien']
        }
    }
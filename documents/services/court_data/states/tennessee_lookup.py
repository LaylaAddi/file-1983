from .base_state_lookup import BaseStateLookup

class TennesseeLookup(BaseStateLookup):
    STATE_CODE = 'TN'
    STATE_NAME = 'Tennessee'
    
    DISTRICTS = {
        'eastern': {
            'name': 'United States District Court for the Eastern District of Tennessee',
            'cities': [
                'knoxville', 'chattanooga', 'johnson city', 'kingsport', 'oak ridge',
                'cleveland', 'morristown', 'maryville', 'cookeville', 'athens'
            ]
        },
        
        'middle': {
            'name': 'United States District Court for the Middle District of Tennessee',
            'cities': [
                'nashville', 'murfreesboro', 'franklin', 'columbia', 'gallatin',
                'lebanon', 'cookeville', 'shelbyville', 'mcminnville', 'tullahoma'
            ]
        },
        
        'western': {
            'name': 'United States District Court for the Western District of Tennessee',
            'cities': [
                'memphis', 'jackson', 'dyersburg', 'union city', 'brownsville',
                'martin', 'paris', 'milan', 'humboldt', 'ripley'
            ]
        }
    }
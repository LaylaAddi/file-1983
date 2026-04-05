from .base_state_lookup import BaseStateLookup

class OhioLookup(BaseStateLookup):
    """Federal district court lookup for Ohio state."""
    
    STATE_CODE = 'OH'
    STATE_NAME = 'Ohio'
    
    DISTRICTS = {
        'northern': {
            'name': 'United States District Court for the Northern District of Ohio',
            'cities': [
                'cleveland', 'toledo', 'akron', 'canton', 'youngstown',
                'lorain', 'elyria', 'mentor', 'parma', 'lakewood'
            ]
        },
        
        'southern': {
            'name': 'United States District Court for the Southern District of Ohio',
            'cities': [
                'columbus', 'cincinnati', 'dayton', 'hamilton', 'springfield',
                'middletown', 'kettering', 'fairborn', 'dublin', 'grove city'
            ]
        }
    }
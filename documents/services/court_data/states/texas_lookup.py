from .base_state_lookup import BaseStateLookup

class TexasLookup(BaseStateLookup):
    """Federal district court lookup for Texas state."""
    
    STATE_CODE = 'TX'
    STATE_NAME = 'Texas'
    
    DISTRICTS = {
        'northern': {
            'name': 'United States District Court for the Northern District of Texas',
            'cities': [
                'dallas', 'fort worth', 'plano', 'garland', 'irving', 'arlington',
                'mckinney', 'frisco', 'carrollton', 'denton', 'richardson'
            ]
        },
        
        'southern': {
            'name': 'United States District Court for the Southern District of Texas',
            'cities': [
                'houston', 'san antonio', 'corpus christi', 'laredo', 'brownsville',
                'mcallen', 'pasadena', 'pearland', 'sugar land', 'league city'
            ]
        },
        
        'eastern': {
            'name': 'United States District Court for the Eastern District of Texas',
            'cities': [
                'tyler', 'longview', 'marshall', 'texarkana', 'lufkin',
                'paris', 'sherman', 'beaumont', 'orange', 'port arthur'
            ]
        },
        
        'western': {
            'name': 'United States District Court for the Western District of Texas',
            'cities': [
                'austin', 'el paso', 'san angelo', 'midland', 'odessa',
                'abilene', 'waco', 'killeen', 'round rock', 'cedar park'
            ]
        }
    }
from .base_state_lookup import BaseStateLookup

class GeorgiaLookup(BaseStateLookup):
    """Federal district court lookup for Georgia state."""
    
    STATE_CODE = 'GA'
    STATE_NAME = 'Georgia'
    
    DISTRICTS = {
        'northern': {
            'name': 'United States District Court for the Northern District of Georgia',
            'cities': [
                'atlanta', 'marietta', 'roswell', 'sandy springs', 'johns creek',
                'alpharetta', 'smyrna', 'dunwoody', 'brookhaven', 'peachtree corners'
            ]
        },
        
        'middle': {
            'name': 'United States District Court for the Middle District of Georgia',
            'cities': [
                'macon', 'columbus', 'warner robins', 'albany', 'valdosta',
                'thomasville', 'cordele', 'americus', 'dublin'
            ]
        },
        
        'southern': {
            'name': 'United States District Court for the Southern District of Georgia',
            'cities': [
                'savannah', 'augusta', 'brunswick', 'waycross', 'statesboro',
                'hinesville', 'pooler', 'richmond hill'
            ]
        }
    }
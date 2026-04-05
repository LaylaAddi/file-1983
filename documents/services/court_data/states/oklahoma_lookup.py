from .base_state_lookup import BaseStateLookup

class OklahomaLookup(BaseStateLookup):
    STATE_CODE = 'OK'
    STATE_NAME = 'Oklahoma'
    
    DISTRICTS = {
        'northern': {
            'name': 'United States District Court for the Northern District of Oklahoma',
            'cities': ['tulsa', 'bartlesville', 'claremore', 'sand springs', 'broken arrow', 'owasso', 'bixby', 'sapulpa']
        },
        
        'eastern': {
            'name': 'United States District Court for the Eastern District of Oklahoma',
            'cities': ['muskogee', 'okmulgee', 'mcalester', 'durant', 'tahlequah', 'poteau', 'eufaula', 'sallisaw']
        },
        
        'western': {
            'name': 'United States District Court for the Western District of Oklahoma',
            'cities': ['oklahoma city', 'norman', 'lawton', 'edmond', 'midwest city', 'enid', 'stillwater', 'ponca city']
        }
    }
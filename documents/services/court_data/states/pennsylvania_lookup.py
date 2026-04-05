# documents/services/court_data/states/pennsylvania_lookup.py

from .base_state_lookup import BaseStateLookup

class PennsylvaniaLookup(BaseStateLookup):
    """Federal district court lookup for Pennsylvania state."""
    
    STATE_CODE = 'PA'
    STATE_NAME = 'Pennsylvania'
    
    DISTRICTS = {
        'western': {
            'name': 'United States District Court for the Western District of Pennsylvania',
            'cities': [
                'pittsburgh', 'allegheny', 'bethel park', 'upper st clair',
                'mount lebanon', 'peters township', 'cranberry township',
                'erie', 'millcreek', 'harborcreek', 'fairview',
                'johnstown', 'somerset', 'windber', 'ebensburg',
                'clarion', 'brookville', 'punxsutawney', 'dubois',
                'clearfield', 'philipsburg', 'state college', 'bellefonte',
                'lock haven', 'williamsport', 'lewisburg', 'sunbury',
                'selinsgrove', 'mifflinburg', 'new castle', 'butler',
                'beaver', 'washington', 'uniontown', 'connellsville',
                'greensburg', 'latrobe', 'jeannette', 'indiana'
            ]
        },
        
        'eastern': {
            'name': 'United States District Court for the Eastern District of Pennsylvania',
            'cities': [
                'philadelphia', 'chester', 'darby', 'yeadon', 'lansdowne',
                'upper darby', 'haverford', 'ardmore', 'bryn mawr',
                'norristown', 'king of prussia', 'conshohocken',
                'west chester', 'coatesville', 'kennett square',
                'media', 'aston', 'bethlehem', 'allentown',
                'easton', 'nazareth', 'emmaus', 'whitehall', 'catasauqua',
                'reading', 'wyomissing', 'shillington', 'west reading',
                'pottstown', 'phoenixville', 'royersford'
            ]
        },
        
        'middle': {
            'name': 'United States District Court for the Middle District of Pennsylvania',
            'cities': [
                'harrisburg', 'camp hill', 'mechanicsburg', 'carlisle',
                'shippensburg', 'chambersburg', 'waynesboro', 'gettysburg',
                'york', 'red lion', 'dallastown', 'spring grove',
                'lancaster', 'columbia', 'ephrata', 'lititz', 'manheim',
                'lebanon', 'palmyra', 'annville', 'hershey',
                'scranton', 'dunmore', 'carbondale', 'archbald',
                'wilkes-barre', 'kingston', 'plymouth', 'nanticoke',
                'hazleton', 'mountain top', 'drums', 'freeland',
                'pottsville', 'schuylkill haven', 'st clair', 'tamaqua',
                'shamokin', 'mount carmel', 'kulpmont', 'elysburg'
            ]
        }
    }
    
    @classmethod
    def _check_city_variations(cls, city):
        """Check for Pennsylvania specific city name variations."""
        city_variations = {
            'philly': 'eastern',
            'pgh': 'western',
            'steel city': 'western'
        }
        
        if city in city_variations:
            district_key = city_variations[city]
            return {
                'court_name': cls.DISTRICTS[district_key]['name'],
                'confidence': 'high',
                'method': 'city_variation',
                'district': district_key,
                'state': cls.STATE_CODE
            }
        return None
    
    @classmethod
    def _geographic_fallback(cls, city):
        """Geographic fallback based on common PA regional patterns."""
        # Western PA patterns
        if any(keyword in city for keyword in ['pittsburgh', 'erie', 'johnstown']):
            return {
                'court_name': cls.DISTRICTS['western']['name'],
                'confidence': 'medium',
                'method': 'geographic_fallback',
                'district': 'western',
                'state': cls.STATE_CODE
            }
        
        # Eastern PA patterns (Philadelphia area)
        elif any(keyword in city for keyword in ['philadelphia', 'chester', 'allentown']):
            return {
                'court_name': cls.DISTRICTS['eastern']['name'],
                'confidence': 'medium',
                'method': 'geographic_fallback',
                'district': 'eastern',
                'state': cls.STATE_CODE
            }
        
        # Middle PA patterns (Central PA)
        elif any(keyword in city for keyword in ['harrisburg', 'scranton', 'york']):
            return {
                'court_name': cls.DISTRICTS['middle']['name'],
                'confidence': 'medium',
                'method': 'geographic_fallback',
                'district': 'middle',
                'state': cls.STATE_CODE
            }
        
        return None
    
    @classmethod
    def _get_default_district(cls):
        """Default to Middle District for unknown PA locations."""
        return {
            'court_name': cls.DISTRICTS['middle']['name'],
            'confidence': 'low',
            'method': 'default_fallback',
            'district': 'middle',
            'state': cls.STATE_CODE,
            'note': 'Could not determine exact district. Middle District used as default. Please verify.'
        }
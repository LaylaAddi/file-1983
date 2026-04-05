# documents/services/court_data/states/new_york_lookup.py

from .base_state_lookup import BaseStateLookup

class NewYorkLookup(BaseStateLookup):
    """Federal district court lookup for New York state."""
    
    STATE_CODE = 'NY'
    STATE_NAME = 'New York'
    
    DISTRICTS = {
        'northern': {
            'name': 'United States District Court for the Northern District of New York',
            'cities': [
                'albany', 'schenectady', 'troy', 'saratoga springs', 'glens falls',
                'plattsburgh', 'watertown', 'utica', 'rome', 'syracuse', 'oswego',
                'fulton', 'oneida', 'herkimer', 'little falls', 'amsterdam',
                'gloversville', 'johnstown', 'cooperstown', 'oneonta', 'cortland',
                'auburn', 'geneva', 'canandaigua', 'elmira', 'corning', 'ithaca',
                'binghamton', 'endicott', 'johnson city'
            ]
        },
        
        'southern': {
            'name': 'United States District Court for the Southern District of New York',
            'cities': [
                'new york', 'manhattan', 'bronx', 'brooklyn', 'queens', 
                'staten island', 'yonkers', 'mount vernon', 'new rochelle',
                'white plains', 'tarrytown', 'peekskill', 'ossining',
                'poughkeepsie', 'newburgh', 'kingston', 'middletown'
            ]
        },
        
        'eastern': {
            'name': 'United States District Court for the Eastern District of New York',
            'cities': [
                'brooklyn', 'queens', 'staten island', 'long island',
                'hempstead', 'freeport', 'levittown', 'hicksville',
                'huntington', 'babylon', 'islip', 'smithtown',
                'riverhead', 'southampton', 'east hampton'
            ]
        },
        
        'western': {
            'name': 'United States District Court for the Western District of New York',
            'cities': [
                'buffalo', 'niagara falls', 'lockport', 'tonawanda',
                'cheektowaga', 'west seneca', 'lancaster', 'depew',
                'rochester', 'irondequoit', 'greece', 'henrietta',
                'brighton', 'penfield', 'webster', 'fairport',
                'batavia', 'geneva', 'canandaigua', 'victor',
                'alfred', 'wellsville', 'hornell', 'dansville',
                'geneseo', 'livonia', 'avon', 'york', 'leicester',
                'mount morris', 'nunda', 'portageville', 'alfred station'
            ]
        }
    }
    
    @classmethod
    def _check_city_variations(cls, city):
        """Check for New York specific city name variations."""
        city_variations = {
            'nyc': 'southern',
            'new york city': 'southern', 
            'manhattan': 'southern',
            'the bronx': 'southern',
            'long island': 'eastern',
            'li': 'eastern'
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
        """Geographic fallback based on common NY regional patterns."""
        # Western NY patterns
        if any(keyword in city for keyword in ['buffalo', 'rochester', 'niagara']):
            return {
                'court_name': cls.DISTRICTS['western']['name'],
                'confidence': 'medium',
                'method': 'geographic_fallback',
                'district': 'western',
                'state': cls.STATE_CODE
            }
        
        # Northern NY patterns (upstate)
        elif any(keyword in city for keyword in ['syracuse', 'albany', 'utica']):
            return {
                'court_name': cls.DISTRICTS['northern']['name'],
                'confidence': 'medium',
                'method': 'geographic_fallback',
                'district': 'northern',
                'state': cls.STATE_CODE
            }
        
        # NYC metro patterns
        elif any(keyword in city for keyword in ['york', 'westchester', 'rockland']):
            return {
                'court_name': cls.DISTRICTS['southern']['name'],
                'confidence': 'medium',
                'method': 'geographic_fallback',
                'district': 'southern',
                'state': cls.STATE_CODE
            }
        
        # Long Island patterns
        elif any(keyword in city for keyword in ['island', 'suffolk', 'nassau']):
            return {
                'court_name': cls.DISTRICTS['eastern']['name'],
                'confidence': 'medium',
                'method': 'geographic_fallback',
                'district': 'eastern',
                'state': cls.STATE_CODE
            }
        
        return None
    
    @classmethod
    def _get_default_district(cls):
        """Default to Northern District for unknown NY locations."""
        return {
            'court_name': cls.DISTRICTS['northern']['name'],
            'confidence': 'low',
            'method': 'default_fallback',
            'district': 'northern',
            'state': cls.STATE_CODE,
            'note': 'Could not determine exact district. Northern District used as default. Please verify.'
        }
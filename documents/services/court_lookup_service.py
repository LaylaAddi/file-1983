class CourtLookupService:
    """Main coordinator for federal district court lookups across all states."""

    # Mapping of state codes to their lookup classes
    STATE_LOOKUPS = {
        # Multi-district states
        'NY': ('new_york_lookup', 'NewYorkLookup'),
        'PA': ('pennsylvania_lookup', 'PennsylvaniaLookup'),
        'CA': ('california_lookup', 'CaliforniaLookup'),
        'TX': ('texas_lookup', 'TexasLookup'),
        'FL': ('florida_lookup', 'FloridaLookup'),
        'IL': ('illinois_lookup', 'IllinoisLookup'),
        'OH': ('ohio_lookup', 'OhioLookup'),
        'GA': ('georgia_lookup', 'GeorgiaLookup'),
        'MI': ('michigan_lookup', 'MichiganLookup'),
        'VA': ('virginia_lookup', 'VirginiaLookup'),
        'NC': ('north_carolina_lookup', 'NorthCarolinaLookup'),
        'TN': ('tennessee_lookup', 'TennesseeLookup'),
        'WI': ('wisconsin_lookup', 'WisconsinLookup'),
        'IN': ('indiana_lookup', 'IndianaLookup'),
        'MO': ('missouri_lookup', 'MissouriLookup'),
        'AL': ('alabama_lookup', 'AlabamaLookup'),
        'SC': ('south_carolina_lookup', 'SouthCarolinaLookup'),
        'KY': ('kentucky_lookup', 'KentuckyLookup'),
        'LA': ('louisiana_lookup', 'LouisianaLookup'),
        'MS': ('mississippi_lookup', 'MississippiLookup'),
        'AR': ('arkansas_lookup', 'ArkansasLookup'),
        'IA': ('iowa_lookup', 'IowaLookup'),
        'OK': ('oklahoma_lookup', 'OklahomaLookup'),
        'WV': ('west_virginia_lookup', 'WestVirginiaLookup'),
        'WA': ('washington_lookup', 'WashingtonLookup'),
        # Single-district states
        'AK': ('alaska_lookup', 'AlaskaLookup'),
        'DE': ('delaware_lookup', 'DelawareLookup'),
        'HI': ('hawaii_lookup', 'HawaiiLookup'),
        'ID': ('idaho_lookup', 'IdahoLookup'),
        'ME': ('maine_lookup', 'MaineLookup'),
        'MT': ('montana_lookup', 'MontanaLookup'),
        'NV': ('nevada_lookup', 'NevadaLookup'),
        'NH': ('new_hampshire_lookup', 'NewHampshireLookup'),
        'RI': ('rhode_island_lookup', 'RhodeIslandLookup'),
        'SD': ('south_dakota_lookup', 'SouthDakotaLookup'),
        'UT': ('utah_lookup', 'UtahLookup'),
        'VT': ('vermont_lookup', 'VermontLookup'),
        'WY': ('wyoming_lookup', 'WyomingLookup'),
        'DC': ('district_of_columbia_lookup', 'DistrictOfColumbiaLookup'),
        'MA': ('massachusetts_lookup', 'MassachusettsLookup'),
        'CT': ('connecticut_lookup', 'ConnecticutLookup'),
        'NJ': ('new_jersey_lookup', 'NewJerseyLookup'),
        'MD': ('maryland_lookup', 'MarylandLookup'),
        'OR': ('oregon_lookup', 'OregonLookup'),
        'CO': ('colorado_lookup', 'ColoradoLookup'),
        'AZ': ('arizona_lookup', 'ArizonaLookup'),
        'MN': ('minnesota_lookup', 'MinnesotaLookup'),
        'ND': ('north_dakota_lookup', 'NorthDakotaLookup'),
        'KS': ('kansas_lookup', 'KansasLookup'),
        'NE': ('nebraska_lookup', 'NebraskaLookup'),
    }

    @classmethod
    def lookup_court_by_location(cls, city, state, county=None, use_gpt_fallback=True):
        """
        Look up federal district court by location.

        First tries static lookup (fast, free). If that fails and use_gpt_fallback=True,
        falls back to GPT with web search (slower, costs money, but always works).

        Args:
            city: City name
            state: State code or name
            county: Optional county name (not currently used)
            use_gpt_fallback: If True, use GPT with web search when static lookup fails

        Returns:
            dict with court_name, confidence, method, etc. or None if lookup fails
        """
        if not city or not state:
            return None

        state = state.strip().upper()

        # Try static lookup first
        result = cls._static_lookup(city, state)
        if result:
            return result

        # Static lookup failed, try GPT fallback if enabled
        if use_gpt_fallback:
            return cls._gpt_fallback_lookup(city, state)

        # No fallback, return None
        return None

    @classmethod
    def _static_lookup(cls, city, state):
        """
        Try static lookup from the state-specific lookup classes.
        Returns the result or None if city not found.
        """
        if state not in cls.STATE_LOOKUPS:
            return None

        module_name, class_name = cls.STATE_LOOKUPS[state]

        try:
            # Dynamic import of state lookup module
            import importlib
            module = importlib.import_module(f'.court_data.states.{module_name}', package='documents.services')
            lookup_class = getattr(module, class_name)
            return lookup_class.lookup_court_by_city(city)
        except (ImportError, AttributeError):
            return None

    @classmethod
    def _gpt_fallback_lookup(cls, city, state):
        """
        Use GPT with web search to find the federal district court.
        Called when static lookup fails to find the city.
        """
        try:
            from .openai_service import OpenAIService
            service = OpenAIService()
            result = service.lookup_federal_court(city, state)

            if result.get('success'):
                return {
                    'court_name': result['court_name'],
                    'district': result.get('district', ''),
                    'confidence': result.get('confidence', 'medium'),
                    'method': 'gpt_web_search',
                    'source': result.get('source', ''),
                    'state': state,
                    'note': f'Found via AI web search for {city}, {state}'
                }
            else:
                # GPT lookup failed, return generic result
                return {
                    'court_name': f'Federal District Court ({state})',
                    'confidence': 'low',
                    'method': 'fallback_failed',
                    'state': state,
                    'note': f'Could not determine exact court for {city}, {state}. Please verify manually.'
                }
        except Exception as e:
            # If GPT service fails, return generic result
            return {
                'court_name': f'Federal District Court ({state})',
                'confidence': 'low',
                'method': 'error',
                'state': state,
                'note': f'Error during lookup: {str(e)}. Please verify manually.'
            }

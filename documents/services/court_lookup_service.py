class CourtLookupService:
    """Main coordinator for federal district court lookups across all states."""

    # Full state name → 2-letter code (handles GPT returning full names)
    STATE_NAME_TO_CODE = {
        'ALABAMA': 'AL', 'ALASKA': 'AK', 'ARIZONA': 'AZ', 'ARKANSAS': 'AR',
        'CALIFORNIA': 'CA', 'COLORADO': 'CO', 'CONNECTICUT': 'CT', 'DELAWARE': 'DE',
        'DISTRICT OF COLUMBIA': 'DC', 'FLORIDA': 'FL', 'GEORGIA': 'GA', 'HAWAII': 'HI',
        'IDAHO': 'ID', 'ILLINOIS': 'IL', 'INDIANA': 'IN', 'IOWA': 'IA',
        'KANSAS': 'KS', 'KENTUCKY': 'KY', 'LOUISIANA': 'LA', 'MAINE': 'ME',
        'MARYLAND': 'MD', 'MASSACHUSETTS': 'MA', 'MICHIGAN': 'MI', 'MINNESOTA': 'MN',
        'MISSISSIPPI': 'MS', 'MISSOURI': 'MO', 'MONTANA': 'MT', 'NEBRASKA': 'NE',
        'NEVADA': 'NV', 'NEW HAMPSHIRE': 'NH', 'NEW JERSEY': 'NJ', 'NEW MEXICO': 'NM',
        'NEW YORK': 'NY', 'NORTH CAROLINA': 'NC', 'NORTH DAKOTA': 'ND', 'OHIO': 'OH',
        'OKLAHOMA': 'OK', 'OREGON': 'OR', 'PENNSYLVANIA': 'PA', 'RHODE ISLAND': 'RI',
        'SOUTH CAROLINA': 'SC', 'SOUTH DAKOTA': 'SD', 'TENNESSEE': 'TN', 'TEXAS': 'TX',
        'UTAH': 'UT', 'VERMONT': 'VT', 'VIRGINIA': 'VA', 'WASHINGTON': 'WA',
        'WEST VIRGINIA': 'WV', 'WISCONSIN': 'WI', 'WYOMING': 'WY',
    }

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
        # Normalize full state names to 2-letter codes (GPT often returns full names)
        state = cls.STATE_NAME_TO_CODE.get(state, state)

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
        Ask GPT which federal district court covers a given city/state.
        Called when the static city list doesn't have the city.
        """
        try:
            from django.conf import settings
            from openai import OpenAI

            api_key = getattr(settings, 'OPENAI_API_KEY', '')
            if not api_key:
                return None

            client = OpenAI(api_key=api_key)
            prompt = (
                f'Which United States federal district court has jurisdiction over {city}, {state}? '
                f'Reply with only the full official court name, e.g. '
                f'"United States District Court for the Southern District of Florida". '
                f'No explanation, just the court name.'
            )
            response = client.chat.completions.create(
                model='gpt-4o',
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0,
                max_tokens=60,
            )
            court_name = response.choices[0].message.content.strip().strip('"')
            if court_name:
                return {
                    'court_name': court_name,
                    'confidence': 'medium',
                    'method': 'gpt_fallback',
                    'state': state,
                }
        except Exception:
            pass
        return None

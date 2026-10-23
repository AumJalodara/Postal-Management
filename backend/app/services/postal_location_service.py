import csv
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from collections import defaultdict

logger = logging.getLogger(__name__)

# Office type hierarchy for deterministic tie-breaking (HO > SO > BO > others)
OFFICE_TYPE_RANK = {
    "HO": 3,
    "SO": 2,
    "BO": 1
}

# Standardized Indian States & Union Territories canonical mapping
STATE_CANONICAL_NAMES = {
    "andaman and nicobar islands": "Andaman and Nicobar Islands",
    "andhra pradesh": "Andhra Pradesh",
    "arunachal pradesh": "Arunachal Pradesh",
    "assam": "Assam",
    "bihar": "Bihar",
    "chandigarh": "Chandigarh",
    "chhattisgarh": "Chhattisgarh",
    "the dadra and nagar haveli and daman and diu": "Dadra and Nagar Haveli and Daman and Diu",
    "dadra and nagar haveli and daman and diu": "Dadra and Nagar Haveli and Daman and Diu",
    "delhi": "Delhi",
    "goa": "Goa",
    "gujarat": "Gujarat",
    "haryana": "Haryana",
    "himachal pradesh": "Himachal Pradesh",
    "jammu and kashmir": "Jammu and Kashmir",
    "jharkhand": "Jharkhand",
    "karnataka": "Karnataka",
    "kerala": "Kerala",
    "ladakh": "Ladakh",
    "lakshadweep": "Lakshadweep",
    "madhya pradesh": "Madhya Pradesh",
    "maharashtra": "Maharashtra",
    "manipur": "Manipur",
    "meghalaya": "Meghalaya",
    "mizoram": "Mizoram",
    "nagaland": "Nagaland",
    "odisha": "Odisha",
    "puducherry": "Puducherry",
    "punjab": "Punjab",
    "rajasthan": "Rajasthan",
    "sikkim": "Sikkim",
    "tamil nadu": "Tamil Nadu",
    "telangana": "Telangana",
    "tripura": "Tripura",
    "uttar pradesh": "Uttar Pradesh",
    "uttarakhand": "Uttarakhand",
    "west bengal": "West Bengal",
}

# Major representative Head Office PIN codes per State / UT for instant smart auto-filling
STATE_DEFAULT_PINS = {
    "Andaman and Nicobar Islands": "744101",
    "Andhra Pradesh": "520001",
    "Arunachal Pradesh": "791111",
    "Assam": "781001",
    "Bihar": "800001",
    "Chandigarh": "160017",
    "Chhattisgarh": "492001",
    "Dadra and Nagar Haveli and Daman and Diu": "396210",
    "Delhi": "110001",
    "Goa": "403001",
    "Gujarat": "380001",
    "Haryana": "134112",
    "Himachal Pradesh": "171001",
    "Jammu and Kashmir": "190001",
    "Jharkhand": "834001",
    "Karnataka": "560001",
    "Kerala": "695001",
    "Ladakh": "194101",
    "Lakshadweep": "682555",
    "Madhya Pradesh": "462001",
    "Maharashtra": "400001",
    "Manipur": "795001",
    "Meghalaya": "793001",
    "Mizoram": "796001",
    "Nagaland": "797001",
    "Odisha": "751001",
    "Puducherry": "605001",
    "Punjab": "141001",
    "Rajasthan": "302001",
    "Sikkim": "737101",
    "Tamil Nadu": "600001",
    "Telangana": "500001",
    "Tripura": "799001",
    "Uttar Pradesh": "226001",
    "Uttarakhand": "248001",
    "West Bengal": "700001",
}


def normalize_text(val: Optional[str]) -> str:
    """Standardizes text for robust dictionary lookups (lowercase, single spaces)."""
    if not val:
        return ""
    return " ".join(val.strip().lower().split())


def canonicalize_state(raw_state: Optional[str]) -> str:
    """Maps raw or stylized state names to standard Title Case string."""
    norm = normalize_text(raw_state)
    return STATE_CANONICAL_NAMES.get(norm, (raw_state or "").strip().title())


def canonicalize_district(raw_district: Optional[str]) -> str:
    """Formats district name to Title Case."""
    if not raw_district:
        return ""
    return " ".join([word.capitalize() for word in raw_district.strip().split()])


class PostalLocationService:
    def __init__(self, data_path: Optional[Path] = None):
        """
        Initializes the Postal Location Service.
        Loads the postal reference CSV into memory for fast PIN resolution,
        state-city indexing, and complete mismatch prevention.
        """
        if data_path is None:
            base_dir = Path(__file__).resolve().parents[3]
            data_path = base_dir / "data" / "postal_reference" / "processed" / "postal_reference_cleaned.csv"
            
        self.data_path = data_path
        self._pin_cache: Dict[str, Dict[str, Any]] = {}
        self._states: List[str] = []
        self._state_districts: Dict[str, List[str]] = defaultdict(list)
        self._state_district_pins: Dict[tuple, List[str]] = defaultdict(list)
        self._state_pins: Dict[str, List[str]] = defaultdict(list)
        self._district_default_pin: Dict[tuple, str] = {}
        self._is_loaded = False
        
    def _load_data(self):
        """Loads and processes the postal reference dataset deterministically."""
        if self._is_loaded:
            return
            
        if not self.data_path.exists():
            logger.error(f"Postal reference data not found at {self.data_path}")
            return
            
        pin_groups: Dict[str, List[Dict[str, Any]]] = {}
        state_district_set: Dict[str, set] = defaultdict(set)
        state_district_pin_set: Dict[tuple, set] = defaultdict(set)
        state_pin_set: Dict[str, set] = defaultdict(set)
        states_set = set()
        
        try:
            with open(self.data_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    pin = row.get('pincode', '').strip()
                    if not pin:
                        continue
                        
                    if pin not in pin_groups:
                        pin_groups[pin] = []
                    pin_groups[pin].append(row)

                    st_raw = row.get('statename', '')
                    dt_raw = row.get('district', '')
                    if st_raw:
                        c_state = canonicalize_state(st_raw)
                        c_dist = canonicalize_district(dt_raw) if dt_raw else "Central"
                        states_set.add(c_state)
                        state_district_set[c_state].add(c_dist)
                        state_district_pin_set[(c_state, c_dist)].add(pin)
                        state_pin_set[c_state].add(pin)
                    
        except Exception as e:
            logger.error(f"Failed to load postal reference data: {e}")
            return
            
        # Deterministically resolve each PIN to a single best representative record
        for pin, records in pin_groups.items():
            best_rec = self._resolve_best_record(records)
            self._pin_cache[pin] = best_rec

        # Precompute sorted structures
        self._states = sorted(list(states_set))
        for st, dset in state_district_set.items():
            self._state_districts[st] = sorted(list(dset))
            
        for (st, dt), pset in state_district_pin_set.items():
            sorted_pins = sorted(list(pset))
            self._state_district_pins[(st, dt)] = sorted_pins
            # Assign the first (lowest / primary) PIN as default for this district
            if sorted_pins:
                self._district_default_pin[(st, dt)] = sorted_pins[0]

        for st, pset in state_pin_set.items():
            self._state_pins[st] = sorted(list(pset))
            
        self._is_loaded = True
        logger.info(
            f"Loaded {len(self._pin_cache)} postal PINs across {len(self._states)} states & UTs."
        )

    def _resolve_best_record(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Deterministically selects the best record for a PIN based on:
        1. Has valid coordinates (True > False)
        2. Delivery status ("Delivery" > "Non-Delivery" or other)
        3. Office type hierarchy (HO > SO > BO)
        4. Alphabetical by office name (as a final tie-breaker)
        """
        records.sort(
            key=lambda r: (
                not bool(r.get('latitude', '').strip() and r.get('longitude', '').strip()),
                r.get('delivery', '').strip().lower() != "delivery",
                -OFFICE_TYPE_RANK.get(r.get('officetype', '').strip().upper(), 0),
                r.get('officename', '').strip()
            )
        )
        return records[0]

    def get_states(self) -> List[str]:
        """Returns the sorted list of all 36 Indian States and Union Territories."""
        if not self._is_loaded:
            self._load_data()
        return list(self._states)

    def get_districts_for_state(self, state: str) -> List[str]:
        """Returns the sorted list of cities/districts available in the given state."""
        if not self._is_loaded:
            self._load_data()
        c_state = canonicalize_state(state)
        # Direct lookup or fallback to case-insensitive match
        if c_state in self._state_districts:
            return list(self._state_districts[c_state])
        
        norm = normalize_text(state)
        for st_name, dists in self._state_districts.items():
            if normalize_text(st_name) == norm:
                return list(dists)
        return []

    def get_default_pin_for_state(self, state: str) -> Optional[str]:
        """Returns the primary representative PIN code for a state."""
        if not self._is_loaded:
            self._load_data()
        c_state = canonicalize_state(state)
        if c_state in STATE_DEFAULT_PINS:
            return STATE_DEFAULT_PINS[c_state]
        pins = self._state_pins.get(c_state, [])
        return pins[0] if pins else None

    def get_default_pin_for_district(self, state: str, district: str) -> Optional[str]:
        """Returns the primary PIN code for a given state & district."""
        if not self._is_loaded:
            self._load_data()
        c_state = canonicalize_state(state)
        c_dist = canonicalize_district(district)
        
        # Exact match
        if (c_state, c_dist) in self._district_default_pin:
            return self._district_default_pin[(c_state, c_dist)]
            
        # Case-insensitive / partial match
        norm_dist = normalize_text(district)
        norm_state = normalize_text(state)
        for (st, dt), pin in self._district_default_pin.items():
            if normalize_text(st) == norm_state and (normalize_text(dt) == norm_dist or norm_dist in normalize_text(dt)):
                return pin

        return self.get_default_pin_for_state(state)

    def get_pincodes_for_location(
        self,
        state: Optional[str] = None,
        district: Optional[str] = None,
        limit: int = 100
    ) -> List[str]:
        """Returns matching PIN codes filtered by state and/or district."""
        if not self._is_loaded:
            self._load_data()
            
        if state and district:
            c_state = canonicalize_state(state)
            c_dist = canonicalize_district(district)
            pins = self._state_district_pins.get((c_state, c_dist), [])
            if not pins:
                # Fallback search
                norm_state = normalize_text(state)
                norm_dist = normalize_text(district)
                for (st, dt), p_list in self._state_district_pins.items():
                    if normalize_text(st) == norm_state and (normalize_text(dt) == norm_dist or norm_dist in normalize_text(dt)):
                        pins = p_list
                        break
            return pins[:limit]

        if state:
            c_state = canonicalize_state(state)
            pins = self._state_pins.get(c_state, [])
            if not pins:
                norm_state = normalize_text(state)
                for st, p_list in self._state_pins.items():
                    if normalize_text(st) == norm_state:
                        pins = p_list
                        break
            return pins[:limit]

        return list(self._pin_cache.keys())[:limit]

    def get_location_for_pin(self, pin: str) -> Optional[Dict[str, Any]]:
        """
        Resolves a PIN code to its geographic and administrative details.
        
        Returns:
            Dict containing:
                - pin
                - latitude (float, or None if missing/invalid)
                - longitude (float, or None if missing/invalid)
                - district
                - state
                - officename
            or None if the PIN is entirely unknown.
        """
        if not self._is_loaded:
            self._load_data()
            
        cleaned_pin = pin.strip() if pin else ""
        record = self._pin_cache.get(cleaned_pin)
        if not record:
            return None
            
        lat_str = record.get('latitude', '').strip()
        lon_str = record.get('longitude', '').strip()
        
        latitude = None
        longitude = None
        
        if lat_str and lon_str:
            try:
                latitude = float(lat_str)
                longitude = float(lon_str)
            except ValueError:
                pass
                
        raw_state = record.get('statename', '').strip()
        raw_dist = record.get('district', '').strip()
        raw_office = record.get('officename', '').strip()

        return {
            "pin": cleaned_pin,
            "latitude": latitude,
            "longitude": longitude,
            "district": canonicalize_district(raw_dist),
            "state": canonicalize_state(raw_state),
            "officename": raw_office.title() if raw_office else ""
        }

    def validate_location(
        self,
        state: str,
        city: Optional[str] = None,
        pin: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validates the geographic consistency of state, city/district, and PIN code.
        Prevents mismatch during booking.
        """
        if not self._is_loaded:
            self._load_data()

        cleaned_pin = (pin or "").strip()
        if not cleaned_pin:
            return {
                "is_valid": True,
                "message": "PIN not provided yet."
            }

        loc = self.get_location_for_pin(cleaned_pin)
        if not loc:
            # If PIN is not found in official directory, verify 6-digit structure
            if len(cleaned_pin) == 6 and cleaned_pin.isdigit() and not cleaned_pin.startswith("0"):
                return {
                    "is_valid": True,
                    "is_unverified": True,
                    "message": "PIN not found in static directory, but format is valid."
                }
            return {
                "is_valid": False,
                "mismatch_type": "INVALID_PIN_FORMAT",
                "message": "PIN code must contain exactly 6 digits and cannot start with 0."
            }

        pin_state = loc["state"]
        pin_district = loc["district"]
        pin_office = loc["officename"]

        # 1. State Mismatch Check
        user_state_norm = normalize_text(state)
        pin_state_norm = normalize_text(pin_state)

        # Allow slight variations like 'Dadra & Nagar Haveli' vs full name
        states_compatible = (
            user_state_norm == pin_state_norm or
            (pin_state_norm in user_state_norm) or
            (user_state_norm in pin_state_norm)
        )

        if not states_compatible:
            return {
                "is_valid": False,
                "mismatch_type": "STATE_MISMATCH",
                "message": f"PIN {cleaned_pin} belongs to {pin_state} ({pin_district}), but you selected '{state}'.",
                "expected_state": pin_state,
                "expected_district": pin_district,
                "expected_officename": pin_office,
                "suggested_pin": self.get_default_pin_for_state(state)
            }

        # 2. City / District Mismatch Check (if city is provided and meaningful)
        if city and len(city.strip()) >= 2:
            user_city_norm = normalize_text(city)
            pin_dist_norm = normalize_text(pin_district)
            pin_off_norm = normalize_text(pin_office)

            city_compatible = (
                user_city_norm in pin_dist_norm or
                pin_dist_norm in user_city_norm or
                user_city_norm in pin_off_norm or
                pin_off_norm in user_city_norm
            )

            # If city is completely incompatible with both district and office name
            if not city_compatible:
                return {
                    "is_valid": False,
                    "mismatch_type": "CITY_MISMATCH",
                    "message": f"PIN {cleaned_pin} is in district '{pin_district}', not '{city}'.",
                    "expected_state": pin_state,
                    "expected_district": pin_district,
                    "expected_officename": pin_office,
                    "suggested_pin": self.get_default_pin_for_district(state, city)
                }

        return {
            "is_valid": True,
            "state": pin_state,
            "district": pin_district,
            "officename": pin_office,
            "latitude": loc.get("latitude"),
            "longitude": loc.get("longitude"),
            "message": f"Verified: {pin_district}, {pin_state} ({pin_office})"
        }


# Global singleton instance for use across the application
postal_location_service = PostalLocationService()

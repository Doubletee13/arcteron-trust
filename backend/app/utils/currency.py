COUNTRY_CURRENCY_MAP = {
    "United States": "USD",
    "United Kingdom": "GBP",
    "Nigeria": "NGN",
    "Canada": "CAD",
    "Australia": "AUD",
    "Germany": "EUR",
    "France": "EUR",
    "Italy": "EUR",
    "Spain": "EUR",
    "Netherlands": "EUR",
    "Switzerland": "CHF",
    "Japan": "JPY",
    "China": "CNY",
    "India": "INR",
    "Brazil": "BRL",
    "South Africa": "ZAR",
    "United Arab Emirates": "AED",
    "Saudi Arabia": "SAR",
    "Singapore": "SGD",
    "Hong Kong": "HKD",
    "New Zealand": "NZD",
    "Mexico": "MXN",
    "Argentina": "ARS",
    "Turkey": "TRY",
    "Russia": "RUB",
    "South Korea": "KRW",
}

def get_currency_for_country(country: str) -> str:
    if not country:
        return "USD"
    # Try exact match, then stripped/case-insensitive match if needed
    cleaned = country.strip()
    if cleaned in COUNTRY_CURRENCY_MAP:
        return COUNTRY_CURRENCY_MAP[cleaned]
    
    # Simple case-insensitive lookup
    for k, v in COUNTRY_CURRENCY_MAP.items():
        if k.lower() == cleaned.lower():
            return v
            
    return "USD"

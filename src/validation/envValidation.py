import requests

from src.locator.mapping import generate_map


def validate_locationiq_key(key: str):
    try:
        generate_map(key, 53.2845324, 10.5339104, [(53.2845324, 10.5339104)])
    except requests.exceptions.HTTPError as e:
        return False

    return True

import requests

LOCATION_IQ_MAP_GENERATION_ENDPOINT = "https://maps.locationiq.com/v3/staticmap"

def generate_map(
        api_key: str,
        lat: float,
        lon: float,
        markers: list[tuple[float, float]],
        zoom: int = 16,
        size: tuple[int, int] = (600, 400),
        img_format: str = "png",
) -> bytes:
    params = {
        "key": api_key,
        "center": f"{lat},{lon}",
        "zoom": zoom,
        "size": f"{size[0]}x{size[1]}",
        "markers": "|".join([f"icon:small-red-cutout|{lat},{lon}" for lat, lon in markers]),
        "format": img_format
    }

    response = requests.get(LOCATION_IQ_MAP_GENERATION_ENDPOINT, params=params)
    response.raise_for_status()
    return response.content

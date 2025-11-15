from skyfield.api import load, wgs84, N, W
from skyfield.units import Angle, Distance

def get_relative_altazd(
        target_body: str,
        observer_latitude: float,
        observer_longitude: float,
        bsp_file: str
) -> tuple[Angle, Angle, Distance]:
    """
    :param target_body: The target body to track (e.g., 'mars', 'jupiter', 'saturn', 'blackholeX', 'star', 'moon', 'sun')
    :param observer_latitude: The observer's latitude
    :param observer_longitude: The observer's longitude
    :param bsp_file: The path to the BSP file (e.g., 'de421.bsp')
    :return: A generator that yields the altitude, azimuth, and distance of the target body relative to the observer
    """
    ts = load.timescale()
    planets = load(bsp_file)

    try:
        body = planets[target_body]
    except (ValueError, KeyError) as e:
        available = list(planets.names().values())
        print(f"Error: '{target_body}' not found in {bsp_file}")
        print(f"Available targets: {available}")
        raise
    try:
        earth = planets['earth']
    except (ValueError, KeyError) as e:
        print(f"Error: 'earth' not found in {bsp_file}")
        print(f"Choose a different bsp file!")
        raise

    observer = earth + wgs84.latlon(observer_latitude * N, observer_longitude * W)
    astrometric = observer.at(ts.now()).observe(body)

    alt, az, d = astrometric.apparent().altaz()
    return alt, az, d

def download_ephemeris_file(bsp_file: str):
    load(bsp_file)
    return

def available_planets(bsp_file: str) -> list[str]:
    planets = load(bsp_file)
    return list(planets.names().values())
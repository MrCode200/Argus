from typing import Optional

from skyfield.api import load, wgs84, N, W
from skyfield.units import Angle, Distance


def get_relative_altazd(
        target_body: str,
        observer_latitude: float,
        observer_longitude: float,
        full_bsp_file: str,
        target_bsp_file: Optional[str] = None
) -> tuple[Angle, Angle, Distance]:
    """
    Calculate altitude, azimuth, and distance of a celestial body.

    :param target_body: Target body name (e.g., 'MARS', 'IO', 'MOON', 'SUN')
    :param observer_latitude: Observer's latitude in degrees
    :param observer_longitude: Observer's longitude in degrees
    :param full_bsp_file: Path to full planetary ephemeris (e.g., 'de421.bsp')
    :param target_bsp_file: Optional path to specialized ephemeris for target body
    :return: (altitude, azimuth, distance) tuple
    """
    ts = load.timescale()

    # Always load full ephemeris (needed for Earth and deflection)
    full_ephemeris = load(full_bsp_file)

    # Get target body - try specialized file first, then fall back to full
    if target_bsp_file:
        target_ephemeris = load(target_bsp_file)
        body = _find_body_by_name(target_ephemeris, target_body, target_bsp_file)
    else:
        # Use full ephemeris for target body too
        body = _find_body_by_name(full_ephemeris, target_body, full_bsp_file)

    # Get Earth from full ephemeris
    earth = full_ephemeris['earth']

    # Create observer at given location
    observer = earth + wgs84.latlon(observer_latitude * N, observer_longitude * W)

    # Observe target body
    astrometric = observer.at(ts.now()).observe(body)

    # Compute apparent position (includes aberration and deflection)
    alt, az, d = astrometric.apparent().altaz()

    return alt, az, d

def _find_body_by_name(ephemeris, target_name: str, filename: str):
    """
    Find a body in an ephemeris by trying all possible name aliases.

    :param ephemeris: Loaded Skyfield ephemeris
    :param target_name: The name to search for
    :param filename: Filename for error messages
    :return: The body object
    :raises ValueError: If body not found
    """
    # First, try direct lookup (fastest)
    try:
        return ephemeris[target_name]
    except (ValueError, KeyError):
        pass

    # If that fails, search through all aliases
    target_upper = target_name.upper()
    all_names = ephemeris.names()

    for code, aliases in all_names.items():
        # aliases is a list like ['SOLAR_SYSTEM_BARYCENTER', 'SSB', 'SOLAR SYSTEM BARYCENTER']
        for alias in aliases:
            if alias.upper() == target_upper:
                # Found it! Use the code to get the body
                return ephemeris[code]

    # Not found - create helpful error message
    available = []
    for aliases in all_names.values():
        if aliases:
            # Use the last alias (usually the most readable one)
            available.append(aliases[-1] if len(aliases) > 0 else str(aliases))

    raise ValueError(
        f"'{target_name}' not found in {filename}\n"
        f"Available targets: {', '.join(sorted(set(available)))}"
    )

def download_ephemeris_file(bsp_file: str):
    load(bsp_file)
    return

def available_planets(bsp_file: str) -> list[str]:
    planets = load(bsp_file)
    return list(planets.names().values())


if __name__ == '__main__':
    print(available_planets("../../ephemerises/jup365.bsp")[0][2])
"""Generate uniformly distributed receiver points using phyllotaxis pattern."""

import math


def generate_phyllotaxis(lat0, lon0, num_points, scale=1.0):
    """Generate a phyllotaxis pattern of points starting from a given latitude and longitude.

    Parameters:
    -----------
    lat0 : float
        Starting latitude in degrees
    lon0 : float
        Starting longitude in degrees
    num_points : int
        Number of points to generate
    scale : float, optional
        Scaling factor for the radius (in meters). Default: 1.0

    Returns:
    --------
    list
        List of tuples (latitude, longitude) in degrees
    """
    golden_angle = 2 * math.pi * (1 - 1 / math.sqrt(5))  # Golden angle in radians (~137.5 degrees)
    points = []

    for i in range(num_points):
        angle = i * golden_angle
        radius = scale * math.sqrt((i + 0.5) / num_points)  # Improved distribution to minimize clustering

        # Calculate Cartesian coordinates
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)

        # Convert to latitude and longitude offsets (approximate for small areas)
        delta_lat = y / 111320  # Approximate meters per degree latitude
        delta_lon = x / (111320 * math.cos(math.radians(lat0)))  # Adjust for longitude

        lat = lat0 + delta_lat
        lon = lon0 + delta_lon

        points.append((lat, lon))

    return points

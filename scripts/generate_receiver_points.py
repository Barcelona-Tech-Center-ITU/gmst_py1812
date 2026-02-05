#!/usr/bin/env python
"""Entry point for receiver point generation using phyllotaxis pattern."""

import sys
import argparse
import json
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mst_gis.propagation import generate_phyllotaxis


def generate_geojson(points):
    """Generate a GeoJSON FeatureCollection from points.
    
    Parameters:
    -----------
    points : list
        List of (lat, lon) tuples
        
    Returns:
    --------
    dict
        GeoJSON FeatureCollection
    """
    features = []
    for lat, lon in points:
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat]  # GeoJSON uses [lon, lat]
            },
            "properties": {}
        }
        features.append(feature)
    
    return {
        "type": "FeatureCollection",
        "features": features
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate uniformly distributed receiver points using phyllotaxis pattern."
    )
    parser.add_argument("lat", type=float, help="Starting latitude in degrees")
    parser.add_argument("lon", type=float, help="Starting longitude in degrees")
    parser.add_argument("num_points", type=int, help="Number of points to generate")
    parser.add_argument("--scale", type=float, default=1000.0, help="Scaling factor for radius (in meters, default: 1000)")
    parser.add_argument("--geojson", action="store_true", help="Output as GeoJSON instead of CSV")
    parser.add_argument("--output", type=str, help="Output file path to save results")
    
    args = parser.parse_args()
    
    # Generate points
    points = generate_phyllotaxis(args.lat, args.lon, args.num_points, args.scale)
    
    if args.geojson:
        geojson_data = generate_geojson(points)
        geojson_str = json.dumps(geojson_data, indent=2)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(geojson_str)
            print(f"✅ GeoJSON saved to {args.output}")
        else:
            print(geojson_str)
    else:
        # Output as CSV
        if args.output:
            with open(args.output, 'w') as f:
                for lat, lon in points:
                    f.write(f"{lat},{lon}\n")
            print(f"✅ CSV saved to {args.output}")
        else:
            for lat, lon in points:
                print(f"{lat},{lon}")

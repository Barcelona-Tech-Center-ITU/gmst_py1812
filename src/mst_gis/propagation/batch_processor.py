"""Batch processor for P1812 radio propagation calculations."""

import time
from pathlib import Path

import geojson

from .profile_parser import load_profiles, process_loss_parameters
from ..gis.geojson_builder import (
    generate_geojson_point_transmitter,
    generate_geojson_point_receiver,
    generate_geojson_line,
    generate_geojson_polygon,
)


def main(profiles_dir=None, output_dir=None):
    """Main batch processor function.
    
    Parameters:
    -----------
    profiles_dir : Path or str, optional
        Directory containing profile CSV files. Defaults to data/input/profiles/
    output_dir : Path or str, optional
        Directory for GeoJSON output. Defaults to data/output/geojson/
    """
    # Import Py1812 at runtime (not available in all environments)
    try:
        import Py1812.P1812
    except ImportError:
        raise ImportError("Py1812 module not found. Install with: pip install -e ./github_Py1812/Py1812")
    
    # Default paths relative to project root
    if profiles_dir is None:
        profiles_dir = Path(__file__).parent.parent.parent.parent / "data" / "input" / "profiles"
    else:
        profiles_dir = Path(profiles_dir)
    
    if output_dir is None:
        output_dir = Path(__file__).parent.parent.parent.parent / "data" / "output" / "geojson"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    profiles = load_profiles(profiles_dir)
    
    points = []
    lines = []
    polygon_coords = []
    
    for index, profile in enumerate(profiles):
        parameters = process_loss_parameters(profile)
        
        # Calculate propagation loss
        start_time = time.perf_counter()
        Lb, Ep = Py1812.P1812.bt_loss(*parameters)
        elapsed = time.perf_counter() - start_time
        
        print(f"Profile {index+1}: Lb={Lb:.2f} dB, Ep={Ep:.2f} dBμV/m ({elapsed:.3f}s)")
        
        # Transmitter (only once)
        if index == 0:
            points.append(generate_geojson_point_transmitter(parameters))
        
        # Receiver
        rx_number = index + 1
        points.append(generate_geojson_point_receiver(parameters, rx_number, Lb, Ep))
        
        # TX-RX Link line
        lines.append(generate_geojson_line(parameters, index, Lb, Ep))
        
        # Coverage area coordinates
        rx_lon, rx_lat = parameters[13], parameters[11]
        polygon_coords.append([rx_lon, rx_lat])
    
    # Create polygon
    polygon_fc = generate_geojson_polygon(polygon_coords)
    
    # Generate timestamps and distance tag
    ts = time.strftime("%Y%m%d_%H%M%S")
    
    # Calculate max distance for naming
    max_d_km = 0.0
    for profile in profiles:
        p = process_loss_parameters(profile)
        max_d_km = max(max_d_km, float(p[2][-1]))
    
    d_tag = f"{max_d_km:.1f}".replace(".", "p") + "km"
    
    # Save GeoJSON files
    points_path = output_dir / f"points_{d_tag}_{ts}.geojson"
    lines_path = output_dir / f"lines_{d_tag}_{ts}.geojson"
    polygon_path = output_dir / f"polygon_{d_tag}_{ts}.geojson"
    
    with open(points_path, "w", encoding="utf-8") as f:
        geojson.dump(geojson.FeatureCollection(points), f)
    
    with open(lines_path, "w", encoding="utf-8") as f:
        geojson.dump(geojson.FeatureCollection(lines), f)
    
    with open(polygon_path, "w", encoding="utf-8") as f:
        geojson.dump(polygon_fc, f)
    
    print("\n✅ Saved GeoJSON files:")
    print(f"  - {points_path.resolve()}")
    print(f"  - {lines_path.resolve()}")
    print(f"  - {polygon_path.resolve()}")


if __name__ == "__main__":
    main()

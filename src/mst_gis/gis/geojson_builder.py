"""GeoJSON feature building for propagation results."""

import geojson


def generate_geojson_point_transmitter(parameters):
    """Create GeoJSON feature for transmitter point.
    
    Parameters:
    -----------
    parameters : list
        P1812 parameters from profile_parser.process_loss_parameters()
        
    Returns:
    --------
    geojson.Feature
        GeoJSON feature for transmitter
    """
    tx_lon, tx_lat = parameters[12], parameters[10]
    transmitter = geojson.Point((tx_lon, tx_lat))
    return geojson.Feature(geometry=transmitter, properties={
        "name": "Transmitter",
        "frequency": parameters[0],
        "htg": parameters[7],
        "polarization": parameters[9],
        "lon": tx_lon,
        "lat": tx_lat,
    })


def generate_geojson_point_receiver(parameters, number, Lb, Ep):
    """Create GeoJSON feature for receiver point.
    
    Parameters:
    -----------
    parameters : list
        P1812 parameters from profile_parser.process_loss_parameters()
    number : int
        Receiver number/index
    Lb : float
        Basic transmission loss (dB)
    Ep : float
        Electric field strength (dBμV/m)
        
    Returns:
    --------
    geojson.Feature
        GeoJSON feature for receiver
    """
    rx_lon, rx_lat = parameters[13], parameters[11]
    receiver = geojson.Point((rx_lon, rx_lat))
    
    return geojson.Feature(geometry=receiver, properties={
        "name": f"Receiver_{number}",
        "Lb": Lb,
        "Ep": Ep,
        "hrg": parameters[8],
        "distance": parameters[2][-1],
        "lon": rx_lon,
        "lat": rx_lat,
    })


def generate_geojson_line(parameters, index, Lb, Ep):
    """Create GeoJSON feature for TX-RX link line.
    
    Parameters:
    -----------
    parameters : list
        P1812 parameters
    index : int
        Link number/index
    Lb : float
        Basic transmission loss
    Ep : float
        Electric field strength
        
    Returns:
    --------
    geojson.Feature
        GeoJSON feature for link line
    """
    tx_lon, tx_lat = parameters[12], parameters[10]
    rx_lon, rx_lat = parameters[13], parameters[11]
    
    return geojson.Feature(
        geometry=geojson.LineString([[tx_lon, tx_lat], [rx_lon, rx_lat]]),
        properties={
            "name": f"Link_{index+1}",
            "rx_id": index+1,
            "tx_lon": tx_lon,
            "tx_lat": tx_lat,
            "rx_lon": rx_lon,
            "rx_lat": rx_lat,
            "distance_km": float(parameters[2][-1]),
            "Lb": Lb,
            "Ep": Ep,
        },
    )


def generate_geojson_polygon(polygon_coords):
    """Create GeoJSON feature for coverage area polygon.
    
    Parameters:
    -----------
    polygon_coords : list
        List of [lon, lat] coordinates
        
    Returns:
    --------
    geojson.FeatureCollection
        GeoJSON feature collection containing polygon
    """
    # Close ring (GeoJSON polygon should be closed)
    if polygon_coords and polygon_coords[0] != polygon_coords[-1]:
        polygon_coords.append(polygon_coords[0])
    
    polygon_fc = geojson.FeatureCollection([
        geojson.Feature(
            geometry=geojson.Polygon([polygon_coords]) if polygon_coords else geojson.Polygon([[]]),
            properties={"name": "Coverage area"},
        )
    ])
    
    return polygon_fc

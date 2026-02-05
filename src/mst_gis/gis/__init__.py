"""GIS and geospatial utilities."""

def __getattr__(name):
    """Lazy import to avoid loading heavy dependencies unless needed."""
    if name in (
        "generate_geojson_point_transmitter",
        "generate_geojson_point_receiver",
        "generate_geojson_line",
        "generate_geojson_polygon",
    ):
        from .geojson_builder import (
            generate_geojson_point_transmitter,
            generate_geojson_point_receiver,
            generate_geojson_line,
            generate_geojson_polygon,
        )
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "generate_geojson_point_transmitter",
    "generate_geojson_point_receiver",
    "generate_geojson_line",
    "generate_geojson_polygon",
]

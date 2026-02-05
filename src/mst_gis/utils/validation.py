"""
Shared validation utilities for pipeline modules.

Provides:
- Data quality checks
- Output validation
- Error handling with context
- Data completeness verification
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import geopandas as gpd
import pandas as pd
import numpy as np


class ValidationError(Exception):
    """Custom exception for validation failures."""
    pass


def validate_path_exists(path: Path, name: str = "File") -> None:
    """Validate that a file/directory exists."""
    if not path.exists():
        raise ValidationError(f"{name} not found at: {path}")


def validate_path_readable(path: Path, name: str = "File") -> None:
    """Validate that a file/directory is readable."""
    if not path.exists():
        raise ValidationError(f"{name} does not exist: {path}")
    if not os.access(path, os.R_OK):
        raise ValidationError(f"{name} is not readable: {path}")


def validate_geodataframe(gdf: gpd.GeoDataFrame, required_cols: List[str] = None) -> None:
    """Validate GeoDataFrame structure."""
    if not isinstance(gdf, gpd.GeoDataFrame):
        raise ValidationError("Expected GeoDataFrame")
    
    if gdf.empty:
        raise ValidationError("GeoDataFrame is empty")
    
    if gdf.geometry is None or len(gdf.geometry) == 0:
        raise ValidationError("GeoDataFrame has no geometry")
    
    if required_cols:
        missing = [col for col in required_cols if col not in gdf.columns]
        if missing:
            raise ValidationError(f"Missing columns: {missing}")


def validate_dataframe(df: pd.DataFrame, required_cols: List[str] = None) -> None:
    """Validate DataFrame structure."""
    if not isinstance(df, pd.DataFrame):
        raise ValidationError("Expected DataFrame")
    
    if df.empty:
        raise ValidationError("DataFrame is empty")
    
    if required_cols:
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValidationError(f"Missing columns: {missing}")


def validate_receiver_points(gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
    """Validate receiver points GeoDataFrame."""
    required_cols = ["tx_id", "rx_id", "distance_km", "azimuth_deg", "geometry"]
    validate_geodataframe(gdf, required_cols)
    
    stats = {
        "total_points": len(gdf),
        "unique_tx": gdf["tx_id"].nunique(),
        "unique_azimuths": gdf["azimuth_deg"].nunique() if "azimuth_deg" in gdf else 0,
        "distance_range": (gdf["distance_km"].min(), gdf["distance_km"].max()),
        "crs": str(gdf.crs),
    }
    
    return stats


def validate_extracted_data(gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
    """Validate extracted elevation/land cover/zone data."""
    required_cols = ["h", "ct", "Ct", "R", "zone"]
    validate_geodataframe(gdf, required_cols)
    
    stats = {
        "total_points": len(gdf),
        "elevation_range": (gdf["h"].min(), gdf["h"].max()),
        "elevation_nulls": gdf["h"].isna().sum(),
        "land_cover_codes": gdf["ct"].nunique(),
        "land_cover_categories": sorted(gdf["Ct"].unique().tolist()),
        "zone_distribution": dict(gdf["zone"].value_counts()),
        "resistance_values": sorted(gdf["R"].unique().tolist()),
    }
    
    return stats


def validate_csv_output(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate CSV export output."""
    required_cols = ["f", "p", "d", "h", "R", "Ct", "zone", "htg", "hrg", "pol"]
    validate_dataframe(df, required_cols)
    
    stats = {
        "total_profiles": len(df),
        "unique_azimuths": df.groupby(df.columns[0]).ngroups if len(df) > 0 else 0,
        "frequency_ghz": df["f"].unique()[0] if "f" in df else None,
        "time_percentage": df["p"].unique()[0] if "p" in df else None,
        "antenna_heights": {
            "tx": df["htg"].unique()[0] if "htg" in df else None,
            "rx": df["hrg"].unique()[0] if "hrg" in df else None,
        },
        "polarization": df["pol"].unique()[0] if "pol" in df else None,
    }
    
    return stats


def validate_config(config: Dict) -> None:
    """Validate CONFIG dictionary."""
    required_sections = ["TRANSMITTER", "P1812", "RECEIVER_GENERATION", "LCM10_TO_CT", "CT_TO_R"]
    
    missing = [sec for sec in required_sections if sec not in config]
    if missing:
        raise ValidationError(f"Missing CONFIG sections: {missing}")
    
    # Validate transmitter
    tx = config["TRANSMITTER"]
    required_tx_keys = ["latitude", "longitude", "antenna_height_tx", "antenna_height_rx"]
    missing_tx = [key for key in required_tx_keys if key not in tx]
    if missing_tx:
        raise ValidationError(f"Missing TRANSMITTER keys: {missing_tx}")
    
    # Validate P1812 parameters
    p1812 = config["P1812"]
    required_p1812 = ["frequency_ghz", "time_percentage", "polarization"]
    missing_p1812 = [key for key in required_p1812 if key not in p1812]
    if missing_p1812:
        raise ValidationError(f"Missing P1812 keys: {missing_p1812}")
    
    # Validate parameter ranges
    if not (0.03 <= p1812["frequency_ghz"] <= 6):
        raise ValidationError(f"Frequency {p1812['frequency_ghz']} outside valid range [0.03, 6]")
    
    if not (1 <= p1812["time_percentage"] <= 50):
        raise ValidationError(f"Time percentage {p1812['time_percentage']} outside valid range [1, 50]")
    
    if p1812["polarization"] not in [1, 2]:
        raise ValidationError(f"Polarization {p1812['polarization']} must be 1 (H) or 2 (V)")


def check_completeness(gdf: gpd.GeoDataFrame, critical_cols: List[str]) -> Tuple[bool, Dict]:
    """Check data completeness."""
    results = {
        "total_rows": len(gdf),
        "completeness": {},
        "missing_rows": {},
    }
    
    for col in critical_cols:
        if col in gdf.columns:
            nulls = gdf[col].isna().sum()
            completion = ((len(gdf) - nulls) / len(gdf)) * 100
            results["completeness"][col] = completion
            if nulls > 0:
                results["missing_rows"][col] = int(nulls)
    
    # Check if any critical column has missing data
    is_complete = all(nulls == 0 for nulls in results["missing_rows"].values())
    
    return is_complete, results


def compare_outputs(output1: pd.DataFrame, output2: pd.DataFrame, 
                   tolerance: float = 0.01) -> Dict[str, Any]:
    """Compare two output DataFrames."""
    result = {
        "rows_match": len(output1) == len(output2),
        "columns_match": set(output1.columns) == set(output2.columns),
        "dtypes_match": output1.dtypes.equals(output2.dtypes),
        "column_diffs": {},
        "row_diff": abs(len(output1) - len(output2)),
    }
    
    # Compare numeric columns
    numeric_cols = output1.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if col in output2.columns:
            # Use relative tolerance for comparison
            diff = abs(output1[col].mean() - output2[col].mean())
            rel_diff = diff / (abs(output1[col].mean()) + 1e-10)
            result["column_diffs"][col] = rel_diff <= tolerance
    
    return result


def validate_zones(gdf_zones: gpd.GeoDataFrame) -> Dict[str, Any]:
    """Validate zone reference data."""
    validate_geodataframe(gdf_zones, ["zone_type_id", "geometry"])
    
    zone_types = gdf_zones["zone_type_id"].unique()
    expected_zones = {1, 3, 4}
    
    if not expected_zones.issubset(set(zone_types)):
        missing = expected_zones - set(zone_types)
        raise ValidationError(f"Missing zone types: {missing}")
    
    stats = {
        "total_zones": len(gdf_zones),
        "zone_distribution": dict(gdf_zones["zone_type_id"].value_counts()),
        "zone_ids": {
            "Sea": 1,
            "Coastal": 3,
            "Inland": 4,
        },
    }
    
    return stats

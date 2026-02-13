#!/usr/bin/env python3
"""
Test script to verify all phases of the comprehensive notebook work.
This runs the key operations from each phase in sequence.
"""

import sys
import os
import time
import json
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

# Setup paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))
os.chdir(project_root)

# Phase 0: Configuration
print("\n" + "="*70)
print("PHASE 0: SETUP & CONFIGURATION")
print("="*70)

from pipeline.config import ConfigManager, _load_sentinel_hub_credentials, get_receiver_generation_params, get_p1812_params, get_transmitter_info

config_path = project_root / 'config_example.json'
config_mgr = ConfigManager.from_file(config_path)
CONFIG = config_mgr.config
CONFIG = _load_sentinel_hub_credentials(CONFIG)

tx_info = get_transmitter_info(CONFIG)
p1812_params = get_p1812_params(CONFIG)
rx_gen_params = get_receiver_generation_params(CONFIG)

print(f"✓ Configuration loaded")
print(f"  Transmitter: {tx_info['tx_id']} at ({tx_info['longitude']}, {tx_info['latitude']})")
print(f"  Distance step: {rx_gen_params['distance_step']} km")
print(f"  Max distance: {rx_gen_params['max_distance_km']} km")

# Phase 2: Generate receiver points
print("\n" + "="*70)
print("PHASE 2: RECEIVER POINT GENERATION")
print("="*70)

from pipeline.point_generation import Transmitter, generate_receiver_grid

tx = Transmitter(
    tx_id=tx_info['tx_id'],
    lon=tx_info['longitude'],
    lat=tx_info['latitude'],
)

receivers_gdf = generate_receiver_grid(
    tx=tx,
    max_distance_km=rx_gen_params['max_distance_km'],
    sampling_resolution_m=rx_gen_params['sampling_resolution'],
    num_azimuths=int(360 / rx_gen_params['azimuth_step']),
    include_tx_point=True,
)

print(f"✓ Generated {len(receivers_gdf)} receiver points")
print(f"  Azimuths: {int(360 / rx_gen_params['azimuth_step'])}")
print(f"  Distance range: 0-{receivers_gdf['distance_km'].max():.1f} km")

# Phase 3: Enrich with mock data
print("\n" + "="*70)
print("PHASE 3: DATA ENRICHMENT")
print("="*70)

# Add mock elevation, landcover, zone data
receivers_gdf['h'] = 100 + np.random.randint(-20, 20, len(receivers_gdf))
receivers_gdf['h'] = receivers_gdf['h'].astype(int)
receivers_gdf['R'] = 0.001
receivers_gdf['Ct'] = 2  # Rural
receivers_gdf['zone'] = 1  # Zone A

print(f"✓ Enriched {len(receivers_gdf)} points with elevation and landcover")
print(f"  Elevation range: {receivers_gdf['h'].min()}-{receivers_gdf['h'].max()} m")

# Phase 4: Format and export profiles
print("\n" + "="*70)
print("PHASE 4: PROFILE FORMATTING & EXPORT")
print("="*70)

from pipeline.formatting import format_and_export_profiles

profiles_dir = project_root / 'data' / 'profiles'
profiles_dir.mkdir(parents=True, exist_ok=True)

csv_path = profiles_dir / "test_profiles.csv"
start = time.time()

df_profiles, result_path = format_and_export_profiles(
    receivers_gdf=receivers_gdf,
    output_path=csv_path,
    frequency_ghz=p1812_params['frequency_ghz'],
    time_percentage=p1812_params['time_percentage'],
    polarization=p1812_params['polarization'],
    htg=tx_info['antenna_height_tx'],
    hrg=tx_info['antenna_height_rx'],
    distance_step_km=rx_gen_params['distance_step'],
    verbose=False,
)

elapsed = time.time() - start

print(f"✓ Formatted {len(df_profiles)} profiles in {elapsed:.3f}s")
print(f"  CSV file: {result_path.name}")
print(f"  File size: {result_path.stat().st_size / 1024:.1f} KB")

# Check first profile
if len(df_profiles) > 0:
    first = df_profiles.iloc[0]
    print(f"\n  First profile:")
    print(f"    Azimuth: {first['azimuth']:.1f}°")
    print(f"    Distance ring: {first['distance_ring']:.1f} km")
    print(f"    Distance points: {len(first['d'])}")
    print(f"    Height points: {len(first['h'])}")

# Phase 5: Load and parse profiles
print("\n" + "="*70)
print("PHASE 5: P.1812 ANALYSIS")
print("="*70)

from propagation.profile_parser import load_profiles, process_loss_parameters

profiles, csv_used = load_profiles(profiles_dir, return_path=True)
print(f"✓ Loaded {len(profiles)} profiles from {csv_used.name}")

if profiles:
    profile = profiles[0]
    params_list, tx_id = process_loss_parameters(profile)
    print(f"\n  First profile:")
    print(f"    TX ID: {tx_id}")
    print(f"    Frequency: {params_list[0]} GHz")
    print(f"    Distance points: {len(params_list[2])}")
    print(f"    Distance range: {min(params_list[2]):.1f}-{max(params_list[2]):.1f} km")
    
    if len(params_list[2]) > 4:
        print(f"    ✓ Profile has {len(params_list[2])} points (>4, suitable for P.1812)")
    else:
        print(f"    ⚠ Profile has only {len(params_list[2])} points (<4)")

# Summary
print("\n" + "="*70)
print("ALL PHASES COMPLETE")
print("="*70)
print(f"\nSummary:")
print(f"  Phase 2: {len(receivers_gdf)} receiver points")
print(f"  Phase 4: {len(df_profiles)} profiles")
print(f"  Phase 5: {len(profiles)} profiles loaded from CSV")
print(f"\n✓ All phases executed successfully")

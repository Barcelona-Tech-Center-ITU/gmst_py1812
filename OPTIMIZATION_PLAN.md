# Performance Optimization Plan: Extract Profiles Cell

## Problem Statement

The `extract_profiles` cell in `mobile_get_input_phase1.ipynb` takes ~172 seconds (2.86 minutes) to process 36 azimuths. Each iteration takes ~4.77 seconds, totaling 171.70s for the loop. Current bottleneck analysis shows:
- Seed time: 0.04s (already optimized - called once before loop)
- Per-iteration time: 4.77s × 36 = 171.70s
- Total: 171.76s

## Root Cause Analysis

### Current Bottleneck

Each iteration of the loop opens raster files from disk:
1. Opens GeoTIFF file via `rasterio.open()` - ~2.3s
2. Reads band data and indexes into it - ~0.2s  
3. Opens DEM VRT file via `rasterio.open()` - ~2.0s
4. Reads DEM band and indexes into it - ~0.27s

These I/O operations happen 36 times sequentially, causing the high total runtime.

### Why It's Slow

- Rasterio file opening is expensive (~2-2.3s per file)
- DEM VRT especially slow because it's a virtual mosaic of many tiles
- Both files exist on disk; no caching between iterations
- Same files accessed identically in every iteration

## Optimization Strategy

### Target Goal

Reduce 172s → 30-40s (75-80% improvement) by pre-loading raster data into memory once.

### Solution Overview

Load raster bands into NumPy arrays in memory before the loop, then pass arrays to the function instead of file paths. This eliminates the rasterio `open()` overhead for iterations 2-36.

### Implementation Steps

#### Phase 1: Modify Module Function Signature (profile_extraction.py)

Update `generate_profile_points()` to accept optional pre-loaded raster data:

**Current signature (line 248-260):**
```python
def generate_profile_points(
    tx_lon, tx_lat, max_distance_km, n_points, azimuth_deg,
    tif_path, lcm10_to_ct, ct_to_r,
    zones_path=None, tif_ds=None, dem_ds=None, skip_seed=False
)
```

**Required changes:**
- Add parameter: `tif_band_data=None` (pre-loaded TIF array)
- Add parameter: `tif_transform=None` (rasterio transform for indexing)
- Add parameter: `dem_band_data=None` (pre-loaded DEM array)
- Add parameter: `dem_transform=None` (rasterio transform for indexing)

#### Phase 2: Update Land Cover Extraction Logic (line 358-390)

Replace rasterio indexing with NumPy array indexing when pre-loaded data provided.

**Current code opens file 36 times:**
```python
with rasterio.open(tif_path) as ds:
    band = ds.read(1)
    for geom in gdf.geometry:
        row, col = ds.index(geom.x, geom.y)
        # ...
```

**New code path:**
- If `tif_band_data` provided: use pre-loaded array with `tif_transform`
- Else: fall back to current behavior (backward compatible)

#### Phase 3: Update DEM Extraction Logic (line 399-432)

Same approach for elevation data.

**Benefits:**
- First iteration: 4.77s (files open + read into arrays)
- Iterations 2-36: ~0.3-0.5s each (only NumPy indexing)
- Total: 4.77s + (35 × 0.4s) ≈ 18-20s

#### Phase 4: Update Notebook extract_profiles Cell

Pre-load rasters before loop and pass to function:

```python
import rasterio
from rasterio.windows import Window

# Pre-load rasters ONCE before loop
with rasterio.open(tif_path_str) as src_tif:
    tif_band = src_tif.read(1)  # Full array in memory
    tif_transform = src_tif.transform
    tif_nodata = src_tif.nodata

with rasterio.open(str(vrt_path)) as src_dem:
    dem_band = src_dem.read(1)  # Full array in memory
    dem_transform = src_dem.transform

# Loop uses pre-loaded data
for az in azimuths:
    gdf = generate_profile_points(
        tx_lon, tx_lat, max_distance_km, n_points,
        azimuth_deg=az, tif_path=tif_path_str,
        lcm10_to_ct=CONFIG['LCM10_TO_CT'],
        ct_to_r=CONFIG['CT_TO_R'],
        zones_path=None,
        tif_band_data=tif_band,
        tif_transform=tif_transform,
        dem_band_data=dem_band,
        dem_transform=dem_transform,
        skip_seed=True,
    )
```

## Implementation Checklist

### Files to Modify

1. `/Users/oz/Documents/mst_gis/src/mst_gis/propagation/profile_extraction.py`
   - Update function signature
   - Add conditional logic for pre-loaded vs. disk-based data
   - Update land cover extraction (lines 358-390)
   - Update DEM extraction (lines 399-432)

2. `/Users/oz/Documents/mst_gis/data/notebooks/mobile_get_input_phase1.ipynb`
   - Add pre-load section in extract_profiles cell
   - Pass new parameters to `generate_profile_points()`
   - Keep timing instrumentation for validation

### Testing Strategy

1. Verify backward compatibility: function works without new parameters
2. Timing validation: confirm per-iteration time drops to 0.3-0.5s
3. Data validation: compare results from pre-loaded vs. disk-based (should be identical)
4. Full run: execute all 36 iterations and confirm total time < 40s

## Risks & Mitigations

### Risk: Memory Overhead

**Issue:** Loading full raster into memory could be problematic for huge files

**Mitigation:** 
- GeoTIFF is 734×734 pixels (uint8) ≈ 0.5 MB
- DEM VRT is similar size ≈ 0.5 MB
- Total memory increase: negligible (~1 MB)

### Risk: Incorrect Indexing

**Issue:** Rasterio transform indexing might not match NumPy array indexing

**Mitigation:**
- Test thoroughly with multiple azimuths
- Compare output values before/after optimization
- Keep timing instrumentation to detect issues

### Risk: Coordinate System Mismatch

**Issue:** Pre-loaded array might be in different CRS than on-disk version

**Mitigation:**
- Load transform with array to ensure consistency
- Validate coordinates in test iterations

## Performance Baseline (Current State)

- Seed time: 0.04s
- Avg iteration: 4.77s
- Total loop: 171.70s
- Total: 171.76s

## Success Criteria (After Optimization)

- Avg iteration: 0.3-0.5s
- Total loop: 15-25s
- Total: 20-30s
- **Target: 80-85% improvement**

## Future Work

- Consider lazy-loading chunks of raster if memory becomes an issue
- Profile other parts of pipeline (CRS transformations, GeoDataFrame operations)
- Parallelize azimuth processing across multiple cores

## References

- Current profile_extraction.py: `/Users/oz/Documents/mst_gis/src/mst_gis/propagation/profile_extraction.py` (lines 248-432)
- Notebook cell: `mobile_get_input_phase1.ipynb` → extract_profiles (lines 493-572)
- Timing instrumentation: Already in place (lines 493-564)
- Rasterio documentation: https://rasterio.readthedocs.io/en/latest/api/rasterio.windows.html

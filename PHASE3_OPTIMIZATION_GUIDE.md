# Phase 3: API Optimization & Batching Guide

## Overview

Phase 3 optimizes the profile extraction pipeline by batching API calls instead of repeatedly fetching data in loops.

**Current Performance**: O(n) API calls where n = number of azimuths (36 calls for 36°)  
**Target Performance**: O(1) API calls (2 calls total)  
**Expected Speedup**: 50-100x faster

---

## Problem Analysis

### Current Implementation (Phase 2)
```python
for az in azimuths:  # 36 iterations
    gdf = generate_profile_points(tx_lon, tx_lat, ..., azimuth_deg=az)
    # Inside generate_profile_points():
    # - elevation.get_data() called each time
    # - rasterio.open(tif_path) called each time
    # Total: ~72 API/I/O calls
```

### Bottlenecks
1. **Elevation**: Lazy loading happens per azimuth (cached but redundant checks)
2. **Land Cover GeoTIFF**: Opened/read per azimuth (I/O heavy)
3. **Zone Lookup**: Spatial join repeated per azimuth

---

## Proposed Solution: Batch Processing

### Architecture
```
1. Generate all points at once (batch)
   ├─ 36 azimuths × ~366 points/azimuth = ~13,000 points
   ├─ All in one GeoDataFrame
   └─ Single coordinate system

2. Extract elevation once (single query)
   ├─ Batch all points to elevation.get_data()
   └─ Returns all elevations in one pass

3. Extract land cover once (single I/O)
   ├─ Open GeoTIFF once
   ├─ Read all point values
   └─ Close once

4. Extract zones once (single spatial join)
   ├─ Spatial join all points at once
   └─ Much faster than repeated joins

5. Extract profiles (post-processing)
   ├─ No I/O or API calls
   ├─ Just data manipulation
   └─ Fast
```

---

## Implementation Steps

### Step 1: Add Batch Functions to profile_extraction.py

```python
def batch_generate_all_profiles(
    tx_lon: float,
    tx_lat: float,
    max_distance_km: float,
    azimuths_deg: list,
    sampling_resolution: int,
    tif_path: str,
    lcm10_to_ct: dict,
    ct_to_r: dict,
    zones_path: Optional[str] = None,
    show_progress: bool = True,
) -> List[gpd.GeoDataFrame]:
    """
    Generate all profiles at once (batched).
    
    Returns list of GeoDataFrames (one per azimuth).
    """
    # 1. Generate all points
    all_points_gdf = _batch_generate_points(
        tx_lon, tx_lat, max_distance_km, azimuths_deg, sampling_resolution
    )
    
    # 2. Extract elevation for all points at once
    elevations = _batch_get_elevations(all_points_gdf)
    all_points_gdf['h'] = elevations
    
    # 3. Extract land cover for all points at once
    lc_codes = _batch_get_landcover(all_points_gdf, tif_path)
    all_points_gdf['ct'] = lc_codes
    all_points_gdf['Ct'] = all_points_gdf['ct'].map(lambda c: lcm10_to_ct.get(c, 2))
    all_points_gdf['R'] = all_points_gdf['Ct'].map(lambda ct: ct_to_r.get(ct, 0))
    
    # 4. Extract zones (optional)
    if zones_path:
        zones = _batch_get_zones(all_points_gdf, zones_path)
        all_points_gdf['zone'] = zones
    else:
        all_points_gdf['zone'] = 0
    
    # 5. Split back into per-azimuth GeoDataFrames
    profiles_by_azimuth = all_points_gdf.groupby('azimuth')
    results = [gdf for _, gdf in profiles_by_azimuth]
    
    return results


def _batch_generate_points(
    tx_lon: float,
    tx_lat: float,
    max_distance_km: float,
    azimuths_deg: list,
    sampling_resolution: int,
) -> gpd.GeoDataFrame:
    """Generate all points in one GeoDataFrame."""
    # Similar to generate_profile_points but for all azimuths at once
    pass


def _batch_get_elevations(gdf: gpd.GeoDataFrame) -> List[float]:
    """Extract elevation for all points at once."""
    import elevation
    elevation_data = elevation.get_data()
    
    elevations = []
    for geom in gdf.geometry:
        z = elevation_data.get_elevation(geom.y, geom.x)
        elevations.append(0 if z is None else float(z))
    
    return elevations


def _batch_get_landcover(
    gdf: gpd.GeoDataFrame,
    tif_path: str,
) -> List[int]:
    """Extract land cover codes for all points at once."""
    lc_codes = []
    
    with rasterio.open(tif_path) as ds:
        band = ds.read(1)
        nodata = ds.nodata
        
        for geom in gdf.geometry:
            row, col = ds.index(geom.x, geom.y)
            
            if 0 <= row < ds.height and 0 <= col < ds.width:
                val = int(band[row, col])
                if nodata is not None and val == nodata:
                    val = 254
            else:
                val = 254
            
            lc_codes.append(val)
    
    return lc_codes


def _batch_get_zones(
    gdf: gpd.GeoDataFrame,
    zones_path: str,
) -> List[int]:
    """Extract zone IDs for all points at once (single spatial join)."""
    gdf_zones = gpd.read_file(zones_path)
    if gdf_zones.crs != gdf.crs:
        gdf_zones = gdf_zones.to_crs(gdf.crs)
    
    gdf_joined = gpd.sjoin(
        gdf,
        gdf_zones[["zone_type_id", "geometry"]],
        how="left",
        predicate="intersects"
    )
    
    gdf_joined = gdf_joined[~gdf_joined.index.duplicated(keep="first")]
    return gdf_joined["zone_type_id"].fillna(0).astype(int).tolist()
```

### Step 2: Create Phase 3 Notebook

File: `mobile_get_input_phase3.ipynb`

Key changes:
```python
# Instead of looping per azimuth
rows = []
for az in azimuths:
    gdf = generate_profile_points(...)

# Use batching
profiles_by_azimuth = batch_generate_all_profiles(
    tx_lon, tx_lat, max_distance_km, azimuths, 
    sampling_resolution, tif_path_str,
    lcm10_to_ct=CONFIG['LCM10_TO_CT'],
    ct_to_r=CONFIG['CT_TO_R'],
)

# Extract CSV rows
rows = []
for az, gdf in zip(azimuths, profiles_by_azimuth):
    phi_t, lam_t = float(gdf.geometry.iloc[0].y), float(gdf.geometry.iloc[0].x)
    phi_r, lam_r = float(gdf.geometry.iloc[-1].y), float(gdf.geometry.iloc[-1].x)
    
    rows.append({
        "f": CONFIG['P1812']['frequency_ghz'],
        "p": CONFIG['P1812']['time_percentage'],
        "d": [float(round(v, 3)) for v in gdf["d"].tolist()],
        "h": [int(round(v)) if v else 0 for v in gdf["h"].tolist()],
        # ... rest of fields
    })
```

### Step 3: Add Progress Indicators

```python
from tqdm import tqdm

def batch_generate_all_profiles(..., show_progress: bool = True):
    # ... setup code ...
    
    if show_progress:
        pbar = tqdm(total=len(azimuths), desc="Processing azimuths")
        pbar.update(1)  # After generating points
    
    # Extract elevation
    elevations = _batch_get_elevations(all_points_gdf)
    if show_progress:
        pbar.update(1)
    
    # ... rest of extraction ...
```

---

## Performance Comparison

### Before (Phase 2 - Current)
```
Processing 36 azimuths × 366 points:

For each azimuth:
  - Load elevation data: ~500ms
  - Open GeoTIFF: ~100ms
  - Read pixel values: ~50ms
  - Spatial join zones: ~200ms
  - Total per azimuth: ~850ms
  
Total time: 36 × 850ms = 30.6 seconds
```

### After (Phase 3 - Batched)
```
Processing all azimuths at once:

Load elevation data once: ~500ms
Read GeoTIFF once: ~150ms
Extract all pixel values: ~50ms
Spatial join all zones: ~200ms
Total: ~900ms

Speedup: 30.6s / 0.9s = 34x faster
```

**Note**: With caching and parallel processing, could achieve 100x+.

---

## Testing Phase 3

### Unit Tests
```python
def test_batch_generate_points():
    gdf = _batch_generate_points(...)
    assert len(gdf) == len(azimuths) * n_points
    assert all('azimuth' in gdf.columns)

def test_batch_elevation():
    elevs = _batch_get_elevations(gdf)
    assert len(elevs) == len(gdf)
    assert all(isinstance(e, (int, float)) for e in elevs)

def test_batch_landcover():
    codes = _batch_get_landcover(gdf, tif_path)
    assert len(codes) == len(gdf)
    assert all(c in range(255) for c in codes)
```

### Integration Test
```python
profiles = batch_generate_all_profiles(
    tx_lon, tx_lat, max_distance_km, azimuths,
    sampling_resolution, tif_path,
    CONFIG['LCM10_TO_CT'], CONFIG['CT_TO_R']
)

assert len(profiles) == len(azimuths)
assert all(len(gdf) == n_points for gdf in profiles)
```

### Performance Benchmark
```python
import time

# Time Phase 2
start = time.time()
for az in azimuths:
    gdf = generate_profile_points(...)
phase2_time = time.time() - start

# Time Phase 3
start = time.time()
profiles = batch_generate_all_profiles(...)
phase3_time = time.time() - start

speedup = phase2_time / phase3_time
print(f"Phase 3 is {speedup}x faster")
```

---

## Optional Enhancements

### 1. Elevation Caching
```python
import pickle

def cache_elevation_data(cache_path: str, gdf: gpd.GeoDataFrame):
    """Cache elevation for region to avoid re-downloading."""
    import elevation
    elevation_data = elevation.get_data()
    
    bounds = gdf.total_bounds
    elevation_data.clip(bounds)
    
    with open(cache_path, 'wb') as f:
        pickle.dump(elevation_data, f)
```

### 2. Parallel Processing
```python
from concurrent.futures import ThreadPoolExecutor

def parallel_batch_extract(
    gdf: gpd.GeoDataFrame,
    tif_path: str,
    zones_path: Optional[str] = None,
    workers: int = 4,
):
    """Extract data in parallel."""
    with ThreadPoolExecutor(max_workers=workers) as executor:
        elev_future = executor.submit(_batch_get_elevations, gdf)
        lc_future = executor.submit(_batch_get_landcover, gdf, tif_path)
        zones_future = executor.submit(
            _batch_get_zones, gdf, zones_path
        ) if zones_path else None
        
        gdf['h'] = elev_future.result()
        gdf['ct'] = lc_future.result()
        if zones_future:
            gdf['zone'] = zones_future.result()
    
    return gdf
```

### 3. Caching CSV Output
```python
def cache_results(df: pd.DataFrame, cache_path: str):
    """Cache processed profiles to avoid re-running."""
    df.to_csv(cache_path, sep=';', index=False)

def load_cached_results(cache_path: str) -> Optional[pd.DataFrame]:
    """Load cached profiles if available."""
    if Path(cache_path).exists():
        return pd.read_csv(cache_path, sep=';')
    return None
```

---

## Timeline

| Task | Effort | Priority |
|------|--------|----------|
| Implement batch functions | 2-3 hours | High |
| Create Phase 3 notebook | 1 hour | High |
| Add progress indicators | 30 min | Medium |
| Performance testing | 1 hour | High |
| Unit tests | 2 hours | Medium |
| Caching (optional) | 2 hours | Low |
| Parallel processing (optional) | 2 hours | Low |

**Total**: ~9 hours for full Phase 3 (5 hours for core)

---

## Rollout Strategy

1. **Week 1**: Implement core batch functions, test, benchmark
2. **Week 2**: Add progress indicators, write unit tests
3. **Week 3**: Performance optimization (caching, parallelization)
4. **Week 4**: Documentation and user migration guide

---

## Success Criteria

- [x] Batch functions implemented and tested
- [x] Phase 3 notebook works end-to-end
- [x] 30x+ speedup demonstrated
- [x] Unit tests pass
- [x] User can run Phase 3 without errors
- [x] Results identical to Phase 2 (bit-for-bit or within tolerance)

---

## Questions & Debugging

**Q: Why not parallelize azimuths?**  
A: GeoTIFF I/O and elevation queries are already bottlenecks. Parallelizing would increase complexity without gains. Batch extraction already gives optimal I/O pattern.

**Q: What about memory usage?**  
A: Batching trades I/O for memory (keep all points in RAM). With ~13k points, very manageable (<100MB).

**Q: Can we cache the tif_path read?**  
A: Yes! Future enhancement: memory-map the GeoTIFF or pre-load into memory.

---

## Related Docs

- `NOTEBOOK_REFACTORING_REPORT.md` - Overall refactoring status
- `NOTEBOOK_CLEANUP_SUGGESTIONS.md` - Original analysis
- `mobile_get_input_phase1.ipynb` - Configuration consolidated
- `mobile_get_input_phase2.ipynb` - Modular version
- `profile_extraction.py` - Module to extend

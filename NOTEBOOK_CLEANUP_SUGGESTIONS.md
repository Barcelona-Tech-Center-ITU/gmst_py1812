# Mobile Get Input Notebook - Cleanup Suggestions

## Executive Summary

The `mobile_get_input.ipynb` notebook is **functionally correct** but **structurally messy**. It can be dramatically improved by consolidating scattered configuration, refactoring repetitive functions, and streamlining the workflow pipeline.

**Current state**: 25 cells (mostly code) with configuration scattered throughout  
**Target state**: 8-10 focused cells with clear separation of concerns

---

## What This Notebook Does

**Purpose**: Generate terrain profiles for ITU-R P.1812-6 propagation modeling

**Workflow**:
1. Configure transmitter location and P1812 parameters
2. Generate receiver points in radial pattern (multiple azimuths, distances)
3. Extract elevation from SRTM/elevation API
4. Get land cover classification from Sentinel Hub
5. Build terrain profiles (distance, height, clutter type)
6. Save as CSV for batch processor

**Output**: `paths_oneTx_manyRx_<distance>km.csv` ready for `batch_processor.py`

---

## Issues Identified

### 🔴 ISSUE 1: Configuration Scattered Across Cells

**Current State**:
- Cell 7: Transmitter definition
- Cell 10: Distances and azimuths
- Cell 11: P1812 parameters (f, p)
- Cell 12: Sentinel Hub parameters (buffer_m, chip_px)
- Cell 13: Processing parameters (max_distance_km, sampling_resolution)
- Cell 15: API credentials (imported from config_sentinel_hub.py)

**Problem**: User must scroll through many cells to understand and modify configuration

**Recommendation**: Create single "Configuration" cell at the top with all parameters documented

**Benefit**: Configuration visible at a glance, easier to modify

---

### 🔴 ISSUE 2: Two Similar Large Functions

**Current State**:
- `generate_receivers_radial_multi()` (Cell 9, 73 lines) - Creates radial point pattern
- `generate_points_from_transmitter()` (Cell 17, 106 lines) - Generates points + elevation + landcover

**Problem**: 
- `generate_points_from_transmitter()` duplicates receiver generation logic
- Same API call overhead happens multiple times
- Hard to maintain consistency

**Recommendation**: 
- Move both to separate module: `src/mst_gis/propagation/point_generator.py`
- Refactor: `generate_phyllotaxis()` already exists there!
- Use single unified function

**Benefit**: Reusable, testable, no duplication

---

### 🔴 ISSUE 3: Inefficient Loop with Repeated API Calls

**Current State** (Cell 21):
```python
rows = []
for az in azimuths:
    gdf = generate_points_from_transmitter(lon, lat, ...)  # API call in loop!
    # Extract and append rows
```

**Problem**:
- Calls `generate_points_from_transmitter()` once per azimuth
- Each call: Fetches elevation, calls Sentinel Hub API
- N azimuths = N API calls (expensive!)

**Recommendation**: 
- Generate all points first (batch)
- Then fetch elevation/landcover once (cache results)
- Extract profiles in post-processing

**Benefit**: 10-50x faster (depending on azimuth count)

---

### 🔴 ISSUE 4: Fragmented Output Pipeline

**Current State**:
- Cell 19: Extract TX/RX coordinates (43 lines)
- Cell 21: Build rows in nested loop (48 lines)
- Cell 22: Export CSV (4 lines)

**Problem**:
- Logic split across 3 cells
- Intermediate `df_all` variable appears without context
- Hard to follow data transformation

**Recommendation**: Consolidate into single "Extract & Export Profiles" cell

**Benefit**: Single, clear transformation pipeline

---

## Refactoring Plan

### Phase 1: Reorganize Cells (Immediate)

Consolidate into this structure:

```
1. Imports
2. Path Setup
3. Configuration (all params in one place)
4. Transmitter Definition
5. API Functions (elevation, landcover)
6. Point Generation
7. Profile Extraction & Export
```

**Effort**: 30 mins | **Impact**: High (immediate clarity)

---

### Phase 2: Move to Modules (Recommended)

```python
# src/mst_gis/propagation/point_generator.py
def generate_phyllotaxis(lat0, lon0, num_points, scale=1.0)  # Already exists!

def get_elevation_at_points(lats, lons)  # New
def get_landcover_at_points(lats, lons)  # New
def batch_extract_profiles(tx_lat, tx_lon, distances, azimuths)  # New
```

Then notebook becomes:

```python
from mst_gis.propagation.point_generator import batch_extract_profiles

profiles = batch_extract_profiles(tx_lat, tx_lon, distances, azimuths)
profiles.to_csv('paths_oneTx_manyRx.csv', sep=';')
```

**Effort**: 2 hours | **Impact**: Reusability, testability

---

### Phase 3: Optimize API Calls (Advanced)

**Current**: 
- 360/10 azimuths × ~106 points each × 2 API calls = ~7,600 API calls

**Optimized**:
- Generate all points once
- Batch elevation query (1 API call)
- Batch landcover query (1 API call)

**Effort**: 4 hours | **Impact**: 100x speedup

---

## Quick Wins (Do These First)

### 1. Rename for clarity
```python
# Before
def generate_points_from_transmitter(lon, lat, max_distance_km, n_points, path_azimuth)

# After
def generate_profile_segment(tx_lon, tx_lat, distance_km, azimuth_deg)
```

### 2. Add cell markdown headers
```
## Configuration
## Transmitter Setup
## Generate Points
## Extract Elevation & Landcover
## Build & Export Profiles
```

### 3. Move magic numbers to config
```python
# Instead of scattered: buffer_m = 11000, chip_px = 734
CONFIG = {
    'SENTINEL_HUB': {
        'buffer_m': 11000,
        'chip_px': 734,
    },
    'P1812': {
        'frequency': 0.9,  # GHz
        'time_percentage': 50,
    },
    'GENERATION': {
        'max_distance_km': 11,
        'azimuth_step': 10,
        'distance_step': 0.5,
    }
}
```

---

## Recommendation

**Start with Phase 1** (reorganize cells) - quick win for immediate clarity

**Then Phase 2** (move to modules) - better long-term structure

**Phase 3** (optimize) - if performance becomes issue

---

## Current Cell Map → Proposed Reorganization

| Current | Proposed | Action |
|---------|----------|--------|
| 1 | 1 | Imports (keep) |
| 2 | 2 | Path Setup (keep) |
| 4 | - | Delete (just docs) |
| 6 | - | Delete (move to config) |
| 7 | 3 | TX config → CONFIG dict |
| 9-10 | - | Delete (move to module) |
| 11-14 | 3 | Consolidate all config |
| 15 | - | Keep (already in config file) |
| 17 | - | Delete (move to module) |
| 18-22 | 7 | Consolidate profile extraction |

**Result**: 25 cells → 7 focused cells

---

## Implementation Priority

1. **High Priority** (do immediately):
   - Consolidate configuration (Cells 11-14)
   - Add markdown section headers
   - Move magic numbers to CONFIG dict

2. **Medium Priority** (do soon):
   - Move functions to `src/mst_gis/propagation/`
   - Consolidate extract/export pipeline

3. **Low Priority** (optimize later):
   - Batch API calls
   - Cache elevation/landcover results

---

## Ready to Proceed?

Which would you like to tackle first?
1. **Quick cleanup** - consolidate config cells
2. **Full refactor** - move code to modules
3. **Leave as-is** - it works, good enough

Let me know!

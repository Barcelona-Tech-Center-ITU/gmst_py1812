# Hardcoded Configuration Values - Locations & Fixes

## Problem
Configuration values are hardcoded in multiple places:
- Phase 0 notebook (CONFIG dict)
- Python module (DEFAULT_CONFIG)
- Function default parameters
- These are NOT linked - changes to one don't affect others

## Single Source of Truth
**File**: `config_example.json` - Use this as reference

**For Notebooks**: Edit `notebooks/phase0_setup.ipynb` cell "config" (lines 204-232)

**For Scripts**: Either:
1. Pass `--config config_example.json` to scripts, OR
2. Edit `src/mst_gis/pipeline/config.py` DEFAULT_CONFIG (lines 20-58)

---

## LOCATIONS OF HARDCODED VALUES

### 1. **Python Module - config.py** (MAIN - DEFAULT_CONFIG)
**File**: `src/mst_gis/pipeline/config.py` (lines 20-58)

```python
DEFAULT_CONFIG: Dict[str, Any] = {
    'TRANSMITTER': {
        'longitude': -13.40694,      # HARDCODED
        'latitude': 9.345,           # HARDCODED
        'antenna_height_tx': 57,     # HARDCODED
        'antenna_height_rx': 10,     # HARDCODED
    },
    'P1812': {
        'frequency_ghz': 0.9,        # HARDCODED
        'time_percentage': 50,       # HARDCODED
        'polarization': 1,           # HARDCODED
    },
    'RECEIVER_GENERATION': {
        'max_distance_km': 11,       # HARDCODED ← YOU TRIED TO CHANGE THIS
        'azimuth_step': 10,          # HARDCODED
        'distance_step': 0.03,       # HARDCODED ← YOU TRIED TO CHANGE THIS
        'sampling_resolution': 30,   # HARDCODED
    },
    ...
}
```

**How to change**: Edit this dict directly OR pass config file via CLI

---

### 2. **Phase 0 Notebook** (used by notebook pipeline)
**File**: `notebooks/phase0_setup.ipynb` (lines 204-232)

**Cell**: "config" section

```python
CONFIG = {
    'TRANSMITTER': {
        'longitude': -13.40694,      # HARDCODED
        'latitude': 9.345,           # HARDCODED
        ...
    },
    'RECEIVER_GENERATION': {
        'distance_step': 0.03,       # HARDCODED ← YOU CHANGED THIS
        ...
    }
}
```

**How to change**: Edit the CONFIG dict in the notebook

---

### 3. **Function Default Parameters** (used when called without arguments)
These have hardcoded defaults that don't pull from CONFIG:

#### `point_generation.py` - `generate_distance_array()` (lines 128-132)
```python
def generate_distance_array(
    min_km: float = 0.0,
    max_km: float = 11.0,           # ← HARDCODED
    step_km: float = 0.03,          # ← HARDCODED
) -> np.ndarray:
```

#### `point_generation.py` - `generate_azimuth_array()` (lines 165-168)
```python
def generate_azimuth_array(
    num_azimuths: int = 36,         # ← HARDCODED
    start_deg: float = 0.0,         # ← HARDCODED
) -> np.ndarray:
```

#### `point_generation.py` - `generate_receiver_grid()` (lines 196-201)
```python
def generate_receiver_grid(
    tx: Transmitter,
    max_distance_km: float = 11.0,  # ← HARDCODED
    distance_step_km: float = 0.03, # ← HARDCODED
    num_azimuths: int = 36,         # ← HARDCODED
    ...
) -> gpd.GeoDataFrame:
```

**Problem**: If called without arguments, these use hardcoded defaults instead of config values

**Solution**: Remove defaults OR get them from CONFIG

---

## RECOMMENDATION: FIX STRATEGY

### Short-term (Quick Fix)
1. **Notebooks**: Edit Phase 0 CONFIG dict - DONE (this is what you did)
2. **Scripts**: Pass `--config config_example.json` to all scripts

### Long-term (Better Architecture)
1. Make ALL functions accept config dict parameter
2. Remove function-level defaults
3. All values flow from single config source
4. Example:

```python
def generate_distance_array(
    max_km: float,          # NO DEFAULT - required from config
    step_km: float,         # NO DEFAULT - required from config
    min_km: float = 0.0,    # Only min has safe default
) -> np.ndarray:
```

---

## TEST YOUR CHANGE

**Before** (original):
- Changed distance_step to 0.05 in Phase 0 notebook
- Result: Still 368 points (0.03 km spacing) ✗
- Why: Notebooks work, but scripts use different DEFAULT_CONFIG

**After fix** (should work):
- Edit Phase 0: distance_step = 0.05 ✓
- Run notebooks: Uses Phase 0 value ✓
- Run scripts: Pass `--config config_example.json` with same value ✓
- Result: Consistent across notebooks AND scripts ✓

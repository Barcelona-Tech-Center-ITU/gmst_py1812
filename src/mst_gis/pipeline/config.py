"""
Configuration management for the radio propagation pipeline.

Provides:
- Default CONFIG dictionary
- CONFIG validation
- CONFIG loading from files
- CONFIG parameter overrides
"""

from pathlib import Path
from typing import Dict, Any, Optional
import json
import yaml

from mst_gis.utils.validation import ValidationError, validate_config as validate_config_dict


# Default configuration
DEFAULT_CONFIG: Dict[str, Any] = {
    'TRANSMITTER': {
        'tx_id': 'TX_0001',
        'longitude': -13.40694,
        'latitude': 9.345,
        'antenna_height_tx': 57,
        'antenna_height_rx': 10,
    },
    'P1812': {
        'frequency_ghz': 0.9,
        'time_percentage': 50,
        'polarization': 1,  # 1=horizontal, 2=vertical
    },
    'RECEIVER_GENERATION': {
        'max_distance_km': 11,
        'azimuth_step': 10,  # degrees
        'distance_step': 0.03,  # km (30 meters)
        'sampling_resolution': 30,  # meters
    },
    'SENTINEL_HUB': {
        'buffer_m': 11000,  # meters around transmitter
        'chip_px': 734,  # pixel size
        'year': 2020,
    },
    'LCM10_TO_CT': {
        # Land cover class mapping to Ct (land cover category)
        100: 1, 80: 2, 30: 2, 40: 2, 70: 2, 110: 2, 254: 2,  # Water, Urban, Herbaceous, etc → 1-2
        20: 3, 50: 3,  # Shrubland → 3
        10: 4, 60: 4, 90: 4,  # Forest, Herbs, Tree → 4
    },
    'CT_TO_R': {
        # Resistance mapping by land cover category
        1: 0,     # Class 1: 0 ohms
        2: 0,     # Class 2: 0 ohms
        3: 10,    # Class 3: 10 ohms
        4: 15,    # Class 4: 15 ohms
        5: 20,    # Class 5: 20 ohms
    },
}


class ConfigManager:
    """Manager for pipeline configuration."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with optional config override."""
        self.config = DEFAULT_CONFIG.copy()
        if config:
            self._deep_update(self.config, config)
        self.validate()
    
    def _deep_update(self, target: Dict, source: Dict) -> None:
        """Deep update target dict with source dict."""
        for key, value in source.items():
            if isinstance(value, dict) and key in target:
                self._deep_update(target[key], value)
            else:
                target[key] = value
    
    def validate(self) -> None:
        """Validate configuration."""
        try:
            validate_config_dict(self.config)
        except ValidationError as e:
            raise ConfigError(f"Invalid configuration: {e}")
    
    def get(self, section: str, key: Optional[str] = None, default: Any = None) -> Any:
        """Get configuration value."""
        if key is None:
            return self.config.get(section, default)
        
        section_data = self.config.get(section, {})
        if isinstance(section_data, dict):
            return section_data.get(key, default)
        return default
    
    def set(self, section: str, key: str, value: Any) -> None:
        """Set configuration value."""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        self.validate()
    
    def to_dict(self) -> Dict[str, Any]:
        """Export config as dictionary."""
        return self.config.copy()
    
    def to_json(self, indent: int = 2) -> str:
        """Export config as JSON string."""
        return json.dumps(self.config, indent=indent)
    
    def to_file(self, path: Path, format: str = 'json') -> None:
        """Save config to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == 'json':
            with open(path, 'w') as f:
                json.dump(self.config, f, indent=2)
        elif format == 'yaml':
            with open(path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    @classmethod
    def from_file(cls, path: Path) -> 'ConfigManager':
        """Load config from file."""
        if not path.exists():
            raise ConfigError(f"Config file not found: {path}")
        
        with open(path) as f:
            if path.suffix == '.json':
                config = json.load(f)
            elif path.suffix in ['.yaml', '.yml']:
                config = yaml.safe_load(f)
            else:
                raise ConfigError(f"Unsupported file format: {path.suffix}")
        
        return cls(config)
    
    @classmethod
    def from_defaults(cls) -> 'ConfigManager':
        """Create config from defaults."""
        return cls()


class ConfigError(Exception):
    """Custom exception for configuration errors."""
    pass


def get_transmitter_info(config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract transmitter information from config."""
    tx = config['TRANSMITTER']
    return {
        'tx_id': tx['tx_id'],
        'latitude': tx['latitude'],
        'longitude': tx['longitude'],
        'antenna_height_tx': tx['antenna_height_tx'],
        'antenna_height_rx': tx['antenna_height_rx'],
    }


def get_p1812_params(config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract P.1812 parameters from config."""
    p1812 = config['P1812']
    return {
        'frequency_ghz': p1812['frequency_ghz'],
        'time_percentage': p1812['time_percentage'],
        'polarization': p1812['polarization'],
    }


def get_receiver_generation_params(config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract receiver generation parameters from config."""
    rg = config['RECEIVER_GENERATION']
    return {
        'max_distance_km': rg['max_distance_km'],
        'azimuth_step': rg['azimuth_step'],
        'distance_step': rg['distance_step'],
        'sampling_resolution': rg['sampling_resolution'],
    }


def get_land_cover_mappings(config: Dict[str, Any]) -> tuple:
    """Get land cover class and resistance mappings."""
    lcm10_to_ct = config['LCM10_TO_CT']
    ct_to_r = config['CT_TO_R']
    return lcm10_to_ct, ct_to_r


def print_config(config: Dict[str, Any]) -> None:
    """Print configuration in readable format."""
    from mst_gis.utils.logging import print_header, print_section
    
    print_header("PIPELINE CONFIGURATION")
    
    # Transmitter
    print_section("Transmitter")
    tx = get_transmitter_info(config)
    for key, value in tx.items():
        print(f"  {key}: {value}")
    
    # P.1812 Parameters
    print_section("P.1812 Parameters")
    p1812 = get_p1812_params(config)
    pol_str = "Horizontal" if p1812['polarization'] == 1 else "Vertical"
    print(f"  Frequency: {p1812['frequency_ghz']} GHz")
    print(f"  Time percentage: {p1812['time_percentage']}%")
    print(f"  Polarization: {pol_str} ({p1812['polarization']})")
    
    # Receiver Generation
    print_section("Receiver Generation")
    rg = get_receiver_generation_params(config)
    for key, value in rg.items():
        print(f"  {key}: {value}")
    
    # Sentinel Hub
    print_section("Sentinel Hub")
    sh = config['SENTINEL_HUB']
    for key, value in sh.items():
        print(f"  {key}: {value}")

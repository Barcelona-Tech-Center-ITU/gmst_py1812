from setuptools import setup, find_packages

setup(
    name="gmst_py1812",
    version="0.1.0",
    description="Radio Propagation Prediction Pipeline using ITU-R P.1812-6",
    author="GMST",
    url="https://github.com/oguzhanerr/gmst_py1812",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=[
        # Core numerical and data processing
        "numpy>=1.21.0",
        "pandas>=1.3.0",
        "matplotlib>=3.4.0",
        # GIS and geospatial
        "geopandas>=0.9.0",
        "rasterio>=1.2.0",
        "shapely>=1.7.0",
        "geojson>=2.5.0",
        "affine>=2.3.0",
        # Data acquisition and utilities
        "requests>=2.26.0",
        "SRTM.py>=0.3.7",
        "certifi>=2024.0.0",
        "PyYAML>=5.1",
        "psutil>=5.8.0",
    ],
    extras_require={
        "dev": [
            "jupyter>=1.0.0",
            "jupyterlab>=3.0.0",
            "ipython>=7.0.0",
            "ipykernel>=6.0.0",
        ],
    },
)

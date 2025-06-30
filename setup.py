"""Setup configuration for DBT Metrics Manager."""

from setuptools import setup, find_packages
from pathlib import Path

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
with open(requirements_path) as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="dbt-metrics-manager",
    version="1.0.0",
    description="Terminal UI for managing DBT metrics",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "dbt-metrics=dbt_metrics_manager.app:main",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    include_package_data=True,
    package_data={
        "dbt_metrics_manager": ["assets/*.css"],
    },
)
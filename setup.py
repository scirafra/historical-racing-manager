from setuptools import setup, find_packages

setup(
    name="historical_racing_manager",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    entry_points={
        'console_scripts': [
            'historical_racing_manager=historical_racing_manager.main:main',
        ],
    },
)

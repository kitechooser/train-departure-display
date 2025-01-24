from setuptools import setup, find_packages

setup(
    name="train-departure-display",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.1",
        "pillow>=8.0.0",
        "luma.core>=2.3.1",
        "luma.oled>=3.8.1"
    ],
    extras_require={
        "test": [
            "pytest>=7.4.3",
            "pytest-cov>=4.1.0",
            "responses>=0.24.1",
            "mock>=5.1.0"
        ]
    }
)

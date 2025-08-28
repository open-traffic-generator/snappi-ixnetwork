"""
To build distribution: python setup.py sdist bdist_wheel --universal
"""
import os
import setuptools

pkg_name = "snappi_ixnetwork"
version = "1.34.0"

# read long description from readme.md
base_dir = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(base_dir, "readme.md")) as fd:
    long_description = fd.read()

setuptools.setup(
    name=pkg_name,
    version=version,
    description="The Snappi IxNetwork Open Traffic Generator Python Package",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/open-traffic-generator/snappi-ixnetwork",
    author="Keysight Technologies",
    author_email="andy.balogh@keysight.com",
    license="MIT",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing :: Traffic Generation",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="snappi ixnetwork testing open traffic generator automation",
    include_package_data=True,
    packages=setuptools.find_packages(),
    python_requires=">=3.7, <4",
    install_requires=["ixnetwork-restpy>=1.7.0"],
    extras_require={
        "testing": [
            "snappi==1.34.1",
            "pytest",
            "mock",
            "dpkt==1.9.4",
        ]
    },
)

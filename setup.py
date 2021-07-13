"""
To build distribution: python setup.py sdist bdist_wheel --universal
"""
import os
import setuptools

pkg_name = "snappi_ixnetwork"
version = "0.4.9"

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
    author="ajbalogh",
    author_email="andy.balogh@keysight.com",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing :: Traffic Generation",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
    ],
    keywords="snappi ixnetwork testing open traffic generator automation",
    include_package_data=True,
    packages=[pkg_name],
    python_requires=">=2.7, <4",
    install_requires=["ixnetwork-restpy>=1.0.52"],
    extras_require={
        "testing": [
            "snappi==0.4.19",
            "snappi_convergence==0.0.23",
            "pytest",
            "dpkt==1.9.4",
        ]
    },
)

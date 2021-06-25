"""Build distributions

To build `python setup.py sdist --formats=gztar bdist_wheel --universal`
"""
import os
from setuptools import setup

# read long description and version number
pkg_name = 'snappi_ixnetwork'
base_dir = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(base_dir, 'README.md')) as fid:
    long_description = fid.read()
with open(os.path.join(base_dir, 'VERSION')) as fid:
    version_number = fid.read()

setup(
    name=pkg_name,
    version=version_number,
    description='The IxNetwork Open Traffic Generator Python Package',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/open-traffic-generator',
    author='ajbalogh',
    author_email='andy.balogh@keysight.com',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Testing :: Traffic Generation',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3'
    ],
    keywords='ixnetwork testing open traffic generator automation',
    packages=[pkg_name],
    include_package_data=True,
    python_requires='>=2.7, <4',
    install_requires=[
        'ixnetwork-restpy>=1.0.52'
    ],
    extras_require={
        'dev': [
            'snappi==0.4.11',
            'snappi_convergence==0.0.14',
            'pytest',
            'flake8==3.8.4',
            'dpkt==1.9.4',
        ]
    }
)

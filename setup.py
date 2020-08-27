import os
import shutil
from setuptools import setup, find_namespace_packages


pkg_name = 'ixnetwork_open_traffic_generator'
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
        'Development Status :: 1 - Planning',
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
        'abstract-open-traffic-generator', 
        'ixnetwork-restpy'
    ],
    tests_require=[
        'pytest'
    ]
)


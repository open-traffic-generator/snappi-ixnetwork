import os
import shutil
from setuptools import setup, find_namespace_packages
import requests


# download the latest version of the open-traffic-generator/models 
# openapi.yaml spec which this package is based on
latest = requests.request('GET', 
    'https://github.com/open-traffic-generator/models/releases/latest/download',
    allow_redirects=False)
openapi_url = latest.headers['location'] + "/openapi.yaml"
download = requests.request('GET', openapi_url)
assert(download.status_code == 200)
doc_dir = './ixnetwork_open_traffic_generator/docs'
if os.path.exists(doc_dir) is False:
    os.mkdir(doc_dir)
with open(os.path.join(doc_dir, 'openapi.yaml'), 'wb') as fid:
    fid.write(download.content)
 
# read long description and version number
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
        'jsonpath-ng',
        'abstract-open-traffic-generator', 
        'ixnetwork-restpy'
    ],
    tests_require=[
        'pytest'
    ]
)


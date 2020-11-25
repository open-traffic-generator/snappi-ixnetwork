"""Build distributions

To build `python setup.py sdist --formats=gztar bdist_wheel --universal`
"""
import os
from setuptools import setup
import requests


# TODO: We shouldn't be fetching latest version
# download the latest version of the open-traffic-generator/models
# openapi.yaml spec which this package is based on
OPENAPI_URL = (
    'https://github.com/open-traffic-generator/models/releases/latest/download'
    '/openapi.yaml'
)
response = requests.request('GET', OPENAPI_URL, allow_redirects=True)
assert response.status_code == 200

# put the downloaded file inside docs dir of package
doc_dir = './ixnetwork_open_traffic_generator/docs'
if os.path.exists(doc_dir) is False:
    os.mkdir(doc_dir)
with open(os.path.join(doc_dir, 'openapi.yaml'), 'wb') as fp:
    fp.write(response.content)

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
        'pyaml',
        'jsonpath-ng',
        'abstract-open-traffic-generator==0.0.64',
        'ixnetwork-restpy>=1.0.52'
    ],
    extras_require={
        'dev': [
            'pytest',
            'flake8==3.8.4',
            'dpkt==1.9.4',
        ]
    }
)

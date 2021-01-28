# Contribute

## Setup

Please make sure that the setup meets [Python Prerequisites](#python-prerequisites).

- Clone this project, `cd` inside it.

- Create virtual environment inside `env/` and activate it.
  
  ```sh
  python -m virtualenv env
  # on linux
  source env/bin/activate
  # on windows
  env\Scripts\activate on Windows
  ```

  **NOTE:** If you do not wish to activate virtual env, you use `env/bin/python` (or `env\scripts\python` on Windows) instead of `python`.

- Install pre-build dependencies followed by project itself.

  ```sh
  python -m pip install --upgrade -r requirements.txt
  # it won't actually install this package, so any new changes in project src
  # will be reflected immediately
  python -m pip install --upgrade -e ".[dev]"
  ```

- Run Tests.

  ```sh
  # provide intended API Server and port addresses
  vi tests/settings.json
  python -m pytest tests/tcp/test_tcp_flow_capture.py
  ```

#### Python Prerequisites

- Please make sure you have `python` and `pip` installed on your system.

  You may have to use `python3` or `absolute path to python executable` depending on Python Installation on system, instead of `python`.

  ```sh
  python -m pip --help
  ```
  
  Please see [pip installation guide](https://pip.pypa.io/en/stable/installing/), if you don't see a help message.

- It is recommended that you use a python virtual environment for development.

  ```sh
  python -m pip install --upgrade virtualenv
  ```

## Coding Style

Do not use `implicit` coding style
```
test = None
if (test):
   print('test is None')
```

Do use the `explicit` coding style
```
test = None
if test is not None:
   print('test is None')
```
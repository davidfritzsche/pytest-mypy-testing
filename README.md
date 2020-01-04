# pytest-mypy-testing — Plugin to test mypy analysis with pytest

## Installation

``` shell
pip install pytest-mypy-testing
```

### Start Development Work ###

* Install pyenv and install Python versions

    ```shell
    for v in 3.8.0 3.7.5 3.6.9 pypy3.6-7.2.0 3.5.8 ; do pyenv install -s $v ; done
    pyenv local 3.8.0 3.7.5 3.6.9 pypy3.6-7.2.0 3.5.8
    ```

* Create and activate a Python virtual environment.
* Install development dependencies by calling `pip install -U -r requirements.txt`.
* Start developing

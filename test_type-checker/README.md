# Static type check with mypy

This is only intended for testing the Python code during development.
A type checker can be used to check the consistency of static data types of Python variables.
This means that runtime exceptions due to type mismatches can be found without trail and error.
This file explains how to use `mypy` to perform a type check.

## Dependencies
The Python module `mypy` is required as the following type definition packages: types-PyYAML, types-paho-mqtt, types-requests, types-pyserial.

```bash
cd /srv/sensorReporter
sudo ./install_dependencies.sh test-typeshed
```

Most checks are disabled by default.
Three configuration files are provided to define common use cases:

| Filename                | use case                                                                                                                                                                                    |
|-------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| mypy-strict.ini         | Prints errors for missing type definitions. Useful for checking individual files and their dependencies. To find out if type annotations are missing.                                       |
| mypy-ignore-untyped.ini | This configuration will skip untyped methods. Useful when checking multiple files containing typed and untyped methods.                                                                     |
| mypy-check-untyped.ini  | This will also check untyped methods and assume unknown types as 'Any'. This will result in errors that will never throw a runtime exception. Useful for checking individual untyped files. |

To run the type checker, specify a configuration and the relative path to the file that you want to be checked.
If the path is omitted, all Python files in the working directory will be checked.

```bash
cd /srv/sensorReporter
bin/python -m mypy --config-file <relative-path/to/ini-file> <relative-path/to/python-file>
bin/python -m mypy --config-file test_type-checker/mypy-strict.ini sensor_reporter.py
```

To find out the data type out mypy has detected, use the following method.
It will print the data type of the given variable.
But note that it will also be parsed by Python at runtime and Python will also print the type.

```python
reveal_type(<variable>)
```
# Bincache
![Build Status](https://img.shields.io/github/actions/workflow/status/simpx/bincache/python-package.yml)
![PyPI](https://img.shields.io/pypi/v/bincache)
![License](https://img.shields.io/github/license/simpx/bincache)
![Issues](https://img.shields.io/github/issues/simpx/bincache)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)

Bincache is a command-line utility designed to cache the output of executable binaries and shell commands.

## Installation

```sh
pip install bincache
```

## Usage

Execute commands through bincache to cache their output.

### Basic Usage

```sh
bincache <binary_or_command> <arg1> [arg2 ... argN]
```

### Examples

Cache the output of the date command:

```sh
bincache date
```

Cache the output of a binary executable:

```
bincache ./a.out -l -a
```

## Configuration

Bincache can be configured using a configuration file `bincache.conf`. The default configuration file is expected to be located at `$HOME/.cache/bincache/bincache.conf`.

### Configuration Options

- `max_size`: Maximum cache size (e.g., 5G for 5 Gigabytes), default `5G`
- `log_file`: Path to the log file, default empty
- `log_level`: Logging level (INFO, DEBUG, WARNING, ERROR, CRITICAL), default `INFO`
- `stats`: Enable or disable statistics, default `false`

Example bincache.conf:

```
max_size = 5G
log_file = /var/log/bincache.log
log_level = INFO
stats = false
```

Environment Variables
- `BINCACHE_DIR`: Override the default cache directory.

## Contributing
To contribute to Bincache, fork the repository, make your changes, and create a pull request. Please ensure that your changes are well-tested by run `pytest`.

## License
Bincache is licensed under the MIT License. See the `LICENSE` file for more information.

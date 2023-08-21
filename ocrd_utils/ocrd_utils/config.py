"""
Most behavior of OCR-D is controlled via command-line flags or keyword args.
Some behavior is global or too cumbersome to handle via explicit code and
better solved by using environment variables.

OcrdEnvConfig is a base class to make this more streamlined, to be subclassed
in the `ocrd` package for the actual values
"""

from os import environ
from pathlib import Path

class OcrdEnvVariable():

    def __init__(self, name, description, parser=str, validator=lambda val: True, default=[False, None]):
        """
        An environment variable for use in OCR-D.

        Args:
            name (str): Name of the environment vairable
            description (str): Description of what the variable is used for.

        Keyword Args:
            parser (callable): Function to transform the raw (string) value to whatever is needed.
            validator (callable): Function to validate that the raw (string) value is parseable.
            default (tuple(bool, any)): 2-tuple, first element is a bool whether there is a default
                value defined and second element contains that default value, which can be a callable
                for defered evaluation
        """
        self.name = name
        self.description = description
        self.parser = parser
        self.validator = validator
        self.has_default = default[0]
        self.default = default[1]

class OcrdEnvConfig():

    def __init__(self):
        self._variables = {}

    def add(self, name, *args, **kwargs):
        self._variables[name] = OcrdEnvVariable(name, *args, **kwargs)

    def has_default(self, name):
        if not name in self._variables:
            raise ValueError(f"Unregistered env variable {name}")
        return self._variables[name].has_default

    def __getattr__(self, name):
        if not name in self._variables:
            raise ValueError(f"Unregistered env variable {name}")
        var_obj = self._variables[name]
        try:
            raw_value = self.raw_value(name)
        except KeyError as e:
            if var_obj.has_default:
                raw_value = var_obj.default() if callable(var_obj.default) else var_obj.default
            else:
                raise e
        if not var_obj.validator(raw_value):
            raise ValueError(f"'{name}' set to invalid value '{raw_value}'")
        return var_obj.parser(raw_value)

    def is_set(self, name):
        if not name in self._variables:
            raise ValueError(f"Unregistered env variable {name}")
        return name in environ

    def raw_value(self, name):
        if not name in self._variables:
            raise ValueError(f"Unregistered env variable {name}")
        return environ[name]

config = OcrdEnvConfig()

config.add('OCRD_METS_CACHING',
    description='If set to `true`, access to the METS file is cached, speeding in-memory search and modification.',
    validator=lambda val: val in ('true', 'false', '0', '1'),
    parser=lambda val: val in ('true', '1'))

config.add('OCRD_MAX_PROCESSOR_CACHE',
    description="Maximum number of processor instances (for each set of parameters) to be kept in memory (including loaded models) for processing workers or processor servers.",
    parser=int,
    default=(True, 128))

config.add("OCRD_PROFILE",
    description="""\
This variable configures the built-in CPU and memory profiling. If empty, no profiling is done. Otherwise expected to contain any of the following tokens:
  * `CPU`: Enable CPU profiling of processor runs
  * `RSS`: Enable RSS memory profiling
  * `PSS`: Enable proportionate memory profiling""",
  validator=lambda val : val in ('', 'CPU', 'RSS', 'PSS'),
  default=(True, ''))

config.add("OCRD_PROFILE_FILE",
    description="If set, then the CPU profile is written to this file for later peruse with a analysis tools like [snakeviz](https://jiffyclub.github.io/snakeviz/)")

config.add("OCRD_DOWNLOAD_RETRIES",
    description="Number of times to retry failed attempts for downloads of workspace files.",
    validator=int,
    parser=int)

def _ocrd_download_timeout_parser(val):
    timeout = val.split(',')
    if len(timeout) > 1:
        timeout = tuple(float(x) for x in timeout)
    else:
        timeout = float(timeout[0])
    return timeout

config.add("OCRD_DOWNLOAD_TIMEOUT",
    description="Timeout in seconds for connecting or reading (comma-separated) when downloading.",
    parser=_ocrd_download_timeout_parser)

config.add("OCRD_NETWORK_SERVER_ADDR_PROCESSING",
        description="Default address of Processing Server to connect to (for `ocrd network client processing`).",
        default=(True, ''))

config.add("OCRD_NETWORK_SERVER_ADDR_WORKFLOW",
        description="Default address of Workflow Server to connect to (for `ocrd network client processing`).",
        default=(True, ''))

config.add("OCRD_NETWORK_SERVER_ADDR_WORKSPACE",
        description="Default address of Workspace Server to connect to (for `ocrd network client processing`).",
        default=(True, ''))

config.add("HOME",
    description="HOME directory, cf. https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html",
    validator=lambda val: Path(val).is_dir(),
    parser=lambda val: Path(val),
    default=(True, lambda: Path.home()))

config.add("XDG_DATA_HOME",
    description="Directory to look for `./ocrd/resources.yml` (i.e. `ocrd resmgr` user database)",
    default=(True, lambda: Path(config.HOME, '.local/share')))

config.add("XDG_CONFIG_HOME",
    description="Directory to look for `./ocrd-resources/*` (i.e. `ocrd resmgr` data location)",
    default=(True, lambda: Path(config.HOME, '.config')))

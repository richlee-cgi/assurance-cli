class AssuranceError(Exception):
    exit_code = 1


class ConfigError(AssuranceError):
    exit_code = 2


class UnsafeCommandError(AssuranceError):
    exit_code = 3


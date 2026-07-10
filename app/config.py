import os


TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
FALSE_VALUES = frozenset({"0", "false", "no", "off"})


def get_env_bool(name, default=False):
    """Parses a boolean environment variable with safe fallback behavior."""
    value = os.getenv(name)
    if value is None:
        return default

    normalized = str(value).strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return default

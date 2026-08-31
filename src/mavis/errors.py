class MavisError(Exception):
    """Base application error."""


class ConfigurationError(MavisError):
    """Invalid or unsafe configuration."""


class DataValidationError(MavisError):
    """Market data failed canonical validation."""


class ContractError(MavisError):
    """A domain or integration contract was violated."""

class FitAiError(Exception):
    """Base exception safe for translation at the tool boundary."""


class NotFoundError(FitAiError):
    pass


class RepositoryError(FitAiError):
    pass


class ValidationFailure(FitAiError):
    pass

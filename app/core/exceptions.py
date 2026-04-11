class TemplateNotFoundError(Exception):
    pass


class FileServiceError(Exception):
    pass


class ValidationError(Exception):
    def __init__(self, errors: list[dict]):
        self.errors = errors
        super().__init__("Validation failed")

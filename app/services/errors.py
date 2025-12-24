class BalanceProviderError(RuntimeError):
    def __init__(self, provider: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.message = message

    def dict(self) -> dict:
        return {"provider": self.provider, "message": self.message, "status_code": self.status_code}

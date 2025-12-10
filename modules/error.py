class Error:
    def __init__(self, exc: Exception) -> None:
        self.exception: Exception = exc

    def temp(self):
        print(self.exception.with_traceback())

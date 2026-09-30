class OpsError(Exception):
    code = "OPS_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UnknownCollector(OpsError):
    code = "UNKNOWN_COLLECTOR"


class CollectorRunning(OpsError):
    code = "COLLECTOR_RUNNING"

from pydantic import BaseModel


class APILog(BaseModel):
    endpoint: str
    response_time_ms: float
    status_code: int

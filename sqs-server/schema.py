from pydantic import BaseModel


class ProduceRequest(BaseModel):
    count: int = 10


class LeaderStats(BaseModel):
    limit: int = 10

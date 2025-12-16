from pydantic import BaseModel


class ProduceRequest(BaseModel):
    count: int = 10

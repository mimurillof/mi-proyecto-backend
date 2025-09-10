from pydantic import BaseModel
from typing import List, Optional

class Asset(BaseModel):
    ticker: str
    quantity: float
    purchase_price: float

class Portfolio(BaseModel):
    name: str
    assets: List[Asset] 
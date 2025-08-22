from pydantic import BaseModel
from typing import List, Optional

class Review(BaseModel):
    id: str
    title: str
    body: str
    reviewerName: str
    date: str
    rating: int
    reviewerAvatar: Optional[str] = None

class Pandel(BaseModel):
    id: int
    name: str
    description: str
    average_rating: float
    coordinates: dict  
    banner_image: str
    created_at: str
    updated_at: str
    images: List[str]  
    category: str
    popularity: float
    avatar_image: str
    address: str
    reviews: List[Review]

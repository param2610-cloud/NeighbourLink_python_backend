from pydantic import BaseModel
from typing import List, Optional

class Pandel(BaseModel):
    id: int
    name: str
    description: str
    average_rating: float
    coordinates: dict  # Should contain 'lat' and 'lng' (not 'long')
    banner_image: str
    created_at: str
    updated_at: str
    images: List[str]  # Array of Cloudinary public IDs
    category: str
    popularity: float
    avatar_image: str
    address: str
    reviews: List[dict]

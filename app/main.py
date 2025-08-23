
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from app.types.types import Pandel, Review
from app.database.firebase  import db
from app.services.image_scraper import ImageScraper
import time

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174","https://neighbourlink.hexabytes.tech","https://backend.neighbourlink.hexabytes.tech"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"Hello": "World"}



@app.get("/pandel/", response_model=List[Pandel])
async def get_pandels():
    docs = db.collection("pandels").stream()
    items = []
    for d in docs:
        data = d.to_dict()
        # ensure id in doc
        data["id"] = int(data.get("id", d.id)) if isinstance(data.get("id"), int) else int(d.id) if str(d.id).isdigit() else data.get("id")
        
        # Ensure coordinates have correct format (lng not long)
        if "coordinates" in data and isinstance(data["coordinates"], dict):
            coords = data["coordinates"]
            if "long" in coords and "lng" not in coords:
                coords["lng"] = coords["long"]
                del coords["long"]
        
        items.append(Pandel(**data))
    return items


@app.post("/pandel/", response_model=Pandel, status_code=201)
async def create_pandel(pandel: Pandel):
    data = pandel.dict()
    # Use the provided numeric id as document id (string), so we can upsert consistently
    doc_id = str(pandel.id)
    db.collection("pandels").document(doc_id).set(data)
    return pandel

@app.post("/list-of-pandels/", response_model=List[Pandel], status_code=201)
async def create_list_of_pandels(pandels: List[Pandel]):
    batch = db.batch()
    col = db.collection("pandels")
    for p in pandels:
        batch.set(col.document(str(p.id)), p.dict())
    batch.commit()
    return pandels


@app.get("/pandel/{pandel_id}", response_model=Pandel)
async def get_pandel(pandel_id: int):
    doc = db.collection("pandels").document(str(pandel_id)).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Pandel not found")
    data = doc.to_dict()
    return Pandel(**data)

@app.put("/pandel/{pandel_id}", response_model=Pandel)
async def update_pandel(pandel_id: int, pandel: Pandel):
    if pandel_id != pandel.id:
        raise HTTPException(status_code=400, detail="Path id and body id must match")
    ref = db.collection("pandels").document(str(pandel_id))
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Pandel not found")
    ref.set(pandel.dict())
    return pandel

@app.patch("/pandel/{pandel_id}/address")
async def update_pandel_address(pandel_id: int, address: dict):
    """Update only the address field of a pandel"""
    if "address" not in address:
        raise HTTPException(status_code=400, detail="Address field is required")
    
    ref = db.collection("pandels").document(str(pandel_id))
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Pandel not found")
    
    ref.update({"address": address["address"]})
    return {"detail": "Address updated successfully"}

@app.delete("/pandel/{pandel_id}")
async def delete_pandel(pandel_id: int):
    ref = db.collection("pandels").document(str(pandel_id))
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Pandel not found")
    ref.delete()
    return {"detail": "Deleted"}


@app.get("/pandel/location/{lat}/{long}", response_model=List[Pandel])
async def get_pandel_by_location(lat: float, long: float, radius: float = 1.0):
    # Basic naive filter: fetch all and filter by haversine distance (Firestore lacks geo by default without geofirestore)
    # Assuming coordinates dict like {"lat": float, "long": float}
    import math

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    docs = db.collection("pandels").stream()
    result = []
    for d in docs:
        data = d.to_dict()
        coords = data.get("coordinates") or {}
        plat, plon = coords.get("lat"), coords.get("lng") or coords.get("long")  # Support both lng and long
        if isinstance(plat, (int, float)) and isinstance(plon, (int, float)):
            if haversine(lat, long, float(plat), float(plon)) <= radius:
                # Ensure coordinates have correct format
                data["coordinates"] = {"lat": float(plat), "lng": float(plon)}
                data["id"] = int(data.get("id", d.id)) if isinstance(data.get("id"), int) else int(d.id) if str(d.id).isdigit() else data.get("id")
                result.append(Pandel(**data))
    return result


@app.get("/pandel/district/{district}", response_model=List[Pandel])
async def get_pandel_by_district(district: str):
    # if address is a string containing district, do a simple contains filter client-side
    docs = db.collection("pandels").stream()
    result = []
    for d in docs:
        data = d.to_dict()
        address = (data.get("address") or "").lower()
        if district.lower() in address:
            result.append(Pandel(**data))
    return result

@app.get("/pandel/category/{category}", response_model=List[Pandel])
async def get_pandel_by_category(category: str):
    # If field is exact category string we can query Firestore directly
    docs = db.collection("pandels").where("category", "==", category).stream()
    return [Pandel(**d.to_dict()) for d in docs]

@app.get("/pandel/search/", response_model=List[Pandel])
async def search_pandels(query: str):
    # naive text search across name and description
    q = query.strip().lower()
    docs = db.collection("pandels").stream()
    result = []
    for d in docs:
        data = d.to_dict()
        if q in (data.get("name") or "").lower() or q in (data.get("description") or "").lower():
            result.append(Pandel(**data))
    return result


@app.post("/pandel/{pandel_id}/scrape-images")
async def scrape_pandel_images(pandel_id: int, background_tasks: BackgroundTasks, max_images: int = 5):
    """Scrape and upload images for a specific pandel"""
    # Check if pandel exists
    doc = db.collection("pandels").document(str(pandel_id)).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Pandel not found")
    
    pandel_data = doc.to_dict()
    pandel_name = pandel_data.get("name", "")
    
    if not pandel_name:
        raise HTTPException(status_code=400, detail="Pandel name not found")
    
    # Add background task to scrape images
    background_tasks.add_task(scrape_images_task, pandel_id, pandel_name, max_images)
    
    return {"detail": f"Image scraping started for pandel {pandel_name}", "pandel_id": pandel_id}


async def scrape_images_task(pandel_id: int, pandel_name: str, max_images: int = 5):
    """Background task to scrape and upload images"""
    try:
        scraper = ImageScraper()
        public_ids = scraper.scrape_and_upload_images(pandel_name, max_images)
        
        if public_ids:
            # Update pandel with new image public_ids
            ref = db.collection("pandels").document(str(pandel_id))
            doc = ref.get()
            
            if doc.exists:
                current_data = doc.to_dict()
                current_images = current_data.get("images", [])
                
                # Add new public_ids to existing images (avoid duplicates)
                updated_images = list(set(current_images + public_ids))
                
                ref.update({"images": updated_images})
                print(f"Updated pandel {pandel_id} with {len(public_ids)} new images")
            else:
                print(f"Pandel {pandel_id} not found during update")
        else:
            print(f"No images were scraped for pandel {pandel_id}")
            
    except Exception as e:
        print(f"Error scraping images for pandel {pandel_id}: {str(e)}")
    finally:
        # Cleanup scraper resources
        try:
            scraper.cleanup()
        except:
            pass


@app.get("/pandel/{pandel_id}/scrape-status")
async def get_scrape_status(pandel_id: int):
    """Get current images for a pandel (to check scraping progress)"""
    doc = db.collection("pandels").document(str(pandel_id)).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Pandel not found")
    
    data = doc.to_dict()
    images = data.get("images", [])
    
    return {
        "pandel_id": pandel_id,
        "name": data.get("name", ""),
        "total_images": len(images),
        "images": images
    }


@app.post("/pandel/{pandel_id}/reviews", response_model=Review)
async def add_review(pandel_id: int, review_data: dict):
    """Add a review to a pandel"""
    # Check if pandel exists
    doc_ref = db.collection("pandels").document(str(pandel_id))
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Pandel not found")
    
    # Create review object
    review = Review(
        id=str(int(time.time() * 1000)),  # Use timestamp as ID
        title=review_data.get("title", ""),
        body=review_data.get("body", ""),
        reviewerName=review_data.get("reviewerName", ""),
        date=review_data.get("date", ""),
        rating=review_data.get("rating", 0),
        reviewerAvatar=review_data.get("reviewerAvatar")
    )
    
    # Get current pandel data
    pandel_data = doc.to_dict()
    current_reviews = pandel_data.get("reviews", [])
    
    # Add new review
    current_reviews.append(review.dict())
    
    # Calculate new average rating
    total_rating = sum(r.get("rating", 0) for r in current_reviews)
    average_rating = total_rating / len(current_reviews) if current_reviews else 0
    
    # Update pandel with new review and average rating
    doc_ref.update({
        "reviews": current_reviews,
        "average_rating": average_rating
    })
    
    return review


@app.get("/pandel/{pandel_id}/reviews", response_model=List[Review])
async def get_reviews(pandel_id: int):
    """Get all reviews for a pandel"""
    doc = db.collection("pandels").document(str(pandel_id)).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Pandel not found")
    
    data = doc.to_dict()
    reviews_data = data.get("reviews", [])
    
    return [Review(**review) for review in reviews_data]


@app.delete("/pandel/{pandel_id}/reviews/{review_id}")
async def delete_review(pandel_id: int, review_id: str):
    """Delete a review from a pandel"""
    doc_ref = db.collection("pandels").document(str(pandel_id))
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Pandel not found")
    
    pandel_data = doc.to_dict()
    reviews = pandel_data.get("reviews", [])
    
    # Filter out the review to delete
    updated_reviews = [r for r in reviews if r.get("id") != review_id]
    
    if len(updated_reviews) == len(reviews):
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Recalculate average rating
    if updated_reviews:
        total_rating = sum(r.get("rating", 0) for r in updated_reviews)
        average_rating = total_rating / len(updated_reviews)
    else:
        average_rating = 0
    
    # Update pandel
    doc_ref.update({
        "reviews": updated_reviews,
        "average_rating": average_rating
    })
    
    return {"detail": "Review deleted successfully"}
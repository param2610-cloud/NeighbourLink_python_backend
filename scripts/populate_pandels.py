import argparse
import json
from pathlib import Path
from datetime import datetime
import sys

try:
    import requests
except Exception as e:
    print("Missing dependency 'requests'. Install with: pip install requests")
    raise

def load_source(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def map_record(src):
    # Map known fields from the source JSON to Pandel model shape.
    # Fill missing fields with sensible defaults.
    lat = src.get("latitude") or src.get("lat") or None
    lon = src.get("longitude") or src.get("long") or None
    coordinates = {"lat": lat, "long": lon} if lat is not None and lon is not None else {}
    now = datetime.utcnow().isoformat() + "Z"
    mapped = {
        "id": int(src.get("id")),
        "name": src.get("name", ""),
        "description": src.get("description", "") or "",
        "average_rating": float(src.get("average_rating", 0.0) or 0.0),
        "coordinates": coordinates,
        # build a banner_image placeholder from banner_photo_uuid if present
        "banner_image": src.get("banner_photo_uuid", "") or "",
        "created_at": src.get("created_at", now),
        "updated_at": src.get("updated_at", now),
        "images": src.get("images", []) or [],
        "category": src.get("category", "") or "",
        "popularity": float(src.get("popularity", 0.0) or 0.0),
        "avatar_image": src.get("avatar_image", "") or "",
        "address": src.get("address", "") or "",
        "reviews": src.get("reviews", []) or []
    }
    return mapped

def post_batch(base_url, payload, dry_run=False):
    url = base_url.rstrip("/") + "/list-of-pandels/"
    if dry_run:
        print("[dry-run] would POST batch to", url, "items:", len(payload))
        return None
    resp = requests.post(url, json=payload, timeout=30)
    try:
        resp.raise_for_status()
    except Exception:
        print("Batch upload failed:", resp.status_code, resp.text)
        raise
    return resp.json()

def post_individual(base_url, item, dry_run=False):
    url = base_url.rstrip("/") + "/pandel/"
    if dry_run:
        print("[dry-run] would POST item to", url, "id:", item["id"])
        return None
    resp = requests.post(url, json=item, timeout=10)
    try:
        resp.raise_for_status()
    except Exception:
        print("Item upload failed id", item.get("id"), "status:", resp.status_code, resp.text)
        raise
    return resp.json()

def main():
    p = argparse.ArgumentParser(description="Populate backend with pandel data via API")
    p.add_argument("--source", "-s", default=str(Path(__file__).parents[2] / "frontend" / "external" / "pandalData_decrypted.json"),
                   help="Path to source JSON")
    p.add_argument("--base-url", "-b", default="http://localhost:8000", help="Backend API base URL")
    p.add_argument("--batch", action="store_true", help="Send all items in one batch to /list-of-pandels/")
    p.add_argument("--dry-run", action="store_true", help="Do not call API, just print what would be sent")
    p.add_argument("--limit", type=int, default=0, help="Limit number of records processed (0 = all)")
    args = p.parse_args()

    src_path = Path(args.source)
    if not src_path.exists():
        print("Source file not found:", src_path)
        sys.exit(1)

    data = load_source(src_path)
    src_items = data.get("pandals") or data.get("pandals", [])
    if not src_items:
        print("No pandals found in source")
        return

    mapped_items = [map_record(i) for i in src_items]
    if args.limit and args.limit > 0:
        mapped_items = mapped_items[: args.limit]

    print(f"Prepared {len(mapped_items)} items for upload (batch={args.batch}, dry-run={args.dry_run})")

    if args.batch:
        # API expects a list of Pandel objects
        try:
            res = post_batch(args.base_url, mapped_items, dry_run=args.dry_run)
            if res is not None:
                print("Batch response:", res)
        except Exception as e:
            print("Batch upload error:", e)
            sys.exit(1)
    else:
        # Post one by one
        for item in mapped_items:
            try:
                res = post_individual(args.base_url, item, dry_run=args.dry_run)
                if res is not None:
                    print("Uploaded id", item["id"])
            except Exception as e:
                print("Stopping on error for id", item.get("id"))
                sys.exit(1)

    print("Done.")

if __name__ == "__main__":
    main()
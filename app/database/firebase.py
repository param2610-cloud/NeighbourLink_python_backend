from pathlib import Path
import firebase_admin
from firebase_admin import credentials, firestore

# Resolve creds.json relative to this file so it works regardless of CWD
_creds_path = Path(__file__).parent / "creds.json"

# Initialize the default Firebase app once
try:
	firebase_admin.get_app()
except ValueError:
	cred = credentials.Certificate(str(_creds_path))
	firebase_admin.initialize_app(cred)

# Firestore client
db = firestore.client()

__all__ = ["db"]


from pathlib import Path
import json, re
import firebase_admin
from firebase_admin import credentials, firestore

creds_path = Path(__file__).parent / "creds_raw.json"

# Load raw JSON text
raw_text = creds_path.read_text()

# Escape newlines in private_key
fixed_text = re.sub(
    r'"private_key":\s*"-----BEGIN PRIVATE KEY-----([\s\S]*?)-----END PRIVATE KEY-----"',
    lambda m: '"private_key": "-----BEGIN PRIVATE KEY-----\\n'
              + m.group(1).strip().replace("\n", "\\n")
              + '\\n-----END PRIVATE KEY-----\\n"',
    raw_text
)

creds = json.loads(fixed_text)

try:
    firebase_admin.get_app()
except ValueError:
    cred = credentials.Certificate(creds)
    firebase_admin.initialize_app(cred)

# 👉 Firestore client export
db = firestore.client()

__all__ = ["db"]

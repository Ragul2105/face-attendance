import firebase_admin
from firebase_admin import credentials, firestore
import os
from app.config import config

_db = None

def get_firestore() -> firestore.Client:
    global _db
    if _db is None:
        if config.FIREBASE_SERVICE_ACCOUNT_JSON:
            cred = credentials.Certificate(config.FIREBASE_SERVICE_ACCOUNT_JSON)
        else:
            # For local development, use default credentials
            cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred, {'projectId': config.FIREBASE_PROJECT_ID})
        _db = firestore.client()
    return _db
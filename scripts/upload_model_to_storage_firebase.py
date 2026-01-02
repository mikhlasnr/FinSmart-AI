"""
Script untuk upload model ke Firebase Storage menggunakan Firebase Admin SDK
"""

import os
import sys
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, storage

# Load .env file jika tersedia
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print("✅ Loaded environment variables from .env file")
except ImportError:
    pass

# Configuration
MODEL_DIR = Path(__file__).parent.parent / "finsmart-ai-finetuned-model"
PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID")
CREDENTIALS_PATH = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
STORAGE_PATH = "models/finsmart-ai-finetuned-model"


def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    try:
        firebase_admin.get_app()
        print("✅ Firebase Admin SDK already initialized")
        return
    except ValueError:
        pass

    if not PROJECT_ID:
        raise ValueError("FIREBASE_PROJECT_ID harus di-set di .env file")

    storage_bucket = f"{PROJECT_ID}.appspot.com"

    if CREDENTIALS_PATH and os.path.exists(CREDENTIALS_PATH):
        cred = credentials.Certificate(CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred, {'storageBucket': storage_bucket})
        print("✅ Firebase Admin SDK initialized with service account")
    else:
        firebase_admin.initialize_app(options={'storageBucket': storage_bucket})
        print("✅ Firebase Admin SDK initialized with default credentials")


def get_bucket():
    """Get Firebase Storage bucket (support kedua format)"""
    bucket_names = [
        f"{PROJECT_ID}.appspot.com",
        f"{PROJECT_ID}.firebasestorage.app"
    ]

    for bucket_name in bucket_names:
        try:
            bucket = storage.bucket(bucket_name)
            bucket.reload()
            print(f"✅ Found bucket: {bucket_name}")
            return bucket
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                continue
            raise

    raise Exception(
        f"Bucket tidak ditemukan. Pastikan Firebase Storage sudah diaktifkan:\n"
        f"https://console.firebase.google.com/project/{PROJECT_ID}/storage"
    )


def upload_model_to_storage():
    """Upload model directory ke Firebase Storage"""
    if not PROJECT_ID:
        print("❌ Error: FIREBASE_PROJECT_ID tidak di-set")
        print("   Set di .env file: FIREBASE_PROJECT_ID=YOUR_PROJECT_ID")
        return False

    if not MODEL_DIR.exists():
        print(f"❌ Error: Model directory tidak ditemukan: {MODEL_DIR}")
        return False

    try:
        initialize_firebase()
        bucket = get_bucket()

        print(f"\n📦 Uploading model to Firebase Storage: {STORAGE_PATH}/")
        print(f"   Source: {MODEL_DIR}")
        print(f"   Bucket: {bucket.name}\n")

        uploaded_files = 0
        for root, dirs, files in os.walk(MODEL_DIR):
            for file in files:
                local_path = Path(root) / file
                relative_path = local_path.relative_to(MODEL_DIR)
                blob_path = f"{STORAGE_PATH}/{relative_path}"

                blob = bucket.blob(blob_path)
                blob.upload_from_filename(str(local_path))

                uploaded_files += 1
                file_size_kb = local_path.stat().st_size / 1024
                print(f"   ✓ Uploaded: {blob_path} ({file_size_kb:.1f} KB)")

        print(f"\n✅ Successfully uploaded {uploaded_files} files!")
        print(f"📝 Model path: {STORAGE_PATH}/")
        return True

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error: {error_msg}")

        if "404" in error_msg or "bucket" in error_msg.lower():
            print("\n💡 Pastikan Firebase Storage sudah diaktifkan di Console")
            print(f"   https://console.firebase.google.com/project/{PROJECT_ID}/storage")
        elif "FIREBASE_PROJECT_ID" in error_msg:
            print("\n💡 Set FIREBASE_PROJECT_ID di .env file")
        else:
            print("\n💡 Pastikan:")
            print("   1. Firebase Storage sudah diaktifkan")
            print("   2. firebase-admin terinstall: pip install firebase-admin")
            print("   3. Authentication sudah setup (gcloud auth atau service account)")

        return False


if __name__ == "__main__":
    success = upload_model_to_storage()
    sys.exit(0 if success else 1)

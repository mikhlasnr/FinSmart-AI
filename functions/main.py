"""
Firebase Cloud Function untuk AI Essay Scoring
Menggunakan model fine-tuned dari Firebase Storage

Model Details:
- Base Model: sentence-transformers/all-MiniLM-L6-v2
- Fine-tuned dengan: Financial Literacy dataset (100 samples)
- Training: 10 epochs, batch size 16, CosineSimilarityLoss
- Performance: Correlation 0.8904 (improvement +67.05% dari pre-trained)
- Model Path: ./finsmart-finetuned-model (disimpan di Firebase Storage)

Notebook Reference: finetuning-model.ipynb
"""

from firebase_functions import https_fn
from firebase_functions.options import set_global_options
# Defer import firebase_admin dan sentence_transformers untuk avoid deployment timeout
# from firebase_admin import initialize_app, storage
# from sentence_transformers import SentenceTransformer, util
import json
import os

# Global options
set_global_options(max_instances=10, region="asia-southeast1")

# Initialize Firebase Admin (lazy - akan di-initialize saat diperlukan)
# initialize_app()  # Defer initialization untuk avoid deployment timeout

# Konfigurasi Firebase Storage
# Model disimpan di Firebase Storage setelah fine-tuning di notebook
# Path harus sama dengan yang digunakan saat upload
MODEL_STORAGE_PATH = "models/finsmart-ai-finetuned-model"  # Path di Firebase Storage (harus sama dengan saat upload)
LOCAL_MODEL_PATH = "/tmp/finsmart-model"  # Temporary path di Cloud Function

# Flag untuk track apakah model sudah di-download
_model_loaded = False
model = None


def load_model_from_firebase_storage():
    """
    Download model dari Firebase Storage dan load ke memory.
    Model hanya di-download sekali saat cold start.
    """
    global model, _model_loaded

    if _model_loaded and model is not None:
        return model

    print(f"Loading model from Firebase Storage: {MODEL_STORAGE_PATH}")

    try:
        # Import firebase_admin saat diperlukan (lazy import)
        from firebase_admin import initialize_app, storage, get_app

        # Initialize Firebase Admin jika belum
        try:
            get_app()
        except ValueError:
            initialize_app()

        # Get default bucket (Firebase Storage bucket)
        bucket = storage.bucket()

        # List semua file di folder model
        blobs = list(bucket.list_blobs(prefix=MODEL_STORAGE_PATH))

        if not blobs or all(blob.name.endswith('/') for blob in blobs):
            raise FileNotFoundError(f"Model tidak ditemukan di Firebase Storage: {MODEL_STORAGE_PATH}")

        # Create local directory
        os.makedirs(LOCAL_MODEL_PATH, exist_ok=True)

        # Download setiap file
        downloaded_files = []
        for blob in blobs:
            # Skip jika ini folder (blob.name ends with /)
            if blob.name.endswith('/'):
                continue

            # Get relative path dari MODEL_STORAGE_PATH
            relative_path = blob.name.replace(MODEL_STORAGE_PATH + "/", "")
            local_file_path = os.path.join(LOCAL_MODEL_PATH, relative_path)

            # Create directory jika perlu
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

            # Download file
            blob.download_to_filename(local_file_path)
            downloaded_files.append(blob.name)
            print(f"  ✅ Downloaded: {blob.name}")

        print(f"Downloaded {len(downloaded_files)} files from Firebase Storage")

        # Import SentenceTransformer saat diperlukan (lazy import)
        from sentence_transformers import SentenceTransformer

        # Load model dari local path
        model = SentenceTransformer(LOCAL_MODEL_PATH)
        _model_loaded = True
        print(f"✅ Model loaded from Firebase Storage successfully!")

        return model

    except Exception as e:
        import traceback
        error_msg = str(e)
        error_traceback = traceback.format_exc()
        print(f"❌ Error loading model from Firebase Storage: {error_msg}")
        print(f"Traceback: {error_traceback}")
        print("Falling back to HuggingFace pre-trained model...")
        try:
            # Import SentenceTransformer saat diperlukan (lazy import)
            from sentence_transformers import SentenceTransformer

            # Fallback ke pre-trained model
            model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            _model_loaded = True
            print("✅ Fallback model loaded successfully")
            return model
        except Exception as fallback_error:
            print(f"❌ Error loading fallback model: {fallback_error}")
            raise fallback_error


# Model akan di-load secara lazy saat function pertama kali dipanggil
# Tidak di-load saat deployment untuk avoid timeout
# model = load_model_from_firebase_storage()  # Commented out untuk avoid deployment timeout


def calculate_similarity(key_answer: str, student_answer: str) -> float:
    """
    Hitung cosine similarity antara key_answer dan student_answer
    menggunakan sentence embeddings dari model fine-tuned.

    Logic ini sama dengan yang digunakan di notebook finetuning-model.ipynb:
    1. Encode kedua teks menjadi embeddings menggunakan SentenceTransformer
    2. Hitung cosine similarity menggunakan util.cos_sim

    Returns:
        float: Similarity score antara 0.0 - 1.0
    """
    try:
        if not key_answer or not student_answer:
            return 0.0

        # Pastikan model sudah loaded
        global model
        if model is None:
            print("Model belum loaded, loading sekarang...")
            model = load_model_from_firebase_storage()

        # Encode kedua teks menjadi embeddings
        # Sama seperti di notebook: model.encode([text1, text2], convert_to_tensor=True)
        embeddings = model.encode([key_answer, student_answer], convert_to_tensor=True)

        # Import util saat diperlukan (lazy import)
        from sentence_transformers import util

        # Hitung cosine similarity
        # Sama seperti di notebook: util.cos_sim(embeddings[0], embeddings[1])
        similarity = util.cos_sim(embeddings[0], embeddings[1])

        return float(similarity.item())
    except Exception as e:
        import traceback
        print(f"❌ Error in calculate_similarity: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        # Return 0.0 jika ada error
        return 0.0


def calculate_final_score(similarity: float, max_score: int) -> int:
    """
    Konversi similarity score (0-1) menjadi final score (0-max_score).

    Di notebook, similarity dikonversi langsung: similarity * 100
    Tapi untuk production, kita gunakan scaling yang lebih fair berdasarkan
    hasil evaluasi model fine-tuned (correlation 0.8904, RMSE 17.88, MAE 15.02).

    Scaling Strategy:
    - similarity >= 0.85 -> 90-100% score (Perfect answers)
    - similarity >= 0.70 -> 70-89% score (Good answers)
    - similarity >= 0.55 -> 50-69% score (Partial answers)
    - similarity >= 0.40 -> 30-49% score (Weak answers)
    - similarity < 0.40 -> 0-29% score (Poor/Irrelevant answers)

    Args:
        similarity: Cosine similarity score dari model (0.0 - 1.0)
        max_score: Maximum score untuk pertanyaan ini

    Returns:
        int: Final score (0 - max_score)
    """
    if similarity >= 0.85:
        # Perfect answers: 90-100% of max_score
        percentage = 0.90 + (similarity - 0.85) * 0.67  # Maps 0.85-1.0 to 0.90-1.0
    elif similarity >= 0.70:
        # Good answers: 70-89% of max_score
        percentage = 0.70 + (similarity - 0.70) * 1.33  # Maps 0.70-0.85 to 0.70-0.90
    elif similarity >= 0.55:
        # Partial answers: 50-69% of max_score
        percentage = 0.50 + (similarity - 0.55) * 1.33  # Maps 0.55-0.70 to 0.50-0.70
    elif similarity >= 0.40:
        # Weak answers: 30-49% of max_score
        percentage = 0.30 + (similarity - 0.40) * 1.33  # Maps 0.40-0.55 to 0.30-0.50
    else:
        # Poor/Irrelevant answers: 0-29% of max_score
        percentage = similarity * 0.75  # Maps 0.0-0.40 to 0.0-0.30

    return round(min(percentage, 1.0) * max_score)


def create_response(data: dict, status: int = 200) -> https_fn.Response:
    """Helper untuk membuat response dengan CORS headers."""
    return https_fn.Response(
        json.dumps(data),
        status=status,
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        }
    )


# Function score_essay dihapus karena tidak digunakan
# Hanya score_exam yang digunakan oleh Next.js

@https_fn.on_request(memory=1024, timeout_sec=120, cors=True)
def score_exam(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP Cloud Function untuk scoring seluruh exam sekaligus.

    Input JSON:
    {
        "answers": [
            {
                "question_id": "exam1",
                "key_answer": "...",
                "student_answer": "...",
                "max_score": 20
            },
            ...
        ]
    }

    Output JSON:
    {
        "results": [
            {
                "question_id": "exam1",
                "similarity_score": 0.85,
                "final_score": 17,
                "max_score": 20
            },
            ...
        ],
        "total_score": 85,
        "total_max_score": 100,
        "status": "success"
    }
    """
    print(f"📥 score_exam called: method={req.method}")

    try:
        if req.method == "OPTIONS":
            print("✅ OPTIONS request - returning CORS headers")
            return create_response({}, 204)

        if req.method != "POST":
            print(f"❌ Invalid method: {req.method}")
            return create_response({"error": "Method not allowed", "status": "error"}, 405)
    except Exception as e:
        import traceback
        print(f"❌ Error in request handling: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return create_response({
            "error": f"Request handling error: {str(e)}",
            "status": "error"
        }, 500)

    try:
        print("📝 Parsing request JSON...")
        request_json = req.get_json(silent=True)

        if not request_json or "answers" not in request_json:
            print("❌ Invalid request: answers array is required")
            return create_response({"error": "answers array is required", "status": "error"}, 400)

        answers = request_json.get("answers", [])
        print(f"✅ Processing {len(answers)} answers...")
        results = []
        total_score = 0
        total_max_score = 0

        for answer in answers:
            question_id = answer.get("question_id", "")
            key_answer = answer.get("key_answer", "").strip()
            student_answer = answer.get("student_answer", "").strip()
            max_score = answer.get("max_score", 100)

            if not student_answer:
                similarity_score = 0.0
                final_score = 0
            else:
                similarity_score = calculate_similarity(key_answer, student_answer)
                final_score = calculate_final_score(similarity_score, max_score)

            results.append({
                "question_id": question_id,
                "similarity_score": round(similarity_score, 4),
                "final_score": final_score,
                "max_score": max_score
            })

            total_score += final_score
            total_max_score += max_score

        return create_response({
            "results": results,
            "total_score": total_score,
            "total_max_score": total_max_score,
            "status": "success"
        })

    except Exception as e:
        import traceback
        error_msg = str(e)
        error_traceback = traceback.format_exc()
        print(f"❌ Error processing exam: {error_msg}")
        print(f"Traceback: {error_traceback}")
        return create_response({
            "error": error_msg,
            "status": "error",
            "details": error_traceback if "DEBUG" in os.environ else None
        }, 500)

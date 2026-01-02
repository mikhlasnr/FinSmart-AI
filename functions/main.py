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
from firebase_admin import initialize_app, storage
from sentence_transformers import SentenceTransformer, util
import json
import os

# Global options
set_global_options(max_instances=10, region="asia-southeast1")

# Initialize Firebase Admin
initialize_app()

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

        # Load model dari local path
        model = SentenceTransformer(LOCAL_MODEL_PATH)
        _model_loaded = True
        print(f"✅ Model loaded from Firebase Storage successfully!")

        return model

    except Exception as e:
        print(f"❌ Error loading model from Firebase Storage: {e}")
        print("Falling back to HuggingFace pre-trained model...")
        # Fallback ke pre-trained model
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        _model_loaded = True
        return model


# Load model saat cold start
print("Initializing model...")
model = load_model_from_firebase_storage()


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
    if not key_answer or not student_answer:
        return 0.0

    # Pastikan model sudah loaded
    global model
    if model is None:
        model = load_model_from_firebase_storage()

    # Encode kedua teks menjadi embeddings
    # Sama seperti di notebook: model.encode([text1, text2], convert_to_tensor=True)
    embeddings = model.encode([key_answer, student_answer], convert_to_tensor=True)

    # Hitung cosine similarity
    # Sama seperti di notebook: util.cos_sim(embeddings[0], embeddings[1])
    similarity = util.cos_sim(embeddings[0], embeddings[1])

    return float(similarity.item())


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


@https_fn.on_request(memory=1024, timeout_sec=120, cors=True)  # 1GB memory untuk model, 2min timeout
def score_essay(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP Cloud Function untuk scoring satu essay.

    Input JSON:
    {
        "key_answer": "The correct answer text...",
        "student_answer": "Student's answer text...",
        "max_score": 20  // Optional, default 100
    }

    Output JSON:
    {
        "similarity_score": 0.85,
        "final_score": 17,
        "max_score": 20,
        "status": "success"
    }
    """
    # Handle preflight CORS request
    if req.method == "OPTIONS":
        return create_response({}, 204)

    # Hanya terima POST request
    if req.method != "POST":
        return create_response({"error": "Method not allowed", "status": "error"}, 405)

    try:
        # Parse request body
        request_json = req.get_json(silent=True)

        if not request_json:
            return create_response({"error": "Invalid JSON body", "status": "error"}, 400)

        key_answer = request_json.get("key_answer", "").strip()
        student_answer = request_json.get("student_answer", "").strip()
        max_score = request_json.get("max_score", 100)

        # Validasi input
        if not key_answer:
            return create_response({"error": "key_answer is required", "status": "error"}, 400)

        if not student_answer:
            # Jika tidak ada jawaban, return score 0
            return create_response({
                "similarity_score": 0.0,
                "final_score": 0,
                "max_score": max_score,
                "status": "success"
            })

        # Hitung similarity
        similarity_score = calculate_similarity(key_answer, student_answer)
        final_score = calculate_final_score(similarity_score, max_score)

        return create_response({
            "similarity_score": round(similarity_score, 4),
            "final_score": final_score,
            "max_score": max_score,
            "status": "success"
        })

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return create_response({"error": str(e), "status": "error"}, 500)


@https_fn.on_request(memory=512, timeout_sec=120, cors=True)
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
    if req.method == "OPTIONS":
        return create_response({}, 204)

    if req.method != "POST":
        return create_response({"error": "Method not allowed", "status": "error"}, 405)

    try:
        request_json = req.get_json(silent=True)

        if not request_json or "answers" not in request_json:
            return create_response({"error": "answers array is required", "status": "error"}, 400)

        answers = request_json.get("answers", [])
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
        print(f"Error processing exam: {str(e)}")
        return create_response({"error": str(e), "status": "error"}, 500)

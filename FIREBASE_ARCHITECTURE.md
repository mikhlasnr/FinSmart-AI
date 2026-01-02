# 🏗️ Arsitektur Firebase: Functions & Storage

## ✅ Ya, kita menggunakan **Firebase Cloud Functions** dan **Firebase Storage**

---

## 📊 Overview Arsitektur

```
┌─────────────────────────────────────────────────────────┐
│                    NEXT.JS APP                          │
│  (FinSmart Frontend)                                     │
└──────────────────┬──────────────────────────────────────┘
                   │
                   │ HTTP Request
                   │ POST /api/score-exam
                   ▼
┌─────────────────────────────────────────────────────────┐
│              FIREBASE CLOUD FUNCTIONS                   │
│  (Gen 2 - Python)                                       │
│  Function: score_exam                                   │
│                                                         │
│  1. Download model dari Storage (cold start)           │
│  2. Load model ke memory                                │
│  3. Process scoring dengan AI model                     │
│  4. Return results                                      │
└──────────────────┬──────────────────────────────────────┘
                   │
                   │ Download model files
                   │ (saat cold start)
                   ▼
┌─────────────────────────────────────────────────────────┐
│              FIREBASE STORAGE                           │
│  Bucket: YOUR_PROJECT_ID.appspot.com                   │
│                                                         │
│  Path: models/finsmart-ai-finetuned-model/              │
│  - model.safetensors (87MB)                            │
│  - config.json                                          │
│  - tokenizer.json                                       │
│  - vocab.txt                                            │
│  - dll.                                                 │
└─────────────────────────────────────────────────────────┘
```

---

## 🔧 Firebase Cloud Functions (Gen 2)

### Fungsi:
- ✅ Menjalankan model AI untuk scoring essay
- ✅ Menerima request dari Next.js API route
- ✅ Memproses jawaban siswa dan menghitung similarity score
- ✅ Mengembalikan hasil scoring

### Lokasi:
- **File**: `FinSmart-AI/functions/main.py`
- **Function Name**: `score_exam`
- **Runtime**: Python 3.11
- **Memory**: 1GB
- **Timeout**: 120 detik
- **Region**: asia-southeast1

### Dependencies:
```python
from firebase_functions import https_fn  # Gen 2 Functions
from firebase_admin import initialize_app, storage  # Admin SDK
```

### Endpoints:
1. **`score_essay`** - Scoring satu essay (single answer)
2. **`score_exam`** - Scoring seluruh exam sekaligus (batch)

---

## 💾 Firebase Storage

### Fungsi:
- ✅ Menyimpan model AI yang sudah di-train
- ✅ Model di-download oleh Cloud Function saat cold start
- ✅ Model terpisah dari function code (lebih scalable)

### Lokasi:
- **Bucket**: `YOUR_PROJECT_ID.appspot.com`
- **Path**: `models/finsmart-ai-finetuned-model/`
- **Files**: Semua file model (model.safetensors, config.json, dll.)

### Upload Model:
```bash
# Menggunakan script
python scripts/upload_model_to_storage.py upload
```

### Download oleh Function:
```python
# Di functions/main.py
bucket = storage.bucket()  # Firebase Storage bucket
blobs = bucket.list_blobs(prefix=MODEL_STORAGE_PATH)
# Download semua file model ke /tmp/
```

---

## 🔄 Flow Lengkap

### 1. **Setup Phase**
```
User → Upload model ke Firebase Storage
      (menggunakan scripts/upload_model_to_storage.py)
```

### 2. **Deployment Phase**
```
Developer → Deploy Cloud Function
           (firebase deploy --only functions:score_exam)
```

### 3. **Runtime Phase (Cold Start)**
```
Request → Cloud Function
         → Download model dari Storage
         → Load model ke memory
         → Ready to process
```

### 4. **Runtime Phase (Warm Start)**
```
Request → Cloud Function
         → Model sudah di memory (cached)
         → Process immediately
```

### 5. **Scoring Phase**
```
Next.js → POST /api/score-exam
        → Cloud Function (score_exam)
        → Process dengan AI model
        → Return results
        → Next.js save ke Firestore
```

---

## 📦 Services yang Digunakan

| Service | Fungsi | Lokasi |
|---------|--------|--------|
| **Firebase Cloud Functions** | Menjalankan model AI | `functions/main.py` |
| **Firebase Storage** | Menyimpan model | `models/finsmart-ai-finetuned-model/` |
| **Firestore** | Menyimpan hasil exam | (di Next.js app) |

---

## 🔍 Detail Implementasi

### Firebase Cloud Functions

**File**: `FinSmart-AI/functions/main.py`

```python
from firebase_functions import https_fn  # Gen 2
from firebase_admin import initialize_app, storage

# Initialize Firebase Admin
initialize_app()

# Download model dari Storage
bucket = storage.bucket()
blobs = bucket.list_blobs(prefix="models/finsmart-ai-finetuned-model/")
# ... download files ...

# Function handler
@https_fn.on_request(memory=1024, timeout_sec=120, cors=True)
def score_exam(req: https_fn.Request):
    # Process scoring
    ...
```

### Firebase Storage

**Upload**: `scripts/upload_model_to_storage.py`

```python
from google.cloud import storage

client = storage.Client(project=PROJECT_ID)
bucket = client.bucket(BUCKET_NAME)

# Upload model files
for file in model_files:
    blob = bucket.blob(f"models/finsmart-ai-finetuned-model/{file}")
    blob.upload_from_filename(local_path)
```

**Download**: `functions/main.py` (otomatis saat cold start)

```python
bucket = storage.bucket()  # Firebase Storage
blobs = bucket.list_blobs(prefix=MODEL_STORAGE_PATH)
for blob in blobs:
    blob.download_to_filename(local_path)
```

---

## 💰 Cost Breakdown

### Firebase Cloud Functions:
- **Invocations**: $0.40 per 1M requests
- **Compute**: $0.0000025 per GB-second
- **Memory**: 1GB (untuk model)

### Firebase Storage:
- **Storage**: $0.026 per GB/month
- **Model size**: ~87MB
- **Cost**: ~$0.002/month

### Total untuk 1000 requests/bulan:
- Functions: ~$0.008
- Storage: ~$0.002
- **Total: ~$0.01/bulan** ✅

---

## ✅ Keuntungan Arsitektur Ini

### 1. **Scalability**
- ✅ Model terpisah dari function code
- ✅ Update model tanpa re-deploy function
- ✅ Function size kecil (deploy cepat)

### 2. **Cost Efficiency**
- ✅ Pay per use (serverless)
- ✅ Model di Storage (murah)
- ✅ Function hanya jalan saat ada request

### 3. **Maintainability**
- ✅ Model management terpisah
- ✅ Easy to update model
- ✅ Version control untuk model

### 4. **Performance**
- ✅ Model cached di memory setelah cold start
- ✅ Warm start sangat cepat
- ✅ Batch processing support

---

## 🔐 Security

### Firebase Cloud Functions:
- ✅ CORS enabled untuk Next.js domain
- ✅ HTTPS only
- ✅ Authentication bisa ditambahkan jika perlu

### Firebase Storage:
- ✅ Private by default
- ✅ Hanya bisa diakses oleh Cloud Function (via Admin SDK)
- ✅ Tidak publicly accessible

---

## 📚 Referensi

- [Firebase Cloud Functions Gen 2](https://firebase.google.com/docs/functions/2nd-gen)
- [Firebase Storage](https://firebase.google.com/docs/storage)
- [Firebase Admin SDK](https://firebase.google.com/docs/admin/setup)

---

## 🎯 Kesimpulan

**Ya, kita menggunakan:**
1. ✅ **Firebase Cloud Functions (Gen 2)** - Untuk menjalankan model AI
2. ✅ **Firebase Storage** - Untuk menyimpan model AI

**Alasan:**
- Scalable dan serverless
- Cost efficient
- Easy to maintain
- Best practices untuk production


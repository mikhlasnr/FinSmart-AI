# 🔐 Setup Environment Variables untuk Upload Model

## 📋 Environment Variables yang Diperlukan

Script `upload_model_to_storage.py` memerlukan environment variables berikut:

1. **`FIREBASE_STORAGE_BUCKET`** - Nama bucket Firebase Storage
2. **`FIREBASE_PROJECT_ID`** - Project ID Firebase Anda
3. **`GOOGLE_APPLICATION_CREDENTIALS`** - (Optional) Path ke service account key

---

## 🎯 Opsi 1: Menggunakan Environment Variables di Terminal (Recommended untuk Testing)

### Setup di Terminal (Mac/Linux)

```bash
# Set environment variables
export FIREBASE_STORAGE_BUCKET="YOUR_PROJECT_ID.appspot.com"
export FIREBASE_PROJECT_ID="YOUR_PROJECT_ID"

# Verifikasi
echo $FIREBASE_STORAGE_BUCKET
echo $FIREBASE_PROJECT_ID
```

**Ganti `YOUR_PROJECT_ID` dengan project ID Firebase Anda.**

**Cara mendapatkan Project ID:**
1. Buka [Firebase Console](https://console.firebase.google.com/)
2. Pilih project Anda
3. Klik ⚙️ (Settings) → **Project settings**
4. Copy **Project ID**

### Menjalankan Script

```bash
cd FinSmart-AI
python scripts/upload_model_to_storage.py upload
```

**Catatan:** Environment variables ini hanya berlaku untuk session terminal saat ini. Jika tutup terminal, perlu set lagi.

---

## 🎯 Opsi 2: Menggunakan .env File (Recommended untuk Development)

### 2.1 Buat File `.env` di Root `FinSmart-AI/`

```bash
cd FinSmart-AI
touch .env
```

### 2.2 Isi File `.env`

Edit file `.env` dengan content:

```env
# Firebase Configuration
FIREBASE_STORAGE_BUCKET=YOUR_PROJECT_ID.appspot.com
FIREBASE_PROJECT_ID=YOUR_PROJECT_ID

# Optional: Service Account Key (jika menggunakan service account)
# GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account-key.json
```

**Ganti `YOUR_PROJECT_ID` dengan project ID Firebase Anda.**

**Contoh:**
```env
FIREBASE_STORAGE_BUCKET=finsmart-project.appspot.com
FIREBASE_PROJECT_ID=finsmart-project
```

### 2.3 Update Script untuk Load .env File

Edit `scripts/upload_model_to_storage.py` dan tambahkan di bagian atas:

```python
import os
import sys
from pathlib import Path
from google.cloud import storage
from google.oauth2 import service_account
import json
from dotenv import load_dotenv  # Tambahkan ini

# Load .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)  # Tambahkan ini

# Path ke model yang sudah di-train
MODEL_DIR = Path(__file__).parent.parent / "finsmart-ai-finetuned-model"
BUCKET_NAME = os.environ.get("FIREBASE_STORAGE_BUCKET")
PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID")
```

### 2.4 Install python-dotenv

```bash
pip install python-dotenv
```

### 2.5 Update requirements.txt (Opsional)

Jika ingin, tambahkan ke `requirements.txt`:
```txt
python-dotenv>=1.0.0
```

### 2.6 Menjalankan Script

```bash
cd FinSmart-AI
python scripts/upload_model_to_storage.py upload
```

**Keuntungan:** Environment variables tersimpan di file, tidak perlu set setiap kali.

---

## 🎯 Opsi 3: Menggunakan Service Account Key (Recommended untuk Production/CI/CD)

### 3.1 Buat Service Account

1. Buka [Google Cloud Console](https://console.cloud.google.com/)
2. Pilih project Firebase Anda
3. Masuk ke **IAM & Admin** → **Service Accounts**
4. Klik **Create Service Account**
5. Isi:
   - **Name**: `finsmart-storage-uploader`
   - **Description**: `Service account untuk upload model ke Storage`
6. Klik **Create and Continue**
7. **Grant access**: Pilih role **Storage Admin**
8. Klik **Done**

### 3.2 Download Service Account Key

1. Klik service account yang baru dibuat
2. Tab **Keys** → **Add Key** → **Create new key**
3. Pilih **JSON**
4. Download file JSON (contoh: `finsmart-storage-key.json`)

### 3.3 Simpan Key File

**⚠️ PENTING: Jangan commit file key ke git!**

```bash
# Simpan di folder yang tidak di-track git
mkdir -p FinSmart-AI/.secrets
mv ~/Downloads/finsmart-storage-key.json FinSmart-AI/.secrets/
```

### 3.4 Update .gitignore

Pastikan `.gitignore` sudah include:

```gitignore
# Secrets
.secrets/
*.json
!package.json
!tsconfig.json
```

### 3.5 Set Environment Variable

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/FinSmart-AI/.secrets/finsmart-storage-key.json"
```

**Atau di `.env` file:**
```env
GOOGLE_APPLICATION_CREDENTIALS=.secrets/finsmart-storage-key.json
```

### 3.6 Menjalankan Script

```bash
cd FinSmart-AI
python scripts/upload_model_to_storage.py upload
```

---

## 🔍 Verifikasi Setup

### Test Environment Variables

```bash
# Cek apakah environment variables sudah di-set
echo $FIREBASE_STORAGE_BUCKET
echo $FIREBASE_PROJECT_ID
echo $GOOGLE_APPLICATION_CREDENTIALS  # Optional
```

### Test Script

```bash
cd FinSmart-AI
python scripts/upload_model_to_storage.py upload
```

**Expected output:**
```
📦 Uploading model to: gs://YOUR_PROJECT_ID.appspot.com/models/finsmart-ai-finetuned-model/
   Source: /path/to/finsmart-ai-finetuned-model
   ✓ Uploaded: model.safetensors (87000.0 KB)
   ✓ Uploaded: config.json (0.7 KB)
   ...
✅ Successfully uploaded X files!
```

---

## 📝 Quick Start (Paling Mudah)

### Untuk Testing Cepat:

```bash
# 1. Set environment variables
export FIREBASE_STORAGE_BUCKET="YOUR_PROJECT_ID.appspot.com"
export FIREBASE_PROJECT_ID="YOUR_PROJECT_ID"

# 2. Login ke gcloud (untuk authentication)
gcloud auth application-default login

# 3. Run script
cd FinSmart-AI
python scripts/upload_model_to_storage.py upload
```

**Ganti `YOUR_PROJECT_ID` dengan project ID Firebase Anda.**

---

## 🎯 Rekomendasi

### Untuk Development:
- ✅ **Opsi 1** (Terminal export) - Cepat untuk testing
- ✅ **Opsi 2** (.env file) - Lebih praktis, tersimpan

### Untuk Production/CI/CD:
- ✅ **Opsi 3** (Service Account) - Lebih secure, bisa di-automate

---

## ❓ Troubleshooting

### Error: FIREBASE_STORAGE_BUCKET not set

**Solusi:**
```bash
export FIREBASE_STORAGE_BUCKET="YOUR_PROJECT_ID.appspot.com"
```

### Error: Authentication failed

**Solusi:**
```bash
# Login ke gcloud
gcloud auth application-default login

# Atau set service account key
export GOOGLE_APPLICATION_CREDENTIALS="path/to/key.json"
```

### Error: Bucket not found

**Solusi:**
1. Pastikan Firebase Storage sudah diaktifkan
2. Pastikan format bucket name benar: `YOUR_PROJECT_ID.appspot.com`
3. Cek di Firebase Console → Storage

### Error: Permission denied

**Solusi:**
1. Pastikan service account memiliki role **Storage Admin**
2. Atau pastikan user yang login memiliki akses ke Storage

---

## 📚 Referensi

- [Firebase Storage Docs](https://firebase.google.com/docs/storage)
- [Google Cloud Storage Authentication](https://cloud.google.com/storage/docs/authentication)
- [python-dotenv Docs](https://pypi.org/project/python-dotenv/)


# FinSmart AI - Model Training & Deployment

## 📁 Struktur Project

```
FinSmart-AI/
├── finsmart-ai-model.ipynb          # Notebook untuk training model
├── finsmart-ai-finetuned-model/    # Model yang sudah di-train (tidak di-commit)
├── functions/                        # Firebase Cloud Functions (Gen 2)
│   ├── main.py                       # Function handler
│   └── requirements.txt               # Dependencies
├── scripts/
│   └── upload_model_to_storage_firebase.py  # Script upload model ke Storage
├── dataset/                           # Training data
├── firebase.json                     # Firebase config
└── STEP_BY_STEP_INTEGRATION.md      # 📖 Panduan lengkap deployment
```

---

## 🚀 Quick Start

### 1. Training Model
Jalankan notebook `finsmart-ai-model.ipynb` untuk training model.

### 2. Deploy ke Firebase
Ikuti panduan di **`STEP_BY_STEP_INTEGRATION.md`** untuk:
- Upload model ke Firebase Storage
- Deploy Cloud Function
- Integrasi dengan Next.js

---

## 📖 Dokumentasi

- **`STEP_BY_STEP_INTEGRATION.md`** ⭐ - **Panduan lengkap step-by-step untuk deployment & integrasi**
- **`ENV_SETUP.md`** - Setup environment variables (.env file)
- **`FIREBASE_ARCHITECTURE.md`** - Arsitektur Firebase (Functions & Storage)

---

## 🔧 Requirements

- Python 3.11+
- Firebase CLI
- Firebase project dengan Blaze plan

---

## 📝 Model Details

- **Base Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Performance**: Correlation 0.8878, R² 0.7552
- **Training**: 10 epochs, batch size 16

---

## ✅ Status

- ✅ Model sudah di-train
- ✅ Model sudah di-upload ke Firebase Storage
- ⏳ Cloud Function siap untuk deploy
- ⏳ Integrasi dengan Next.js siap

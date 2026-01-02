# 📝 Step-by-Step: Integrasi FinSmart AI dengan Next.js

## 🎯 Tujuan
Deploy model AI ke Firebase Cloud Functions dan integrasikan dengan aplikasi Next.js FinSmart.

---

## ✅ Checklist Persiapan

Sebelum mulai, pastikan:
- [ ] Firebase project sudah dibuat
- [ ] Firebase CLI terinstall (`npm install -g firebase-tools`)
- [ ] Python 3.11+ terinstall
- [ ] Model sudah di-train (`finsmart-ai-finetuned-model/` ada)
- [ ] Login ke Firebase (`firebase login`)

---

## Step 1: Setup Firebase Project (5 menit)

### 1.1 Login ke Firebase
```bash
firebase login
```

### 1.2 Pilih Project
```bash
cd FinSmart-AI
firebase use YOUR_PROJECT_ID
```

**Ganti `YOUR_PROJECT_ID` dengan project ID Firebase Anda.**

### 1.3 Aktifkan Services di Firebase Console

Buka [Firebase Console](https://console.firebase.google.com/) → Pilih project Anda:

**A. Storage:**
1. Klik **Storage** → **Get Started**
2. Pilih **Production mode**
3. Pilih location: **asia-southeast1**
4. Klik **Done**

**B. Functions:**
1. Klik **Functions** → **Get Started**
2. Enable Cloud Functions API (jika diminta)
3. **PENTING**: Pastikan billing sudah diaktifkan (Blaze plan)

---

## Step 2: Upload Model ke Firebase Storage (10 menit)

### 2.1 Aktifkan Firebase Storage

**Di Firebase Console:**
1. Buka [Firebase Console](https://console.firebase.google.com/)
2. Pilih project Anda
3. Klik **Storage** → **Get Started**
4. Pilih **Production mode** → Location: **asia-southeast1**
5. Klik **Done**

### 2.2 Install Dependencies
```bash
pip install firebase-admin python-dotenv
```

### 2.3 Set Environment Variables

**Opsi A: Terminal (Sementara)**
```bash
export FIREBASE_PROJECT_ID="YOUR_PROJECT_ID"
```

**Opsi B: .env File (Permanen - Recommended)**
```bash
cd FinSmart-AI
touch .env
```

Edit `.env`:
```env
FIREBASE_PROJECT_ID=YOUR_PROJECT_ID
```

### 2.4 Setup Authentication
```bash
# Login ke gcloud
gcloud auth application-default login

# Set project
gcloud config set project YOUR_PROJECT_ID
```

**Ganti `YOUR_PROJECT_ID` dengan project ID Anda.**

### 2.5 Upload Model
```bash
cd FinSmart-AI
python scripts/upload_model_to_storage_firebase.py upload
```

**Catatan:** Gunakan script `upload_model_to_storage_firebase.py` yang menggunakan Firebase Admin SDK (lebih native untuk Firebase).

**Output yang diharapkan:**
```
📦 Uploading model to: gs://YOUR_PROJECT_ID.appspot.com/models/finsmart-ai-finetuned-model/
   ✓ Uploaded: model.safetensors
   ✓ Uploaded: config.json
   ...
✅ Successfully uploaded X files!
```

### 2.4 Verifikasi Upload
```bash
gsutil ls -r gs://YOUR_PROJECT_ID.appspot.com/models/finsmart-ai-finetuned-model/
```

**Pastikan file-file berikut ada:**
- `model.safetensors` (file terbesar ~87MB)
- `config.json`
- `tokenizer.json`
- `vocab.txt`
- `modules.json`
- dll.

---

## Step 3: Setup Cloud Functions (5 menit)

### 3.1 Install Dependencies
```bash
cd FinSmart-AI/functions
pip install -r requirements.txt
```

**Ini akan install:**
- firebase-functions
- firebase-admin
- sentence-transformers
- torch
- dll.

**Catatan:** Install bisa memakan waktu 5-10 menit karena model dependencies besar.

### 3.2 Verifikasi Konfigurasi

Pastikan file berikut ada dan benar:

**`FinSmart-AI/firebase.json`:**
```json
{
  "functions": [
    {
      "source": "functions",
      "codebase": "default",
      "runtime": "python311"
    }
  ]
}
```

**`FinSmart-AI/functions/main.py`:**
- Pastikan `MODEL_STORAGE_PATH = "models/finsmart-ai-finetuned-model"`

---

## Step 4: Deploy Cloud Function (10 menit)

### 4.1 Deploy
```bash
cd FinSmart-AI
firebase deploy --only functions:score_exam
```

**Output yang diharapkan:**
```
✔  functions[score_exam(asia-southeast1)] Successful create operation.
Function URL: https://asia-southeast1-YOUR_PROJECT_ID.cloudfunctions.net/score_exam
```

**⚠️ PENTING: Copy URL function ini!**

### 4.2 Verifikasi Deployment

Buka [Firebase Console](https://console.firebase.google.com/) → **Functions**:
- Harus ada function `score_exam` dengan status **Active**

---

## Step 5: Integrasi dengan Next.js (5 menit)

### 5.1 Update Environment Variable

Edit file `FinSmart/.env.local`:

```env
AI_SCORING_URL=https://asia-southeast1-YOUR_PROJECT_ID.cloudfunctions.net/score_exam
```

**Ganti `YOUR_PROJECT_ID` dengan project ID Anda.**

**Jika file `.env.local` belum ada, buat file baru.**

### 5.2 Verifikasi API Route

File `FinSmart/app/api/score-exam/route.ts` sudah siap dan akan:
- ✅ Memanggil Cloud Function dari `AI_SCORING_URL`
- ✅ Fallback ke simple similarity jika Cloud Function gagal
- ✅ Return response dalam format yang diharapkan

**Tidak perlu edit file ini jika sudah sesuai.**

---

## Step 6: Testing (10 menit)

### 6.1 Test Cloud Function Langsung

```bash
curl -X POST https://asia-southeast1-YOUR_PROJECT_ID.cloudfunctions.net/score_exam \
  -H "Content-Type: application/json" \
  -d '{
    "answers": [
      {
        "question_id": "test1",
        "key_answer": "Zero-based budgeting means allocating every unit of income to a specific purpose.",
        "student_answer": "In zero-based budgeting, you assign every dollar of income to specific categories.",
        "max_score": 100
      }
    ]
  }'
```

**Expected response:**
```json
{
  "results": [
    {
      "question_id": "test1",
      "similarity_score": 0.6982,
      "final_score": 74.77,
      "max_score": 100
    }
  ],
  "total_score": 74.77,
  "total_max_score": 100,
  "status": "success"
}
```

**Jika dapat response seperti ini, Cloud Function berfungsi! ✅**

### 6.2 Test dari Next.js App

```bash
cd FinSmart
npm run dev
```

**Test flow:**
1. Buka browser: `http://localhost:3000`
2. Login ke aplikasi
3. Buka **Modules** → Pilih module → **Exam**
4. Isi jawaban untuk semua pertanyaan
5. Klik **Submit Exam**
6. **Cek hasil:**
   - Harus muncul score dan hasil detail
   - Cek browser console (F12) untuk melihat response dari API
   - Pastikan tidak ada error

**Jika hasil scoring muncul dengan benar, integrasi berhasil! ✅**

---

## 🔧 Troubleshooting

### ❌ Error: Model not found di Storage

**Solusi:**
1. Verifikasi model sudah di-upload:
   ```bash
   gsutil ls -r gs://YOUR_PROJECT_ID.appspot.com/models/finsmart-ai-finetuned-model/
   ```

2. Pastikan path di `functions/main.py` benar:
   ```python
   MODEL_STORAGE_PATH = "models/finsmart-ai-finetuned-model"
   ```

3. Pastikan Firebase Admin SDK sudah di-initialize di `main.py`:
   ```python
   initialize_app()  # Harus ada di awal file
   ```

### ❌ Error: Function timeout

**Solusi:**
- Function sudah dikonfigurasi dengan timeout 120 detik
- Jika masih timeout, cek logs: `firebase functions:log`
- Pertimbangkan setup min instances untuk avoid cold start

### ❌ Error: CORS di browser

**Solusi:**
- CORS sudah di-handle dengan `cors=True` di decorator
- Pastikan request dari domain yang benar
- Cek browser console untuk error detail

### ❌ Error: Memory limit exceeded

**Solusi:**
- Function sudah dikonfigurasi 1GB memory
- Jika masih error, bisa increase ke 2GB di `main.py`:
  ```python
  @https_fn.on_request(memory=2048, timeout_sec=120, cors=True)
  ```

### ❌ Error: Module not found saat deploy

**Solusi:**
1. Pastikan semua dependencies terinstall:
   ```bash
   cd functions
   pip install -r requirements.txt
   ```

2. Pastikan `requirements.txt` lengkap

### ❌ Next.js tidak bisa connect ke Cloud Function

**Solusi:**
1. Pastikan `.env.local` sudah di-update dengan URL yang benar
2. Restart Next.js dev server setelah update `.env.local`
3. Pastikan URL format benar: `https://asia-southeast1-...`
4. Cek apakah Cloud Function sudah deployed dan active

---

## 📊 Monitoring

### View Logs
```bash
firebase functions:log
```

### Atau di Firebase Console
1. Buka [Firebase Console](https://console.firebase.google.com/)
2. **Functions** → **score_exam** → **Logs**
3. Lihat logs untuk debugging

### Monitor Metrics
1. **Functions** → **score_exam** → **Metrics**
2. Monitor: Invocations, Errors, Latency, Memory usage

---

## ✅ Final Checklist

Setelah semua step selesai, pastikan:

- [ ] Model sudah di-upload ke Firebase Storage
- [ ] Cloud Function sudah deployed dan active
- [ ] URL function sudah di-copy
- [ ] `.env.local` sudah di-update dengan URL function
- [ ] Test Cloud Function langsung berhasil
- [ ] Test dari Next.js app berhasil
- [ ] Hasil scoring muncul dengan benar di UI

---

## 🎉 Selesai!

Jika semua checklist terpenuhi, integrasi sudah selesai!

**Next Steps:**
1. Monitor performance di Firebase Console
2. Setup alerting untuk errors
3. Collect feedback untuk improve model
4. Optimize cold start jika perlu

---

## 📞 Need Help?

Jika ada masalah:
1. Cek logs: `firebase functions:log`
2. Cek Firebase Console → Functions → Logs
3. Verifikasi semua step sudah dilakukan dengan benar
4. Pastikan semua environment variables sudah di-set

---

## 📚 Dokumentasi Tambahan

- **`ENV_SETUP.md`** - Setup environment variables (.env file)
- **`FIREBASE_ARCHITECTURE.md`** - Arsitektur Firebase (Functions & Storage)

## 📚 Referensi External

- [Firebase Functions Docs](https://firebase.google.com/docs/functions/2nd-gen)
- [Firebase Storage Docs](https://firebase.google.com/docs/storage)
- [Firebase Admin SDK](https://firebase.google.com/docs/admin/setup)


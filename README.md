
# QuickForm

QuickForm is a tool that automatically generates Google Forms quizzes from images or text using OCR and Gemini AI.

---

## 📦 Features

- Upload worksheet images or paste text
- Extracts questions using OCR (EasyOCR)
- Uses Gemini API to convert to quiz questions
- Auto-creates Google Forms quizzes with validation
- Supports multiple-choice, checkbox, and short answer
- Fully Python-based backend (Flask)

---

## ⚙️ Setup

1. **Clone the repo**

```bash
git clone https://github.com/yourusername/quickform.git
cd quickform
```

2. **Create a virtual environment**

```bash
python3 -m venv .venv
source .venv/bin/activate  # For Windows: .venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Create your `.env` file**

```
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GEMINI_API_KEY=your_gemini_api_key
```
You must also create OAuth credentials in Google Cloud and download the `credentials.json`.

5. **Run the app**

```bash
python backend.py
```

The app runs on `http://localhost:5000`

---

## 🧠 Technologies

- Python 3.9+
- Flask
- Google Forms API
- EasyOCR
- Gemini Pro Vision API (text & image input)
- 

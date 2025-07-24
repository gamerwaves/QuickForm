from flask import Flask, request, jsonify, render_template
from backend import generateFormQuestions, create_form_with_questions
import numpy as np
import cv2

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # limit file size

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/generate", methods=["POST"])
def generate():
    # Handle both JSON and form data
    if request.content_type and 'application/json' in request.content_type:
        data = request.get_json()
        access_token = data.get("accessToken")
        amount = data.get("amount", 5)
        difficulty = data.get("difficulty", "medium")
        topic = data.get("topic", "General Knowledge")
        language = data.get("language", "English")
        questionType = data.get("questionType", "ai_choice")
        is_quiz = data.get("isQuiz", True)
        image = None
    else:
        # Handle form data with file upload
        access_token = request.form.get("accessToken")
        amount = int(request.form.get("amount", 5))
        difficulty = request.form.get("difficulty", "medium")
        topic = request.form.get("topic", "General Knowledge")
        language = request.form.get("language", "English")
        questionType = request.form.get("questionType", "ai_choice")
        # Fix checkbox handling - if checkbox is checked, it sends "on", if unchecked, it's None
        is_quiz = request.form.get("isQuiz") is not None
        
        # Handle image upload
        image = None
        if "image" in request.files:
            image_file = request.files["image"]
            if image_file.filename != '':
                file_bytes = np.frombuffer(image_file.read(), np.uint8)
                image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    if not access_token:
        return jsonify({"error": "Missing access token"}), 401

    form_data = generateFormQuestions(amount, difficulty, topic, language, questionType, is_quiz, image)
    if not form_data or not form_data.get("questions"):
        return jsonify({"error": "Failed to generate questions"}), 500

    form_id = create_form_with_questions(form_data, access_token=access_token, shuffle=True, is_quiz=is_quiz)
    if not form_id:
        return jsonify({"error": "Failed to create Google Form"}), 500

    return jsonify({
        "questions": form_data["questions"],
        "formUrl": f"https://docs.google.com/forms/d/{form_id}/edit"
    })

if __name__ == "__main__":
    app.run(debug=True, port=37121)
from flask import Flask, request, jsonify, render_template
from backend import generateFormQuestions, create_form_with_questions


app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json()

    amount = data.get("amount", 5)
    difficulty = data.get("difficulty", "medium")
    topic = data.get("topic", "General Knowledge")
    language = data.get("language", "English")
    questionType = data.get("questionType", "ai_choice")
    is_quiz = data.get("isQuiz", True)

    form_data = generateFormQuestions(amount, difficulty, topic, language, questionType, is_quiz)
    form_id = create_form_with_questions(form_data, shuffle=True, is_quiz=is_quiz)

    return jsonify({
        "questions": form_data["questions"],
        "formUrl": f"https://docs.google.com/forms/d/{form_id}/edit"
    })


if __name__ == "__main__":
    app.run(debug=True)

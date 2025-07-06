import json, os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google import genai
from google.genai import types

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/forms.body"]
DISCOVERY_DOC = "https://forms.googleapis.com/$discovery/rest?version=v1"

# Gemini setup
genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def get_form_service_from_token(access_token):
    creds = Credentials(token=access_token)
    return build(
        "forms",
        "v1",
        credentials=creds,
        discoveryServiceUrl=DISCOVERY_DOC,
        static_discovery=False,
    )

def generateFormQuestions(amount, difficulty, topic, language, questionType, isQuiz):
    prompt = f"""
In the entire text, if theres double outer curly braces, remove them, they never existed. They are for formatting purpouses. Generate {amount} Google Form questions with difficulty level {difficulty} about "{topic}" in "{language}". 
Use the question type "{questionType}". If the type is "ai-choice", pick and choose from based on the question:
Short Answer (SA), Long Answer (LA), Multiple Choice (MC), Checkbox - Has Multiple Answers (CB), Dropdown (DD), 
Linear Scale (LS), Rating (RT), Date (DT), Time (TT), else just use the question type provided by the user.

Your output must be a valid JSON object in this format:
{{
  "questions": ["Question 1", "Question 2", ...],
  "types": ["MC", "SA", ...],
  "answers": ["Answer 1", "Answer 2", ...]
}}

Rules:
- A phrase would be a short answer. If the text is longer than that, it should be a long answer.
- If isQuiz = {isQuiz} = true, include an "answers" key in the output.
  - For Multiple Choice, Checkbox, Dropdown, etc: format the answer for the question in the "answers" array as {{"Actual Answer": ["choice1", "choice2", "choice3", "choice4"]}}. Instead of "Actual Answers", use the actual answer.
  - For short/long answer or others without clear choices, you can use simple strings or null.
- If isQuiz = false, do not include the "answers" key at all — just return "questions" and "types", else explicitly include "answers". There should be no null values in the "answers" array.
This is invalid format: {{'Ice Hockey': ['Ice Hockey', 'Lacrosse', 'Basketball', 'Soccer'], 'Lacrosse': ['Ice Hockey', 'Lacrosse', 'Basketball', 'Soccer']}}
Only return valid JSON. No comments, no extra text, no markdown.
"""
    response = genai_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[{"parts": [{"text": prompt}]}],
    )
    try:
        return json.loads(response.text) if isinstance(response.text, str) else response.text
    except Exception as e:
        print("[!] Failed to parse Gemini response:", e)
        return {"questions": [], "types": [], "answers": []}

def create_form_with_questions(form_data, access_token, shuffle=True, is_quiz=True):
    form_service = get_form_service_from_token(access_token)
    form_title = "AI Generated Form"
    new_form = {"info": {"title": form_title}}

    try:
        result = form_service.forms().create(body=new_form).execute()
    except Exception as e:
        print("[!] Failed to create form:", e)
        return None

    form_id = result["formId"]

    if is_quiz:
        quiz_update = {
            "requests": [
                {
                    "updateSettings": {
                        "settings": {"quizSettings": {"isQuiz": True}},
                        "updateMask": "quizSettings.isQuiz",
                    }
                }
            ]
        }
        form_service.forms().batchUpdate(formId=form_id, body=quiz_update).execute()

    requests = []
    form_index = 0
    questions = form_data.get("questions", [])
    types = form_data.get("types", [])
    answers = form_data.get("answers", [])

    for i, question in enumerate(questions):
        q_type = types[i]
        answer = answers[i] if i < len(answers) else None

        item = {
            "title": question,
            "questionItem": {
                "question": {},
            }
        }

        grading = None

        if q_type in ["MC", "CB", "DD"]:
            if not isinstance(answer, dict) or len(answer) != 1:
                print(f"[!] Question {i+1} has invalid answer format: {answer}")
                continue

            correct, choices = list(answer.items())[0]

            qtype_map = {
                "MC": "RADIO",
                "CB": "CHECKBOX",
                "DD": "DROP_DOWN"
            }

            item["questionItem"]["question"]["choiceQuestion"] = {
                "type": qtype_map[q_type],
                "options": [{"value": c} for c in choices],
                "shuffle": shuffle
            }

            if is_quiz:
                correct_values = (
                    [v.strip() for v in correct.split(",")]
                    if isinstance(correct, str)
                    else correct if isinstance(correct, list)
                    else []
                )
                correct_values = [v for v in correct_values if v in choices]

                grading = {
                    "pointValue": 1,
                    "correctAnswers": {
                        "answers": [{"value": val} for val in correct_values]
                    },
                    "whenRight": {"text": "Correct!"},
                    "whenWrong": {"text": "Wrong answer."}
                }

        elif q_type == "SA":
            item["questionItem"]["question"]["textQuestion"] = {
                "paragraph": False
            }
            if is_quiz and isinstance(answer, str):
                grading = {
                    "pointValue": 1,
                    "correctAnswers": {
                        "answers": [{"value": answer}]
                    },
                    "generalFeedback": {"text": "Auto-graded short answer."}
                }

        elif q_type == "LA":
            item["questionItem"]["question"]["textQuestion"] = {
                "paragraph": True
            }

        else:
            print(f"[!] Question {i+1} has unsupported type '{q_type}'. Skipping.")
            continue

        if grading:
            item["questionItem"]["question"]["grading"] = grading

        question_data = item["questionItem"]["question"]
        if "grading" in question_data and not any(
            question_data.get(k) for k in ["choiceQuestion", "textQuestion", "rowQuestion"]
        ):
            item["questionItem"]["grading"] = question_data.pop("grading")

        requests.append({
            "createItem": {
                "item": item,
                "location": {"index": form_index}
            }
        })
        form_index += 1

    if not requests:
        print("[!] No questions to add, aborting.")
        return None

    try:
        response = form_service.forms().batchUpdate(formId=form_id, body={"requests": requests}).execute()
    except Exception as e:
        print("[!] Failed to add questions:", e)
        return None

    update_requests = []
    for reply in response.get("replies", []):
        item_id = reply.get("createItem", {}).get("item", {}).get("itemId")
        if item_id:
            update_requests.append({
                "updateItem": {
                    "item": {
                        "itemId": item_id,
                        "required": True
                    },
                    "updateMask": "required"
                }
            })

    if update_requests:
        try:
            form_service.forms().batchUpdate(formId=form_id, body={"requests": update_requests}).execute()
        except Exception as e:
            print("[!] Failed to update required status:", e)

    print(f"Form created: https://docs.google.com/forms/d/{form_id}/edit")
    return form_id

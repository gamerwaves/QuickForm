import json, os, re, time
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google import genai
from google.genai import types
import easyocr, cv2, io, base64
from PIL import Image

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



def generateFormQuestions(amount, difficulty, topic, language, questionType, isQuiz, image=None):
    global cropped
    print("[DEBUG] GENERATING QUESTIONS")
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

Rules
- A phrase would be a short answer. If the text is longer than that, it should be a long answer.
- If isQuiz = {isQuiz} = true, ALWAYS include an "answers" key in the output, especialy if it's SA and if not make the form like a survey or something. 
  - For Multiple Choice, Checkbox, Dropdown, etc: format the answer for the question in the "answers" array as {{"Actual Answer": ["choice1", "choice2", "choice3", "choice4"]}}. Instead of "Actual Answers", use the actual answer.
  - For short/long answer or others without clear choices, you can use simple strings or null.
- If isQuiz = false, do not include the "answers" key at all — just return "questions" and "types", else explicitly include "answers". There should be no null values in the "answers" array.
This is invalid format: {{'Ice Hockey': ['Ice Hockey', 'Lacrosse', 'Basketball', 'Soccer'], 'Lacrosse': ['Ice Hockey', 'Lacrosse', 'Basketball', 'Soccer']}}
Only return valid JSON. No comments, no extra text, no markdown.
"""
    
    if image is not None:
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(img_rgb)
        buffered = io.BytesIO()
        pil_image.save(buffered, format="JPEG")
        buffered.seek(0)
        image_upload = genai_client.files.upload(file=buffered, config={"mime_type": "image/jpeg"})
        prompt += " An image was uploaded. Use this image to follow users instructions and base your questions off of it."
        print("[DEBUG] IMAGE UPLOADED")
        
        # Proper content structure with image
        contents = [
            {
                "role": "user",
                "parts": [
                    {"file_data": {"file_uri": image_upload.uri, "mime_type": "image/jpeg"}},
                    {"text": prompt}
                ]
            }
        ]
    else:
        # Content structure without image
        contents = [
            {
                "role": "user", 
                "parts": [{"text": prompt}]
            }
        ]

    response = genai_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
    )
    try:
        print("[DEBUG] RAW GEMINI OUTPUT:", response.text)
        
        # Clean the response text to remove markdown code blocks
        response_text = response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]  # Remove ```json
        if response_text.startswith("```"):
            response_text = response_text[3:]   # Remove ```
        if response_text.endswith("```"):
            response_text = response_text[:-3]  # Remove trailing ```
        
        response_text = response_text.strip()
        
        return json.loads(response_text) if isinstance(response_text, str) else response_text
    except Exception as e:
        print("[!] Failed to parse Gemini response:", e)
        print("[!] Cleaned response text:", response_text if 'response_text' in locals() else 'N/A')
        return {"questions": [], "types": [], "answers": []}

def create_form_with_questions(form_data, access_token, shuffle=True, is_quiz=True):
    print("[DEBUG] CREATING FORM")
    form_service = get_form_service_from_token(access_token)
    form_title = "AI Generated Form"
    new_form = {"info": {"title": form_title}}
    print("[DEBUG] RAW GEMINI OUTPUT:", form_data)

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
                "question": {
                    "required": is_quiz  # Move required inside the question object
                },
            }
        }

        grading = None

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
                correct_values = []
                if isinstance(correct, str):
                    # Handle comma-separated values
                    correct_values = [v.strip() for v in correct.split(",")]
                elif isinstance(correct, list):
                    correct_values = correct
                
                # Filter to only include values that exist in choices
                correct_values = [v for v in correct_values if v in choices]

                if correct_values:
                    grading = {
                        "pointValue": 1,
                        "correctAnswers": {
                            "answers": [{"value": val} for val in correct_values]
                        },
                        "whenRight": {"text": "Correct!"},
                        "whenWrong": {"text": "Incorrect. The correct answer is: " + ", ".join(correct_values)}
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
                print("[DEBUG] PROVIDED ANSWERS:", answers)
            else:
                print("[!] No answers provided by gemini.")

        elif q_type == "LA":
            item["questionItem"]["question"]["textQuestion"] = {
                "paragraph": True
            }

        else:
            print(f"[!] Question {i+1} has unsupported type '{q_type}'. Skipping.")
            continue

        # Add grading to the question if it exists
        if grading:
            item["questionItem"]["question"]["grading"] = grading
        print(item)    

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
        print(f"Form created: https://docs.google.com/forms/d/{form_id}/edit")
        return form_id
    except Exception as e:
        print("[!] Failed to add questions:", e)
        return None
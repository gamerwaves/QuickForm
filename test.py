import json, os, re, time
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google import genai
from google.genai import types
import easyocr, cv2, io, base64
from PIL import Image

# 1. Create form
result = form_service.forms().create(body={"info": {"title": "Test Quiz"}}).execute()
form_id = result["formId"]

# 2. Enable quiz mode
form_service.forms().batchUpdate(formId=form_id, body={
    "requests": [
        {
            "updateSettings": {
                "settings": {"quizSettings": {"isQuiz": True}},
                "updateMask": "quizSettings.isQuiz"
            }
        }
    ]
}).execute()

# 3. Add a short answer graded question
requests = [{
    "createItem": {
        "item": {
            "title": "What is 2 + 2?",
            "questionItem": {
                "question": {
                    "textQuestion": {"paragraph": False},
                }
            },
            "grade": {
                "pointValue": 1,
                "correctAnswers": {"answers": [{"value": "4"}]},
                "generalFeedback": {"text": "Auto-graded short answer."}
            }
        },
        "location": {"index": 0}
    }
}]

form_service.forms().batchUpdate(formId=form_id, body={"requests": requests}).execute()

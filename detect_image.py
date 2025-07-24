import base64, cv2, os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


def io_to_base64(im_file):
    im_bytes = im_file.getvalue()
    return base64.b64encode(im_bytes)

def detect(image):
    client = genai.Client(
        api_key=os.getenv("GEMINI_API_KEY"),
    )

    model = "gemini-2.5-pro"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_bytes(
                    mime_type="image/jpeg",
                    data=base64.b64decode(io_to_base64(image))
                ),
                types.Part.from_text(text="""Your task is to analyze an image and identify the coordinates of any supplementary visual elements, such as illustrations, diagrams, or photos, that accompany a primary body of text.

Goal: To programmatically separate visual aids from textual content within a single image, like a screenshot of a quiz or an online article.

What to find:

Images embedded next to or within text.
Contextual illustrations for questions.
Figures or diagrams in a document layout.

What to ignore:
The text itself.
The overall page background.
UI elements like buttons or menus (if applicable).
Websites
Example Scenario:
Input Image: A screenshot showing the question "How many eyes does the duck have?" positioned next to a small drawing of a duck with three eyes.
Desired Output: The bounding box coordinates (e.g., [x1, y1, x2, y2]) for the rectangle (even if theres no rectangle, make the figure fit.) that perfectly encloses the drawing of the duck.
Final Output Format: Provide the results as a JSON list of coordinate objects, like so: [{"box_2d": [x1, y1, x2, y2]}, {"box_2d": [x3, y3, x4, y4]}, etc.]"""),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        thinking_config = types.ThinkingConfig(
            thinking_budget=-1,
        ),
    )

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        print(chunk.text, end="")
        return chunk.text

if __name__ == "__main__":
    detect("./solved_worksheet.png")
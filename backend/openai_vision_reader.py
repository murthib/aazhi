import os
from dotenv import load_dotenv

from openai import OpenAI
import base64
import json

# Load environment variables
load_dotenv()



api_key = os.getenv("OPENAI_API_KEY")


if not api_key:
    raise ValueError("OPENAI_API_KEY not found. Please set it in .env file.")

client = OpenAI(api_key=api_key)



def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def extract_handwritten_text(image_path):

    base64_image = encode_image(image_path)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": """
You are an expert document reader.

Extract handwritten text from exam answer sheets.

Rules:
- Preserve section titles (e.g., PART - A).
- Preserve question numbers (including circled numbers).
- Preserve line breaks.
- Correct obvious OCR-style mistakes.
- If something is unclear, mark it as [unclear].
- Return clean structured JSON.
"""
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract the handwritten text from this answer sheet."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        temperature=0
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    result = extract_handwritten_text("test.jpeg")
    print(result)
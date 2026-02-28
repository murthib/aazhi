from openai import OpenAI
import os
from dotenv import load_dotenv

# Load .env from project root
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY not found. Please set it in .env file.")

client = OpenAI(api_key=api_key)



def generate_exam(academic_level, subject, chapter, duration, partA_bloom, partB_bloom, partC_bloom):

    prompt = f"""
Generate a CBSE exam question paper in STRICT JSON format.

Return ONLY valid JSON.
Do NOT add explanations.
Do NOT wrap in markdown.

Top-level JSON structure must be:

{{
  "academic_level": "{academic_level}",
  "subject": "{subject}",
  "chapter": "{chapter}",
  "duration": "{duration}",
  "parts": {{
      "Part A": {{
          "questions": [
              {{
                  "question": "...",
                  "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
                  "correct_option": "A",
                  "correct_answer_text": "...",
                  "concept_tags": []
              }}
          ]
      }},
      "Part B": {{
          "questions": [
              {{
                  "question": "...",
                  "model_answer": "...",
                  "evaluation_rubric": []
              }}
          ]
      }},
      "Part C": {{
          "questions": [
              {{
                  "question": "...",
                  "model_answer": "...",
                  "evaluation_rubric": []
              }}
          ]
      }}
  }}
}}

Important rules:
- MCQs must include BOTH correct_option AND correct_answer_text.
- Descriptive questions must include model_answer.
- Do not omit any required fields.
- Continue the question number sequence across parts (e.g., if Part A has 5 questions, Part B should start from 6).
- Use the provided Bloom's taxonomy levels to guide question difficulty and type.   

"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )

        if not response.choices:
            print("No choices returned from OpenAI")
            return None

        content = response.choices[0].message.content

        if not content:
            print("OpenAI returned empty content")
            return None

        return content

    except Exception as e:
        print("OPENAI ERROR:", str(e))
        return None
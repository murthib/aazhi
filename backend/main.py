from http.client import HTTPException
from unittest import result

from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import date, datetime
import uuid
import json
from dotenv import load_dotenv
import pytesseract
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
import base64

from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Load environment variables
load_dotenv()

from pydantic import BaseModel
from typing import Optional

class TeacherReviewRequest(BaseModel):
    response_id: int
    teacher_marks: int
    teacher_feedback: Optional[str] = None


from typing import List
from pydantic import BaseModel
from typing import Optional

class TeacherReviewItem(BaseModel):
    response_id: int
    teacher_marks: int
    teacher_feedback: Optional[str] = None



# ==================================
# APPLICATION SETTINGS
# ==================================

APP_SETTINGS = {
    "AUTO_GRADING_AFTER_SUBMISSION": True  # 🔁 Toggle this
}


# Relative imports (IMPORTANT)
from models.database import save_exam_to_db, get_db
from agents.exam_agent import generate_exam

from models.database import (
    save_exam_to_db,
    get_db,
    Student,
    Submission,
    Question,
    StudentResponse,
    Option,
    Exam
)




app = FastAPI()

from models.database import Student

class StudentLogin(BaseModel):
    student_id: str
    password: str


from models.database import (
    AcademicLevel,
    Subject,
    Teacher,
    TeacherAssignment,
    Student
)

@app.post("/seed-data")
def seed_data(db: Session = Depends(get_db)):

    # -------- Academic Levels --------
    class8 = AcademicLevel(name="Class 8", level_type="SCHOOL")
    class9 = AcademicLevel(name="Class 9", level_type="SCHOOL")
    class10 = AcademicLevel(name="Class 10", level_type="SCHOOL")
    bsc_physics = AcademicLevel(name="B.Sc Physics", level_type="COLLEGE")

    db.add_all([class8, class9, class10, bsc_physics])
    db.commit()

    # -------- Subjects --------
    maths8 = Subject(name="Mathematics", academic_level_id=class8.id)
    physics8 = Subject(name="Physics", academic_level_id=class8.id)
    maths9 = Subject(name="Mathematics", academic_level_id=class9.id)
    maths10 = Subject(name="Mathematics", academic_level_id=class10.id)
    mechanics = Subject(name="Mechanics", academic_level_id=bsc_physics.id)

    db.add_all([maths8, physics8, maths9, maths10, mechanics])
    db.commit()

    # -------- Teacher --------
    teacher = Teacher(
        teacher_id="T001",
        name="Anita",
        password="1234"
    )

    db.add(teacher)
    db.commit()
    db.refresh(teacher)

    # -------- Teacher Assignments --------
    assignments = [
        TeacherAssignment(teacher_id=teacher.id, academic_level_id=class8.id, subject_id=maths8.id),
        TeacherAssignment(teacher_id=teacher.id, academic_level_id=class9.id, subject_id=maths9.id),
        TeacherAssignment(teacher_id=teacher.id, academic_level_id=class10.id, subject_id=maths10.id),
        TeacherAssignment(teacher_id=teacher.id, academic_level_id=class8.id, subject_id=physics8.id),
    ]

    db.add_all(assignments)
    db.commit()

    # -------- Students --------
    students = [
        Student(student_id="S001", name="Ananya", password="1234", academic_level_id=class8.id),
        Student(student_id="S002", name="Rahul", password="1234", academic_level_id=class8.id),
        Student(student_id="S003", name="Kavya", password="1234", academic_level_id=class9.id),
        Student(student_id="S004", name="Arjun", password="1234", academic_level_id=class10.id),
        Student(student_id="S005", name="Vikram", password="1234", academic_level_id=class8.id),
    ]

    db.add_all(students)
    db.commit()

    return {"message": "Database seeded successfully"}
















@app.post("/student-login")
def student_login(request: StudentLogin, db: Session = Depends(get_db)):

    student = db.query(Student).filter(
        Student.student_id == request.student_id,
        Student.password == request.password
    ).first()

    if not student:
        return {"success": False, "message": "Invalid credentials"}

    return {
        "success": True,
        "student_id": student.id,
        "name": student.name
    }

class ExamRequest(BaseModel):
    teacher_id: int
    academic_level_id: int
    subject_id: int
    chapter: str
    duration: str
    partA_bloom: str
    partB_bloom: str
    partC_bloom: str
    


@app.post("/generate-exam")
def create_exam(request: ExamRequest, db: Session = Depends(get_db)):

    # 🔒 1️⃣ Validate Teacher Assignment
    assignment = db.query(TeacherAssignment).filter(
        TeacherAssignment.teacher_id == request.teacher_id,
        TeacherAssignment.academic_level_id == request.academic_level_id,
        TeacherAssignment.subject_id == request.subject_id
    ).first()

    if not assignment:
        return {
            "error": "You are not assigned to this Academic Level and Subject"
        }

    # 🔎 2️⃣ Fetch Subject Name (for AI generation)
    subject = db.query(Subject).filter(
        Subject.id == request.subject_id
    ).first()

    if not subject:
        return {"error": "Invalid subject selected"}

    level = db.query(AcademicLevel).filter(
        AcademicLevel.id == request.academic_level_id
    ).first()

    if not level:
        return {"error": "Invalid academic level selected"}

    # 3️⃣ Generate Exam from OpenAI
    result = generate_exam(
        level.name,      # 🔥 Use actual academic level name
        subject.name,   # 🔥 Use actual subject name
        request.chapter,
        request.duration,
        request.partA_bloom,
        request.partB_bloom,
        request.partC_bloom
    )

    if not result:
        raise ValueError("Empty response from OpenAI")

    # 4️⃣ Clean Markdown if model adds it
    clean_result = result.strip()

    if clean_result.startswith("```"):
        clean_result = clean_result.replace("```json", "")
        clean_result = clean_result.replace("```", "")
        clean_result = clean_result.strip()

    # 5️⃣ Convert to JSON
    try:
        exam_data = json.loads(clean_result)
    except Exception as e:
        raise ValueError(f"Invalid JSON from OpenAI: {e}")

    # 6️⃣ Create Metadata
    exam_id = "EXAM_" + uuid.uuid4().hex[:8]

    metadata = {
        "exam_id": exam_id,
        "academic_level_id": request.academic_level_id,
        "academic_level_name": level.name,  # 🔥 ADD THIS
        "subject_id": request.subject_id,
        "created_by": request.teacher_id,
        "created_at": datetime.utcnow().isoformat(),
        "status": "CREATED"
    }

    # 7️⃣ Save to DB
    db_exam  = save_exam_to_db(db, metadata, exam_data)

    # 8️⃣ Return Response
    return {
        "metadata": metadata,
        "exam": exam_data,
        "db_exam_id": db_exam.id   # 🔥 ADD THIS

    }



from models.database import Exam

@app.get("/exams")
def get_exams(db: Session = Depends(get_db)):
    exams = db.query(Exam).all()

    return [
        {
            "id": e.id,  # 🔥 ADD THIS
            "exam_id": e.exam_id,
            "subject": e.subject,
            "chapter": e.chapter,
            "created_by": e.created_by,
            "created_at": e.created_at,
            "status": e.status
        }
        for e in exams
    ]

@app.get("/published-exams")
def get_published_exams(db: Session = Depends(get_db)):

    exams = db.query(Exam).filter(
        Exam.status == "PUBLISHED"
    ).all()

    return [
        {
            "id": e.id,
            "exam_id": e.exam_id,
            "subject": e.subject,
            "chapter": e.chapter,
            "deadline": e.deadline.strftime("%Y-%m-%d") if e.deadline else None
        }
        for e in exams
    ]



from fastapi import File, UploadFile
import shutil
import os

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.post("/submit-exam/{student_id}/{exam_id}")
def submit_exam(
    student_id: int,
    exam_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    submission = Submission(
        student_id=student_id,
        exam_id=exam_id,
        uploaded_pdf_path=file_path,
        status="UPLOADED"
    )

    exam = db.query(Exam).filter(Exam.id == exam_id).first()

    if exam.deadline and datetime.utcnow() > exam.deadline:
        return {"error": "Submission deadline has passed"}

    db.add(submission)
    db.commit()
    db.refresh(submission)


    # ==================================
    # AUTO GRADING SWITCH
    # ==================================
    if APP_SETTINGS["AUTO_GRADING_AFTER_SUBMISSION"]:
        run_ai_evaluation(
            submission_id=submission.id,
            grading_mode="STRICT",
            db=db
        )
        message = "File uploaded and AI evaluated"
    else:
        message = "File uploaded. Awaiting teacher evaluation"

    return {
        "message": message,
        "submission_id": submission.id,
        "auto_grading_enabled": APP_SETTINGS["AUTO_GRADING_AFTER_SUBMISSION"]
    }


from pdf2image import convert_from_path
import pytesseract
import cv2
import numpy as np

# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# # def extract_text_from_pdf(pdf_path):

# #     pages = convert_from_path(
# #         pdf_path,
# #         poppler_path=r"C:\poppler-25.12.0\Library\bin"
# #     )

# #     text = ""

# #     for page in pages:

# #         # Convert PIL image to OpenCV format
# #         img = np.array(page)
# #         img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

# #         # Increase contrast
# #         img = cv2.GaussianBlur(img, (5, 5), 0)
# #         _, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

# #         # OCR with better config
# #         custom_config = r'--oem 3 --psm 6'

# #         page_text = pytesseract.image_to_string(img, config=custom_config)

# #         text += page_text + "\n"

# #     print("OCR TEXT:", text)

# #     return text



def evaluate_answer(student_text, correct_answer, max_marks, grading_mode):

    # 🔹 Preserve core strict grading rules
    grading_tone = ""

    if grading_mode == "STRICT":
        grading_tone = """
        Additional Strictness:
        - Be strict like a board examiner.
        - Require completeness and depth.
        - Penalize missing components clearly.
        """

    elif grading_mode == "MODERATE":
                grading_tone = """
        Additional Moderation:
        - Be fair like a school internal examiner.
        - If core concept is correct, do not heavily penalize minor omissions.
        - Allow reasonable interpretation of partially complete answers.
        """

    elif grading_mode == "LENIENT":
                grading_tone = """
        Additional Leniency:
        - Be slightly generous.
        - If main idea is correct, award higher proportional marks.
        - Focus on conceptual understanding rather than perfect completeness.
        """

    prompt = f"""
        You are a strict but fair school examiner.

        Evaluate the student's answer against the model answer.

        Model Answer:
        {correct_answer}

        Student Answer:
        {student_text}

        Evaluation Rules:
        1. Award marks proportionally based on relevance and completeness.
        2. Do NOT award marks for unrelated content.
        3. Do NOT assume missing points.
        4. If answer is partially correct, give proportional marks.
        5. If answer is completely incorrect, give 0 marks.
        6. Do not exceed {max_marks} marks.
        7. Keep feedback short and specific.

        {grading_tone}

        Return STRICTLY valid JSON:

        {{
        "marks_awarded": integer between 0 and {max_marks},
        "feedback": "1-2 sentence explanation"
        }}
        """

    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        temperature=0,
        messages=[
            {"role": "system", "content": "You are an expert school examiner."},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content



def run_ai_evaluation(submission_id: int, grading_mode: str, db: Session):

    submission = db.query(Submission).filter(
        Submission.id == submission_id
    ).first()

    if not submission:
        raise ValueError("Submission not found")

    submission.grading_mode = grading_mode

    # Step 1: Extract structured answers using AI
    student_answers = extract_answers_from_pdf_with_ai(
        submission.uploaded_pdf_path
    )


    # 🔥 ADD THIS BLOCK HERE
    db.query(StudentResponse).filter(
        StudentResponse.submission_id == submission.id
    ).delete()


    submission.extracted_text = json.dumps(student_answers)
    submission.status = "OCR_DONE"
    db.commit()

    questions = db.query(Question).filter(
        Question.exam_id == submission.exam_id
    ).all()

    total_marks = 0

    for q in questions:

        student_answer_text = student_answers.get(q.question_number)

        if not student_answer_text:
            continue

        if q.question_type == "MCQ":

            is_correct = student_answer_text.strip().upper() == q.correct_option
            marks = q.max_marks if is_correct else 0

            response = StudentResponse(
                submission_id=submission.id,
                student_id=submission.student_id,
                question_id=q.id,
                answer_text=student_answer_text,
                ai_is_correct=is_correct,
                ai_marks_awarded=marks,
                teacher_marks_awarded=marks,
                final_marks=marks,
                evaluated_status="AI_EVALUATED"
            )

        else:

            evaluation_json = evaluate_answer(
                student_text=student_answer_text,
                correct_answer=q.teacher_final_answer,
                max_marks=q.max_marks,
                grading_mode=grading_mode
            )

            evaluation_data = json.loads(evaluation_json)
            marks = evaluation_data.get("marks_awarded", 0)

            response = StudentResponse(
                submission_id=submission.id,
                student_id=submission.student_id,
                question_id=q.id,
                answer_text=student_answer_text,
                ai_marks_awarded=marks,
                ai_feedback=evaluation_data.get("feedback"),
                teacher_marks_awarded=marks,
                final_marks=marks,
                evaluated_status="AI_EVALUATED"
            )

        db.add(response)
        total_marks += marks

    submission.ai_total_marks = total_marks
    submission.final_total_marks = total_marks
    submission.status = "AI_EVALUATED"

    db.commit()

    return total_marks



@app.post("/evaluate-submission/{submission_id}")
def evaluate_submission(
    submission_id: int,
    grading_mode: str = "STRICT",
    db: Session = Depends(get_db)
):

    total_marks = run_ai_evaluation(
        submission_id=submission_id,
        grading_mode=grading_mode,
        db=db
    )

    return {"total_marks": total_marks}


@app.get("/submissions-for-review")
def get_submissions_for_review(db: Session = Depends(get_db)):

    submissions = db.query(Submission).filter(
        Submission.status.in_(["UPLOADED", "AI_EVALUATED", "TEACHER_REVIEWED"])
    ).all()

    return [
        {
            "id": s.id,
            "student_id": s.student_id,
            "exam_id": s.exam_id,
            "status": s.status,
            "grading_mode": s.grading_mode
        }
        for s in submissions
    ]



# # @app.post("/evaluate-mcq-from-submission/{submission_id}")
# # def evaluate_mcq_from_submission(submission_id: int, db: Session = Depends(get_db)):

# #     submission = db.query(Submission).filter(
# #         Submission.id == submission_id
# #     ).first()

# #     if not submission:
# #         return {"error": "Submission not found"}

# #     # Step 1: OCR
# #     extracted_text = extract_text_from_pdf(submission.uploaded_pdf_path)

# #     submission.extracted_text = extracted_text
# #     db.commit()

# #     # Step 2: Extract MCQ answers
# #     mcq_answers = extract_mcq_answers(extracted_text)

# #     # Step 3: Get MCQ questions
# #     questions = db.query(Question).filter(
# #         Question.exam_id == submission.exam_id,
# #         Question.question_type == "MCQ"
# #     ).all()

# #     total_marks = 0

# #     for q in questions:

# #         student_option_letter = mcq_answers.get(q.question_number)

# #         if not student_option_letter:
# #             continue

# #         correct_letter = q.correct_option

# #         is_correct = student_option_letter == correct_letter
# #         marks = q.max_marks if is_correct else 0

# #         response = StudentResponse(
# #             student_id=submission.student_id,
# #             submission_id=submission.id,
# #             question_id=q.id,
# #             ai_is_correct=is_correct,
# #             ai_marks_awarded=marks,
# #             final_marks=marks,
# #             evaluated_status="AI_EVALUATED"
# #         )

# #         db.add(response)

# #         total_marks += marks

# #     submission.ai_total_marks = total_marks
# #     submission.status = "AI_EVALUATED"

# #     db.commit()

# #     return {"total_mcq_marks": total_marks}






def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def extract_answers_from_image(image_path):

    base64_image = encode_image(image_path)

    prompt = """
    You are reading a student's full exam answer sheet.

    The page may contain:
    - MCQ answers (A/B/C/D)
    - Short descriptive answers
    - Long descriptive answers
    - Mixed formats

    Important assumptions:
    - The student writes answers on a separate sheet.
    - The student writes clear question numbers (1, 2, 3, ...).
    - Each answer begins with its question number.

    Your tasks:
    1. Detect question numbers clearly and exactly as written.
    2. Extract the student's answer written under each question number.
    3. If MCQ, return only the selected option letter (A/B/C/D).
    4. If descriptive, return the full written answer exactly as written.
    5. Do NOT merge answers across question numbers.
    6. Do NOT invent content.
    7. Do NOT invent missing answers.
    8. If something is unreadable, mark it as "[unclear]".
    9. If a question number is present but no answer is written, return an empty string.

    Return STRICTLY valid JSON in this format:

    {
    "answers": [
        {
        "question_number": 1,
        "answer_text": "..."
        }
    ]
    }
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        temperature=0,
        messages=[
            {"role": "system", "content": "You are an expert exam paper reader."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
    )

    return response.choices[0].message.content


from pdf2image import convert_from_path
from io import BytesIO
import json

def extract_answers_from_pdf_with_ai(pdf_path):

    pages = convert_from_path(pdf_path)
    all_answers = {}

    for page in pages:
        buffer = BytesIO()
        page.save(buffer, format="JPEG")
        buffer.seek(0)

        ai_json = extract_answers_from_image(buffer)
        parsed = json.loads(ai_json)

        for ans in parsed.get("answers", []):
            q_no = ans.get("question_number")
            text = ans.get("answer_text")

            if q_no:
                all_answers[int(q_no)] = text

    return all_answers

# def extract_answers_from_pdf_with_ai(pdf_path):

#     # pages = convert_from_path(
#     #     pdf_path,
#     #     poppler_path=r"C:\poppler-25.12.0\Library\bin"
#     # )

#     # pages = convert_from_path(
#     #     pdf_path,
#     #     poppler_path=r""
#     # )

#     # all_answers = {}

#     # for i, page in enumerate(pages):

#     #     temp_image_path = f"temp_page_{i}.jpg"
#     #     page.save(temp_image_path, "JPEG")

#     #     ai_json = extract_answers_from_image(temp_image_path)
#     #     parsed = json.loads(ai_json)

#     #     for ans in parsed.get("answers", []):
#     #         q_no = ans.get("question_number")
#     #         text = ans.get("answer_text")

#     #         if q_no:
#     #             all_answers[int(q_no)] = text

#     return 


@app.get("/submission-result/{submission_id}")
def get_submission_result(submission_id: int, db: Session = Depends(get_db)):

    submission = db.query(Submission).filter(
        Submission.id == submission_id
    ).first()

    if not submission:
        return {"error": "Submission not found"}

    responses = db.query(StudentResponse).filter(
        StudentResponse.submission_id == submission.id
    ).all()

    result = []

    for r in responses:

        question = db.query(Question).filter(
            Question.id == r.question_id
        ).first()

        # =========================
        # MCQ QUESTION
        # =========================
        if question.question_type == "MCQ":

            options = db.query(Option).filter(
                Option.question_id == question.id
            ).all()

            result.append({
                "question_number": question.question_number,
                "question_type": "MCQ",
                "question_text": question.question_text,
                "options": [
                    {
                        "option_text": opt.option_text,
                        "is_correct": opt.is_correct
                    }
                    for opt in options
                ],
                "student_answer": r.answer_text,
                "correct_option": question.correct_option,
                "marks_awarded": r.final_marks,
                "max_marks": question.max_marks,
                "ai_feedback": r.ai_feedback,
                "teacher_feedback": r.teacher_feedback

            })

        # =========================
        # DESCRIPTIVE QUESTION
        # =========================
        else:

            result.append({
                "question_number": question.question_number,
                "question_type": question.question_type,
                "question_text": question.question_text,
                "student_answer": r.answer_text,
                "correct_answer": question.teacher_final_answer,
                "marks_awarded": r.final_marks,
                "max_marks": question.max_marks,
                "ai_feedback": r.ai_feedback,
                "teacher_feedback": r.teacher_feedback
            })

    # 🔥 Move outside loop
    weak_topics = []
    strong_topics = []

    for q in result:
        percentage = (q["marks_awarded"] / q["max_marks"]) * 100 if q["max_marks"] else 0

        if percentage < 50:
            weak_topics.append(q["question_text"][:50])
        else:
            strong_topics.append(q["question_text"][:50])

    return {
        "exam_id": submission.exam_id,
        "ai_total_marks": submission.ai_total_marks,
        "final_total_marks": submission.final_total_marks,
        "total_marks": submission.final_total_marks,   # 👈 student sees final
        "questions": result,
        "weak_topics": weak_topics,
        "strong_topics": strong_topics,
        "answer_pdf_path": submission.uploaded_pdf_path,
        "suggested_videos": [
            f"https://www.youtube.com/results?search_query={topic.replace(' ', '+')}"
            for topic in weak_topics
        ]
    }


@app.post("/teacher-override/{response_id}")
def teacher_override(
    response_id: int,
    teacher_marks: int,
    teacher_comment: str = "",
    db: Session = Depends(get_db)
):

    response = db.query(StudentResponse).filter(
        StudentResponse.id == response_id
    ).first()

    if not response:
        return {"error": "Response not found"}

    response.teacher_marks_awarded = teacher_marks
    response.teacher_feedback = teacher_comment
    response.final_marks = teacher_marks
    response.evaluated_status = "TEACHER_REVIEWED"

    db.commit()

    return {"message": "Override saved"}


def recalculate_submission_total(submission_id, db):

    submission = db.query(Submission).filter(
        Submission.id == submission_id
    ).first()

    responses = db.query(StudentResponse).join(Question).filter(
        StudentResponse.submission_id == submission.id
    ).all()

    total = sum(r.final_marks for r in responses)

    submission.final_total_marks = total
    db.commit()


@app.post("/publish-result/{submission_id}")
def publish_result(submission_id: int, db: Session = Depends(get_db)):

    submission = db.query(Submission).filter(
        Submission.id == submission_id
    ).first()

    if not submission:
        return {"error": "Submission not found"}

    # 🔒 Prevent double publishing
    if submission.status == "RESULT_PUBLISHED":
        return {"error": "Result already published"}

    # 🔒 Only allow publish after evaluation
    if submission.status not in ["AI_EVALUATED", "TEACHER_REVIEWED"]:
        return {
            "error": f"Result cannot be published from current state: {submission.status}"
        }

    # 🔄 Recalculate final total marks
    responses = db.query(StudentResponse).filter(
        StudentResponse.submission_id == submission_id
    ).all()

    final_total = sum(r.final_marks for r in responses)

    submission.final_total_marks = final_total
    submission.status = "RESULT_PUBLISHED"

    db.commit()

    return {"message": "Result published successfully"}

@app.get("/submission-review/{submission_id}")
def get_submission_review(submission_id: int, db: Session = Depends(get_db)):

    submission = db.query(Submission).filter(
        Submission.id == submission_id
    ).first()

    if not submission:
        return {"error": "Submission not found"}

    responses = db.query(StudentResponse).join(Question).filter(
        StudentResponse.submission_id == submission.id
    ).all()

    result = []

    for r in responses:

        question = db.query(Question).filter(
            Question.id == r.question_id
        ).first()

        result.append({
            "response_id": r.id,
            "question_number": question.question_number,
            "question_text": question.question_text,
            "student_answer": r.answer_text,
            "max_marks": question.max_marks,
            "ai_marks": r.ai_marks_awarded,
            "ai_feedback": r.ai_feedback,
            "teacher_marks": r.teacher_marks_awarded,
            "teacher_feedback": r.teacher_feedback,
            "final_marks": r.final_marks
        })

    return {
        "submission_id": submission.id,
        "student_id": submission.student_id,
        "exam_id": submission.exam_id,
        "status": submission.status,
        "grading_mode": submission.grading_mode,
        "ai_total_marks": submission.ai_total_marks,
        "final_total_marks": submission.final_total_marks,
        "questions": result
    }



@app.post("/teacher-review/{submission_id}")
def teacher_review(
    submission_id: int,
    updates: List[TeacherReviewItem],
    db: Session = Depends(get_db)
):

    for item in updates:

        response = db.query(StudentResponse).filter(
            StudentResponse.id == item.response_id,
            StudentResponse.submission_id == submission_id
        ).first()

        if not response:
            continue

        response.teacher_marks_awarded = item.teacher_marks
        response.teacher_feedback = item.teacher_feedback
        response.final_marks = item.teacher_marks
        response.evaluated_status = "TEACHER_REVIEWED"

    # Recalculate total
    recalculate_submission_total(submission_id, db)

    db.commit()

    return {"message": "Teacher review saved"}

from sqlalchemy import desc
import json

@app.get("/student-dashboard/{student_id}")
def student_dashboard(student_id: int, db: Session = Depends(get_db)):

    student = db.query(Student).filter(
        Student.id == student_id
    ).first()

    if not student:
        return {"error": "Student not found"}

    # 🔒 Filter exams by academic level and published
    exams = db.query(Exam).filter(
        Exam.status == "PUBLISHED",
        Exam.academic_level_id == student.academic_level_id
    ).all()

    result = []

    for e in exams:

        # ✅ Get latest submission for this student + exam
        submission = (
            db.query(Submission)
            .filter(
                Submission.student_id == student_id,
                Submission.exam_id == e.id
            )
            .order_by(desc(Submission.id))
            .first()
        )

        # Default values
        status = "NOT_ATTEMPTED"
        ai_total_marks = None
        final_total_marks = None
        max_marks = None

        if submission:
            status = submission.status
            ai_total_marks = submission.ai_total_marks
            final_total_marks = submission.final_total_marks

        # ✅ Calculate total max marks from exam JSON
        try:
            exam_data = json.loads(e.exam_json)

            max_marks = sum(
                q["max_marks"]
                for part in exam_data.get("parts", {}).values()
                for q in part.get("questions", [])
            )
        except:
            max_marks = None

        result.append({
            "exam_id": e.id,
            "exam_name": e.exam_id,
            "subject": e.subject.name,
            "subject_id": e.subject_id,
            "chapter": e.chapter,
            "status": status,
            "deadline": e.deadline.strftime("%Y-%m-%d") if e.deadline else None,  # ✅ ADD THIS
            "ai_total_marks": ai_total_marks,
            "final_total_marks": final_total_marks,
            "max_marks": max_marks
        })

    return result


@app.get("/submission-status/{submission_id}")
def submission_status(submission_id: int, db: Session = Depends(get_db)):

    submission = db.query(Submission).filter(
        Submission.id == submission_id
    ).first()

    if not submission:
        return {"error": "Not found"}

    return {
        "status": submission.status,
        "ai_total_marks": submission.ai_total_marks,
        "final_total_marks": submission.final_total_marks
    }


@app.get("/latest-submission/{student_id}/{exam_id}")
def get_latest_submission(student_id: int, exam_id: int, db: Session = Depends(get_db)):

    submission = db.query(Submission).filter(
        Submission.student_id == student_id,
        Submission.exam_id == exam_id
    ).order_by(Submission.id.desc()).first()

    if not submission:
        return {"error": "No submission found"}

    return {
        "submission_id": submission.id,
        "status": submission.status
    }


from fastapi.responses import FileResponse

@app.get("/download-answer/{submission_id}")
def download_answer(submission_id: int, db: Session = Depends(get_db)):

    submission = db.query(Submission).filter(
        Submission.id == submission_id
    ).first()

    if not submission:
        return {"error": "Submission not found"}

    return FileResponse(
        submission.uploaded_pdf_path,
        media_type="application/pdf",
        filename="Student_Answer.pdf"
    )



class TeacherLogin(BaseModel):
    teacher_id: str
    password: str


@app.post("/teacher-login")
def teacher_login(request: TeacherLogin, db: Session = Depends(get_db)):

    teacher = db.query(Teacher).filter(
        Teacher.teacher_id == request.teacher_id,
        Teacher.password == request.password
    ).first()

    if not teacher:
        return {"success": False, "message": "Invalid credentials"}

    return {
        "success": True,
        "teacher_id": teacher.id,
        "name": teacher.name
    }


@app.get("/teacher-assignments/{teacher_id}")
def get_teacher_assignments(teacher_id: int, db: Session = Depends(get_db)):

    assignments = db.query(TeacherAssignment).filter(
        TeacherAssignment.teacher_id == teacher_id
    ).all()

    result = []

    for a in assignments:
        result.append({
            "academic_level_id": a.academic_level.id,
            "academic_level_name": a.academic_level.name,
            "subject_id": a.subject.id,
            "subject_name": a.subject.name
        })

    return result


from datetime import timedelta

@app.post("/publish-exam/{exam_id}")
def publish_exam(exam_id: int, db: Session = Depends(get_db)):

    exam = db.query(Exam).filter(
        Exam.id == exam_id
    ).first()

    if not exam:
        return {"error": "Exam not found"}

    if exam.status == "PUBLISHED":
        return {"error": "Exam already published"}

    if exam.status != "CREATED":
        return {"error": f"Cannot publish from state {exam.status}"}

    # ✅ Set publish date
    exam.status = "PUBLISHED"

    # ✅ Auto-set deadline = today + 15 days
    exam.deadline = datetime.utcnow() + timedelta(days=15)

    db.commit()

    return {
        "message": "Exam published successfully",
        "deadline": exam.deadline.strftime("%Y-%m-%d")
    }


@app.get("/teacher-dashboard/{teacher_id}")
def teacher_dashboard(teacher_id: int, db: Session = Depends(get_db)):

    # -------------------------
    # Exams Created
    # -------------------------
    total_exams = db.query(Exam).filter(
        Exam.created_by == teacher_id
    ).count()

    published_exams = db.query(Exam).filter(
        Exam.created_by == teacher_id,
        Exam.status == "PUBLISHED"
    ).count()

    draft_exams = db.query(Exam).filter(
        Exam.created_by == teacher_id,
        Exam.status == "CREATED"
    ).count()

    # -------------------------
    # Submissions
    # -------------------------
    exams_by_teacher = db.query(Exam.id).filter(
        Exam.created_by == teacher_id
    ).all()

    exam_ids = [e.id for e in exams_by_teacher]

    total_submissions = db.query(Submission).filter(
        Submission.exam_id.in_(exam_ids)
    ).count()

    results_published = db.query(Submission).filter(
        Submission.exam_id.in_(exam_ids),
        Submission.status == "RESULT_PUBLISHED"
    ).count()

    # -------------------------
    # Performance Metrics
    # -------------------------
    marks = db.query(Submission.final_total_marks).filter(
        Submission.exam_id.in_(exam_ids),
        Submission.status == "RESULT_PUBLISHED"
    ).all()

    marks_list = [m[0] for m in marks if m[0] is not None]

    if marks_list:
        highest = max(marks_list)
        lowest = min(marks_list)
        average = round(sum(marks_list) / len(marks_list), 2)
    else:
        highest = lowest = average = 0

    return {
        "total_exams": total_exams,
        "published_exams": published_exams,
        "draft_exams": draft_exams,
        "total_submissions": total_submissions,
        "results_published": results_published,
        "highest_mark": highest,
        "lowest_mark": lowest,
        "average_mark": average
    }


@app.get("/student-performance/{student_id}")
def student_performance(student_id: int, db: Session = Depends(get_db)):

    student = db.query(Student).filter(
        Student.id == student_id
    ).first()

    if not student:
        return {"error": "Student not found"}

    # -------------------------
    # Exams Available
    # -------------------------
    total_exams = db.query(Exam).filter(
        Exam.status == "PUBLISHED",
        Exam.academic_level_id == student.academic_level_id
    ).count()

    # -------------------------
    # Submissions
    # -------------------------
    submissions = db.query(Submission).filter(
        Submission.student_id == student_id
    ).all()

    attempted = len(submissions)

    results_published = len([
        s for s in submissions if s.status == "RESULT_PUBLISHED"
    ])

    pending_results = len([
        s for s in submissions if s.status != "RESULT_PUBLISHED"
    ])

    # -------------------------
    # Performance Stats
    # -------------------------
    marks = [
        s.final_total_marks
        for s in submissions
        if s.status == "RESULT_PUBLISHED"
        and s.final_total_marks is not None
    ]

    if marks:
        highest = max(marks)
        lowest = min(marks)
        average = round(sum(marks) / len(marks), 2)
    else:
        highest = lowest = average = 0

    # -------------------------
    # Overall Performance %
    # -------------------------
    if total_exams > 0 and average > 0:
        overall_percentage = average
    else:
        overall_percentage = 0

    return {
        "total_exams": total_exams,
        "attempted": attempted,
        "results_published": results_published,
        "pending_results": pending_results,
        "highest_mark": highest,
        "lowest_mark": lowest,
        "average_mark": average,
        "overall_percentage": overall_percentage
    }



@app.get("/exams/{teacher_id}")
def get_exams(teacher_id: int, db: Session = Depends(get_db)):

    exams = db.query(Exam).filter(
        Exam.created_by == teacher_id
    ).all()

    result = []

    for e in exams:

        submissions = db.query(Submission).filter(
            Submission.exam_id == e.id
        ).all()

        submission_count = len(submissions)

        ai_evaluated_count = len([
            s for s in submissions
            if s.status in ["AI_EVALUATED", "TEACHER_REVIEWED", "RESULT_PUBLISHED"]
        ])

        results_published_count = len([
            s for s in submissions
            if s.status == "RESULT_PUBLISHED"
        ])

        result.append({
            "exam_id": e.exam_id,
            "id": e.id,
            "subject": e.subject.name if e.subject else "",
            "chapter": e.chapter,
            "status": e.status,
            "deadline": e.deadline.strftime("%Y-%m-%d") if e.deadline else "-",
            "pdf_link": f"/download-exam-pdf/{e.id}",
            "submission_count": submission_count,
            "ai_evaluated_count": ai_evaluated_count,
            "results_published_count": results_published_count
        })

    return result


from fastapi.responses import StreamingResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from io import BytesIO
from fastapi.responses import StreamingResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from io import BytesIO

@app.get("/download-exam-pdf/{exam_id}")
def download_exam_pdf(exam_id: int, db: Session = Depends(get_db)):

    exam = db.query(Exam).filter(Exam.id == exam_id).first()

    if not exam:
        return {"error": "Exam not found"}

    exam_data = json.loads(exam.exam_json)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # ==============================
    # HEADER
    # ==============================

    elements.append(Paragraph("CBSE Examination Paper", styles["Heading1"]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(f"Exam ID: {exam.exam_id}", styles["Normal"]))
    elements.append(Paragraph(f"Class: {exam.academic_level.name}", styles["Normal"]))
    elements.append(Paragraph(f"Subject: {exam.subject.name}", styles["Normal"]))
    elements.append(Paragraph(f"Chapter: {exam.chapter}", styles["Normal"]))
    elements.append(Paragraph(f"Duration: {exam.duration}", styles["Normal"]))
    elements.append(Spacer(1, 20))

    # ==============================
    # QUESTIONS
    # ==============================

    parts = exam_data.get("parts", {})
    question_number = 1   # 🔥 Global counter

    for part_name, part_data in parts.items():

        elements.append(Paragraph(part_name, styles["Heading2"]))
        elements.append(Spacer(1, 10))

        for q in part_data.get("questions", []):

            elements.append(
                Paragraph(f"{question_number}. {q['question']}", styles["Normal"])
            )
            elements.append(Spacer(1, 6))

            # 🔥 ADD MCQ OPTIONS
            if "options" in q:
                for opt in q["options"]:
                    elements.append(
                        Paragraph(f"- {opt}", styles["Normal"])
                    )
                    elements.append(Spacer(1, 4))

            elements.append(Spacer(1, 10))

            question_number += 1

        elements.append(Spacer(1, 20))

    doc.build(elements)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={exam.exam_id}.pdf"
        }
    )



@app.get("/subject-analysis/{student_id}/{subject_id}")
def subject_analysis(student_id: int, subject_id: int, db: Session = Depends(get_db)):

    # -----------------------------
    # 1️⃣ Get student submissions for this subject
    # -----------------------------
    student_submissions = (
        db.query(Submission)
        .join(Exam)
        .filter(
            Submission.student_id == student_id,
            Exam.subject_id == subject_id,
            Submission.status == "RESULT_PUBLISHED"
        )
        .all()
    )

    if not student_submissions:
        return {
            "analysis": "No published results available for this subject yet."
        }

    # -----------------------------
    # 2️⃣ Aggregate student feedback
    # -----------------------------
    student_feedback = []

    for sub in student_submissions:
        responses = db.query(StudentResponse).filter(
            StudentResponse.submission_id == sub.id
        ).all()

        for r in responses:
            if r.ai_feedback:
                student_feedback.append(r.ai_feedback)
            if r.teacher_feedback:
                student_feedback.append(r.teacher_feedback)

    combined_student_feedback = "\n".join(student_feedback)

    # -----------------------------
    # 3️⃣ Identify topper threshold (Top 20%)
    # -----------------------------
    all_submissions = (
        db.query(Submission)
        .join(Exam)
        .filter(
            Exam.subject_id == subject_id,
            Submission.status == "RESULT_PUBLISHED"
        )
        .all()
    )

    marks = [
        s.final_total_marks
        for s in all_submissions
        if s.final_total_marks is not None
    ]

    if not marks:
        topper_feedback_text = ""
    else:
        marks_sorted = sorted(marks, reverse=True)
        cutoff_index = max(1, len(marks_sorted) // 5)
        topper_threshold = marks_sorted[cutoff_index - 1]

        topper_submissions = [
            s for s in all_submissions
            if s.final_total_marks >= topper_threshold
        ]

        topper_feedback = []

        for sub in topper_submissions:
            responses = db.query(StudentResponse).filter(
                StudentResponse.submission_id == sub.id
            ).all()

            for r in responses:
                if r.ai_feedback:
                    topper_feedback.append(r.ai_feedback)
                if r.teacher_feedback:
                    topper_feedback.append(r.teacher_feedback)

        topper_feedback_text = "\n".join(topper_feedback)

    # -----------------------------
    # 4️⃣ Get subject name
    # -----------------------------
    subject = db.query(Subject).filter(
        Subject.id == subject_id
    ).first()

    subject_name = subject.name if subject else "Subject"

    # -----------------------------
    # 5️⃣ AI Meta Analysis
    # -----------------------------
    prompt = f"""
You are an academic growth mentor.

Subject: {subject_name}

Below is feedback given to a student across multiple exams in this subject:

STUDENT FEEDBACK:
{combined_student_feedback}

Below is feedback given to high-scoring students in the same subject:

TOPPER FEEDBACK:
{topper_feedback_text}

Your tasks:

1. Identify student's strengths.
2. Identify repeated weaknesses or patterns of mark loss.
3. Provide 3-5 actionable improvement suggestions.
4. Explain what high-scoring students are doing differently.
5. Be constructive, encouraging and clear.
6. Do NOT mention marks or ranking.
7. Do NOT mention specific student names.

Return structured response in this format:

📘 {subject_name}

💚 Strength:
...

📉 You Lost Marks Because:
...

🎯 Improvement Plan:
...

🏆 What Toppers Are Doing:
...
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.3,
            messages=[
                {"role": "system", "content": "You are an expert academic mentor."},
                {"role": "user", "content": prompt}
            ]
        )

        analysis_text = response.choices[0].message.content

    except Exception as e:
        analysis_text = f"AI analysis failed: {str(e)}"

    return {
        "subject": subject_name,
        "analysis": analysis_text
    }


from datetime import date, timedelta

@app.put("/publish-exam/{exam_id}")
def publish_exam(exam_id: str, db: Session = Depends(get_db)):

    exam = db.query(Exam).filter(Exam.exam_id == exam_id).first()

    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if exam.status == "PUBLISHED":
        raise HTTPException(status_code=400, detail="Already published")

    exam.status = "PUBLISHED"
    exam.deadline = date.today() + timedelta(days=15)

    db.commit()

    return {"message": "Exam published successfully"}




@app.get("/")
def home():
    return {"message": "Aazhi Backend is Running 🚀"}


from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For now allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




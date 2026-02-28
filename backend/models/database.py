from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Boolean
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import json

# ==================================
# DATABASE CONFIG
# ==================================

DATABASE_URL = "sqlite:///./aazhi.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


# ==================================
# 1️⃣ ACADEMIC LEVEL TABLE
# ==================================

class AcademicLevel(Base):
    __tablename__ = "academic_levels"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True)
    level_type = Column(String)  # SCHOOL / COLLEGE / CERTIFICATION

    students = relationship("Student", back_populates="academic_level")
    subjects = relationship("Subject", back_populates="academic_level")
    exams = relationship("Exam", back_populates="academic_level")
    assignments = relationship("TeacherAssignment", back_populates="academic_level")


# ==================================
# 2️⃣ SUBJECT TABLE
# ==================================

class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)

    academic_level_id = Column(Integer, ForeignKey("academic_levels.id"))

    academic_level = relationship("AcademicLevel", back_populates="subjects")
    exams = relationship("Exam", back_populates="subject")
    assignments = relationship("TeacherAssignment", back_populates="subject")


# ==================================
# 3️⃣ TEACHER TABLE
# ==================================

class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True)
    teacher_id = Column(String, unique=True, index=True)
    name = Column(String)
    password = Column(String)

    assignments = relationship("TeacherAssignment", back_populates="teacher", cascade="all, delete")


# ==================================
# 4️⃣ TEACHER ASSIGNMENT TABLE
# ==================================

class TeacherAssignment(Base):
    __tablename__ = "teacher_assignments"

    id = Column(Integer, primary_key=True)

    teacher_id = Column(Integer, ForeignKey("teachers.id"))
    academic_level_id = Column(Integer, ForeignKey("academic_levels.id"))
    subject_id = Column(Integer, ForeignKey("subjects.id"))

    teacher = relationship("Teacher", back_populates="assignments")
    academic_level = relationship("AcademicLevel", back_populates="assignments")
    subject = relationship("Subject", back_populates="assignments")


# ==================================
# 5️⃣ STUDENT TABLE
# ==================================

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True)
    student_id = Column(String, unique=True, index=True)
    name = Column(String)
    password = Column(String)

    academic_level_id = Column(Integer, ForeignKey("academic_levels.id"))
    academic_level = relationship("AcademicLevel", back_populates="students")

    submissions = relationship("Submission", back_populates="student", cascade="all, delete")


# ==================================
# 6️⃣ EXAM TABLE
# ==================================

class Exam(Base):
    __tablename__ = "exams"


    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(String, unique=True, index=True)

    academic_level_id = Column(Integer, ForeignKey("academic_levels.id"), index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), index=True)

    chapter = Column(String)
    duration = Column(String)

    created_by = Column(String, index=True)
    status = Column(String, default="CREATED")

    exam_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    academic_level = relationship("AcademicLevel", back_populates="exams")
    subject = relationship("Subject", back_populates="exams")

    questions = relationship("Question", back_populates="exam", cascade="all, delete")
    submissions = relationship("Submission", back_populates="exam", cascade="all, delete")
    
    deadline = Column(DateTime, nullable=True)


# ==================================
# 7️⃣ QUESTION TABLE
# ==================================

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)

    question_number = Column(Integer)
    exam_id = Column(Integer, ForeignKey("exams.id"), index=True)

    part = Column(String)
    question_type = Column(String)

    question_text = Column(Text)
    max_marks = Column(Integer)

    correct_option = Column(String, nullable=True)
    correct_answer_text = Column(Text, nullable=True)

    llm_generated_answer = Column(Text, nullable=True)
    teacher_final_answer = Column(Text, nullable=True)
    is_answer_edited = Column(Boolean, default=False)

    exam = relationship("Exam", back_populates="questions")
    options = relationship("Option", back_populates="question", cascade="all, delete")
    responses = relationship("StudentResponse", back_populates="question", cascade="all, delete")


# ==================================
# 8️⃣ OPTION TABLE
# ==================================

class Option(Base):
    __tablename__ = "options"

    id = Column(Integer, primary_key=True, index=True)

    question_id = Column(Integer, ForeignKey("questions.id"))

    option_text = Column(Text)
    is_correct = Column(Boolean, default=False)

    question = relationship("Question", back_populates="options")


# ==================================
# 9️⃣ SUBMISSION TABLE
# ==================================

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True)

    student_id = Column(Integer, ForeignKey("students.id"), index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), index=True)

    grading_mode = Column(String, default="STRICT")

    uploaded_pdf_path = Column(String)
    extracted_text = Column(Text)

    ai_total_marks = Column(Integer, default=0)
    final_total_marks = Column(Integer, default=0)

    status = Column(String, default="UPLOADED")

    submitted_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="submissions")
    exam = relationship("Exam", back_populates="submissions")


# ==================================
# 🔟 STUDENT RESPONSE TABLE
# ==================================

class StudentResponse(Base):
    __tablename__ = "student_responses"

    id = Column(Integer, primary_key=True, index=True)

    submission_id = Column(Integer, ForeignKey("submissions.id", ondelete="CASCADE"), index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), index=True)

    selected_option_id = Column(Integer, ForeignKey("options.id"), nullable=True)

    answer_text = Column(Text, nullable=True)

    ai_is_correct = Column(Boolean, nullable=True)
    ai_marks_awarded = Column(Integer, default=0)
    ai_feedback = Column(Text, nullable=True)

    teacher_marks_awarded = Column(Integer, nullable=True)
    teacher_feedback = Column(Text, nullable=True)

    final_marks = Column(Integer, default=0)

    evaluated_status = Column(String, default="PENDING")

    question = relationship("Question", back_populates="responses")
    submission = relationship("Submission", backref="responses")


# ==================================
# CREATE TABLES
# ==================================

Base.metadata.create_all(bind=engine)


# ==================================
# DB SESSION DEPENDENCY
# ==================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================================
# SAVE EXAM FUNCTION
# ==================================

def save_exam_to_db(db, metadata, exam_data):

    db_exam = Exam(
        exam_id=metadata["exam_id"],
        academic_level_id=metadata["academic_level_id"],
        subject_id=metadata["subject_id"],
        chapter=exam_data.get("chapter"),
        duration=exam_data.get("duration"),
        created_by=metadata["created_by"],
        status=metadata["status"],
        exam_json=json.dumps(exam_data)
    )

    db.add(db_exam)
    db.commit()
    db.refresh(db_exam)

    parts = exam_data.get("parts", {})
    question_counter = 1

    for part_name, part_data in parts.items():

        for q in part_data.get("questions", []):

            if "options" in q:
                question_type = "MCQ"
                max_marks = 1
            elif part_name == "Part B":
                question_type = "SHORT"
                max_marks = 2
            else:
                question_type = "LONG"
                max_marks = 5

            db_question = Question(
                question_number=question_counter,
                exam_id=db_exam.id,
                part=part_name,
                question_type=question_type,
                question_text=q.get("question"),
                max_marks=max_marks,
                correct_option=q.get("correct_option"),
                correct_answer_text=q.get("model_answer"),
                llm_generated_answer=q.get("model_answer"),
                teacher_final_answer=q.get("model_answer"),
                is_answer_edited=False
            )

            db.add(db_question)
            db.commit()
            db.refresh(db_question)

            if question_type == "MCQ":
                for opt in q.get("options", []):
                    option_letter = opt.split(")")[0].strip()

                    db_option = Option(
                        question_id=db_question.id,
                        option_text=opt,
                        is_correct=(option_letter == q.get("correct_option"))
                    )

                    db.add(db_option)

                db.commit()

            question_counter += 1

    return db_exam


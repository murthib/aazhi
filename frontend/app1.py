import streamlit as st
import requests
import json
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from datetime import date, timedelta


# ==================================
# APPLICATION SETTINGS
# ==================================

APP_SETTINGS = {
    "AUTO_GRADING_AFTER_SUBMISSION": True  # 🔁 Toggle this
}

# API_URL = "http://127.0.0.1:8000"

API_URL = "https://aazhi-c2yt.onrender.com"

st.set_page_config(page_title="EduEval AI", layout="wide")



# =====================================================
# PDF GENERATION FUNCTION (UNCHANGED)
# =====================================================

def generate_pdf(metadata, exam):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # ==============================
    # 📘 HEADER
    # ==============================

    elements.append(Paragraph("CBSE Examination Paper", styles["Heading1"]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(f"Exam ID: {metadata.get('exam_id')}", styles["Normal"]))
    elements.append(Paragraph(f"Created By: {metadata.get('created_by')}", styles["Normal"]))

    # 🔥 Academic Level from metadata (NOT AI)
    elements.append(
        Paragraph(f"Class: {metadata.get('academic_level_name')}", styles["Normal"])
    )

    elements.append(Paragraph(f"Subject: {exam.get('subject')}", styles["Normal"]))
    elements.append(Paragraph(f"Chapter: {exam.get('chapter')}", styles["Normal"]))
    elements.append(Paragraph(f"Duration: {exam.get('duration')}", styles["Normal"]))
    elements.append(Spacer(1, 20))

    # ==============================
    # 📄 QUESTIONS
    # ==============================

    parts = exam.get("parts", {})
    question_number = 1  # 🔥 Global counter

    for part_name, part_data in parts.items():

        elements.append(Paragraph(part_name, styles["Heading2"]))
        elements.append(Spacer(1, 10))

        for q in part_data.get("questions", []):

            elements.append(
                Paragraph(f"{question_number}. {q['question']}", styles["Normal"])
            )
            elements.append(Spacer(1, 6))

            # MCQ Options
            if "options" in q:
                for opt in q["options"]:
                    elements.append(
                        Paragraph(f"- {opt}", styles["Normal"])
                    )
                    elements.append(Spacer(1, 4))

            elements.append(Spacer(1, 10))

            question_number += 1  # 🔥 Continuous numbering

        elements.append(Spacer(1, 20))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ==================================
# ROLE SELECTION
# ==================================

mode = st.sidebar.radio(
    "Select Role",
    ["Teacher", "Student"]
)

# =====================================================
# TEACHER SECTION
# =====================================================

if mode == "Teacher":

    st.title("🎓 EduEval AI - Teacher Portal")

    # -----------------------------
    # 🔐 TEACHER LOGIN
    # -----------------------------

    if "teacher_id" not in st.session_state:

        st.subheader("Teacher Login")

        tid = st.text_input("Teacher ID")
        pwd = st.text_input("Password", type="password")

        if st.button("Login"):

            response = requests.post(
                f"{API_URL}/teacher-login",
                json={"teacher_id": tid, "password": pwd}
            )

            if response.status_code == 200:
                data = response.json()

                if data.get("success"):
                    st.session_state["teacher_id"] = data["teacher_id"]
                    st.session_state["teacher_name"] = data["name"]
                    st.success("Login successful")
                    st.rerun()
                else:
                    st.error("Invalid credentials")

    # -----------------------------
    # 🎯 AFTER LOGIN
    # -----------------------------

    else:

        teacher_id = st.session_state["teacher_id"]

        st.sidebar.success(f"Welcome {st.session_state['teacher_name']}")

        if st.sidebar.button("Logout"):
            st.session_state.clear()
            st.rerun()

        # ---------------------------------
        # 📚 TEACHER NAVIGATION MENU
        # ---------------------------------

        teacher_menu = st.sidebar.radio(
            "Teacher Menu",
            [
                "Past Exams",
                "Generate Exam",
                "Review Submissions"
            ]
        )

        # ==================================
        # 📊 DASHBOARD
        # ==================================

        if teacher_menu == "Dashboard":

            dashboard_response = requests.get(
                f"{API_URL}/teacher-dashboard/{teacher_id}"
            )

            if dashboard_response.status_code == 200:

                stats = dashboard_response.json()

                st.markdown("## 📊 Teacher Dashboard")

                col1, col2, col3 = st.columns(3)
                col1.metric("Total Exams", stats["total_exams"])
                col2.metric("Published Exams", stats["published_exams"])
                col3.metric("Draft Exams", stats["draft_exams"])

                col4, col5 = st.columns(2)
                col4.metric("Submissions", stats["total_submissions"])
                col5.metric("Results Published", stats["results_published"])

                st.markdown("### 🎯 Student Performance")

                col6, col7, col8 = st.columns(3)
                col6.metric("Highest", stats["highest_mark"])
                col7.metric("Lowest", stats["lowest_mark"])
                col8.metric("Average", stats["average_mark"])

        # ==================================
        # 📝 GENERATE EXAM
        # ==================================

        elif teacher_menu == "Generate Exam":

            st.markdown("## 📝 Generate Exam")

            # 👉 MOVE YOUR EXISTING:
            # assignment fetch
            # level selection
            # subject selection
            # bloom config
            # generate exam button
            # show generated exam
            # publish logic
            #
            # Paste that entire block here unchanged


            # =============================
            # 📘 FETCH ASSIGNMENTS
            # =============================

            assignment_response = requests.get(
                f"{API_URL}/teacher-assignments/{teacher_id}"
            )

            assignments = assignment_response.json()

            if not assignments:
                st.warning("No subject assignments found.")
                st.stop()

            # Build AcademicLevel → Subjects map
            level_map = {}
            for a in assignments:
                level_id = a["academic_level_id"]
                if level_id not in level_map:
                    level_map[level_id] = {
                        "name": a["academic_level_name"],
                        "subjects": []
                    }

                level_map[level_id]["subjects"].append({
                    "id": a["subject_id"],
                    "name": a["subject_name"]
                })

            # =============================
            # 🎓 SELECT ACADEMIC LEVEL
            # =============================

            selected_level_id = st.selectbox(
                "Select Academic Level",
                options=list(level_map.keys()),
                format_func=lambda x: level_map[x]["name"]
            )

            subjects = level_map[selected_level_id]["subjects"]

            selected_subject = st.selectbox(
                "Select Subject",
                options=subjects,
                format_func=lambda x: x["name"]
            )

            chapter = st.text_input("Chapter")
            duration = st.selectbox("Exam Duration", ["1 hour", "2 hours", "3 hours"])

            st.markdown("---")
            st.markdown("## Configure Bloom Levels")

            partA_bloom = st.selectbox("Part A (MCQ)", ["Remember", "Understand"])
            partB_bloom = st.selectbox("Part B (Short)", ["Understand", "Apply"])
            partC_bloom = st.selectbox("Part C (Long)", ["Apply", "Analyze"])


            # =============================
            # 🚀 GENERATE EXAM
            # =============================

            if st.button("🚀 Generate Exam Paper"):

                payload = {
                    "teacher_id": teacher_id,
                    "academic_level_id": selected_level_id,
                    "subject_id": selected_subject["id"],
                    "chapter": chapter,
                    "duration": duration,
                    "partA_bloom": partA_bloom,
                    "partB_bloom": partB_bloom,
                    "partC_bloom": partC_bloom
                }

                with st.spinner("Generating exam paper using AI..."):
                    response = requests.post(
                        f"{API_URL}/generate-exam",
                        json=payload
                    )

                if response.status_code == 200:
                    raw_response = response.json()

                    metadata = raw_response.get("metadata", {})
                    exam_data = raw_response.get("exam", {})

                    if isinstance(exam_data, str):
                        exam_data = exam_data.strip()
                        if exam_data.startswith("```"):
                            exam_data = exam_data.replace("```json", "").replace("```", "").strip()
                        exam_data = json.loads(exam_data)

                    st.session_state["metadata"] = metadata
                    st.session_state["exam"] = exam_data
                    st.session_state["db_exam_id"] = raw_response.get("db_exam_id")

                    st.success("✅ Exam Created Successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to generate exam")
                    st.write(response.json())


            # =============================
            # 📄 SHOW GENERATED EXAM
            # =============================

            if "exam" in st.session_state:

                metadata = st.session_state["metadata"]
                exam = st.session_state["exam"]
                exam_info = exam.get("exam", exam)

                st.markdown("---")
                st.markdown("## 📄 Generated Question Paper")

                st.write(f"**Exam ID:** {metadata.get('exam_id')}")
                st.write(f"**Created At:** {metadata.get('created_at')}")
                st.write(f"**Status:** {metadata.get('status')}")

                st.write(f"**Subject:** {exam_info.get('subject')}")
                st.write(f"**Chapter:** {exam_info.get('chapter')}")
                st.write(f"**Duration:** {exam_info.get('duration')}")

                parts = exam_info.get("parts", {})

                question_number = 1

                for part_name, part_data in parts.items():
                    st.markdown(f"### {part_name}")

                    for q in part_data["questions"]:
                        st.write(f"**{question_number}. {q['question']}**")

                        if "options" in q:
                            for opt in q["options"]:
                                st.write(f"- {opt}")

                        st.markdown("---")
                        question_number += 1


                # PDF Download
                pdf_buffer = generate_pdf(metadata, exam_info)

                st.download_button(
                    label="📥 Download PDF",
                    data=pdf_buffer,
                    file_name=f"{metadata.get('exam_id')}.pdf",
                    mime="application/pdf"
                )

                # =============================
                # 📢 PUBLISH BUTTON
                # =============================

                if metadata.get("status") == "CREATED":

                    if st.button("📢 Publish Exam"):

                        db_exam_id = st.session_state.get("db_exam_id")

                        if db_exam_id:

                            publish_response = requests.put(
                                f"{API_URL}/publish-exam/{db_exam_id}"
                            )

                            if publish_response.status_code == 200:

                                st.success("Exam Published Successfully!")
                                metadata["status"] = "PUBLISHED"
                                st.rerun()

                            else:
                                st.error(f"Publish failed: {publish_response.text}")










        # ==================================
        # 📜 PAST EXAMS
        # ==================================

        elif teacher_menu == "Past Exams":

            import pandas as pd

            st.markdown("## 📜 Past Exams")

            response = requests.get(f"{API_URL}/exams/{teacher_id}")

            if response.status_code == 200:

                exams = response.json()

                if not exams:
                    st.info("No exams found.")
                else:

                    # Table Header
                    header_cols = st.columns(10)
                    headers = [
                        "Exam ID", "Subject", "Chapter", "Status",
                        "Deadline", "Submissions", "AI Evaluated",
                        "Results Published", "PDF", "Action (Publish question paper)"
                    ]

                    for col, header in zip(header_cols, headers):
                        col.markdown(f"**{header}**")

                    st.markdown("---")

                    # Table Rows
                    for exam in exams:

                        row_cols = st.columns(10)

                        row_cols[0].write(exam["exam_id"])
                        row_cols[1].write(exam["subject"])
                        row_cols[2].write(exam["chapter"])
                        row_cols[3].write(exam["status"])
                        row_cols[4].write(exam["deadline"] or "-")
                        row_cols[5].write(exam["submission_count"])
                        row_cols[6].write(exam["ai_evaluated_count"])
                        row_cols[7].write(exam["results_published_count"])

                        # PDF Link
                        if exam.get("pdf_link"):
                            row_cols[8].markdown(
                                f"[Download]({API_URL}{exam['pdf_link']})"
                            )
                        else:
                            row_cols[8].write("-")

                        # ✅ Publish Button Logic
                        if exam["status"] == "CREATED":

                            if row_cols[9].button(
                                "📢 Publish",
                                key=f"publish_{exam['exam_id']}"
                            ):

                                deadline_date = date.today() + timedelta(days=15)

                                publish_response = requests.put(
                                    f"{API_URL}/publish-exam/{exam['exam_id']}",
                                    params={"deadline": deadline_date}
                                )

                                if publish_response.status_code == 200:
                                    st.success("Exam Published Successfully!")
                                    st.rerun()
                                else:
                                    st.error(publish_response.json()["detail"])

                        else:
                            row_cols[9].write("✅ Published")

            else:
                st.error("Failed to fetch past exams")
                
                                

        # ==================================
        # 📝 REVIEW SUBMISSIONS
        # ==================================

        elif teacher_menu == "Review Submissions":

            st.markdown("## 📝 Review Submissions")


            response = requests.get(f"{API_URL}/submissions-for-review")

            if response.status_code != 200:
                st.error("Failed to fetch submissions.")
            else:
                submissions = response.json()

                if not submissions:
                    st.info("No submissions available for review.")
                else:
                    submission_options = {
                        f"Submission {s['id']} | Student {s['student_id']} | Exam {s['exam_id']}":
                        s["id"]
                        for s in submissions
                    }

                    selected = st.selectbox("Select Submission", list(submission_options.keys()))
                    submission_id = submission_options[selected]

                    grading_mode = st.selectbox(
                        "Select Grading Mode",
                        ["STRICT", "MODERATE", "LENIENT"]
                    )

                    if st.button("🚀 Run AI Evaluation"):
                        eval_response = requests.post(
                            f"{API_URL}/evaluate-submission/{submission_id}?grading_mode={grading_mode}"
                        )
                        if eval_response.status_code == 200:
                            st.success("AI Evaluation completed!")
                        else:
                            st.error("Evaluation failed.")

                    review_response = requests.get(
                        f"{API_URL}/submission-review/{submission_id}"
                    )

                    if review_response.status_code == 200:
                        review_data = review_response.json()

                        st.markdown(f"### Status: {review_data['status']}")
                        st.markdown(f"### 🤖 AI Total: {review_data['ai_total_marks']}")
                        st.markdown(f"### 🏁 Final Total: {review_data['final_total_marks']}")

                        updates = []

                        for q in review_data["questions"]:
                            st.markdown("---")
                            st.write(f"### Q{q['question_number']} ({q['max_marks']} marks)")
                            st.write("**Student Answer:**", q["student_answer"])
                            st.write("**AI Marks:**", q["ai_marks"])
                            st.write("**AI Feedback:**", q["ai_feedback"])

                            teacher_marks = st.number_input(
                                f"Teacher Marks for Q{q['question_number']}",
                                min_value=0,
                                max_value=q["max_marks"],
                                value=q["teacher_marks"],
                                key=f"marks_{q['response_id']}"
                            )

                            teacher_feedback = st.text_input(
                                f"Teacher Feedback for Q{q['question_number']}",
                                value=q["teacher_feedback"] or "",
                                key=f"feedback_{q['response_id']}"
                            )

                            updates.append({
                                "response_id": q["response_id"],
                                "teacher_marks": teacher_marks,
                                "teacher_feedback": teacher_feedback
                            })

                        # =============================
                        # 📢 PUBLISH RESULT
                        # =============================

                        if review_data["status"] != "RESULT_PUBLISHED":

                            if st.button("📢 Publish Result"):

                                clean_updates = []

                                for update in updates:
                                    clean_updates.append({
                                        "response_id": int(update["response_id"]),
                                        "teacher_marks": int(update["teacher_marks"]),
                                        "teacher_feedback": (
                                            str(update["teacher_feedback"])
                                            if update["teacher_feedback"]
                                            else None
                                        )
                                    })

                                # Save teacher review
                                save_response = requests.post(
                                    f"{API_URL}/teacher-review/{submission_id}",
                                    json=clean_updates
                                )

                                if save_response.status_code != 200:
                                    st.error("Failed to save teacher review")
                                    st.stop()

                                # Publish result
                                publish_response = requests.post(
                                    f"{API_URL}/publish-result/{submission_id}"
                                )

                                if publish_response.status_code == 200:
                                    st.success("Result published!")
                                    st.rerun()
                                else:
                                    st.error("Publish failed")

                        else:
                            st.warning("Result already published. Locked.")

# =====================================================
# STUDENT SECTION (UNCHANGED)
# =====================================================

elif mode == "Student":

    st.title("🎓 Student Portal")

    # 🔐 LOGIN CHECK
    if "student_id" not in st.session_state:

        st.subheader("Login")

        sid = st.text_input("Student ID")
        pwd = st.text_input("Password", type="password")

        if st.button("Login"):

            response = requests.post(
                f"{API_URL}/student-login",
                json={"student_id": sid, "password": pwd}
            )

            if response.status_code == 200:
                data = response.json()

                if data["success"]:
                    st.session_state["student_id"] = data["student_id"]
                    st.session_state["student_name"] = data["name"]
                    st.success("Login successful")
                    st.rerun()
                else:
                    st.error("Invalid credentials")

    # 👇 THIS ELSE BELONGS TO: if "student_id" not in st.session_state
    else:

        student_id = st.session_state["student_id"]

        st.sidebar.success(f"Welcome {st.session_state['student_name']}")

        if st.sidebar.button("Logout"):
            st.session_state.clear()
            st.rerun()

        student_menu = st.sidebar.radio(
            "Student Menu",
            ["Available Exams", "My Results", "📘 Subject Insights"]
        )

        # ==================================
        # 📊 DASHBOARD
        # ==================================

        if student_menu == "Dashboard":

            response = requests.get(
                f"{API_URL}/student-dashboard/{student_id}"
            )

            exams = response.json()

            performance_response = requests.get(
                f"{API_URL}/student-performance/{student_id}"
            )

            if performance_response.status_code == 200:

                stats = performance_response.json()

                st.markdown("## 📊 Your Academic Dashboard")

                col1, col2, col3 = st.columns(3)
                col1.metric("Total Exams", stats["total_exams"])
                col2.metric("Exams Attempted", stats["attempted"])
                col3.metric("Results Published", stats["results_published"])

                col4, col5 = st.columns(2)
                col4.metric("Pending Results", stats["pending_results"])
                col5.metric("Average Mark", stats["average_mark"])

                st.markdown("### 🎯 Performance Overview")

                col6, col7, col8 = st.columns(3)
                col6.metric("Highest Mark", stats["highest_mark"])
                col7.metric("Lowest Mark", stats["lowest_mark"])
                col8.metric("Overall %", stats["overall_percentage"])

        # ==================================
        # 📚 AVAILABLE EXAMS
        # ==================================
        elif student_menu == "Available Exams":

            from datetime import datetime

            response = requests.get(
                f"{API_URL}/student-dashboard/{student_id}"
            )

            exams = response.json()

            st.markdown("## 📚 Available Exams")

            if not exams:
                st.info("No exams available.")
            else:

                # Table Header
                h1, h2, h3, h4, h5, h6, h7 = st.columns([2,2,2,2,2,1,1])
                h1.markdown("**Exam**")
                h2.markdown("**Subject**")
                h3.markdown("**Chapter**")
                h4.markdown("**Deadline**")
                h5.markdown("**Status**")
                h6.markdown("**📄**")
                h7.markdown("**🚀**")

                st.markdown("---")

                for exam in exams:

                    deadline = exam.get("deadline")

                    if deadline:
                        deadline_date = datetime.strptime(deadline, "%Y-%m-%d")
                        today = datetime.today()

                        if deadline_date < today:
                            deadline_display = f"❌ {deadline}"
                            overdue = True
                        else:
                            days_left = (deadline_date - today).days
                            deadline_display = f"{deadline} ({days_left}d)"
                            overdue = False
                    else:
                        deadline_display = "-"
                        overdue = False

                    col1, col2, col3, col4, col5, col6, col7 = st.columns([2,2,2,2,2,1,1])

                    col1.write(exam["exam_name"])
                    col2.write(exam["subject"])
                    col3.write(exam["chapter"])
                    col4.write(deadline_display)
                    col5.write(exam["status"])

                    # 📄 Question Paper Button
                    
                    col6.markdown(
                        f"""
                        <a href="{API_URL}/download-exam-pdf/{exam['exam_id']}" target="_blank">
                            <button style="
                                padding:6px 12px;
                                border-radius:6px;
                                border:1px solid #ccc;
                                background-color:#f8f9fa;
                                cursor:pointer;
                            ">
                                View
                            </button>
                        </a>
                        """,
                        unsafe_allow_html=True
                    )


                    # 🚀 Attempt Button
                    can_attempt = exam["status"] in ["NOT_ATTEMPTED", "RESULT_PUBLISHED"]

                    if col7.button(
                        "Attempt",
                        key=f"attempt_{exam['exam_id']}",
                        disabled=not can_attempt or overdue
                    ):
                        st.session_state["selected_exam"] = exam

                # ==================================
                # 🚀 Upload Section (Appears After Click)
                # ==================================

                if "selected_exam" in st.session_state:

                    selected_exam = st.session_state["selected_exam"]

                    st.markdown("---")
                    st.markdown(f"### 🚀 Upload Answer for {selected_exam['exam_name']}")

                    uploaded_file = st.file_uploader(
                        "Upload your PDF answer sheet",
                        type=["pdf"],
                        key="upload_section"
                    )

                    if uploaded_file:

                        with st.spinner("📤 Uploading and processing your answer sheet... Please wait..."):

                            files = {"file": uploaded_file}

                            upload_response = requests.post(
                                f"{API_URL}/submit-exam/{student_id}/{selected_exam['exam_id']}",
                                files=files
                            )

                        if upload_response.status_code == 200:

                            progress_bar = st.progress(0)
                            status_text = st.empty()

                            stages = [
                                "📄 Uploading answer sheet...",
                                "🔍 Extracting handwritten answers...",
                                "🧠 Evaluating responses with AI...",
                                "📊 Calculating marks and feedback...",
                                "✅ Finalizing your result..."
                            ]

                            import time

                            for i, stage in enumerate(stages):
                                status_text.markdown(f"**{stage}**")
                                progress_bar.progress((i + 1) * 20)
                                time.sleep(0.4)

                            st.success("🎉 AI Evaluation Completed Successfully!")
                            st.balloons()

                            time.sleep(1.5)
                            st.session_state.pop("selected_exam")
                            st.rerun()

        # ==================================
        # 🏆 MY RESULTS
        # ==================================

        elif student_menu == "My Results":

            response = requests.get(
                f"{API_URL}/student-dashboard/{student_id}"
            )

            exams = response.json()

            st.markdown("## 🏆 My Results")

            result_exams = [
                exam for exam in exams
                if exam["status"] in ["AI_EVALUATED", "RESULT_PUBLISHED"]
            ]

            if not result_exams:
                st.info("No results available yet.")
            else:

                # Header
                h1, h2, h3, h4, h5, h6, h7 = st.columns([2,2,2,2,2,2,1])

                h1.markdown("**Exam**")
                h2.markdown("**Subject**")
                h3.markdown("**Chapter**")
                h4.markdown("**Status**")
                h5.markdown("**🤖 AI Marks**")
                h6.markdown("**👩‍🏫 Final Marks**")
                h7.markdown("**📊**")

                st.markdown("---")

                for exam in result_exams:

                    col1, col2, col3, col4, col5, col6, col7 = st.columns([2,2,2,2,2,2,1])

                    col1.write(exam["exam_name"])
                    col2.write(exam["subject"])
                    col3.write(exam["chapter"])

                    # Status Badge
                    if exam["status"] == "AI_EVALUATED":
                        col4.warning("Awaiting Teacher Review")
                    elif exam["status"] == "RESULT_PUBLISHED":
                        col4.success("Final Published")
                    else:
                        col4.write(exam["status"])

                    # 🤖 AI Marks Column
                    ai_marks = exam.get("ai_total_marks")

                    if ai_marks is not None:
                        col5.info(f"{ai_marks}")
                    else:
                        col5.write("-")

                    # 👩‍🏫 Final Marks Column
                    final_marks = exam.get("final_total_marks")

                    if final_marks is not None:
                        col6.success(f"{final_marks}")
                    else:
                        col6.write("-")

                    # View Button
                    if col7.button("View", key=f"view_result_{exam['exam_id']}"):
                        st.session_state["selected_result_exam"] = exam

                        

                if "selected_result_exam" in st.session_state:

                    selected_exam = st.session_state["selected_result_exam"]

                    submission_response = requests.get(
                        f"{API_URL}/latest-submission/{student_id}/{selected_exam['exam_id']}"
                    )

                    submission_data = submission_response.json()

                    if "submission_id" in submission_data:

                        submission_id = submission_data["submission_id"]

                        result = requests.get(
                            f"{API_URL}/submission-result/{submission_id}"
                        ).json()

                        st.markdown("---")
                        st.markdown(f"## 📊 Detailed Result - {selected_exam['exam_name']}")

                        st.success(f"🏆 Final Marks: {result['final_total_marks']}")

                        # 🔽 Keep your existing question breakdown rendering here

                        # 🔥 THIS IS THE IMPORTANT PART — YOUR OLD LOOP
                        for q in result["questions"]:

                            st.markdown("---")
                            st.markdown(f"### Q{q['question_number']}")

                            st.write("📘 **Question:**")
                            st.write(q["question_text"])

                            if q.get("question_type") == "MCQ":

                                st.write("📝 **Options:**")

                                for opt in q["options"]:

                                    option_letter = opt["option_text"].split(")")[0]

                                    if option_letter == q["student_answer"]:
                                        if opt["is_correct"]:
                                            st.success(f"{opt['option_text']} ✔")
                                        else:
                                            st.error(f"{opt['option_text']} ✖")
                                    elif opt["is_correct"]:
                                        st.info(f"{opt['option_text']} ✔")
                                    else:
                                        st.write(opt["option_text"])

                            else:

                                st.write("✍ **Your Answer:**")
                                st.info(q["student_answer"])

                                st.write("✅ **Model Answer:**")
                                st.write(q["correct_answer"])

                            st.write("🎯 Marks:", q["marks_awarded"], "/", q["max_marks"])

                            if q.get("teacher_feedback"):
                                st.success(f"👩‍🏫 {q['teacher_feedback']}")

                            if q.get("ai_feedback"):
                                st.info(f"🤖 {q['ai_feedback']}")

        elif student_menu == "📘 Subject Insights":        
            response = requests.get(
            f"{API_URL}/student-dashboard/{student_id}"
            )

            exams = response.json()

            subjects = {}

            for exam in exams:
                if exam["status"] == "RESULT_PUBLISHED":
                    subjects[exam["subject"]] = exam["exam_id"]

            st.markdown("## 📘 Your Subject Growth Insights")

            subject_options = {
                exam["subject"]: exam["subject_id"]
                for exam in exams
                if exam["status"] == "RESULT_PUBLISHED"
            }

            if not subject_options:
                st.info("No subject insights available yet.")
            else:
                selected_subject = st.selectbox(
                    "Select Subject",
                    options=list(subject_options.keys())
                )

                subject_id = subject_options[selected_subject]        

            if st.button("🧠 Generate Subject Insight"):

                with st.spinner("Analyzing performance across exams..."):

                    analysis_response = requests.get(
                        f"{API_URL}/subject-analysis/{student_id}/{subject_id}"
                    )

                if analysis_response.status_code == 200:
                    analysis_data = analysis_response.json()

                    st.markdown("---")
                    st.markdown(analysis_data["analysis"])


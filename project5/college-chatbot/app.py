import os

from flask import Flask, render_template, request, session


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "college-chatbot-dev-secret")

CREATOR_INFO = {
    "first_name": "Nathan",
    "last_name": "Nguyen",
    "email": "nguye3np@gmail.com",
}

QUESTION_ANSWERS = {
    "internships": {
        "label": "What internship opportunities does the college provide?",
        "answer": (
            "The college supports internships through a network of corporate partners, "
            "regional employers, and nonprofit organizations that recruit students across "
            "multiple majors. Many programs also offer cooperative education placements, "
            "faculty-guided research internships, and project-based experiences that let "
            "students build practical skills before graduation. Career advisors work with "
            "students to identify opportunities, prepare application materials, and connect "
            "them with employers aligned to their academic goals."
        ),
    },
    "organizations": {
        "label": "What student organizations are available?",
        "answer": (
            "Students can choose from a wide range of organizations, including academic honor "
            "societies, student government, cultural associations, service clubs, intramural "
            "sports, and major-specific groups in areas like business, engineering, and health "
            "sciences. The college also promotes leadership development through entrepreneurial "
            "clubs, media organizations, and technology-focused communities. These groups help "
            "students build friendships, strengthen professional networks, and develop skills "
            "outside the classroom."
        ),
    },
    "study_abroad": {
        "label": "Does the college offer study abroad programs?",
        "answer": (
            "Yes, the college offers study abroad opportunities through semester exchanges, "
            "short-term faculty-led travel courses, and international partnership programs in "
            "several regions around the world. Students can select experiences that support "
            "their academic plan while gaining global perspective, cultural awareness, and "
            "valuable real-world experience. Advisors assist with program selection, transfer "
            "credit planning, and pre-departure preparation to make the process clear and "
            "accessible."
        ),
    },
    "career_services": {
        "label": "What career services are available after graduation?",
        "answer": (
            "Graduates continue to benefit from career support that includes resume and cover "
            "letter reviews, interview coaching, employer networking events, and access to job "
            "search resources. The college regularly hosts career fairs, alumni panels, and "
            "recruiting programs designed to connect students and graduates with hiring "
            "organizations. This continued support helps alumni navigate career transitions, "
            "strengthen their professional brand, and pursue long-term advancement."
        ),
    },
}

QUESTION_KEYWORDS = {
    "internships": [
        "internship",
        "internships",
        "co-op",
        "co op",
        "placement",
        "placements",
        "research",
        "career experience",
    ],
    "organizations": [
        "organization",
        "organizations",
        "club",
        "clubs",
        "student life",
        "activities",
        "groups",
        "society",
        "societies",
    ],
    "study_abroad": [
        "study abroad",
        "abroad",
        "exchange",
        "international",
        "travel course",
        "global program",
    ],
    "career_services": [
        "career",
        "careers",
        "job",
        "jobs",
        "employment",
        "resume",
        "interview",
        "job fair",
        "networking",
        "after graduation",
    ],
}

FALLBACK_ANSWER = (
    "I can currently help with four college inquiry topics: internship opportunities, "
    "student organizations, study abroad programs, and career services after graduation. "
    "Please ask about one of those areas so I can provide a detailed response."
)


def match_question(user_question):
    normalized_question = user_question.lower()

    for topic, keywords in QUESTION_KEYWORDS.items():
        if any(keyword in normalized_question for keyword in keywords):
            return topic

    return None


def validate_form(form_data):
    student_info = {
        "first_name": form_data.get("first_name", "").strip(),
        "last_name": form_data.get("last_name", "").strip(),
        "email": form_data.get("email", "").strip(),
    }
    user_question = form_data.get("question", "").strip()
    errors = []

    if not student_info["first_name"]:
        errors.append("First name is required.")
    if not student_info["last_name"]:
        errors.append("Last name is required.")
    if not student_info["email"]:
        errors.append("Email address is required.")
    if not user_question:
        errors.append("Please enter a college-related question.")

    return student_info, user_question, errors


@app.route("/", methods=["GET", "POST"])
def index():
    chat_history = session.get("chat_history", [])
    context = {
        "student_info": {"first_name": "", "last_name": "", "email": ""},
        "creator_info": CREATOR_INFO,
        "user_question": "",
        "chat_history": chat_history,
        "errors": [],
    }

    if request.method == "POST":
        student_info, user_question, errors = validate_form(request.form)
        context["student_info"] = student_info
        context["user_question"] = user_question
        context["errors"] = errors

        if not errors:
            matched_topic = match_question(user_question)

            if matched_topic:
                selected_answer = QUESTION_ANSWERS[matched_topic]["answer"]
            else:
                selected_answer = FALLBACK_ANSWER

            chat_history = chat_history + [
                {
                    "role": "user",
                    "label": student_info["first_name"] or "Student",
                    "text": user_question,
                },
                {
                    "role": "bot",
                    "label": "College Inquiry Bot",
                    "text": selected_answer,
                },
            ]
            session["chat_history"] = chat_history
            context["chat_history"] = chat_history
            context["user_question"] = ""

    return render_template("index.html", **context)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)

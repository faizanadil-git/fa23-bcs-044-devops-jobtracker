
# JobTrack
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
import requests
from urllib.parse import urlparse
import json
import re
from dotenv import load_dotenv

load_dotenv()  # loads .env file automatically

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
MONGO_URI = os.environ.get("MONGO_URI")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_URL = "https://api.groq.com/openai/v1/chat/completions"

# COMMENT JUST FOR CICD PIPELINING CHECK
#COMMENT JUST FOR CICD PIPELINING CHECK

client = MongoClient(MONGO_URI)
db = client["job_tracker"]
jobs = db["applications"]
users = db["users"]
debriefs = db["debriefs"]

# ── XP Config ────────────────────────────────────────────
XP_RULES = {
    "Applied":   10,
    "Interview": 30,
    "Offer":     100,
    "Rejected":  5,
}


BADGES = [
    {"id": "first_step",     "name": "First Step",        "desc": "Submit your first application",          "icon": "🚀", "condition": lambda s: s["total"] >= 1},
    {"id": "persistence",    "name": "Persistence King",  "desc": "Submit 10 applications",                 "icon": "👑", "condition": lambda s: s["total"] >= 10},
    {"id": "hustler",        "name": "Hustler",           "desc": "Submit 25 applications",                 "icon": "⚡", "condition": lambda s: s["total"] >= 25},
    {"id": "interview_ace",  "name": "Interview Ace",     "desc": "Land your first interview",              "icon": "🎯", "condition": lambda s: s.get("Interview", 0) >= 1},
    {"id": "multi_interview","name": "In Demand",         "desc": "Land 3 interviews",                      "icon": "🔥", "condition": lambda s: s.get("Interview", 0) >= 3},
    {"id": "offer_getter",   "name": "Offer Getter",      "desc": "Receive your first offer",               "icon": "💎", "condition": lambda s: s.get("Offer", 0) >= 1},
    {"id": "resilient",      "name": "Resilient",         "desc": "Keep going after 5 rejections",          "icon": "🛡️", "condition": lambda s: s.get("Rejected", 0) >= 5},
    {"id": "debriefer",      "name": "Debriefer",         "desc": "Complete your first interview debrief",  "icon": "📝", "condition": lambda s: s.get("debriefs", 0) >= 1},
]

def compute_xp_and_badges(uid):
    pipeline = [{"$match": {"user_id": uid}}, {"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    status_counts = {r["_id"]: r["count"] for r in jobs.aggregate(pipeline)}
    total = sum(status_counts.values())
    xp = sum(XP_RULES.get(s, 0) * c for s, c in status_counts.items())
    debrief_count = debriefs.count_documents({"user_id": uid})
    stats = {**status_counts, "total": total, "debriefs": debrief_count}
    earned = [{"id": b["id"], "name": b["name"], "desc": b["desc"], "icon": b["icon"]}
              for b in BADGES if b["condition"](stats)]
    level = max(1, xp // 100)
    xp_in_level = xp % 100
    return {"xp": xp, "level": level, "xp_in_level": xp_in_level, "badges": earned, "status_counts": status_counts, "total": total}

def ghosting_score(job):
    if job.get("status") not in ("Applied", "Interview"):
        return None
    created = job.get("created_at", "")
    try:
        dt = datetime.fromisoformat(created)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        days = (datetime.now(timezone.utc) - dt).days
    except:
        return None
    if days < 7:
        level = "safe"
    elif days < 14:
        level = "amber"
    elif days < 21:
        level = "red"
    else:
        level = "ghost"
    return {"days": days, "level": level}

def gemini(prompt):
    if not GEMINI_API_KEY:
        return "No API key configured."
    payload = {
        "model": "openai/gpt-oss-120b",
        "messages": [{"role": "user", "content": prompt}]
    }
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json"
    }
    r = requests.post(GEMINI_URL, json=payload, headers=headers, timeout=30)
    if r.status_code != 200:
        return f"API error: {r.status_code} — {r.text[:200]}"
    try:
        return r.json()["choices"][0]["message"]["content"]
    except:
        return "Could not parse response."
# ── Auth Helpers ──────────────────────────────────────────

def serialize(doc):
    doc["_id"] = str(doc["_id"])
    return doc

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated

def api_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

def uid():
    return session.get("user_id")

# ── Pages ─────────────────────────────────────────────────

@app.route("/")
def root():
    if "user_id" in session:
        return redirect(url_for("index"))
    return render_template("landing.html")  # ← change this line

@app.route("/login")
def login_page():
    return redirect(url_for("index")) if "user_id" in session else render_template("login.html")

@app.route("/register")
def register_page():
    return redirect(url_for("index")) if "user_id" in session else render_template("register.html")

@app.route("/dashboard")
@login_required
def index():
    return render_template("index.html", username=session.get("username"))

@app.route("/analytics")
@login_required
def analytics_page():
    return render_template("analytics.html", username=session.get("username"))

@app.route("/debrief/<job_id>")
@login_required
def debrief_page(job_id):
    job = jobs.find_one({"_id": ObjectId(job_id), "user_id": uid()})
    if not job:
        return redirect(url_for("index"))
    existing = debriefs.find_one({"job_id": job_id, "user_id": uid()})
    return render_template("debrief.html", username=session.get("username"),
                           job=serialize(job), existing=serialize(existing) if existing else None)

@app.route("/interview/<job_id>")
@login_required
def interview_page(job_id):
    job = jobs.find_one({"_id": ObjectId(job_id), "user_id": uid()})
    if not job:
        return redirect(url_for("index"))
    return render_template("interview.html", username=session.get("username"), job=serialize(job))

@app.route("/culture/<job_id>")
@login_required
def culture_page(job_id):
    job = jobs.find_one({"_id": ObjectId(job_id), "user_id": uid()})
    if not job:
        return redirect(url_for("index"))
    return render_template("culture.html", username=session.get("username"), job=serialize(job))

# ── Auth API ──────────────────────────────────────────────

@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username", "").strip().lower()
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")
    if not username or not email or not password:
        return jsonify({"error": "All fields required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    if users.find_one({"$or": [{"username": username}, {"email": email}]}):
        return jsonify({"error": "Username or email already exists"}), 409
    result = users.insert_one({"username": username, "email": email,
                                "password": generate_password_hash(password),
                                "created_at": datetime.utcnow().isoformat()})
    session["user_id"] = str(result.inserted_id)
    session["username"] = username
    return jsonify({"message": "Registered"}), 201

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    identifier = data.get("identifier", "").strip().lower()
    password   = data.get("password", "")
    user = users.find_one({"$or": [{"username": identifier}, {"email": identifier}]})
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid credentials"}), 401
    session["user_id"] = str(user["_id"])
    session["username"] = user["username"]
    return jsonify({"message": "Logged in", "username": user["username"]})

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})

# ── Jobs API ──────────────────────────────────────────────

@app.route("/api/jobs", methods=["GET"])
@api_login_required
def get_jobs():
    all_jobs = list(jobs.find({"user_id": uid()}).sort("created_at", -1))
    result = []
    for j in all_jobs:
        s = serialize(j)
        s["ghosting"] = ghosting_score(j)
        result.append(s)
    return jsonify(result)

@app.route("/api/jobs", methods=["POST"])
@api_login_required
def add_job():
    data = request.json
    job = {
        "user_id":    uid(),
        "company":    data.get("company", "").strip(),
        "role":       data.get("role", "").strip(),
        "status":     data.get("status", "Applied"),
        "location":   data.get("location", "").strip(),
        "salary":     data.get("salary", "").strip(),
        "link":       data.get("link", "").strip(),
        "notes":      data.get("notes", "").strip(),
        "deadline":   data.get("deadline", "").strip(),
        "checklist":  data.get("checklist", []),
        "created_at": datetime.utcnow().isoformat()
    }
    result = jobs.insert_one(job)
    job["_id"] = str(result.inserted_id)
    job["ghosting"] = ghosting_score(job)
    return jsonify(job), 201

@app.route("/api/jobs/<job_id>", methods=["PUT"])
@api_login_required
def update_job(job_id):
    data = request.json
    allowed = ["company", "role", "status", "location", "salary", "link", "notes", "deadline", "checklist"]
    update = {k: data[k] for k in allowed if k in data}
    jobs.update_one({"_id": ObjectId(job_id), "user_id": uid()}, {"$set": update})
    updated = jobs.find_one({"_id": ObjectId(job_id)})
    s = serialize(updated)
    s["ghosting"] = ghosting_score(updated)
    return jsonify(s)

@app.route("/api/jobs/<job_id>", methods=["DELETE"])
@api_login_required
def delete_job(job_id):
    jobs.delete_one({"_id": ObjectId(job_id), "user_id": uid()})
    return jsonify({"deleted": job_id})

# ── Stats & XP ────────────────────────────────────────────

@app.route("/api/stats", methods=["GET"])
@api_login_required
def stats():
    u = uid()
    pipeline = [{"$match": {"user_id": u}}, {"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    status_data = {r["_id"]: r["count"] for r in jobs.aggregate(pipeline)}
    all_jobs = list(jobs.find({"user_id": u}, {"created_at": 1}))
    monthly = {}
    for j in all_jobs:
        try:
            key = datetime.fromisoformat(j["created_at"]).strftime("%b %d")
            monthly[key] = monthly.get(key, 0) + 1
        except: pass
    company_pipe = [{"$match": {"user_id": u}}, {"$group": {"_id": "$company", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}, {"$limit": 5}]
    top_companies = [{"company": r["_id"], "count": r["count"]} for r in jobs.aggregate(company_pipe)]
    total = sum(status_data.values()) or 1
    xp_data = compute_xp_and_badges(u)
    return jsonify({
        "status": status_data,
        "timeline": monthly,
        "top_companies": top_companies,
        "success_rate": round((status_data.get("Offer", 0) / total) * 100, 1),
        "interview_rate": round(((status_data.get("Interview", 0) + status_data.get("Offer", 0)) / total) * 100, 1),
        "total": total,
        "xp": xp_data
    })

@app.route("/api/xp", methods=["GET"])
@api_login_required
def get_xp():
    return jsonify(compute_xp_and_badges(uid()))

# ── Debrief API ───────────────────────────────────────────

@app.route("/api/debrief/<job_id>", methods=["POST"])
@api_login_required
def save_debrief(job_id):
    data = request.json
    doc = {
        "user_id":        uid(),
        "job_id":         job_id,
        "hardest_q":      data.get("hardest_q", ""),
        "excited_about":  data.get("excited_about", ""),
        "went_well":      data.get("went_well", ""),
        "went_poorly":    data.get("went_poorly", ""),
        "followup":       data.get("followup", ""),
        "energy":         data.get("energy", 5),
        "overall":        data.get("overall", 5),
        "saved_at":       datetime.utcnow().isoformat()
    }
    debriefs.update_one({"job_id": job_id, "user_id": uid()}, {"$set": doc}, upsert=True)
    return jsonify({"message": "Debrief saved"})

@app.route("/api/debrief/<job_id>", methods=["GET"])
@api_login_required
def get_debrief(job_id):
    d = debriefs.find_one({"job_id": job_id, "user_id": uid()})
    return jsonify(serialize(d) if d else {})

# ── AI Endpoints ──────────────────────────────────────────

@app.route("/api/ai/culture", methods=["POST"])
@api_login_required
def ai_culture():
    data = request.json
    company  = data.get("company", "")
    role     = data.get("role", "")
    jd       = data.get("job_description", "")
    about    = data.get("about_us", "")
    prefs    = data.get("user_prefs", "")
    prompt = f"""You are a career coach and organizational psychologist. Analyze this company and job posting.

Company: {company}
Role: {role}

Job Description:
{jd}

About Us / Company Culture:
{about}

User's self-reported work preferences:
{prefs}

Provide a structured analysis with these exact sections:

## Culture Vibe
Describe the company culture in 2-3 sentences using vivid adjectives (e.g. "fast-paced and results-driven" or "collaborative and academic").

## Culture Match Score
Rate the match between the user's preferences and this company culture as X/10 with a one-line explanation.

## Language Mirror
List 6-8 specific keywords or phrases the user should naturally weave into their interview answers to resonate with this company. Format as a simple list.

## Watch Out For
2-3 potential culture friction points the user should be aware of.

## Tailored Advice
3 concrete, specific tips for this exact company and role.

Keep the tone honest, direct, and genuinely helpful."""
    return jsonify({"result": gemini(prompt)})

@app.route("/api/ai/interview/start", methods=["POST"])
@api_login_required
def ai_interview_start():
    data = request.json
    company = data.get("company", "")
    role    = data.get("role", "")
    prompt = f"""You are a professional recruiter at {company} interviewing a candidate for the {role} position.

Start the interview naturally. Introduce yourself briefly (make up a name), welcome the candidate, and ask your FIRST interview question. 

Mix behavioral, situational, and role-specific questions throughout the interview.
Ask only ONE question at a time.
Keep your messages concise — like a real interview.
Do not number your questions.
Start now."""
    return jsonify({"result": gemini(prompt)})

@app.route("/api/ai/interview/respond", methods=["POST"])
@api_login_required
def ai_interview_respond():
    data = request.json
    company  = data.get("company", "")
    role     = data.get("role", "")
    history  = data.get("history", [])
    answer   = data.get("answer", "")
    q_count  = data.get("question_count", 1)

    history_text = "\n".join([f"{'Recruiter' if m['role']=='ai' else 'Candidate'}: {m['text']}" for m in history])

    if q_count >= 5:
        prompt = f"""You are a recruiter at {company} interviewing for {role}.

Conversation so far:
{history_text}
Candidate: {answer}

This was the final answer. Wrap up the interview naturally — thank the candidate, mention next steps briefly, and then provide a "Confidence Score" section formatted exactly like this:

---
**Confidence Score: X/10**

**Strengths:** (2-3 bullet points of what came across well)
**Areas to improve:** (2-3 bullet points of constructive feedback)
**Overall impression:** (1-2 sentences)
---"""
    else:
        prompt = f"""You are a recruiter at {company} interviewing for {role}.

Conversation so far:
{history_text}
Candidate: {answer}

React briefly and naturally to their answer (1-2 sentences max), then ask your next interview question. Ask only ONE question. Keep it conversational."""

    return jsonify({"result": gemini(prompt)})


# ── Page Routes ───────────────────────────────────────────────────────────────

@app.route("/coverletter/<job_id>")
@login_required
def coverletter_page(job_id):
    job = jobs.find_one({"_id": ObjectId(job_id), "user_id": uid()})
    if not job:
        return redirect(url_for("index"))
    return render_template("coverletter.html", username=session.get("username"), job=serialize(job))


@app.route("/import")
@login_required
def import_page():
    return render_template("import_job.html", username=session.get("username"))


# ── Cover Letter API ──────────────────────────────────────────────────────────

@app.route("/api/ai/coverletter", methods=["POST"])
@api_login_required
def ai_coverletter():
    data = request.json
    company = data.get("company", "")
    role = data.get("role", "")
    jd = data.get("job_description", "")
    resume = data.get("resume", "")
    name = data.get("name", "The Applicant")
    email = data.get("email", "")
    tone = data.get("tone", "professional")
    length = data.get("length", "medium")
    extra = data.get("extra", "")

    tone_map = {
        "professional": "formal, polished, and confident",
        "enthusiastic": "energetic, passionate, and genuinely excited about the role",
        "concise": "extremely direct and to-the-point — no fluff whatsoever",
        "storytelling": "narrative-driven — open with a brief compelling story or moment",
        "casual": "warm, friendly, and conversational — like writing to a colleague",
    }
    length_map = {
        "short": "Keep it SHORT — around 150 words maximum. One strong paragraph.",
        "medium": "Keep it MEDIUM — around 250 words. Three tight paragraphs.",
        "long": "Write a FULL letter — around 400 words. Four paragraphs with depth.",
    }

    prompt = f"""You are an expert career coach and professional writer. Write a cover letter for this application.

Applicant name: {name}
{f"Applicant email: {email}" if email else ""}
Company: {company}
Role: {role}

Job Description:
{jd if jd else "Not provided — infer requirements from the company name and role."}

Applicant background / resume points:
{resume if resume else "Not provided — write a strong general letter for this role."}

Tone: {tone_map.get(tone, "professional")}
Length: {length_map.get(length, "Around 250 words.")}
{f"Special instructions: {extra}" if extra else ""}

Rules:
- Output ONLY the cover letter text — no meta-commentary, no notes, no explanations
- Do NOT use placeholder brackets like [Your Name] — use the actual name given
- Start with the salutation e.g. "Dear Hiring Manager," or "Dear {company} Team,"
- End with a proper sign-off and the applicant name
- Reference the company name and role specifically — make it feel genuinely tailored
- Avoid the cliche opener "I am writing to express my interest" — be stronger
- No filler phrases like "I am a passionate individual" or "I would be a great fit\""""

    result = gemini(prompt)
    return jsonify({"result": result})


# ── Helpers for import ────────────────────────────────────────────────────────

def _parse_ai_job_json(raw_text):
    """Extract JSON from AI response, handling markdown code fences."""
    import json, re
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError("No JSON found in AI response")


# ── Job Import API ────────────────────────────────────────────────────────────

@app.route("/api/ai/import/paste", methods=["POST"])
@api_login_required
def ai_import_paste():
    """Extract job fields from pasted job description text using AI."""
    import re
    data = request.json
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400

    prompt = f"""You are a job posting parser. Extract structured information from this job posting.

Job posting:
{text[:4000]}

Return ONLY a valid JSON object with these exact keys (empty string "" if not found):
{{
  "company": "company name",
  "role": "job title",
  "location": "city, country or Remote",
  "salary": "salary range or empty string",
  "link": "application URL if mentioned, else empty string",
  "notes": "2-3 sentence summary of the role and key requirements"
}}

Return ONLY the JSON. No explanation, no markdown, no code fences."""

    raw = gemini(prompt)
    try:
        extracted = _parse_ai_job_json(raw)
        clean = {k: str(extracted.get(k, "")).strip()
                 for k in ["company", "role", "location", "salary", "link", "notes"]}
        return jsonify(clean)
    except Exception as e:
        return jsonify({"error": f"Could not parse AI response: {str(e)}"}), 500


@app.route("/api/ai/import/url", methods=["POST"])
@api_login_required
def ai_import_url():
    """Fetch a LinkedIn/Indeed URL, extract page text, then parse with AI."""
    import re
    from urllib.parse import urlparse as _urlparse
    data = request.json
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        parsed = _urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return jsonify({"error": "Invalid URL"}), 400
    except Exception:
        return jsonify({"error": "Invalid URL"}), 400

    # Fetch page
    try:
        hdrs = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }
        resp = requests.get(url, headers=hdrs, timeout=15)
        resp.raise_for_status()
        page_text = resp.text
    except requests.exceptions.Timeout:
        return jsonify({"error": "Request timed out. Try pasting the description instead."}), 502
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Could not fetch URL: {str(e)[:100]}. Try pasting instead."}), 502

    # Strip HTML
    clean = re.sub(r"<style[^>]*>.*?</style>", " ", page_text, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"<script[^>]*>.*?</script>", " ", clean, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()

    if len(clean) < 100:
        return jsonify({
            "error": "Could not extract content. LinkedIn/Indeed may block this. Please paste the description text instead.",
            "company": "", "role": "", "location": "", "salary": "", "link": url, "notes": ""
        }), 200

    prompt = f"""You are a job posting parser. Extract structured information from this webpage text scraped from a job posting.

Webpage text:
{clean[:4000]}

Original URL: {url}

Return ONLY a valid JSON object with these exact keys (empty string "" if not found):
{{
  "company": "company name",
  "role": "job title",
  "location": "city, country or Remote",
  "salary": "salary range or empty string",
  "link": "{url}",
  "notes": "2-3 sentence summary of the role and key requirements"
}}

Return ONLY the JSON. No explanation, no markdown, no code fences."""

    raw = gemini(prompt)
    try:
        extracted = _parse_ai_job_json(raw)
        clean_out = {k: str(extracted.get(k, "")).strip()
                     for k in ["company", "role", "location", "salary", "link", "notes"]}
        if not clean_out.get("link"):
            clean_out["link"] = url
        return jsonify(clean_out)
    except Exception as e:
        return jsonify({"error": f"Could not parse AI response: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

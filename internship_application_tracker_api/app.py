"""
Internship Application Tracker REST API
Course: SW426 - Software Quality Engineering

Built with Flask + SQLite (through SQLAlchemy). Data is exchanged as JSON.
This file started from an instructor-provided CRUD API and was modified
as described in the comments marked [KEPT], [CHANGED] or [NEW].
"""

import json
import re
from datetime import date

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

# ---------------------------------------------------------------------------
# 1. Application and database setup  [KEPT]
# ---------------------------------------------------------------------------
app = Flask(__name__)
# "sqlite:///internships.db" -> Flask-SQLAlchemy creates the file
# instance/internships.db inside the project folder.
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///internships.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ---------------------------------------------------------------------------
# 2. Validation rules (constants)  [CHANGED: added field lists and limits]
# ---------------------------------------------------------------------------
ALLOWED_STATUSES = {"Applied", "Interview", "Accepted", "Rejected"}
REQUIRED_FIELDS = ("company_name", "role", "application_date", "status")
OPTIONAL_FIELDS = ("location", "notes")
ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS

# Maximum text lengths. The first three match the database column sizes.
MAX_LENGTHS = {"company_name": 120, "role": 120, "location": 120, "notes": 1000}

# Largest whole number SQLite can store as an ID (2 to the power 63, minus 1).
MAX_ID = 2**63 - 1

# Only the exact format YYYY-MM-DD is accepted (digits 0-9 only).
DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


# ---------------------------------------------------------------------------
# 3. Database model  [CHANGED: duplicate rule and never-reused IDs]
# ---------------------------------------------------------------------------
class Internship(db.Model):
    # Each class attribute becomes one column of the table "internship".
    __table_args__ = (
        # [NEW] Same company + role + date cannot be stored twice.
        db.UniqueConstraint(
            "company_name", "role", "application_date", name="uq_company_role_date"
        ),
        # [NEW] Tell SQLite never to reuse the ID of a deleted record.
        {"sqlite_autoincrement": True},
    )

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(120), nullable=False)
    application_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Applied")
    location = db.Column(db.String(120), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    def to_dict(self):
        """Convert one database row into a dictionary that can become JSON.  [KEPT]"""
        return {
            "id": self.id,
            "company_name": self.company_name,
            "role": self.role,
            "application_date": self.application_date.isoformat(),
            "status": self.status,
            "location": self.location,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# 4. Helper functions
# ---------------------------------------------------------------------------
def error(message, status_code, **extra):
    """Build a JSON error response.  [KEPT, now accepts extra details]"""
    body = {"error": message}
    body.update(extra)
    return jsonify(body), status_code


def parse_record_id(raw_id):
    """[NEW] Check that the ID in the URL is a positive whole number.

    Returns (id_as_int, None) if valid, or (None, error_response) if not.
    """
    looks_valid = raw_id.isascii() and raw_id.isdigit() and len(raw_id) <= 19
    if not looks_valid or not (1 <= int(raw_id) <= MAX_ID):
        return None, error("ID must be a positive whole number", 400, received=raw_id[:30])
    return int(raw_id), None


def read_json_object():
    """[CHANGED] Read the request body and make sure it is a JSON object.

    Returns (dictionary, None) if valid, or (None, error_response) if not.
    """
    if not request.is_json:
        return None, error("Content-Type must be application/json", 415)

    try:
        payload = json.loads(request.get_data(as_text=True))
    except ValueError:
        return None, error("Malformed JSON: the body is empty or not valid JSON", 400)

    if not isinstance(payload, dict):
        return None, error("Request body must be a JSON object, not a list or single value", 400)
    return payload, None


def validate_internship_data(payload):
    """[CHANGED] Validate a complete internship record.

    Used by both POST and PUT. Returns (clean_values, None) if valid,
    or (None, error_response) if not.
    """
    # 1. Reject fields we do not know about (also blocks "id" in the body).
    unknown = sorted(set(payload) - set(ALL_FIELDS))
    if unknown:
        return None, error("Unknown field(s)", 400, fields=unknown)

    # 2. All required fields must be present.
    missing = [field for field in REQUIRED_FIELDS if field not in payload]
    if missing:
        return None, error("Missing required fields", 400, fields=missing)

    clean = {}

    # 3. company_name and role: non-empty text within the length limit.
    for field in ("company_name", "role"):
        value = payload[field]
        if not isinstance(value, str) or not value.strip():
            return None, error(f"{field} must be a non-empty string", 400)
        value = value.strip()
        if len(value) > MAX_LENGTHS[field]:
            return None, error(f"{field} must be at most {MAX_LENGTHS[field]} characters", 400)
        clean[field] = value

    # 4. status: must be exactly one of the allowed values (case-sensitive).
    status = payload["status"]
    if not isinstance(status, str) or status not in ALLOWED_STATUSES:
        return None, error(
            "status must be one of the allowed values",
            400,
            allowed_values=sorted(ALLOWED_STATUSES),
        )
    clean["status"] = status

    # 5. application_date: a real calendar date written as YYYY-MM-DD.
    raw_date = payload["application_date"]
    if not isinstance(raw_date, str) or not DATE_PATTERN.fullmatch(raw_date):
        return None, error("application_date must be a real date in YYYY-MM-DD format", 400)
    try:
        clean["application_date"] = date.fromisoformat(raw_date)
    except ValueError:  # e.g. 2026-13-45 matches the pattern but is not a real date
        return None, error("application_date must be a real date in YYYY-MM-DD format", 400)

    # 6. location and notes: optional. Missing or null is stored as null.
    for field in OPTIONAL_FIELDS:
        value = payload.get(field)
        if value is not None:
            if not isinstance(value, str):
                return None, error(f"{field} must be a string or null", 400)
            value = value.strip()
            if len(value) > MAX_LENGTHS[field]:
                return None, error(f"{field} must be at most {MAX_LENGTHS[field]} characters", 400)
        clean[field] = value

    return clean, None


def save_changes():
    """[NEW] Commit to the database. Returns a 409 response if it is a duplicate."""
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()  # undo the failed change so the session stays usable
        return error("An application for this company, role and date already exists", 409)
    return None


# ---------------------------------------------------------------------------
# 5. Routes
# ---------------------------------------------------------------------------
@app.get("/")
def home():
    """Overview page, useful for checking that the server is running.  [KEPT]"""
    return jsonify({
        "message": "Internship Application Tracker API",
        "endpoints": {
            "create": "POST /api/internships",
            "read_all": "GET /api/internships",
            "read_one": "GET /api/internships/<id>",
            "update": "PUT /api/internships/<id>",
            "delete": "DELETE /api/internships/<id>",
        }
    }), 200


@app.post("/api/internships")
def create_internship():
    """CREATE: add a new application. Returns 201 with the created record."""
    payload, problem = read_json_object()
    if problem:
        return problem
    clean, problem = validate_internship_data(payload)
    if problem:
        return problem

    record = Internship(**clean)
    db.session.add(record)
    conflict = save_changes()
    if conflict:
        return conflict
    return jsonify(record.to_dict()), 201


@app.get("/api/internships")
def get_internships():
    """READ ALL: return every application as a JSON array.  [KEPT]"""
    records = Internship.query.order_by(Internship.id.asc()).all()
    return jsonify([record.to_dict() for record in records]), 200


@app.get("/api/internships/<record_id>")
def get_internship(record_id):
    """READ ONE: return one application, or 404 if it does not exist."""
    record_id, problem = parse_record_id(record_id)
    if problem:
        return problem
    record = db.session.get(Internship, record_id)
    if record is None:
        return error("Internship application not found", 404)
    return jsonify(record.to_dict()), 200


@app.put("/api/internships/<record_id>")
def update_internship(record_id):
    """UPDATE: replace an existing application with the full record sent.

    [CHANGED] The starter allowed partial updates. Following the assignment
    example, PUT now needs all required fields. Optional fields left out
    (location, notes) are set back to null.
    """
    record_id, problem = parse_record_id(record_id)
    if problem:
        return problem
    record = db.session.get(Internship, record_id)
    if record is None:
        return error("Internship application not found", 404)

    payload, problem = read_json_object()
    if problem:
        return problem
    clean, problem = validate_internship_data(payload)
    if problem:
        return problem

    for field, value in clean.items():
        setattr(record, field, value)
    conflict = save_changes()
    if conflict:
        return conflict
    return jsonify(record.to_dict()), 200


@app.delete("/api/internships/<record_id>")
def delete_internship(record_id):
    """DELETE: remove an application. Returns 200 with a confirmation message."""
    record_id, problem = parse_record_id(record_id)
    if problem:
        return problem
    record = db.session.get(Internship, record_id)
    if record is None:
        return error("Internship application not found", 404)

    db.session.delete(record)
    db.session.commit()
    return jsonify({"message": "Internship application deleted successfully", "id": record_id}), 200


# ---------------------------------------------------------------------------
# 6. Error handlers (always answer in JSON)
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(_error):
    return error("Endpoint not found", 404)


@app.errorhandler(405)
def method_not_allowed(_error):
    return error("HTTP method not allowed for this endpoint", 405)


@app.errorhandler(500)
def server_error(_error):
    """[NEW] Last safety net: unexpected problems still return JSON, not HTML."""
    db.session.rollback()
    return error("Internal server error", 500)


# ---------------------------------------------------------------------------
# 7. Create the database tables, then start the server  [KEPT]
# ---------------------------------------------------------------------------
with app.app_context():
    db.create_all()  # creates the table only if it does not already exist


if __name__ == "__main__":
    app.run(debug=True)
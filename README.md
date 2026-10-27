# Internship Application Tracker REST API

SW426 Software Quality Engineering, Problem Based Learning project
Mehran University of Engineering and Technology, SZAB Campus, Khairpur Mir's

- **Student:** Sindhu Sahito, K22SW004
- **Instructor:** Engr. Asmatullah Zubair
- **Batch:** K22SW

A REST API for managing internship applications. It supports Create, Read, Update and Delete (CRUD), stores data in a SQLite database through SQLAlchemy, exchanges data as JSON, and is tested with Postman.

## Academic note: starter code

This project started from a CRUD REST API that the course instructor provided and permitted students to use. The main changes I made are:

- PUT now replaces the whole record and requires all required fields.
- Invalid or very large IDs return a JSON 400 error instead of a generic or unhandled error.
- Deleted IDs are never reused (SQLite AUTOINCREMENT).
- Text length limits, strict `YYYY-MM-DD` date checking and consistent rejection of unknown fields.
- Separate error messages for malformed JSON and a wrong content type (415).
- An optional duplicate check (409 Conflict) and a JSON handler for unexpected errors (500).
- A new Postman collection with 28 requests and automated test scripts, and the helper script `show_db.py`.

The full comparison is in Section 4.3 of the project report.

## Requirements

- Windows with Python 3.10 or newer (developed and tested with Python 3.14.2)
- Postman (for the API tests)
- Optional: DB Browser for SQLite (to view the database)

## Setup and run (Windows PowerShell)

Open the project folder in a terminal and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

If PowerShell blocks the activation script, run this once in the same terminal and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

The server starts at **http://127.0.0.1:5000**. Opening that address in a browser shows an overview of the endpoints. The database file `instance/internships.db` is created automatically on the first start. Stop the server with `Ctrl + C`.

## Record format

| Field | Type | Required | Rules |
|---|---|---|---|
| id | Integer | Generated | Unique, never reused, not accepted in request bodies |
| company_name | Text | Yes | Not empty, at most 120 characters |
| role | Text | Yes | Not empty, at most 120 characters |
| application_date | Date | Yes | Exact format `YYYY-MM-DD`, a real date |
| status | Text | Yes | Exactly `Applied`, `Interview`, `Accepted` or `Rejected` |
| location | Text | No | At most 120 characters, or null |
| notes | Text | No | At most 1000 characters, or null |

Example request body:

```json
{
  "company_name": "Example Tech",
  "role": "Python Intern",
  "application_date": "2026-10-14",
  "status": "Applied",
  "location": "Remote",
  "notes": "Applied through the company website"
}
```

## Endpoints

| Operation | Method | URL | Success code |
|---|---|---|---|
| Create | POST | /api/internships | 201 Created |
| Read all | GET | /api/internships | 200 OK |
| Read one | GET | /api/internships/{id} | 200 OK |
| Update | PUT | /api/internships/{id} | 200 OK |
| Delete | DELETE | /api/internships/{id} | 200 OK |

Error responses are JSON, for example `{"error": "Internship application not found"}`.

| Code | Meaning |
|---|---|
| 400 | Invalid input: missing or invalid fields, malformed JSON, invalid ID |
| 404 | Record or endpoint not found |
| 405 | HTTP method not allowed |
| 409 | Duplicate record (same company, role and date) |
| 415 | Request body is not sent as application/json |
| 500 | Unexpected server error (returned as JSON) |

## Testing with Postman

1. Start the server (`python app.py`).
2. In Postman, choose Import and select `internship_api_tests.postman_collection.json`.
3. Run the whole collection from the top with the Collection Runner. Run it in order, because later requests use IDs saved by earlier ones.

The collection contains 28 requests (26 test cases and 2 support requests) with test scripts. In my run, all 85 checks passed and none failed. The manual test cases, expected and actual results and screenshots are in the project report.

## Inspecting the database

With the virtual environment active, run:

```powershell
python show_db.py
```

It prints the table definition and all stored rows. The file can also be opened (read-only) in DB Browser for SQLite.

## Project files

| File | Purpose |
|---|---|
| app.py | The whole application: configuration, model, validation, routes and error handlers |
| requirements.txt | Python dependencies |
| show_db.py | Prints the tables and rows of the SQLite database |
| internship_api_tests.postman_collection.json | Postman collection with automated tests |
| README.md | This file |
| .gitignore | Keeps .venv, the database and generated files out of Git |
| Screenshots | It contains the screenshots of postman vscode database and outputs |

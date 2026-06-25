"""EventLens — upload event data and get an automated data report."""

import os

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

import storage
from analysis import analyze_csv

ALLOWED_EXTENSIONS = {".csv"}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB upload cap

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

# Probe the database once at import time and pick MySQL or in-memory storage.
storage.init()


def _allowed(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def home():
    return render_template(
        "index.html",
        reports=storage.list_reports(),
        status=storage.storage_status(),
    )


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")
    if file is None or file.filename == "":
        flash("Please choose a CSV file to upload.", "error")
        return redirect(url_for("home"))

    if not _allowed(file.filename):
        flash("Only .csv files are supported.", "error")
        return redirect(url_for("home"))

    try:
        report = analyze_csv(file.stream, filename=file.filename)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("home"))
    except Exception:  # noqa: BLE001 - surface a friendly message, log the rest
        app.logger.exception("Failed to analyse uploaded file")
        flash("Something went wrong while analysing that file.", "error")
        return redirect(url_for("home"))

    report_id = storage.save_report(file.filename, report)
    return redirect(url_for("report", report_id=report_id))


@app.route("/report/<int:report_id>")
def report(report_id: int):
    record = storage.get_report(report_id)
    if record is None:
        abort(404)
    return render_template("report.html", record=record, report=record["report"])


@app.route("/report/<int:report_id>/delete", methods=["POST"])
def delete(report_id: int):
    if storage.delete_report(report_id):
        flash("Report deleted.", "success")
    else:
        flash("Report not found.", "error")
    return redirect(url_for("home"))


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404


@app.errorhandler(413)
def too_large(_):
    flash("That file is too large (10 MB max).", "error")
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)

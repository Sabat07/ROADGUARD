from flask import (
    Flask, request, redirect, url_for,
    render_template_string, send_from_directory
)
from werkzeug.utils import secure_filename
import json
import os
import uuid

app = Flask(__name__)

DATA_FILE = "reports.json"
UPLOAD_FOLDER = os.path.join(app.root_path, "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024


# -------------------- DATA FUNCTIONS --------------------

def load_reports():
    if not os.path.exists(DATA_FILE):
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data if isinstance(data, list) else []

    except (json.JSONDecodeError, OSError):
        return []


def save_reports(reports):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(reports, file, indent=4)


def get_report_id(report, index):
    return report.get("id", index + 1)


# -------------------- MAIN PAGE --------------------

@app.route("/")
def home():
    reports = load_reports()
    query = request.args.get("q", "").strip().lower()

    displayed_reports = []

    for index, original_report in reversed(list(enumerate(reports))):
        report = dict(original_report)
        report["id"] = get_report_id(report, index)
        report.setdefault("status", "Unresolved")

        searchable_text = (
            str(report["id"]) + " " +
            str(report.get("location", "")) + " " +
            str(report.get("description", ""))
        ).lower()

        if not query or query in searchable_text:
            displayed_reports.append(report)

    total = len(reports)

    resolved = sum(
        1 for report in reports
        if str(report.get("status", "")).lower() == "resolved"
    )

    unresolved = total - resolved

    map_reports = []

    for index, report in enumerate(reports):
        try:
            latitude = float(report["latitude"])
            longitude = float(report["longitude"])

            if (
                -90 <= latitude <= 90
                and -180 <= longitude <= 180
            ):
                map_reports.append({
                    "id": get_report_id(report, index),
                    "latitude": latitude,
                    "longitude": longitude,
                    "location": str(report.get("location", "")),
                    "description": str(report.get("description", "")),
                    "status": str(report.get("status", "Unresolved"))
                })

        except (KeyError, TypeError, ValueError):
            continue

    return render_template_string(
        PAGE,
        reports=displayed_reports,
        map_reports=map_reports,
        total=total,
        resolved=resolved,
        unresolved=unresolved,
        query=query
    )


# -------------------- SUBMIT REPORT --------------------

@app.route("/submit", methods=["POST"])
def submit():
    location = request.form.get("location", "").strip()
    description = request.form.get("description", "").strip()
    latitude = request.form.get("latitude", "").strip()
    longitude = request.form.get("longitude", "").strip()

    if not location or not description:
        return "Please enter both location and description.", 400

    if len(location) > 200 or len(description) > 2000:
        return "Your report is too long.", 400

    # Handle an optional photo upload.
    photo = request.files.get("photo")
    photo_filename = None

    if photo and photo.filename:
        safe_name = secure_filename(photo.filename)

        if "." not in safe_name:
            return "Invalid image filename.", 400

        extension = safe_name.rsplit(".", 1)[-1].lower()

        if extension not in ALLOWED_EXTENSIONS:
            return "Use PNG, JPG, JPEG or WebP images.", 400

        photo_filename = f"{uuid.uuid4().hex}.{extension}"
        photo_path = os.path.join(UPLOAD_FOLDER, photo_filename)

        try:
            photo.save(photo_path)
        except OSError:
            return "Unable to save the photo. Please try again.", 500

    reports = load_reports()

    existing_ids = [
        int(get_report_id(report, index))
        for index, report in enumerate(reports)
        if str(get_report_id(report, index)).isdigit()
    ]

    next_id = max(existing_ids, default=0) + 1

    new_report = {
        "id": next_id,
        "location": location,
        "description": description,
        "status": "Unresolved"
    }

    # Save coordinates if the user selected a map location.
    if latitude or longitude:
        try:
            lat = float(latitude)
            lon = float(longitude)

            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                return "Invalid map coordinates.", 400

            new_report["latitude"] = lat
            new_report["longitude"] = lon

        except ValueError:
            return "Invalid map coordinates.", 400

    # Attach the photo filename to the report.
    if photo_filename:
        new_report["photo"] = photo_filename

    reports.append(new_report)

    try:
        save_reports(reports)
    except OSError:
        return "Unable to save the report.", 500

    return redirect(url_for("home"))


# -------------------- DISPLAY UPLOADED PHOTOS --------------------

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )


# -------------------- RESOLVE REPORT --------------------

@app.route("/resolve/<int:report_id>", methods=["POST"])
def resolve(report_id):
    reports = load_reports()

    for index, report in enumerate(reports):
        if get_report_id(report, index) == report_id:
            report["status"] = "Resolved"
            break

    save_reports(reports)

    return redirect(url_for("home"))


# -------------------- WEBSITE DESIGN --------------------

PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>RoadGuard | Road Hazard Reporter</title>

    <link rel="stylesheet"
          href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">

    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #f3f6fb;
            color: #172033;
        }

        header {
            background: #14213d;
            color: white;
            padding: 24px 7%;
        }

        header h1 {
            margin: 0 0 8px;
            font-size: 30px;
        }

        header p {
            margin: 0;
            color: #d8e2f0;
        }

        main {
            max-width: 1100px;
            margin: 28px auto;
            padding: 0 18px;
        }

        .stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 24px;
        }

        .stat, .card {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 3px 15px #1720330d;
        }

        .stat h3 {
            margin: 0 0 10px;
            font-size: 14px;
            color: #64748b;
        }

        .stat strong {
            font-size: 28px;
        }

        .card {
            margin-bottom: 22px;
        }

        h2 {
            margin-top: 0;
        }

        label {
            display: block;
            font-weight: bold;
            margin: 14px 0 7px;
        }

        input, textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid #ccd5e1;
            border-radius: 7px;
            font: inherit;
        }

        textarea {
            resize: vertical;
            min-height: 90px;
        }

        input[type="file"] {
            background: #f8fafc;
        }

        button, .button {
            background: #1769e0;
            color: white;
            padding: 10px 15px;
            border: 0;
            border-radius: 7px;
            cursor: pointer;
            font: inherit;
            text-decoration: none;
            display: inline-block;
        }

        button:hover, .button:hover {
            background: #1054b8;
        }

        #map, #report-map {
            height: 350px;
            border-radius: 10px;
            margin-top: 12px;
            z-index: 1;
        }

        .hint {
            color: #64748b;
            font-size: 14px;
            line-height: 1.5;
        }

        .report {
            border: 1px solid #e1e7ef;
            border-radius: 9px;
            padding: 16px;
            margin-top: 14px;
            overflow-wrap: anywhere;
        }

        .report h3 {
            margin: 0 0 8px;
        }

        .report-photo {
            display: block;
            max-width: 100%;
            max-height: 350px;
            object-fit: contain;
            border-radius: 8px;
            margin: 12px 0;
        }

        .badge {
            display: inline-block;
            padding: 5px 9px;
            border-radius: 20px;
            font-size: 12px;
            background: #fff0d5;
            color: #875600;
        }

        .badge.resolved {
            background: #d9fbe7;
            color: #126638;
        }

        .search-row {
            display: flex;
            gap: 8px;
        }

        .search-row input {
            flex: 1;
            min-width: 0;
        }

        @media (max-width: 600px) {
            .stats {
                grid-template-columns: 1fr;
            }

            header {
                padding: 22px;
            }

            .search-row {
                flex-direction: column;
            }

            #map, #report-map {
                height: 300px;
            }
        }
    </style>
</head>

<body>
<header>
    <h1>🛡️ RoadGuard</h1>
    <p>Report road hazards. Help make roads safer.</p>
</header>

<main>
    <section class="stats">
        <div class="stat">
            <h3>Total Reports</h3>
            <strong>{{ total }}</strong>
        </div>

        <div class="stat">
            <h3>Unresolved</h3>
            <strong>{{ unresolved }}</strong>
        </div>

        <div class="stat">
            <h3>Resolved</h3>
            <strong>{{ resolved }}</strong>
        </div>
    </section>

    <section class="card">
        <h2>📍 Report a Road Hazard</h2>

        <p class="hint">
            Enter the location and describe the hazard.
            Select a point on the map or use GPS.
        </p>

        <form action="/submit" method="POST"
              enctype="multipart/form-data">

            <label for="location">Location or landmark</label>
            <input id="location" name="location"
                   maxlength="200"
                   placeholder="e.g. Near a bus stop" required>

            <label for="description">Describe the hazard</label>
            <textarea id="description" name="description"
                      maxlength="2000"
                      placeholder="e.g. Large pothole near a junction"
                      required></textarea>

            <label for="photo">📸 Upload a hazard photo</label>
            <input type="file" id="photo" name="photo"
                   accept="image/png,image/jpeg,image/webp"
                   capture="environment">

            <p class="hint">
                Optional. Choose a photo from your gallery or camera.
                Maximum upload size: 5 MB.
            </p>

            <label>Select the location on the map</label>

            <button type="button" onclick="useMyLocation()">
                📍 Use My Current Location
            </button>

            <p id="gps-message" class="hint">
                Or click directly on the map to select a location.
            </p>

            <div id="map"></div>

            <p id="coordinates" class="hint">
                No coordinates selected yet.
            </p>

            <input type="hidden" id="latitude" name="latitude">
            <input type="hidden" id="longitude" name="longitude">

            <button type="submit" style="margin-top: 12px;">
                Submit Report
            </button>
        </form>
    </section>

    <section class="card">
        <h2>🔎 Search Reports</h2>

        <form action="/" method="GET" class="search-row">
            <input name="q" value="{{ query }}"
                   placeholder="Search by ID, location or description">

            <button type="submit">Search</button>
            <a href="/" class="button">Clear</a>
        </form>
    </section>

    <section class="card">
        <h2>🗺️ Report Map</h2>

        <p class="hint">
            Pins show reports that have saved coordinates.
        </p>

        <div id="report-map"></div>
    </section>

    <section class="card">
        <h2>📋 Road Reports</h2>

        {% if reports %}
            {% for report in reports %}
                <article class="report">
                    <h3>Report #{{ report.id }}</h3>

                    <p>
                        <strong>Location:</strong>
                        {{ report.location }}
                    </p>

                    <p>
                        <strong>Description:</strong>
                        {{ report.description }}
                    </p>

                    {% if report.photo %}
                        <img
                            class="report-photo"
                            src="{{ url_for('uploaded_file', filename=report.photo) }}"
                            alt="Photo attached to report {{ report.id }}"
                            loading="lazy">
                    {% endif %}

                    <p>
                        <strong>Status:</strong>

                        <span class="badge
                        {% if report.status == 'Resolved' %}resolved{% endif %}">
                            {{ report.status }}
                        </span>
                    </p>

                    {% if report.status != 'Resolved' %}
                        <form action="/resolve/{{ report.id }}"
                              method="POST">
                            <button type="submit">
                                Mark as Resolved
                            </button>
                        </form>
                    {% endif %}
                </article>
            {% endfor %}
        {% else %}
            <p>No matching reports found.</p>
        {% endif %}
    </section>

    <p class="hint">
        RoadGuard is a student project. Reports are not automatically
        sent to municipal authorities.
    </p>
</main>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

<script>
    // Map for selecting a location.
    const selectionMap = L.map("map").setView(
        [19.0760, 72.8777], 11
    );

    L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            maxZoom: 19,
            attribution:
                '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }
    ).addTo(selectionMap);

    let selectionMarker = null;

    function selectLocation(lat, lon) {
        const point = L.latLng(lat, lon);

        document.getElementById("latitude").value = lat;
        document.getElementById("longitude").value = lon;

        document.getElementById("coordinates").textContent =
            "Selected coordinates: " +
            lat.toFixed(6) + ", " + lon.toFixed(6);

        if (selectionMarker) {
            selectionMarker.setLatLng(point);
        } else {
            selectionMarker = L.marker(point).addTo(selectionMap);
        }

        selectionMarker.bindPopup("Selected hazard location");
    }

    selectionMap.on("click", function(event) {
        selectLocation(event.latlng.lat, event.latlng.lng);
        selectionMarker.openPopup();
    });

    // GPS feature.
    function useMyLocation() {
        const message = document.getElementById("gps-message");
        message.textContent = "Detecting your location...";

        if (!navigator.geolocation) {
            message.textContent =
                "GPS is not supported by this browser.";
            return;
        }

        navigator.geolocation.getCurrentPosition(
            function(position) {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;

                selectLocation(lat, lon);
                selectionMap.setView([lat, lon], 16);
                selectionMarker.openPopup();

                message.textContent =
                    "Your location has been selected.";
            },
            function(error) {
                if (error.code === 1) {
                    message.textContent =
                        "Location permission denied. Allow access in browser settings.";
                } else {
                    message.textContent =
                        "Unable to detect location. Try again or click the map.";
                }
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            }
        );
    }

    // Map showing saved reports.
    const reportMap = L.map("report-map").setView(
        [19.0760, 72.8777], 11
    );

    L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            maxZoom: 19,
            attribution:
                '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }
    ).addTo(reportMap);

    const savedReports = {{ map_reports | tojson }};

    savedReports.forEach(function(report) {
        const marker = L.marker([
            report.latitude,
            report.longitude
        ]).addTo(reportMap);

        const popup = document.createElement("div");
        const title = document.createElement("strong");
        const location = document.createElement("p");
        const description = document.createElement("p");
        const status = document.createElement("p");

        title.textContent = "Report #" + report.id;
        location.textContent = "Location: " + report.location;
        description.textContent = "Hazard: " + report.description;
        status.textContent = "Status: " + report.status;

        popup.append(title, location, description, status);
        marker.bindPopup(popup);
    });

    if (savedReports.length > 0) {
        const points = savedReports.map(function(report) {
            return [report.latitude, report.longitude];
        });

        reportMap.fitBounds(points, {
            padding: [25, 25],
            maxZoom: 15
        });
    }
</script>
</body>
</html>
"""


# -------------------- START APPLICATION --------------------

if __name__ == "__main__":
    app.run(debug=True)
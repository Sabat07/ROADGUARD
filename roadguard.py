
import json
import os

FILE = "reports.json"


def load_reports():
    if os.path.exists(FILE):
        with open(FILE, "r") as f:
            return json.load(f)
    return []


def save_reports(reports):
    with open(FILE, "w") as f:
        json.dump(reports, f, indent=4)


def submit_report():
    location = input("Enter road location: ").strip()
    description = input("Describe the hazard: ").strip()

    if not location or not description:
        print("Error: Location and description cannot be empty.")
        return

    reports = load_reports()

    report_id = max(
        (r.get("id", 0) for r in reports), default=0
    ) + 1

    reports.append({
        "id": report_id,
        "location": location,
        "description": description,
        "status": "Reported"
    })

    save_reports(reports)
    print(f"\nReport saved! Your Report ID: {report_id}")


def view_reports():
    reports = load_reports()

    if not reports:
        print("\nNo reports found.")
        return

    print("\n=== ALL ROAD REPORTS ===")

    for i, r in enumerate(reports, start=1):
        print(f"\nID: {r.get('id', i)}")
        print("Location:", r["location"])
        print("Hazard:", r["description"])
        print("Status:", r["status"])


def resolve_report():
    reports = load_reports()

    if not reports:
        print("\nNo reports available.")
        return

    view_reports()

    try:
        report_id = int(input("\nEnter ID to resolve: "))
    except ValueError:
        print("Please enter a valid number.")
        return

    for i, r in enumerate(reports, start=1):
        if r.get("id", i) == report_id:
            if r["status"] == "Resolved":
                print("This report is already resolved.")
                return

            r["status"] = "Resolved"
            save_reports(reports)
            print("Report marked as Resolved!")
            return

    print("Report ID not found.")


def search_reports():
    reports = load_reports()

    if not reports:
        print("\nNo reports available to search.")
        return

    query = input("Enter report ID or location: ").strip()

    if not query:
        print("Search cannot be empty.")
        return

    results = [
        (i, r) for i, r in enumerate(reports, start=1)
        if (
            query.lower() in r["location"].lower()
            or query.lower() in r["description"].lower()
            or query == str(r.get("id", i))
        )
    ]

    if not results:
        print("\nNo matching reports found.")
        return

    print("\n=== SEARCH RESULTS ===")

    for i, r in results:
        print(f"\nID: {r.get('id', i)}")
        print("Location:", r["location"])
        print("Hazard:", r["description"])
        print("Status:", r["status"])


def show_dashboard():
    reports = load_reports()

    total = len(reports)
    resolved = sum(
        1 for r in reports if r["status"] == "Resolved"
    )
    unresolved = total - resolved

    print("\n=== ROADGUARD DASHBOARD ===")
    print("Total Reports:", total)
    print("Resolved:", resolved)
    print("Unresolved:", unresolved)


while True:
    print("\n===== ROADGUARD =====")
    print("1. Submit a report")
    print("2. View all reports")
    print("3. Resolve a report")
    print("4. Search reports")
    print("5. Exit")
    print("6. View dashboard")

    choice = input("Choose an option: ").strip()

    if choice == "1":
        submit_report()
    elif choice == "2":
        view_reports()
    elif choice == "3":
        resolve_report()
    elif choice == "4":
        search_reports()
    elif choice == "5":
        print("Thank you for using RoadGuard!")
        break
    elif choice == "6":
        show_dashboard()
    else:
        print("Invalid choice. Please select 1-6.")

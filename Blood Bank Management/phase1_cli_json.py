# Phase 1 — CLI (JSON storage)
import json
import os
from datetime import datetime

DONORS_FILE = "donors.json"
INVENTORY_FILE = "inventory.json"
REQUESTS_FILE = "requests.json"

BLOOD_GROUPS = ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]

def init_files():
    for fp in [DONORS_FILE, INVENTORY_FILE, REQUESTS_FILE]:
        if not os.path.exists(fp):
            with open(fp, "w", encoding="utf-8") as f:
                json.dump([], f)

def load(fp):
    with open(fp, "r", encoding="utf-8") as f:
        return json.load(f)

def save(fp, data):
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def normalize_bg(bg):
    bg = (bg or "").strip().upper()
    if bg not in BLOOD_GROUPS:
        raise ValueError("Invalid blood group. Allowed: " + ", ".join(BLOOD_GROUPS))
    return bg

# Donor Management
def add_donor():
    donors = load(DONORS_FILE)
    name = input("Name: ").strip()
    age = int(input("Age: ").strip())
    gender = input("Gender (Male/Female/Other): ").strip().title()
    phone = input("Phone: ").strip()
    address = input("Address: ").strip()
    blood_group = normalize_bg(input("Blood Group: ").strip())
    last_donation_date = input("Last donation date (YYYY-MM-DD or blank): ").strip()
    if last_donation_date:
        try:
            datetime.strptime(last_donation_date, "%Y-%m-%d")
        except ValueError:
            print("Invalid date. Use YYYY-MM-DD.")
            return
    donor_id = (max([d.get("id", 0) for d in donors]) + 1) if donors else 1
    donors.append({
        "id": donor_id,
        "name": name,
        "age": age,
        "gender": gender,
        "phone": phone,
        "address": address,
        "blood_group": blood_group,
        "last_donation_date": last_donation_date or None
    })
    save(DONORS_FILE, donors)
    print("Donor added.")

def view_donors():
    donors = load(DONORS_FILE)
    if not donors:
        print("No donors found.")
        return
    for d in donors:
        print(f"{d['id']}: {d['name']} | {d['blood_group']} | Last donation: {d.get('last_donation_date') or 'N/A'}")

# Inventory
def add_inventory():
    inv = load(INVENTORY_FILE)
    blood_group = normalize_bg(input("Blood Group: ").strip())
    qty = int(input("Quantity (units): ").strip())
    found = next((i for i in inv if i["blood_group"] == blood_group), None)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if found:
        found["quantity"] += qty
        found["last_updated"] = now
    else:
        inv.append({"blood_group": blood_group, "quantity": qty, "last_updated": now})
    save(INVENTORY_FILE, inv)
    print("Inventory updated.")

def view_inventory():
    inv = load(INVENTORY_FILE)
    if not inv:
        print("Inventory empty.")
        return
    for i in inv:
        print(f"{i['blood_group']}: {i['quantity']} units (updated {i['last_updated']})")

# Requests / Issue
def issue_blood():
    inv = load(INVENTORY_FILE)
    reqs = load(REQUESTS_FILE)
    blood_group = normalize_bg(input("Requested Blood Group: ").strip())
    qty = int(input("Quantity (units): ").strip())
    item = next((i for i in inv if i["blood_group"] == blood_group), None)
    if not item:
        print("Blood group not available.")
        return
    if item["quantity"] < qty:
        print(f"Insufficient stock. Available: {item['quantity']}")
        return
    item["quantity"] -= qty
    item["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    reqs.append({
        "id": (max([r.get("id", 0) for r in reqs]) + 1) if reqs else 1,
        "blood_group": blood_group,
        "quantity": qty,
        "issue_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    save(INVENTORY_FILE, inv)
    save(REQUESTS_FILE, reqs)
    print("Blood issued.")

def view_requests():
    reqs = load(REQUESTS_FILE)
    if not reqs:
        print("No requests.")
        return
    for r in reqs:
        print(f"{r['id']}: {r['blood_group']} - {r['quantity']} unit(s) at {r['issue_date']}")

def main():
    init_files()
    while True:
        print("\n=== Phase 1 CLI (JSON) ===")
        print("1. Add Donor")
        print("2. View Donors")
        print("3. Add Blood to Inventory")
        print("4. View Inventory")
        print("5. Issue Blood")
        print("6. View Requests")
        print("0. Exit")
        ch = input("Choose: ").strip()
        try:
            if ch == "1":
                add_donor()
            elif ch == "2":
                view_donors()
            elif ch == "3":
                add_inventory()
            elif ch == "4":
                view_inventory()
            elif ch == "5":
                issue_blood()
            elif ch == "6":
                view_requests()
            elif ch == "0":
                print("Bye.")
                break
            else:
                print("Invalid choice.")
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    main()
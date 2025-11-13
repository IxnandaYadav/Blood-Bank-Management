# Phase 3 — Flask Web API (PostgreSQL)
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from typing import Any

app = Flask(__name__)
CORS(app)

# Update this with your PostgreSQL credentials
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:nanda123@localhost:5432/blood_bank"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

BLOOD_GROUPS = ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]
COMPATIBILITY = {
    "O-": ["O-"],
    "O+": ["O-", "O+"],
    "A-": ["O-", "A-"],
    "A+": ["O-", "O+", "A-", "A+"],
    "B-": ["O-", "B-"],
    "B+": ["O-", "O+", "B-", "B+"],
    "AB-": ["O-", "A-", "B-", "AB-"],
    "AB+": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
}
DONATION_EXPIRY_DAYS = 42

class User(db.Model):  # type: ignore[name-defined]
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(16), nullable=False, default="staff")  # admin/staff
    
    def __init__(self, username, password_hash, role="staff"):
        self.username = username
        self.password_hash = password_hash
        self.role = role

class Donor(db.Model):  # type: ignore[name-defined]
    __tablename__ = 'donor'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(16))
    phone = db.Column(db.String(32))
    address = db.Column(db.String(200))
    blood_group = db.Column(db.String(4), nullable=False)
    last_donation_date = db.Column(db.Date, nullable=True)
    
    def __init__(self, name, age, blood_group, gender=None, phone=None, address=None, last_donation_date=None):
        self.name = name
        self.age = age
        self.gender = gender
        self.phone = phone
        self.address = address
        self.blood_group = blood_group
        self.last_donation_date = last_donation_date

class Recipient(db.Model):  # type: ignore[name-defined]
    __tablename__ = 'recipient'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    required_blood_group = db.Column(db.String(4), nullable=False)
    quantity_needed = db.Column(db.Integer, nullable=False)
    hospital_name = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, name, age, required_blood_group, quantity_needed, hospital_name=None):
        self.name = name
        self.age = age
        self.required_blood_group = required_blood_group
        self.quantity_needed = quantity_needed
        self.hospital_name = hospital_name

class Donation(db.Model):  # type: ignore[name-defined]
    __tablename__ = 'donation'
    id = db.Column(db.Integer, primary_key=True)
    donor_id = db.Column(db.Integer, db.ForeignKey("donor.id"), nullable=False)
    donation_code = db.Column(db.String(64), unique=True, nullable=False)
    blood_group = db.Column(db.String(4), nullable=False)
    units = db.Column(db.Integer, nullable=False)
    donation_date = db.Column(db.DateTime, nullable=False)
    expiry_date = db.Column(db.DateTime, nullable=False)
    
    def __init__(self, donor_id, donation_code, blood_group, units, donation_date, expiry_date):
        self.donor_id = donor_id
        self.donation_code = donation_code
        self.blood_group = blood_group
        self.units = units
        self.donation_date = donation_date
        self.expiry_date = expiry_date

class Issue(db.Model):  # type: ignore[name-defined]
    __tablename__ = 'issue'
    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey("recipient.id"), nullable=False)
    requested_blood_group = db.Column(db.String(4), nullable=False)
    blood_group_issued = db.Column(db.String(4), nullable=False)
    units = db.Column(db.Integer, nullable=False)
    issue_date = db.Column(db.DateTime, default=datetime.utcnow)
    compatible = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(32), default="issued")
    
    def __init__(self, recipient_id, requested_blood_group, blood_group_issued, units, issue_date=None, compatible=True, status="issued"):
        self.recipient_id = recipient_id
        self.requested_blood_group = requested_blood_group
        self.blood_group_issued = blood_group_issued
        self.units = units
        if issue_date is not None:
            self.issue_date = issue_date
        self.compatible = compatible
        self.status = status

def normalize_bg(bg):
    bg = (bg or "").strip().upper()
    if bg not in BLOOD_GROUPS:
        raise ValueError("Invalid blood group")
    return bg

@app.route("/init", methods=["POST"])
def init():
    db.create_all()
    if not User.query.filter_by(username="admin").first():
        db.session.add(User(username="admin", password_hash=generate_password_hash("admin123"), role="admin"))
        db.session.commit()
    return jsonify({"status":"ok"})

@app.route("/login", methods=["POST"])
def login():
    data = request.json or {}
    user = User.query.filter_by(username=data.get("username")).first()
    if user and check_password_hash(user.password_hash, data.get("password") or ""):
        return jsonify({"ok": True, "role": user.role})
    return jsonify({"ok": False}), 401

@app.route("/donors", methods=["GET","POST"])
def donors():
    if request.method == "POST":
        d = request.json or {}
        bg = normalize_bg(d.get("blood_group"))
        last = d.get("last_donation_date")
        last_date = datetime.strptime(last, "%Y-%m-%d").date() if last else None
        donor = Donor(name=d["name"], age=int(d["age"]), gender=d.get("gender"), phone=d.get("phone"),
                      address=d.get("address"), blood_group=bg, last_donation_date=last_date)
        db.session.add(donor); db.session.commit()
        return jsonify({"id": donor.id})
    donors = Donor.query.order_by(Donor.name).all()  # type: ignore[attr-defined]
    return jsonify([{
        "id": x.id, "name": x.name, "age": x.age, "gender": x.gender, "phone": x.phone,
        "address": x.address, "blood_group": x.blood_group,
        "last_donation_date": x.last_donation_date.isoformat() if x.last_donation_date else None
    } for x in donors])

@app.route("/donors/<int:did>", methods=["PUT","DELETE"])
def donor_update_delete(did):
    d = Donor.query.get_or_404(did)
    if request.method == "DELETE":
        db.session.delete(d); db.session.commit(); return jsonify({"deleted": True})
    data = request.json or {}
    for k in ["name","age","gender","phone","address","blood_group","last_donation_date"]:
        if k in data and data[k] is not None:
            if k == "blood_group": setattr(d, k, normalize_bg(data[k]))
            elif k == "age": setattr(d, k, int(data[k]))
            elif k == "last_donation_date": setattr(d, k, datetime.strptime(data[k], "%Y-%m-%d").date())
            else: setattr(d, k, data[k])
    db.session.commit()
    return jsonify({"updated": True})

@app.route("/recipients", methods=["GET","POST"])
def recipients():
    if request.method == "POST":
        r = request.json or {}
        bg = normalize_bg(r.get("required_blood_group"))
        rec = Recipient(name=r["name"], age=int(r["age"]), required_blood_group=bg,
                        quantity_needed=int(r["quantity_needed"]), hospital_name=r.get("hospital_name"))
        db.session.add(rec); db.session.commit()
        return jsonify({"id": rec.id})
    rs = Recipient.query.order_by(Recipient.created_at.desc()).all()  # type: ignore[attr-defined]
    return jsonify([{
        "id": x.id, "name": x.name, "age": x.age, "required_blood_group": x.required_blood_group,
        "quantity_needed": x.quantity_needed, "hospital_name": x.hospital_name, "created_at": x.created_at.isoformat()
    } for x in rs])

@app.route("/compatibility/<bg>", methods=["GET"])
def compatibility(bg):
    return jsonify({"recipient": normalize_bg(bg), "compatible_donors": COMPATIBILITY[normalize_bg(bg)]})

@app.route("/donations", methods=["POST","GET"])
def donations():
    if request.method == "POST":
        d = request.json or {}
        donor_id = int(d["donor_id"])
        bg = normalize_bg(d["blood_group"])
        units = int(d["units"])
        now = datetime.utcnow()
        expiry = now + timedelta(days=DONATION_EXPIRY_DAYS)
        code = f"D-{now.strftime('%Y%m%d%H%M%S')}-{donor_id}"
        db.session.add(Donation(donor_id=donor_id, donation_code=code, blood_group=bg, units=units,
                                donation_date=now, expiry_date=expiry))
        don = Donor.query.get(donor_id)
        if don: don.last_donation_date = now.date()
        db.session.commit()
        return jsonify({"code": code})
    ds = Donation.query.order_by(Donation.donation_date.desc()).all()  # type: ignore[attr-defined]
    return jsonify([{
        "code": x.donation_code, "donor_id": x.donor_id, "blood_group": x.blood_group,
        "units": x.units, "donation_date": x.donation_date.isoformat(), "expiry_date": x.expiry_date.isoformat()
    } for x in ds])

@app.route("/issues", methods=["POST","GET"])
def issues():
    if request.method == "POST":
        d = request.json or {}
        rid = int(d["recipient_id"])
        req_bg = normalize_bg(d["requested_blood_group"])
        units = int(d["units"])
        now = datetime.utcnow()
        def available(bg):
            donated = db.session.query(db.func.coalesce(db.func.sum(Donation.units), 0)).filter(  # type: ignore[attr-defined]
                Donation.blood_group == bg, Donation.expiry_date >= now).scalar()  # type: ignore[attr-defined]
            issued = db.session.query(db.func.coalesce(db.func.sum(Issue.units), 0)).filter(  # type: ignore[attr-defined]
                Issue.blood_group_issued == bg).scalar()  # type: ignore[attr-defined]
            return max(0, int(donated) - int(issued))
        candidates = [req_bg] + [g for g in COMPATIBILITY[req_bg] if g != req_bg]
        issued_group = None
        for g in candidates:
            if available(g) >= units:
                issued_group = g; break
        if not issued_group:
            return jsonify({"error": "Insufficient compatible stock"}), 400
        iss = Issue(recipient_id=rid, requested_blood_group=req_bg, blood_group_issued=issued_group,
                    units=units, issue_date=datetime.utcnow(), compatible=True, status="issued")
        db.session.add(iss); db.session.commit()
        return jsonify({"issued_group": issued_group})
    isx = Issue.query.order_by(Issue.issue_date.desc()).all()  # type: ignore[attr-defined]
    return jsonify([{
        "id": x.id, "recipient_id": x.recipient_id, "requested_blood_group": x.requested_blood_group,
        "blood_group_issued": x.blood_group_issued, "units": x.units, "issue_date": x.issue_date.isoformat(),
        "compatible": x.compatible, "status": x.status
    } for x in isx])

if __name__ == "__main__":
    app.run(debug=True)
# Phase 2 — Tkinter GUI (uses database.py)
import tkinter as tk
from tkinter import ttk, messagebox
import database

class BloodBankApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Blood Bank Management (Phase 2)")
        self.root.geometry("1024x720")
        database.init_db()
        self.create_login()

    def clear_root(self):
        for w in self.root.winfo_children():
            w.destroy()

    def create_login(self):
        self.clear_root()
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(expand=True)
        ttk.Label(frame, text="Login", font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=10)
        ttk.Label(frame, text="Username").grid(row=1, column=0, sticky="w")
        self.username = ttk.Entry(frame)
        self.username.grid(row=1, column=1, pady=5)
        ttk.Label(frame, text="Password").grid(row=2, column=0, sticky="w")
        self.password = ttk.Entry(frame, show="*")
        self.password.grid(row=2, column=1, pady=5)
        ttk.Button(frame, text="Login", command=self.login).grid(row=3, column=0, columnspan=2, pady=10)
        self.root.bind("<Return>", lambda e: self.login())

    def login(self):
        u = self.username.get().strip()
        p = self.password.get().strip()
        ok, user, role = database.authenticate(u, p)
        if ok:
            self.current_user = user
            self.current_role = role
            self.create_main()
        else:
            messagebox.showerror("Error", "Invalid credentials")

    def create_main(self):
        self.clear_root()
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        file_m = tk.Menu(menubar, tearoff=0)
        file_m.add_command(label="Logout", command=self.create_login)
        file_m.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_m)
        if getattr(self, "current_role", "staff") == "admin":
            admin_m = tk.Menu(menubar, tearoff=0)
            admin_m.add_command(label="Seed Sample Data", command=self.seed_sample)
            menubar.add_cascade(label="Admin", menu=admin_m)

        nb = ttk.Notebook(self.root)
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        donors_f = ttk.Frame(nb); nb.add(donors_f, text="Donors")
        inventory_f = ttk.Frame(nb); nb.add(inventory_f, text="Inventory")
        requests_f = ttk.Frame(nb); nb.add(requests_f, text="Requests")
        recipients_f = ttk.Frame(nb); nb.add(recipients_f, text="Recipients")

        self.build_donors_tab(donors_f)
        self.build_inventory_tab(inventory_f)
        self.build_requests_tab(requests_f)
        self.build_recipients_tab(recipients_f)

    def build_donors_tab(self, parent):
        lf = ttk.LabelFrame(parent, text="Add/Update Donor", padding=10)
        lf.pack(fill=tk.X, padx=10, pady=10)
        self.d_fields = {}
        labels = ["Name","Age","Gender","Phone","Address","Blood Group","Last Donation (YYYY-MM-DD)"]
        keys = ["name","age","gender","phone","address","blood_group","last_donation_date"]
        for i,(lbl,key) in enumerate(zip(labels, keys)):
            ttk.Label(lf, text=lbl).grid(row=i//3, column=(i%3)*2, sticky="w", pady=5)
            e = ttk.Entry(lf, width=22)
            e.grid(row=i//3, column=(i%3)*2+1, padx=5, pady=5)
            self.d_fields[key] = e
        ttk.Button(lf, text="Add Donor", command=self.add_donor).grid(row=3, column=0, columnspan=2, pady=8)
        ttk.Button(lf, text="Update Selected", command=self.update_donor).grid(row=3, column=2, columnspan=2, pady=8)
        ttk.Button(lf, text="Delete Selected", command=self.delete_donor).grid(row=3, column=4, columnspan=2, pady=8)

        sf = ttk.LabelFrame(parent, text="Search", padding=10)
        sf.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(sf, text="Term").grid(row=0, column=0); self.search_term = ttk.Entry(sf, width=25); self.search_term.grid(row=0, column=1)
        ttk.Label(sf, text="Blood Group").grid(row=0, column=2); self.search_bg = ttk.Entry(sf, width=10); self.search_bg.grid(row=0, column=3)
        ttk.Label(sf, text="Location").grid(row=0, column=4); self.search_loc = ttk.Entry(sf, width=20); self.search_loc.grid(row=0, column=5)
        ttk.Button(sf, text="Search", command=self.search_donors).grid(row=0, column=6, padx=5)
        ttk.Button(sf, text="Show All", command=self.load_donors).grid(row=0, column=7)

        tf = ttk.Frame(parent); tf.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        cols = ("ID","Name","Age","Gender","Phone","Address","Blood Group","Last Donation")
        self.d_tree = ttk.Treeview(tf, columns=cols, show="headings", height=15)
        for c in cols: self.d_tree.heading(c, text=c); self.d_tree.column(c, width=120)
        vs = ttk.Scrollbar(tf, orient=tk.VERTICAL, command=self.d_tree.yview); self.d_tree.configure(yscrollcommand=vs.set)
        self.d_tree.grid(row=0, column=0, sticky="nsew"); vs.grid(row=0, column=1, sticky="ns")
        tf.grid_rowconfigure(0, weight=1); tf.grid_columnconfigure(0, weight=1)
        self.load_donors()

    def add_donor(self):
        f = self.d_fields
        try:
            database.add_donor(f["name"].get(), int(f["age"].get()), f["gender"].get(), f["phone"].get(),
                               f["address"].get(), f["blood_group"].get(), f["last_donation_date"].get() or None)
            messagebox.showinfo("Success","Donor added."); self.load_donors()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_donor(self):
        sel = self.d_tree.selection()
        if not sel: return
        did = self.d_tree.item(sel[0])["values"][0]
        fields = {}
        for k,e in self.d_fields.items():
            v = e.get().strip()
            if v: fields[k] = v
        try:
            database.update_donor(did, **fields); messagebox.showinfo("Success","Donor updated."); self.load_donors()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_donor(self):
        sel = self.d_tree.selection()
        if not sel: return
        did = self.d_tree.item(sel[0])["values"][0]
        database.delete_donor(did); self.load_donors()

    def load_donors(self):
        for i in self.d_tree.get_children(): self.d_tree.delete(i)
        for r in database.list_donors():
            self.d_tree.insert("", tk.END, values=(r["id"], r["name"], r["age"], r["gender"], r["phone"], r["address"], r["blood_group"], r["last_donation_date"]))

    def search_donors(self):
        term = self.search_term.get().strip()
        bg = self.search_bg.get().strip()
        loc = self.search_loc.get().strip()
        try:
            rows = database.search_donors(term=term or None, blood_group=bg or None, location=loc or None)
            for i in self.d_tree.get_children(): self.d_tree.delete(i)
            for r in rows:
                self.d_tree.insert("", tk.END, values=(r["id"], r["name"], r["age"], r["gender"], r["phone"], r["address"], r["blood_group"], r["last_donation_date"]))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def build_inventory_tab(self, parent):
        lf = ttk.LabelFrame(parent, text="Record Donation / View Inventory", padding=10)
        lf.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(lf, text="Donor ID").grid(row=0, column=0); self.don_id = ttk.Entry(lf, width=10); self.don_id.grid(row=0, column=1)
        ttk.Label(lf, text="Blood Group").grid(row=0, column=2); self.don_bg = ttk.Entry(lf, width=10); self.don_bg.grid(row=0, column=3)
        ttk.Label(lf, text="Units").grid(row=0, column=4); self.don_units = ttk.Entry(lf, width=10); self.don_units.grid(row=0, column=5)
        ttk.Button(lf, text="Record Donation", command=self.record_donation).grid(row=0, column=6, padx=5)
        ttk.Button(lf, text="Refresh Inventory", command=self.load_inventory).grid(row=0, column=7)

        tf = ttk.Frame(parent); tf.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        cols = ("Blood Group","Available Units","Updated")
        self.inv_tree = ttk.Treeview(tf, columns=cols, show="headings", height=15)
        for c in cols: self.inv_tree.heading(c, text=c); self.inv_tree.column(c, width=160)
        vs = ttk.Scrollbar(tf, orient=tk.VERTICAL, command=self.inv_tree.yview); self.inv_tree.configure(yscrollcommand=vs.set)
        self.inv_tree.grid(row=0, column=0, sticky="nsew"); vs.grid(row=0, column=1, sticky="ns")
        tf.grid_rowconfigure(0, weight=1); tf.grid_columnconfigure(0, weight=1)
        self.load_inventory()

        alert_f = ttk.LabelFrame(parent, text="Alerts", padding=10); alert_f.pack(fill=tk.X, padx=10, pady=10)
        self.alert_lbl = ttk.Label(alert_f, text=""); self.alert_lbl.pack(anchor="w")
        self.update_alerts()

    def record_donation(self):
        try:
            code = database.record_donation(int(self.don_id.get()), self.don_bg.get(), int(self.don_units.get()))
            messagebox.showinfo("Donation Recorded", f"Code: {code}")
            self.load_inventory(); self.update_alerts()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def load_inventory(self):
        for i in self.inv_tree.get_children(): self.inv_tree.delete(i)
        for r in database.list_inventory():
            self.inv_tree.insert("", tk.END, values=(r["blood_group"], r["available_units"], r["updated_at"]))

    def update_alerts(self):
        low, out = database.low_stock_alerts()
        text = f"Low stock: {[r['blood_group'] for r in low]} | Out of stock: {[r['blood_group'] for r in out]}"
        self.alert_lbl.config(text=text)

    def build_requests_tab(self, parent):
        lf = ttk.LabelFrame(parent, text="Issue Blood", padding=10)
        lf.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(lf, text="Recipient ID").grid(row=0, column=0); self.rec_id = ttk.Entry(lf, width=10); self.rec_id.grid(row=0, column=1)
        ttk.Label(lf, text="Requested BG").grid(row=0, column=2); self.req_bg = ttk.Entry(lf, width=10); self.req_bg.grid(row=0, column=3)
        ttk.Label(lf, text="Units").grid(row=0, column=4); self.req_units = ttk.Entry(lf, width=10); self.req_units.grid(row=0, column=5)
        ttk.Button(lf, text="Record Issue", command=self.record_issue).grid(row=0, column=6, padx=5)

        tf = ttk.Frame(parent); tf.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        cols = ("ID","Recipient ID","Requested BG","Issued BG","Units","Issue Date","Compatible","Status")
        self.req_tree = ttk.Treeview(tf, columns=cols, show="headings", height=15)
        for c in cols: self.req_tree.heading(c, text=c); self.req_tree.column(c, width=120)
        vs = ttk.Scrollbar(tf, orient=tk.VERTICAL, command=self.req_tree.yview); self.req_tree.configure(yscrollcommand=vs.set)
        self.req_tree.grid(row=0, column=0, sticky="nsew"); vs.grid(row=0, column=1, sticky="ns")
        tf.grid_rowconfigure(0, weight=1); tf.grid_columnconfigure(0, weight=1)
        self.load_requests()

    def record_issue(self):
        try:
            issued = database.record_issue(int(self.rec_id.get()), self.req_bg.get(), int(self.req_units.get()))
            messagebox.showinfo("Issued", f"Issued group: {issued}")
            self.load_inventory(); self.load_requests(); self.update_alerts()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def load_requests(self):
        conn = database.get_conn()
        rows = conn.execute("SELECT * FROM issues ORDER BY issue_date DESC").fetchall()
        conn.close()
        for i in self.req_tree.get_children(): self.req_tree.delete(i)
        for r in rows:
            self.req_tree.insert("", tk.END, values=(r["id"], r["recipient_id"], r["requested_blood_group"], r["blood_group_issued"], r["units"], r["issue_date"], r["compatible"], r["status"]))

    def build_recipients_tab(self, parent):
        lf = ttk.LabelFrame(parent, text="Add/Update Recipient", padding=10)
        lf.pack(fill=tk.X, padx=10, pady=10)
        self.r_fields = {}
        labels = ["Name","Age","Required BG","Quantity Needed","Hospital"]
        keys = ["name","age","required_blood_group","quantity_needed","hospital_name"]
        for i,(lbl,key) in enumerate(zip(labels, keys)):
            ttk.Label(lf, text=lbl).grid(row=i//3, column=(i%3)*2, sticky="w", pady=5)
            e = ttk.Entry(lf, width=22)
            e.grid(row=i//3, column=(i%3)*2+1, padx=5, pady=5)
            self.r_fields[key] = e
        ttk.Button(lf, text="Add Recipient", command=self.add_recipient).grid(row=2, column=0, columnspan=2, pady=8)
        ttk.Button(lf, text="Update Selected", command=self.update_recipient).grid(row=2, column=2, columnspan=2, pady=8)
        ttk.Button(lf, text="Delete Selected", command=self.delete_recipient).grid(row=2, column=4, columnspan=2, pady=8)

        tf = ttk.Frame(parent); tf.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        cols = ("ID","Name","Age","Required BG","Qty Needed","Hospital","Created")
        self.r_tree = ttk.Treeview(tf, columns=cols, show="headings", height=15)
        for c in cols: self.r_tree.heading(c, text=c); self.r_tree.column(c, width=120)
        vs = ttk.Scrollbar(tf, orient=tk.VERTICAL, command=self.r_tree.yview); self.r_tree.configure(yscrollcommand=vs.set)
        self.r_tree.grid(row=0, column=0, sticky="nsew"); vs.grid(row=0, column=1, sticky="ns")
        tf.grid_rowconfigure(0, weight=1); tf.grid_columnconfigure(0, weight=1)
        self.load_recipients()

    def add_recipient(self):
        f = self.r_fields
        try:
            database.add_recipient(f["name"].get(), int(f["age"].get()), f["required_blood_group"].get(), int(f["quantity_needed"].get()), f["hospital_name"].get())
            messagebox.showinfo("Success","Recipient added."); self.load_recipients()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_recipient(self):
        sel = self.r_tree.selection()
        if not sel: return
        rid = self.r_tree.item(sel[0])["values"][0]
        fields = {}
        for k,e in self.r_fields.items():
            v = e.get().strip()
            if v: fields[k] = v
        try:
            database.update_recipient(rid, **fields); messagebox.showinfo("Success","Recipient updated."); self.load_recipients()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_recipient(self):
        sel = self.r_tree.selection()
        if not sel: return
        rid = self.r_tree.item(sel[0])["values"][0]
        database.delete_recipient(rid); self.load_recipients()

    def load_recipients(self):
        for i in self.r_tree.get_children(): self.r_tree.delete(i)
        for r in database.list_recipients():
            self.r_tree.insert("", tk.END, values=(r["id"], r["name"], r["age"], r["required_blood_group"], r["quantity_needed"], r["hospital_name"], r["created_at"]))

    def seed_sample(self):
        try:
            database.add_donor("Alice", 28, "Female", "900000001", "City A", "A+", "2025-07-01")
            database.add_donor("Bob", 35, "Male", "900000002", "City B", "O-", "2025-06-15")
            database.add_recipient("Patient X", 40, "A+", 2, "Hospital 1")
            database.add_recipient("Patient Y", 55, "O-", 1, "Hospital 2")
            messagebox.showinfo("Seed", "Seeded minimal data.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = BloodBankApp(root)
    root.mainloop()
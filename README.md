# Tech Lead & Developer Intern Group Assignment

Automate grouping developer interns into balanced teams under tech leads based on their college affiliation.

---

## 🚀 What It Does

- Matches developer interns and tech leads by their **college affiliation**.
- Groups developers into teams of 5 per group, assigning up to 5 groups (25 developers) per tech lead.
- Assigns leftover developers randomly to tech leads with capacity.
- Tracks developer intern **Active/Inactive status** that tech leads can update.
- Provides a dashboard summary for each tech lead showing counts of active vs inactive interns.
- Generates lists of unassigned developers and tech leads (if any).
- Provides an easy **Streamlit web app** to look up tech leads and their assigned groups by email.
- Tech leads can toggle intern status in real-time, and the statuses are saved persistently.

---

## 📂 How to Use

1. **Add or update your data files:**

   - `dev_y.csv` — Developer interns data
   - `tech_y.csv` — Tech leads data

   Ensure CSVs include these columns:

   - `Full Name`
   - `Email Address`
   - `Contact Number`
   - `Affiliation` (college name)
   - `Gender` (optional)

2. **Run the Streamlit app:**

   ```bash
   streamlit run techlead_app.py
3. **In the app:**

   - Enter your Tech Lead Email to view assigned groups.
   - Developer interns are displayed in neat, aligned card layouts.
   - Use the **Active/Inactive checkbox** next to each developer to update their status.
   - The dashboard at the top summarizes how many interns are currently active and inactive under your supervision.
   - Status changes are saved persistently and restored on your next login.

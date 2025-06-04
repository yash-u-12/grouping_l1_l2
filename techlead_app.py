import streamlit as st
import pandas as pd
from collections import defaultdict
import os
import pickle

# ========= Constants ==========
DEV_FILE = "dev_y.csv"
TECH_FILE = "tech_y.csv"
ASSIGNMENT_FILE = "final_assignments.pkl"
UNASSIGNED_DEV_FILE = "unassigned_developer_interns.csv"
UNASSIGNED_TECH_FILE = "unassigned_techleads.csv"
STATUS_FILE = "status.csv"
RANDOM_SEED = 42

# ========= UI Styling ==========
st.markdown("""
    <style>
    div.stContainer > div {
        padding: 15px;
        border: 1px solid #ddd;
        border-radius: 10px;
        margin-bottom: 16px;
        background-color: #f9f9f9;
    }
    .developer-card {
        padding: 10px;
        border: 1px solid #aaa;
        border-radius: 8px;
        margin-bottom: 8px;
        background-color: #ffffff;
    }
    </style>
""", unsafe_allow_html=True)

# ========= Load Data ==========
@st.cache_data
def load_data():
    devs = pd.read_csv(DEV_FILE, dtype={"Contact Number": str})
    techs = pd.read_csv(TECH_FILE, dtype={"Contact Number": str})
    devs.columns = devs.columns.str.strip()
    techs.columns = techs.columns.str.strip()
    return devs, techs

# ========= Assignment Logic ==========
def compute_assignments(devs, techs):
    devs = devs.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)
    techs = techs.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)

    devs['Affiliation'] = devs['Affiliation'].str.strip().str.lower()
    techs['Affiliation'] = techs['Affiliation'].str.strip().str.lower()
    techs['Email Address'] = techs['Email Address'].str.strip().str.lower()

    assignments = defaultdict(list)
    leftout_groups = []

    grouped_devs = devs.groupby("Affiliation")
    grouped_techs = techs.groupby("Affiliation")

    for college, dev_group in grouped_devs:
        intern_groups = [dev_group.iloc[i:i+5] for i in range(0, len(dev_group), 5)]
        techs_in_college = grouped_techs.get_group(college) if college in grouped_techs.groups else pd.DataFrame()
        tech_index = 0
        for group in intern_groups:
            if len(group) < 5:
                leftout_groups.append(group)
            elif not techs_in_college.empty:
                assigned = False
                while tech_index < len(techs_in_college):
                    email = techs_in_college.iloc[tech_index]['Email Address']
                    if len(assignments[email]) < 5:
                        assignments[email].append(group)
                        assigned = True
                        if len(assignments[email]) == 5:
                            tech_index += 1
                        break
                    else:
                        tech_index += 1
                if not assigned:
                    leftout_groups.append(group)
            else:
                leftout_groups.append(group)

    leftover_techs = [email for email in techs['Email Address'].unique() if len(assignments[email]) < 5]

    for group in leftout_groups:
        assigned = False
        for email in leftover_techs:
            if len(assignments[email]) < 5:
                assignments[email].append(group)
                if len(assignments[email]) == 5:
                    leftover_techs.remove(email)
                assigned = True
                break

    unassigned_interns = []
    for group in leftout_groups:
        assigned = any(group.equals(g) for groups in assignments.values() for g in groups)
        if not assigned:
            unassigned_interns.extend(group.to_dict(orient="records"))

    final_unassigned_devs = pd.DataFrame(unassigned_interns)
    assigned_emails = set(assignments.keys())
    final_unassigned_techs = techs[~techs['Email Address'].isin(assigned_emails)].reset_index(drop=True)

    return assignments, final_unassigned_devs, final_unassigned_techs

# ========= Assignment Loader ==========
def load_or_create_assignments():
    if os.path.exists(ASSIGNMENT_FILE):
        with open(ASSIGNMENT_FILE, "rb") as f:
            return pickle.load(f)
    else:
        devs, techs = load_data()
        assignments, unassigned_devs, unassigned_techs = compute_assignments(devs, techs)
        with open(ASSIGNMENT_FILE, "wb") as f:
            pickle.dump((assignments, unassigned_devs, unassigned_techs), f)
        unassigned_devs.to_csv(UNASSIGNED_DEV_FILE, index=False)
        unassigned_techs.to_csv(UNASSIGNED_TECH_FILE, index=False)
        return assignments, unassigned_devs, unassigned_techs

# ========= Status Management ==========
def load_status(devs):
    if os.path.exists(STATUS_FILE):
        status_df = pd.read_csv(STATUS_FILE, dtype={"Email Address": str, "Status": str})
        missing_devs = devs[~devs["Email Address"].isin(status_df["Email Address"])]
        if not missing_devs.empty:
            missing_status = pd.DataFrame({"Email Address": missing_devs["Email Address"], "Status": "Inactive"})
            status_df = pd.concat([status_df, missing_status], ignore_index=True)
            status_df.to_csv(STATUS_FILE, index=False)
    else:
        status_df = pd.DataFrame({"Email Address": devs["Email Address"], "Status": "Inactive"})
        status_df.to_csv(STATUS_FILE, index=False)
    return status_df

def save_status(status_df):
    status_df.to_csv(STATUS_FILE, index=False)

# ========= Streamlit App ==========
st.title("🚀 Tech Lead - Developer Intern Lookup & Status")

assignments, unassigned_devs, unassigned_techs = load_or_create_assignments()
devs, techs = load_data()

email_input = st.text_input("🔐 Enter your Tech Lead Email:").strip().lower()

if email_input:
    if email_input in assignments:
        tech_row = techs[techs['Email Address'] == email_input]
        if not tech_row.empty:
            tech_row = tech_row.iloc[0]
            st.success("✅ Tech Lead Found")
            st.write(f"**Full Name:** {tech_row['Full Name']}")
            st.write(f"**Affiliation:** {tech_row['Affiliation'].title()}")
            st.write(f"**Gender:** {tech_row['Gender']}")
            st.write(f"**Contact:** {tech_row['Contact Number']}")
            st.write(f"**Email:** {tech_row['Email Address']}")

        assigned_groups = assignments[email_input]
        all_devs = pd.concat(assigned_groups, ignore_index=True)
        status_df = load_status(all_devs)

        active_count, inactive_count, total_assigned = 0, 0, 0
        updated_status = []

        st.subheader("👥 Assigned Developer Intern Groups")
        for idx, group in enumerate(assigned_groups, 1):
            st.markdown(f"### Group {idx}")
            with st.container():
                for _, row in group.iterrows():
                    email = row["Email Address"]
                    current_status = status_df[status_df["Email Address"] == email]["Status"].values[0]

                    with st.container():
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.markdown(
                                f"""
                                <div class="developer-card">
                                    <b>{row['Full Name']}</b><br>
                                    {row['Contact Number']}<br>
                                    {email}
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                        with col2:
                            is_active = st.checkbox(
                                "Active",
                                value=(current_status == "Active"),
                                key=f"{email}_{idx}"
                            )

                    updated_status.append({"Email Address": email, "Status": "Active" if is_active else "Inactive"})
                    active_count += is_active
                    inactive_count += not is_active
                    total_assigned += 1

        for update in updated_status:
            status_df.loc[status_df["Email Address"] == update["Email Address"], "Status"] = update["Status"]
        save_status(status_df)

        st.markdown("---")
        st.subheader("📊 Activity Summary")
        st.write(f"**Total Assigned Developers:** {total_assigned}")
        st.write(f"🟢 Active: **{active_count}**")
        st.write(f"🔴 Inactive: **{inactive_count}**")
    else:
        st.error("❌ No groups found for this email. Please check and try again.")

# ========= Download Section ==========
with st.expander("📥 Download Unassigned Data"):
    st.write("Interns who couldn't be grouped into full teams or tech leads who received no teams.")
    with open(UNASSIGNED_DEV_FILE, "rb") as f:
        st.download_button("Download Unassigned Developer Interns", f, file_name=UNASSIGNED_DEV_FILE)
    with open(UNASSIGNED_TECH_FILE, "rb") as f:
        st.download_button("Download Unassigned Tech Leads", f, file_name=UNASSIGNED_TECH_FILE)

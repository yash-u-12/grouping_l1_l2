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
INTERN_STATUS_FILE = "intern_statuses.pkl" # New file for intern statuses
RANDOM_SEED = 42
GROUP_SIZE = 5 # Define group size as a constant

# ========= Load CSVs ==========
@st.cache_data
def load_data():
    """Load and preprocess developer and tech lead data."""
    devs = pd.read_csv(DEV_FILE, dtype={"Contact Number": str})
    techs = pd.read_csv(TECH_FILE, dtype={"Contact Number": str})
    
    # Clean column names and remove duplicates
    devs.columns = devs.columns.str.strip()
    techs.columns = techs.columns.str.strip()
    devs = devs.drop_duplicates(subset=['Email Address'])
    
    return devs, techs

# ========= Assignment Logic (Keep as is) ==========
def compute_assignments(devs, techs):
    """
    Compute assignments of developer interns to tech leads.
    Returns: assignments dict, unassigned devs, unassigned techs
    """
    # Shuffle for fairness & reset index
    devs = devs.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)
    techs = techs.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)

    # Normalize strings for matching
    devs['Affiliation'] = devs['Affiliation'].str.strip().str.lower()
    techs['Affiliation'] = techs['Affiliation'].str.strip().str.lower()
    techs['Email Address'] = techs['Email Address'].str.strip().str.lower()

    assignments = defaultdict(list)
    leftout_groups = []

    # Group by college/affiliation
    grouped_devs = devs.groupby("Affiliation")
    grouped_techs = techs.groupby("Affiliation")

    # Assign groups college-wise
    for college, dev_group in grouped_devs:
        intern_groups = [dev_group.iloc[i:i+GROUP_SIZE] for i in range(0, len(dev_group), GROUP_SIZE)]

        techs_in_college = grouped_techs.get_group(college) if college in grouped_techs.groups else pd.DataFrame()

        tech_index = 0
        for group in intern_groups:
            if len(group) < GROUP_SIZE:
                leftout_groups.append(group)
            elif not techs_in_college.empty:
                assigned = False
                while tech_index < len(techs_in_college):
                    email = techs_in_college.iloc[tech_index]['Email Address']
                    # Check if tech lead has capacity (less than 5 groups)
                    if len(assignments[email]) < 5:
                        assignments[email].append(group)
                        assigned = True
                        # Move to the next tech lead in this college if capacity reached
                        if len(assignments[email]) == 5:
                            tech_index += 1
                        break
                    else:
                        tech_index += 1
                if not assigned:
                    # If no tech lead in this college has capacity, add group to leftout
                    leftout_groups.append(group)
            else:
                # If no tech leads in this college, add all groups to leftout
                leftout_groups.extend(intern_groups)
                break # All groups for this college are now in leftout_groups

    # Tech leads with capacity globally (those not fully assigned in the first pass)
    leftover_techs = [email.strip().lower() for email in techs['Email Address'] if len(assignments[email.strip().lower()]) < 5]

    # Assign leftover groups globally
    # Filter leftout_groups to only include those with GROUP_SIZE members for global assignment
    assignable_leftover_groups = [group for group in leftout_groups if len(group) == GROUP_SIZE]

    for group in assignable_leftover_groups:
        assigned = False
        for email in leftover_techs:
            if len(assignments[email]) < 5:
                assignments[email].append(group)
                # Remove tech lead from leftover_techs if capacity is reached
                if len(assignments[email]) == 5:
                    leftover_techs.remove(email)
                assigned = True
                break
        # Note: Groups not assigned here remain in leftout_groups implicitly

    # Flatten unassigned interns: This includes interns from original leftout_groups
    # that were not assigned in the second pass, and groups with < GROUP_SIZE members.
    unassigned_interns = []
    all_assigned_dev_emails = set()
    for groups in assignments.values():
        for group in groups:
            all_assigned_dev_emails.update(group['Email Address'].str.strip().str.lower().tolist())

    # Go through original developers and find those not in assigned groups
    final_unassigned_devs = devs[~devs['Email Address'].str.strip().str.lower().isin(all_assigned_dev_emails)].reset_index(drop=True)

    # Tech leads with zero assignments
    assigned_tech_emails = set(assignments.keys())
    final_unassigned_techs = techs[~techs['Email Address'].str.strip().str.lower().isin(assigned_tech_emails)].reset_index(drop=True)

    return assignments, final_unassigned_devs, final_unassigned_techs

# ========= Helper function to load or create assignments AND statuses ==========
def load_data_assignments_statuses():
    """Load existing assignments and statuses, or create them."""
    # Load or create assignments and unassigned lists
    if os.path.exists(ASSIGNMENT_FILE):
        with open(ASSIGNMENT_FILE, "rb") as f:
            assignments, unassigned_devs, unassigned_techs = pickle.load(f)
    else:
        # If assignment file doesn't exist, compute assignments
        devs, techs = load_data()
        assignments, unassigned_devs, unassigned_techs = compute_assignments(devs, techs)
        
        # Save new assignments and unassigned lists
        with open(ASSIGNMENT_FILE, "wb") as f:
            pickle.dump((assignments, unassigned_devs, unassigned_techs), f)
        
        # Save unassigned lists to CSVs (overwrite if they exist)
        unassigned_devs.to_csv(UNASSIGNED_DEV_FILE, index=False)
        unassigned_techs.to_csv(UNASSIGNED_TECH_FILE, index=False)
        
    # Load or initialize intern statuses
    if os.path.exists(INTERN_STATUS_FILE):
        with open(INTERN_STATUS_FILE, "rb") as f:
            intern_statuses = pickle.load(f)
    else:
        # Initialize all intern statuses to Active (True) for all unique interns
        intern_statuses = {}
        # Need access to the original developer list to initialize statuses for everyone
        devs, _ = load_data() # Load original data to get all unique intern emails
        for email in devs['Email Address'].str.strip().str.lower().unique():
            intern_statuses[email] = True # Default to Active

    return assignments, unassigned_devs, unassigned_techs, intern_statuses

# ========= Helper function to save intern statuses ==========
def save_intern_statuses(intern_statuses_dict):
    """Save the current state of intern statuses."""
    with open(INTERN_STATUS_FILE, "wb") as f:
        pickle.dump(intern_statuses_dict, f)

# ========= Callback function for status checkbox ==========
def save_intern_status_callback(intern_email, checkbox_key, intern_statuses_dict):
    """Callback to update and save intern status when checkbox changes."""
    # The checkbox value is automatically updated in st.session_state[checkbox_key]
    # Update the intern_statuses dictionary with the new status
    intern_statuses_dict[intern_email] = st.session_state[checkbox_key]
    # Save the updated statuses
    save_intern_statuses(intern_statuses_dict)
    # Streamlit will rerun after this callback, updating the dashboard counts


# ========= Streamlit UI ==========
st.set_page_config(page_title="Tech Lead Group Lookup", layout="wide", page_icon="🔍")

# Sidebar
def sidebar():
    st.sidebar.title("Navigation")
    st.sidebar.info(
        """
        - Enter your Tech Lead email to view your assigned developer intern groups and dashboard.
        - Download lists of unassigned interns and tech leads.
        """
    )
    st.sidebar.markdown("---")
    st.sidebar.write("Made with ❤️ using Streamlit")

sidebar()

# Main content
st.title("🔍 Tech Lead - Developer Group Lookup")
st.markdown(
    """
    Welcome! Use this dashboard to look up tech leads, view assignment statistics, and manage intern statuses.
    """
)

# Load data, assignments, and statuses
# Use st.session_state to persist assignments and statuses across reruns
if 'assignments' not in st.session_state:
    st.session_state.assignments, st.session_state.unassigned_devs, st.session_state.unassigned_techs, st.session_state.intern_statuses = load_data_assignments_statuses()

# Access data from session state
assignments = st.session_state.assignments
unassigned_devs = st.session_state.unassigned_devs
unassigned_techs = st.session_state.unassigned_techs
intern_statuses = st.session_state.intern_statuses

devs, techs = load_data() # Reload original devs/techs for total counts and tech lead details

# Tech Lead Lookup
st.markdown("---")
st.header("👩‍💼 Tech Lead Lookup")

with st.form("lookup_form"):
    email_input = st.text_input("Enter your Tech Lead Email:", placeholder="your.email@domain.com").strip().lower()
    submitted = st.form_submit_button("🔎 Lookup")

# Display tech lead info and assigned groups if email is entered and found
if email_input:
    if email_input in assignments:
        tech_row = techs[techs['Email Address'].str.strip().str.lower() == email_input]

        if not tech_row.empty:
            tech_row = tech_row.iloc[0]
            st.success("✅ Tech Lead Found")
            st.markdown(
                f"""
                <div style='background-color:#f0f2f6;padding:15px;border-radius:10px;'>
                <b>Full Name:</b> {tech_row['Full Name']}<br>
                <b>Affiliation:</b> {tech_row['Affiliation'].title()}<br>
                <b>Gender:</b> {tech_row['Gender']}<br>
                <b>Contact Number:</b> {tech_row['Contact Number']}<br>
                <b>Email:</b> {tech_row['Email Address']}
                </div>
                """,
                unsafe_allow_html=True
            )

            # --- Tech Lead Specific Dashboard ---
            st.markdown("---")
            st.header("📊 Your Assignment Dashboard")

            st.info("Metrics specific to the Tech Lead: **{tech_row['Full Name']}**") # Added descriptive text

            with st.container(border=True):
                assigned_intern_emails = set()
                for group in assignments[email_input]:
                     # Ensure emails are lower case and stripped when adding to set
                     assigned_intern_emails.update(group['Email Address'].str.strip().str.lower().tolist())

                active_count = 0
                inactive_count = 0
                for intern_email in assigned_intern_emails:
                     # Use the status from the session state dictionary. Default to Active if status not found (shouldn't happen if initialized correctly)
                     if st.session_state.intern_statuses.get(intern_email, True): 
                          active_count += 1
                     else:
                          inactive_count += 1

                dash_col1, dash_col2, dash_col3 = st.columns(3)
                dash_col1.metric("Total Assigned Interns", len(assigned_intern_emails))
                dash_col2.metric("Active Interns", active_count)
                dash_col3.metric("Inactive Interns", inactive_count)


            # --- Assigned Developer Intern Groups with Status ---
            st.markdown("---")
            st.subheader("👥 Assigned Developer Intern Groups")

            for idx, group in enumerate(assignments[email_input], 1):
                with st.expander(f"📦 Group {idx}"):
                    # Display intern details and a status checkbox
                    st.write("Intern Details and Status:")
                    # Iterate through rows (interns) in the group DataFrame
                    for intern_idx, intern_row in group.iterrows():
                         intern_email = intern_row['Email Address'].strip().lower()
                         # Get the status from the session state dictionary
                         current_status = st.session_state.intern_statuses.get(intern_email, True) # Default to Active

                         # Use a unique key for each checkbox based on intern email
                         checkbox_key = f"status_{intern_email}"

                         # Display checkbox and intern info. Use st.columns for better alignment.
                         col_status, col_info = st.columns([1, 3])

                         with col_status:
                              st.checkbox(
                                   "Active", # Label for the checkbox itself
                                   value=current_status,
                                   key=checkbox_key,
                                   on_change=save_intern_status_callback,
                                   args=(intern_email, checkbox_key, st.session_state.intern_statuses)
                              )
                         with col_info:
                              st.write(f"**{intern_row['Full Name']}**")
                              st.write(f"Email: {intern_row['Email Address']}, Contact: {intern_row['Contact Number']}")

                         st.markdown("\n") # Add a small gap after each intern entry

        else:
            st.error("❌ Tech Lead email found in assignments, but details not found in Tech Leads data. Data mismatch?")

    else:
        st.error("❌ No groups found for this email. Please check and try again.")

elif submitted and not email_input:
     st.warning("Please enter a Tech Lead email to search.")

# --- Global Assignment Dashboard ---
st.markdown("---")
st.header("📊 Overall Assignment Dashboard")

total_devs = len(devs)
total_techs = len(techs)
assigned_tech_leads_count = len(set(assignments.keys()))

# Count total assigned interns across all tech leads
total_assigned_interns_count = 0
for groups in assignments.values():
     for group in groups:
          total_assigned_interns_count += len(group)

overall_col1, overall_col2, overall_col3 = st.columns(3)
overall_col1.metric("👨‍💻 Total Developer Interns", total_devs)
overall_col2.metric("✅ Assigned Interns (Overall)", total_assigned_interns_count)
overall_col3.metric("❌ Unassigned Interns (Overall)", total_devs - total_assigned_interns_count)


overall_col4, overall_col5, overall_col6 = st.columns(3)
overall_col4.metric("👩‍🏫 Total Tech Leads", total_techs)
overall_col5.metric("✅ Assigned Tech Leads (Overall)", assigned_tech_leads_count)
overall_col6.metric("❌ Unassigned Tech Leads (Overall)", total_techs - assigned_tech_leads_count)


# ========= Download Unassigned Data ==========
st.markdown("---")
st.header("📥 Download Unassigned Data")
with st.expander("Show Download Options"):
    st.write("Interns who couldn't be grouped into full teams or tech leads who received no teams.")
    
    # Ensure files exist before offering download
    if os.path.exists(UNASSIGNED_DEV_FILE):
         with open(UNASSIGNED_DEV_FILE, "rb") as f:
             st.download_button("⬇️ Download Unassigned Developer Interns", f, file_name=UNASSIGNED_DEV_FILE)
    else:
         st.info(f"{UNASSIGNED_DEV_FILE} not yet generated.")

    if os.path.exists(UNASSIGNED_TECH_FILE):
         with open(UNASSIGNED_TECH_FILE, "rb") as f:
             st.download_button("⬇️ Download Unassigned Tech Leads", f, file_name=UNASSIGNED_TECH_FILE)
    else:
         st.info(f"{UNASSIGNED_TECH_FILE} not yet generated.")

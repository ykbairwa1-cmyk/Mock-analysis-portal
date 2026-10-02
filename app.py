import streamlit as st
import pandas as pd
from PIL import Image
import os
import uuid
import json
from datetime import datetime, timedelta
from fpdf import FPDF

# --- Setup & Constants ---
DATA_FILE = "mock_data_images.csv"
IMAGE_DIR = "saved_images"
EXAMS_FILE = "exams_settings.json"
CHAPTERS_FILE = "chapters_settings.json"

if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

# --- Settings Managers ---
def load_exams():
    if os.path.exists(EXAMS_FILE):
        with open(EXAMS_FILE, 'r') as f:
            return json.load(f)
    else:
        default_exams = {
            "RRB Section Controller": ["Mathematics", "General Intelligence & Reasoning", "General Awareness", "General Science"],
            "UPSC CSE (Anthro)": ["GS 1 - History & Geo", "GS 2 - Polity", "GS 3 - Economy & Sci", "GS 4 - Ethics", "CSAT", "Anthropology Paper 1", "Anthropology Paper 2"]
        }
        with open(EXAMS_FILE, 'w') as f:
            json.dump(default_exams, f)
        return default_exams

def save_exams(exams_dict):
    with open(EXAMS_FILE, 'w') as f:
        json.dump(exams_dict, f)

def load_chapters():
    if os.path.exists(CHAPTERS_FILE):
        with open(CHAPTERS_FILE, 'r') as f:
            data = json.load(f)
            if isinstance(data, list):
                return {"General": data}
            return data
    else:
        default_chapters = {
            "Polity": ["Fundamental Rights", "Parliament", "Executive"],
            "Mathematics": ["Time & Work", "Number System", "Percentage"]
        }
        with open(CHAPTERS_FILE, 'w') as f:
            json.dump(default_chapters, f)
        return default_chapters

def save_chapters(chapters_dict):
    with open(CHAPTERS_FILE, 'w') as f:
        json.dump(chapters_dict, f)

# --- Database Manager ---
def init_db():
    df = pd.DataFrame(columns=[
        "Date", "Exam_Category", "Mock_Name", "Subject", "Chapter", "Micro_Topic", 
        "Mistake_Reason", "Time_Taken_Sec", "Image_Path", "Next_Revision_Date"
    ])
    df.to_csv(DATA_FILE, index=False)

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            if "Exam_Category" not in df.columns:
                raise ValueError("Old CSV Schema")
            return df
        except Exception:
            try: os.rename(DATA_FILE, f"backup_corrupted_{uuid.uuid4().hex[:5]}.csv")
            except: os.remove(DATA_FILE)
            init_db()
            return pd.read_csv(DATA_FILE)
    else:
        init_db()
        return pd.read_csv(DATA_FILE)

def save_data(data_dict):
    df = pd.DataFrame([data_dict])
    df.to_csv(DATA_FILE, mode='a', header=not os.path.exists(DATA_FILE), index=False)

def update_csv_values(column_name, old_val, new_val):
    df = load_data()
    if not df.empty and old_val in df[column_name].values:
        df.loc[df[column_name] == old_val, column_name] = new_val
        df.to_csv(DATA_FILE, index=False)

def delete_record(index_to_drop):
    df = load_data()
    if index_to_drop in df.index:
        img_path = df.loc[index_to_drop, "Image_Path"]
        if pd.notna(img_path) and os.path.exists(img_path):
            try: os.remove(img_path)
            except: pass
        df = df.drop(index_to_drop)
        df.to_csv(DATA_FILE, index=False)
        st.rerun()

def calculate_revision_date(reason):
    today = datetime.now()
    if reason in ["Conceptual Gap", "Clueless"]: return (today + timedelta(days=2)).strftime("%Y-%m-%d")
    elif reason == "Memory/Fact Based": return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    elif reason in ["Time Pressure", "Overtime"]: return (today + timedelta(days=5)).strftime("%Y-%m-%d") 
    else: return (today + timedelta(days=7)).strftime("%Y-%m-%d")

# --- Page Config & Navigation ---
st.set_page_config(page_title="Mock Pro Tracker", layout="wide", initial_sidebar_state="expanded")

st.sidebar.title("🎯 Mock Tracker Pro")
main_menu = st.sidebar.radio("Navigation:", [
    "📤 Upload Questions", 
    "📂 Manage & Delete", 
    "📊 Smart Analysis & Revision", 
    "📥 Export PDF Workbook",
    "⚙️ Settings & Bulk Upload"
])

df_global = load_data()
exams_dict = load_exams()
saved_chapters = load_chapters()
reasons_list = ["Silly Mistake", "Conceptual Gap", "Memory/Fact Based", "Time Pressure", "Skipped", "Overtime", "Clueless"]

# --- 1. Upload Question Images ---
if main_menu == "📤 Upload Questions":
    st.title("Upload Mistake Screenshots")
    
    if not exams_dict:
        st.warning("Please add an Exam Category in Settings first.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            selected_exam = st.selectbox("1. Select Exam Category:", list(exams_dict.keys()))
            available_subjects = exams_dict[selected_exam]
            
        with col2:
            existing_mocks = df_global[df_global['Exam_Category'] == selected_exam]['Mock_Name'].unique().tolist() if not df_global.empty else []
            mock_choice = st.selectbox("2. Select or Create Mock:", ["-- Create New Mock --"] + existing_mocks)
            mock_name = st.text_input("Enter New Mock Name:") if mock_choice == "-- Create New Mock --" else mock_choice

        uploaded_files = st.file_uploader("3. Upload Screenshots (Select multiple)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        
        if uploaded_files:
            with st.form("batch_upload_form"):
                metadata = []
                for i, file in enumerate(uploaded_files):
                    st.subheader(f"Question {i+1}")
                    c1, c2, c3 = st.columns([1, 1.5, 1.5])
                    
                    with c1:
                        img = Image.open(file).convert('RGB')
                        st.image(img, use_container_width=True)
                    with c2:
                        subj = st.selectbox("Subject", available_subjects, key=f"sub_{i}")
                        
                        subject_chapters = saved_chapters.get(subj, [])
                        chap_choice = st.selectbox("Chapter", ["-- Add New Chapter --"] + subject_chapters, key=f"chap_choice_{i}")
                        
                        if chap_choice == "-- Add New Chapter --":
                            chap = st.text_input("Type New Chapter Name", key=f"chap_new_{i}")
                        else:
                            chap = chap_choice
                            
                        micro = st.text_input("Micro Topic", "General", key=f"mic_{i}")
                    with c3:
                        reason = st.selectbox("Reason", reasons_list, key=f"res_{i}")
                        time_sec = st.number_input("Time Taken (sec)", min_value=0, value=60, key=f"time_{i}")
                    
                    metadata.append({"img": img, "subj": subj, "chap": chap, "micro": micro, "reason": reason, "time": time_sec})
                    st.divider()
                    
                if st.form_submit_button("💾 Save All Questions"):
                    if not mock_name:
                        st.error("Mock Test Name is required!")
                    else:
                        new_chapters_added = False
                        for data in metadata:
                            if data["chap"]:
                                current_sub = data["subj"]
                                if current_sub not in saved_chapters:
                                    saved_chapters[current_sub] = []
                                if data["chap"].strip() not in saved_chapters[current_sub]:
                                    saved_chapters[current_sub].append(data["chap"].strip())
                                    new_chapters_added = True
                                
                            filename = f"{uuid.uuid4().hex}.jpg"
                            img_path = os.path.join(IMAGE_DIR, filename)
                            data["img"].thumbnail((1200, 1200))
                            data["img"].save(img_path, "JPEG", quality=85)
                            
                            save_data({
                                "Date": datetime.now().strftime("%Y-%m-%d"),
                                "Exam_Category": selected_exam,
                                "Mock_Name": mock_name,
                                "Subject": data["subj"],
                                "Chapter": data["chap"].strip(),
                                "Micro_Topic": data["micro"],
                                "Mistake_Reason": data["reason"],
                                "Time_Taken_Sec": data["time"],
                                "Image_Path": img_path,
                                "Next_Revision_Date": calculate_revision_date(data["reason"])
                            })
                            
                        if new_chapters_added:
                            save_chapters(saved_chapters)
                            
                        st.success("✅ Logged successfully! Chapters linked to subjects automatically.")

# --- 2. Manage & Delete Sections ---
elif main_menu == "📂 Manage & Delete":
    st.title("Review & Delete Logged Questions")
    df = load_data()
    
    if df.empty:
        st.info("No questions logged yet.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            filter_exam = st.selectbox("Filter by Exam:", ["All Exams"] + list(df['Exam_Category'].unique()))
        with col2:
            mocks_available = df[df['Exam_Category'] == filter_exam]['Mock_Name'].unique().tolist() if filter_exam != "All Exams" else df['Mock_Name'].unique().tolist()
            filter_mock = st.selectbox("Filter by Mock:", ["All Mocks"] + mocks_available)
        
        display_df = df
        if filter_exam != "All Exams": display_df = display_df[display_df['Exam_Category'] == filter_exam]
        if filter_mock != "All Mocks": display_df = display_df[display_df['Mock_Name'] == filter_mock]
            
        st.write(f"Showing **{len(display_df)}** questions.")
        
        for idx, row in display_df.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([1, 3, 1])
                with c1:
                    if pd.notna(row['Image_Path']) and os.path.exists(row['Image_Path']): st.image(row['Image_Path'], use_container_width=True)
                with c2:
                    st.markdown(f"**Mock:** {row['Mock_Name']} | **Subject:** {row['Subject']}")
                    st.markdown(f"**Topic:** {row['Chapter']} ➡️ *{row['Micro_Topic']}*")
                    st.markdown(f"**Reason:** `{row['Mistake_Reason']}` | 📅 **Revise On:** {row['Next_Revision_Date']}")
                with c3:
                    if st.button("🗑️ Delete", key=f"del_{idx}"): delete_record(idx)
                st.divider()

# --- 3. Smart Analysis & Revision ---
elif main_menu == "📊 Smart Analysis & Revision":
    st.title("Performance & Priority Engine")
    df = load_data()
    
    if df.empty:
        st.info("Log some questions to generate your priority list.")
    else:
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        st.subheader("📅 Today's Actionable Revision")
        revision_df = df[df['Next_Revision_Date'] <= today_str]
        
        if revision_df.empty:
            st.success("🎉 All caught up! No pending revisions for today.")
        else:
            st.warning(f"You have {len(revision_df)} question(s) pending for revision today!")
            rev_display = revision_df[['Subject', 'Chapter', 'Micro_Topic', 'Mistake_Reason', 'Mock_Name', 'Next_Revision_Date']].copy()
            st.dataframe(rev_display, use_container_width=True)

        st.divider()

        st.subheader("🔥 Weakest Topics (Priority Set)")
        priority_data = []
        grouped = df.groupby(['Subject', 'Chapter', 'Micro_Topic'])
        
        for name, group in grouped:
            total_mistakes = len(group)
            silly = len(group[group['Mistake_Reason'] == 'Silly Mistake'])
            concept = len(group[group['Mistake_Reason'].isin(['Conceptual Gap', 'Clueless'])])
            
            if concept >= 2 or total_mistakes >= 4: priority = "🔴 HIGH (Must Revise Concepts)"
            elif silly >= 3 or total_mistakes >= 2: priority = "🟡 MEDIUM (Practice Needed)"
            else: priority = "🟢 LOW (Occasional Error)"
                
            priority_data.append({
                "Subject": name[0], "Chapter": name[1], "Micro Topic": name[2],
                "Total Mistakes": total_mistakes, "Concept Gaps": concept, "Priority Level": priority
            })
            
        priority_df = pd.DataFrame(priority_data).sort_values(by=["Concept Gaps", "Total Mistakes"], ascending=False)
        st.dataframe(priority_df, use_container_width=True)

# --- 4. Export PDF ---
elif main_menu == "📥 Export PDF Workbook":
    st.title("Export PDF with Safe Formatting")
    df = load_data()
    
    if df.empty:
        st.info("No data available to export.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            sel_exam = st.selectbox("Exam Filter:", ["All Exams"] + list(df['Exam_Category'].unique()))
        with col2:
            mocks_available = df[df['Exam_Category'] == sel_exam]['Mock_Name'].unique().tolist() if sel_exam != "All Exams" else df['Mock_Name'].unique().tolist()
            sel_mock = st.selectbox("Mock Filter:", ["All Mocks"] + mocks_available)
        with col3:
            sel_reason = st.selectbox("Reason Filter:", ["All Reasons"] + reasons_list)
            
        if st.button("📄 Generate PDF Workbook"):
            export_df = df
            if sel_exam != "All Exams": export_df = export_df[export_df['Exam_Category'] == sel_exam]
            if sel_mock != "All Mocks": export_df = export_df[export_df['Mock_Name'] == sel_mock]
            if sel_reason != "All Reasons": export_df = export_df[export_df['Mistake_Reason'] == sel_reason]
                
            if export_df.empty:
                st.warning("No data matches this filter.")
            else:
                progress = st.progress(0)
                pdf = FPDF()
                pdf.set_auto_page_break(auto=True, margin=15)
                
                for index, row in export_df.iterrows():
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 14)
                    pdf.cell(0, 8, f"Exam: {row['Exam_Category']} | Mock: {row['Mock_Name']}", ln=True)
                    
                    pdf.set_font("Arial", 'B', 12)
                    pdf.cell(0, 8, f"Subject: {row['Subject']} | Chapter: {row['Chapter']} ({row['Micro_Topic']})", ln=True)
                    
                    pdf.set_font("Arial", 'I', 11)
                    pdf.cell(0, 8, f"Reason: {row['Mistake_Reason']} | Time: {row['Time_Taken_Sec']}s", ln=True)
                    pdf.ln(5)
                    
                    img_path = row['Image_Path']
                    if pd.notna(img_path) and os.path.exists(img_path):
                        try: pdf.image(img_path, w=170) 
                        except Exception as e: pdf.cell(0, 10, f"[Image Render Error: {str(e)}]", ln=True)
                    else:
                        pdf.cell(0, 10, "[Image Missing from Storage]", ln=True)
                        
                    current_idx = export_df.index.get_loc(index)
                    progress.progress((current_idx + 1) / len(export_df))
                    
                pdf_file = "Revision_Workbook.pdf"
                pdf.output(pdf_file)
                st.success("✅ PDF is ready!")
                
                with open(pdf_file, "rb") as f:
                    st.download_button("📥 Click Here to Download PDF", f, file_name="Revision_Workbook.pdf", mime="application/pdf")

# --- 5. Settings & Customization ---
elif main_menu == "⚙️ Settings & Bulk Upload":
    st.title("Settings & App Customization")
    
    # ------------------ EXAM & SUBJECTS ------------------
    st.header("1. Exam & Subject Management")
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Add New Exam Category")
        new_exam = st.text_input("New Exam Name (e.g. SSC CGL):")
        new_exam_subs = st.text_input("Enter Subjects (Comma separated):")
        if st.button("Add Exam"):
            if new_exam and new_exam_subs:
                subs_list = [s.strip() for s in new_exam_subs.split(",")]
                exams_dict[new_exam] = subs_list
                save_exams(exams_dict)
                st.success(f"Added {new_exam}!")
                st.rerun()
                
        st.divider()
        edit_exam = st.selectbox("Select Exam to modify:", list(exams_dict.keys()), key="add_sub_ex")
        add_sub = st.text_input("Add a New Subject to this Exam:")
        if st.button("Add Subject"):
            if add_sub and add_sub not in exams_dict[edit_exam]:
                exams_dict[edit_exam].append(add_sub.strip())
                save_exams(exams_dict)
                st.success(f"Added '{add_sub}'!")
                st.rerun()

    with c2:
        st.subheader("Edit / Delete Subjects")
        edit_exam_del = st.selectbox("Select Exam:", list(exams_dict.keys()), key="del_sub_ex")
        if exams_dict[edit_exam_del]:
            subject_to_edit = st.selectbox("Select Subject:", exams_dict[edit_exam_del])
            
            new_sub_name = st.text_input("Rename Subject To:", value=subject_to_edit)
            if st.button("Rename Subject"):
                if new_sub_name != subject_to_edit:
                    idx = exams_dict[edit_exam_del].index(subject_to_edit)
                    exams_dict[edit_exam_del][idx] = new_sub_name.strip()
                    save_exams(exams_dict)
                    
                    if subject_to_edit in saved_chapters:
                        saved_chapters[new_sub_name.strip()] = saved_chapters.pop(subject_to_edit)
                        save_chapters(saved_chapters)
                        
                    update_csv_values("Subject", subject_to_edit, new_sub_name.strip())
                    st.success("Renamed successfully!")
                    st.rerun()
                    
            if st.button("🗑️ Delete Subject", type="primary"):
                exams_dict[edit_exam_del].remove(subject_to_edit)
                save_exams(exams_dict)
                if subject_to_edit in saved_chapters:
                    del saved_chapters[subject_to_edit]
                    save_chapters(saved_chapters)
                st.warning("Subject Deleted.")
                st.rerun()
                
        st.divider()
        if st.button("🚨 Delete Entire Exam Category", type="primary"):
            del exams_dict[edit_exam_del]
            save_exams(exams_dict)
            st.rerun()
            
    st.divider()
    
    # ------------------ BULK CHAPTER MANAGEMENT ------------------
    st.header("2. Bulk Chapter List Management")
    st.write("Add all chapters for a specific subject at once, or edit existing ones.")
    
    col3, col4 = st.columns(2)
    with col3:
        st.subheader("Bulk Add Chapters")
        bulk_exam = st.selectbox("Select Exam:", list(exams_dict.keys()), key="bulk_ex")
        if exams_dict[bulk_exam]:
            bulk_sub = st.selectbox("Select Subject:", exams_dict[bulk_exam], key="bulk_sub")
            
            # --- VIEW EXISTING CHAPTERS BUTTON (Expander) ---
            existing_chaps = saved_chapters.get(bulk_sub, [])
            with st.expander(f"👀 View {len(existing_chaps)} Existing Chapters"):
                if existing_chaps:
                    st.write(", ".join(existing_chaps))
                else:
                    st.write("No chapters added to this subject yet.")
            
            bulk_chaps = st.text_area("Paste Chapters Here (Comma separated):\ne.g. Percentage, Algebra, Geometry, Average")
            
            if st.button("Add Chapters in Bulk", type="secondary"):
                if bulk_chaps.strip():
                    if bulk_sub not in saved_chapters:
                        saved_chapters[bulk_sub] = []
                        
                    new_chaps = [c.strip() for c in bulk_chaps.split(",") if c.strip()]
                    added_count = 0
                    for nc in new_chaps:
                        if nc not in saved_chapters[bulk_sub]:
                            saved_chapters[bulk_sub].append(nc)
                            added_count += 1
                            
                    if added_count > 0:
                        save_chapters(saved_chapters)
                        st.success(f"Successfully added {added_count} new chapters to {bulk_sub}!")
                        st.rerun()
                    else:
                        st.info("These chapters already exist.")

    with col4:
        st.subheader("Edit / Delete Existing Chapter")
        edit_sub_chap = st.selectbox("Select Subject to view Chapters:", list(saved_chapters.keys()), key="edit_sub_chap")
        
        if edit_sub_chap and saved_chapters[edit_sub_chap]:
            chap_to_edit = st.selectbox("Select Chapter:", saved_chapters[edit_sub_chap])
            new_chap_name = st.text_input("Rename Chapter To:", value=chap_to_edit)
            
            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if st.button("Rename Chapter"):
                    if new_chap_name != chap_to_edit:
                        idx = saved_chapters[edit_sub_chap].index(chap_to_edit)
                        saved_chapters[edit_sub_chap][idx] = new_chap_name.strip()
                        save_chapters(saved_chapters)
                        update_csv_values("Chapter", chap_to_edit, new_chap_name.strip())
                        st.success("Chapter Renamed!")
                        st.rerun()
            with c_btn2:
                if st.button("🗑️️ Delete Chapter", type="primary"):
                    saved_chapters[edit_sub_chap].remove(chap_to_edit)
                    save_chapters(saved_chapters)
                    st.warning("Chapter removed from Dropdown.")
                    st.rerun()
        else:
            st.info("No chapters added to this subject yet.")

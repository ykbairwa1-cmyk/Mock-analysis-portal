import streamlit as st
import pandas as pd
from PIL import Image
import os
import uuid
from datetime import datetime
from fpdf import FPDF

# --- Database & Folder Setup ---
DATA_FILE = "mock_data_images.csv"
IMAGE_DIR = "saved_images"

# Create folder for saving images if it doesn't exist
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

def init_db():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=[
            "Date", "Mock_Name", "Subject", "Chapter", 
            "Mistake_Reason", "Time_Taken_Sec", "Image_Path"
        ])
        df.to_csv(DATA_FILE, index=False)

def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame()

def save_data(data_dict):
    df = pd.DataFrame([data_dict])
    df.to_csv(DATA_FILE, mode='a', header=not os.path.exists(DATA_FILE), index=False)

init_db()

# --- Page Config & Navigation ---
st.set_page_config(page_title="Mock Analysis Pro", layout="wide")

st.sidebar.title("🎯 Navigation")
main_menu = st.sidebar.radio("Go To:", ["Upload Question Images", "Mock Sections", "Analysis Dashboard", "Export Revision PDF"])

df_global = load_data()
existing_mocks = df_global['Mock_Name'].unique().tolist() if not df_global.empty else []
reasons_list = ["Silly Mistake", "Conceptual Gap", "Memory/Fact Based", "Time Pressure", "Skipped", "Overtime", "Clueless"]

# --- 1. Upload Question Images ---
if main_menu == "Upload Question Images":
    st.title("📤 Upload Questions (No API Required)")
    st.write("Upload screenshots of your questions directly. They will be saved as images.")
    
    # Mock Selection (Flexible)
    mock_choice = st.selectbox("Select Existing Mock Test or Create New:", ["-- Create New Mock Test --"] + existing_mocks)
    if mock_choice == "-- Create New Mock Test --":
        mock_name = st.text_input("Enter New Mock Test Name (e.g., RRB Test 1):")
    else:
        mock_name = mock_choice

    uploaded_files = st.file_uploader("Upload Question Screenshots", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    
    if uploaded_files:
        st.info(f"{len(uploaded_files)} image(s) selected. Fill details below and save.")
        
        with st.form("batch_upload_form"):
            metadata = []
            
            for i, file in enumerate(uploaded_files):
                st.markdown(f"### Question {i+1}")
                col1, col2, col3 = st.columns([1, 2, 2])
                
                with col1:
                    img = Image.open(file).convert('RGB') # Convert to RGB for PDF compatibility
                    st.image(img, use_container_width=True)
                
                with col2:
                    subj = st.text_input(f"Subject", "General Studies", key=f"sub_{i}")
                    chap = st.text_input(f"Chapter", "Polity", key=f"chap_{i}")
                
                with col3:
                    reason = st.selectbox(f"Mistake Reason", reasons_list, key=f"res_{i}")
                    time_sec = st.number_input(f"Time Taken (sec)", min_value=0, value=60, key=f"time_{i}")
                
                metadata.append({"img": img, "subj": subj, "chap": chap, "reason": reason, "time": time_sec})
                st.divider()
                
            submitted = st.form_submit_button("💾 Save All Questions")
            
            if submitted:
                if not mock_name:
                    st.error("Please enter a Mock Test Name!")
                else:
                    for idx, data in enumerate(metadata):
                        # Save image to local folder with unique ID
                        unique_filename = f"{uuid.uuid4().hex}.jpg"
                        img_path = os.path.join(IMAGE_DIR, unique_filename)
                        data["img"].save(img_path, "JPEG")
                        
                        # Save record to CSV
                        save_data({
                            "Date": datetime.now().strftime("%Y-%m-%d"),
                            "Mock_Name": mock_name,
                            "Subject": data["subj"],
                            "Chapter": data["chap"],
                            "Mistake_Reason": data["reason"],
                            "Time_Taken_Sec": data["time"],
                            "Image_Path": img_path
                        })
                        
                    st.success("✅ All questions saved successfully! Check 'Mock Sections' to view them.")

# --- 2. Mock Sections ---
elif main_menu == "Mock Sections":
    st.title("📂 Mock Test Folders")
    df = load_data()
    if df.empty:
        st.info("No data recorded yet.")
    else:
        selected_mock = st.selectbox("Choose Mock Test:", df['Mock_Name'].unique())
        mock_df = df[df['Mock_Name'] == selected_mock]
        
        st.metric("Total Questions Logged", len(mock_df))
        
        for idx, row in mock_df.iterrows():
            with st.expander(f"[{row['Subject']}] {row['Chapter']} - {row['Mistake_Reason']} ({row['Time_Taken_Sec']} sec)"):
                if os.path.exists(row['Image_Path']):
                    st.image(row['Image_Path'], use_container_width=True)
                else:
                    st.error("Image file missing!")

# --- 3. Dashboard Analysis ---
elif main_menu == "Analysis Dashboard":
    st.title("🚨 Analytics & Red Zone")
    df = load_data()
    if df.empty:
        st.info("No data available.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Mistakes by Reason")
            st.bar_chart(df['Mistake_Reason'].value_counts())
        with c2:
            st.subheader("Priority Chapters (Red Zone)")
            chapter_counts = df['Chapter'].value_counts()
            for chap, count in chapter_counts.items():
                if count >= 2:
                    st.error(f"**{chap}** — {count} mistakes. Revise immediately!")
                else:
                    st.warning(f"**{chap}** — {count} mistake.")

# --- 4. Export PDF (Now with Images!) ---
elif main_menu == "Export PDF":
    st.title("📥 Export Revision Workbook")
    df = load_data()
    if df.empty:
        st.info("No data to export.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            sel_mock = st.selectbox("Select Mock:", ["All Mocks"] + list(df['Mock_Name'].unique()))
        with col2:
            sel_reason = st.selectbox("Filter by Reason:", ["All Reasons"] + reasons_list)
            
        if st.button("Generate PDF with Images"):
            export_df = df
            if sel_mock != "All Mocks":
                export_df = export_df[export_df['Mock_Name'] == sel_mock]
            if sel_reason != "All Reasons":
                export_df = export_df[export_df['Mistake_Reason'] == sel_reason]
                
            if export_df.empty:
                st.warning("No questions match this filter.")
            else:
                progress = st.progress(0)
                status = st.empty()
                
                pdf = FPDF()
                pdf.set_auto_page_break(auto=True, margin=15)
                
                for index, row in export_df.iterrows():
                    status.text(f"Processing question {index + 1} of {len(export_df)}...")
                    
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 12)
                    pdf.cell(0, 8, f"Mock: {row['Mock_Name']} | Subject: {row['Subject']} | Chapter: {row['Chapter']}", ln=True)
                    
                    pdf.set_font("Arial", 'I', 11)
                    pdf.cell(0, 8, f"Reason: {row['Mistake_Reason']} | Time Taken: {row['Time_Taken_Sec']}s", ln=True)
                    pdf.ln(5)
                    
                    # Add Image to PDF
                    img_path = row['Image_Path']
                    if os.path.exists(img_path):
                        # Calculate image width to fit A4 page
                        pdf.image(img_path, w=180) # 180mm leaves a nice margin
                    else:
                        pdf.set_font("Arial", 'B', 12)
                        pdf.cell(0, 10, "[Image File Missing]", ln=True)
                        
                    progress.progress((index + 1) / len(export_df))
                    
                pdf_file = "Mock_Revision_Workbook.pdf"
                pdf.output(pdf_file)
                status.text("✅ PDF Generated Successfully!")
                
                with open(pdf_file, "rb") as f:
                    st.download_button("📥 Download PDF", f, file_name=pdf_file, mime="application/pdf")

import streamlit as st
import pandas as pd
from PIL import Image
import os
import time
from datetime import datetime
import google.generativeai as genai
from fpdf import FPDF

# --- Database Setup ---
DATA_FILE = "mock_data_pro.csv"

def init_db():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=[
            "Date", "Mock_Name", "Subject", "Chapter", 
            "Mistake_Reason", "Time_Taken_Sec", "Question_Text"
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

st.sidebar.title("⚙️ Settings")
api_key = st.sidebar.text_input("Enter Gemini API Key:", type="password")

# Yahan naya Model Selector add kiya gaya hai error fix karne ke liye
selected_model = st.sidebar.selectbox("Select AI Model:", ["gemini-1.5-flash-latest", "gemini-1.5-pro-latest", "gemini-1.5-flash"])

st.sidebar.title("🎯 Navigation")
main_menu = st.sidebar.radio("Go To:", ["Batch Upload (Smart OCR)", "Mock Sections", "Dashboard", "Export PDF"])

df_global = load_data()
existing_mocks = df_global['Mock_Name'].unique().tolist() if not df_global.empty else []

reasons_list = ["Silly Mistake", "Conceptual Gap", "Memory/Fact Based", "Time Pressure", "Skipped", "Overtime", "Clueless"]

# --- 1. Batch Upload & AI OCR ---
if main_menu == "Batch Upload (Smart OCR)":
    st.title("📤 Batch Upload & Extract (No API Limit Issue)")
    
    mock_choice = st.selectbox("Select Existing Mock Test or Create New:", ["-- Create New Mock Test --"] + existing_mocks)
    if mock_choice == "-- Create New Mock Test --":
        mock_name = st.text_input("Enter New Mock Test Name (e.g., RRB Test 1):")
    else:
        mock_name = mock_choice

    uploaded_files = st.file_uploader("Upload Multiple Question Screenshots", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    
    if uploaded_files:
        st.info(f"{len(uploaded_files)} images uploaded. Fill details below and extract all at once.")
        
        with st.form("batch_processing_form"):
            metadata = []
            
            for i, file in enumerate(uploaded_files):
                st.markdown(f"### Question {i+1}")
                col1, col2, col3 = st.columns([1, 2, 2])
                
                with col1:
                    img = Image.open(file)
                    st.image(img, use_container_width=True)
                
                with col2:
                    subj = st.text_input(f"Subject", "General Studies", key=f"sub_{i}")
                    chap = st.text_input(f"Chapter", "Polity", key=f"chap_{i}")
                
                with col3:
                    reason = st.selectbox(f"Mistake Reason", reasons_list, key=f"res_{i}")
                    time_sec = st.number_input(f"Time Taken (sec)", min_value=0, value=60, key=f"time_{i}")
                
                metadata.append({"file": file, "img": img, "subj": subj, "chap": chap, "reason": reason, "time": time_sec})
                st.divider()
                
            submitted = st.form_submit_button("🤖 Extract Text & Save All Questions")
            
            if submitted:
                if not api_key:
                    st.error("Please enter your Gemini API Key in the sidebar first!")
                elif not mock_name:
                    st.error("Please enter a Mock Test Name!")
                else:
                    genai.configure(api_key=api_key)
                    # Ab yeh dynamic model use karega jo aap sidebar se select karenge
                    model = genai.GenerativeModel(selected_model)
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for idx, data in enumerate(metadata):
                        status_text.text(f"Extracting text for Question {idx+1}/{len(metadata)}...")
                        
                        try:
                            prompt = "Extract ONLY the main question text from this image. Do not include the options (A, B, C, D) unless they are part of the question logic. Ignore any UI elements like battery, time, or buttons."
                            response = model.generate_content([prompt, data["img"]])
                            extracted_text = response.text.strip()
                        except Exception as e:
                            extracted_text = f"[Error extracting text: {e}]"
                            
                        save_data({
                            "Date": datetime.now().strftime("%Y-%m-%d"),
                            "Mock_Name": mock_name,
                            "Subject": data["subj"],
                            "Chapter": data["chap"],
                            "Mistake_Reason": data["reason"],
                            "Time_Taken_Sec": data["time"],
                            "Question_Text": extracted_text
                        })
                        
                        progress_bar.progress((idx + 1) / len(metadata))
                        
                        if idx < len(metadata) - 1:
                            time.sleep(3)
                            
                    status_text.text("✅ All questions extracted and saved successfully!")
                    st.success("Batch processing complete! Check 'Mock Sections' to view them.")

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
            with st.expander(f"[{row['Subject']}] {row['Chapter']} - {row['Mistake_Reason']}"):
                st.write(f"**Time Taken:** {row['Time_Taken_Sec']} sec")
                st.write(f"**Question:**\n{row['Question_Text']}")

# --- 3. Dashboard ---
elif main_menu == "Dashboard":
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

# --- 4. Export PDF ---
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
            
        if st.button("Generate PDF"):
            export_df = df
            if sel_mock != "All Mocks":
                export_df = export_df[export_df['Mock_Name'] == sel_mock]
            if sel_reason != "All Reasons":
                export_df = export_df[export_df['Mistake_Reason'] == sel_reason]
                
            if export_df.empty:
                st.warning("No questions match this filter.")
            else:
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(0, 10, "Revision Workbook", ln=True, align="C")
                pdf.ln(5)
                
                for index, row in export_df.iterrows():
                    pdf.set_font("Arial", 'B', 11)
                    pdf.cell(0, 8, f"Mock: {row['Mock_Name']} | [{row['Subject']}] {row['Chapter']}", ln=True)
                    
                    pdf.set_font("Arial", 'I', 10)
                    pdf.cell(0, 6, f"Reason: {row['Mistake_Reason']} | Time: {row['Time_Taken_Sec']}s", ln=True)
                    
                    pdf.set_font("Arial", '', 10)
                    q_text = str(row['Question_Text']).encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(0, 6, f"{q_text}")
                    pdf.cell(0, 6, "-" * 50, ln=True)
                    pdf.ln(2)
                    
                pdf_file = "Mock_Workbook.pdf"
                pdf.output(pdf_file)
                
                with open(pdf_file, "rb") as f:
                    st.download_button("Download PDF", f, file_name=pdf_file, mime="application/pdf")

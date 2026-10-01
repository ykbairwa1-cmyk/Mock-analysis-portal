import streamlit as st
import pandas as pd
from PIL import Image
import os
from datetime import datetime
from fpdf import FPDF

DATA_FILE = "mock_data.csv"

def init_db():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=[
            "Date", "Mock_Name", "Subject", "Chapter", 
            "MicroTopic", "Mistake_Reason", "Time_Taken_Sec", 
            "Guess_Type", "Question_Text"
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

st.set_page_config(page_title="Mock Analysis Pro", layout="wide")

st.sidebar.title("🎯 Mock Portal Navigation")
main_menu = st.sidebar.radio("Go To:", ["Upload & Analyze", "Mock-wise Sections", "Dashboard & Priority", "Export PDF Workbook"])

df_global = load_data()

if main_menu == "Upload & Analyze":
    st.title("📤 Upload Mock Question (No API Key Required)")
    
    # Mock test management
    existing_mocks = df_global['Mock_Name'].unique().tolist() if not df_global.empty else []
    mock_choice = st.selectbox("Select Existing Mock Test or Create New:", ["-- Create New Mock Test --"] + existing_mocks)
    
    if mock_choice == "-- Create New Mock Test --":
        mock_name = st.text_input("Enter New Mock Test Name (e.g., Section Controller Test 1):")
    else:
        mock_name = mock_choice

    uploaded_file = st.file_uploader("Upload Question Image", type=["png", "jpg", "jpeg"])
    
    col1, col2 = st.columns(2)
    with col1:
        subject = st.text_input("Subject (e.g., Mathematics, Reasoning, General Awareness):", "General Studies")
        chapter = st.text_input("Chapter Name (e.g., Time & Distance, Polity):", "General")
        micro_topic = st.text_input("Micro Topic / Concept:", "Core Concept")
    with col2:
        mistake_reason = st.selectbox("Reason for Mistake", [
            "Silly Mistake (Calculation/Reading)", 
            "Conceptual Gap (Logic Failed)", 
            "Memory/Fact Based (Forgot formula)", 
            "Time Pressure", 
            "Clueless (Didn't study)"
        ])
        time_taken = st.number_input("Time Taken (sec):", min_value=0, value=60)
        guess_type = st.radio("Guess Type", ["No Guess (Normal Try)", "Educated Guess (50-50)", "Blind Guess"])

    question_text = st.text_area("Question Text / Notes (Optional description):", "Custom uploaded question notes.")

    if uploaded_file:
        st.image(uploaded_file, width=400)
        
    if st.button("Save Mistake Analysis"):
        if not mock_name:
            st.error("Please provide a Mock Test Name!")
        else:
            save_data({
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "Mock_Name": mock_name,
                "Subject": subject,
                "Chapter": chapter,
                "MicroTopic": micro_topic,
                "Mistake_Reason": mistake_reason,
                "Time_Taken_Sec": time_taken,
                "Guess_Type": guess_type,
                "Question_Text": question_text
            })
            st.success(f"Successfully logged mistake under mock: **{mock_name}**!")

elif main_menu == "Mock-wise Sections":
    st.title("📂 Mock Test Specific Sections")
    df = load_data()
    if df.empty:
        st.info("No mock data recorded yet. Upload some questions first!")
    else:
        mock_list = df['Mock_Name'].unique()
        selected_mock = st.selectbox("Choose Mock Test Section:", mock_list)
        
        st.markdown(f"### 📊 Analysis for: `{selected_mock}`")
        mock_df = df[df['Mock_Name'] == selected_mock]
        
        st.metric("Total Mistakes Logged", len(mock_df))
        
        # Display table of mistakes for this mock
        st.dataframe(mock_df[['Date', 'Subject', 'Chapter', 'Mistake_Reason', 'Time_Taken_Sec']], use_container_width=True)
        
        # Detailed cards
        for idx, row in mock_df.iterrows():
            with st.expander(f"[{row['Subject']}] {row['Chapter']} - Reason: {row['Mistake_Reason']}"):
                st.write(f"**Micro-Topic:** {row['MicroTopic']}")
                st.write(f"**Time Taken:** {row['Time_Taken_Sec']} sec | **Guess Type:** {row['Guess_Type']}")
                st.write(f"**Notes/Text:** {row['Question_Text']}")

elif main_menu == "Dashboard & Priority":
    st.title("📈 Performance Dashboard & Red Zone")
    df = load_data()
    if df.empty:
        st.info("No data available yet.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Mistakes by Reason")
            st.bar_chart(df['Mistake_Reason'].value_counts())
        with c2:
            st.subheader("Mistakes by Subject")
            st.bar_chart(df['Subject'].value_counts())
            
        st.subheader("🚨 THE RED ZONE (Priority Chapters)")
        chapter_counts = df['Chapter'].value_counts()
        for chapter, count in chapter_counts.items():
            if count >= 2:
                st.error(f"**{chapter}** — {count} mistakes recorded. Revise Immediately!")
            else:
                st.warning(f"**{chapter}** — {count} mistake recorded.")

elif main_menu == "Export PDF Workbook":
    st.title("📥 Export Revision Workbook for iPad (GoodNotes/CollaNote)")
    df = load_data()
    if df.empty:
        st.info("No mistakes logged to export.")
    else:
        selected_export_mock = st.selectbox("Select Mock Test to Export:", ["All Mocks Combined"] + list(df['Mock_Name'].unique()))
        
        if st.button("Generate iPad PDF Workbook"):
            export_df = df if selected_export_mock == "All Mocks Combined" else df[df['Mock_Name'] == selected_export_mock]
            
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            
            pdf.cell(0, 10, f"Revision Workbook - {selected_export_mock}", ln=True, align="C")
            pdf.ln(5)
            
            for index, row in export_df.iterrows():
                q_text = str(row['Question_Text']).encode('latin-1', 'replace').decode('latin-1')
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(0, 8, f"Mock: {row['Mock_Name']} | Subject: {row['Subject']} | Chapter: {row['Chapter']}", ln=True)
                pdf.set_font("Arial", '', 10)
                pdf.multi_cell(0, 6, f"Details: {q_text}")
                pdf.cell(0, 6, f"Mistake Reason: {row['Mistake_Reason']} | Time: {row['Time_Taken_Sec']}s", ln=True)
                pdf.cell(0, 6, "-" * 50, ln=True)
                
            pdf.output("Revision_Workbook.pdf")
            
            with open("Revision_Workbook.pdf", "rb") as f:
                st.download_button("📥 Download PDF File", f, "Revision_Workbook.pdf", "application/pdf")

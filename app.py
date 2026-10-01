
import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import json
import os
from fpdf import FPDF
from datetime import datetime

DATA_FILE = "mock_data.csv"

def init_db():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=["Date", "Mock_Name", "Subject", "Chapter", "MicroTopic", "Mistake_Reason", "Time_Taken_Sec", "Guess_Type", "Question_Text"])
        df.to_csv(DATA_FILE, index=False)

def load_data(): return pd.read_csv(DATA_FILE)

def save_data(data_dict):
    df = pd.DataFrame([data_dict])
    df.to_csv(DATA_FILE, mode='a', header=not os.path.exists(DATA_FILE), index=False)

init_db()

st.set_page_config(page_title="Mock Analysis Pro", layout="wide")
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go To:", ["Upload & Analyze", "Dashboard & Priority", "Export PDF Workbook"])
API_KEY = st.sidebar.text_input("Enter Gemini API Key", type="password")

if page == "Upload & Analyze":
    st.title("Upload Mock Question")
    mock_name = st.text_input("Mock Test Name:")
    uploaded_file = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"])
    
    col1, col2 = st.columns(2)
    with col1:
        mistake_reason = st.selectbox("Reason for Mistake", ["Silly Mistake (Calculation/Reading)", "Conceptual Gap (Logic Failed)", "Memory/Fact Based (Forgot formula)", "Time Pressure", "Clueless (Didn't study)"])
        time_taken = st.number_input("Time (sec)", min_value=0, value=60)
    with col2:
        guess_type = st.radio("Guess Type", ["No Guess (Normal Try)", "Educated Guess (50-50)", "Blind Guess"])

    if uploaded_file and API_KEY:
        st.image(uploaded_file, width=400)
        if st.button("Extract Data & Analyze"):
            try:
                genai.configure(api_key=API_KEY)
                model = genai.GenerativeModel('gemini-1.5-flash') # ya gemini-2.5-flash / gemini-1.5-pro

                img = Image.open(uploaded_file)
                prompt = 'Extract details from this exam question image. Return ONLY JSON format.\n{"QuestionText": "text", "Subject": "subject", "Chapter": "chapter", "MicroTopic": "topic"}'
                with st.spinner("AI is analyzing the question..."):
                    response = model.generate_content([prompt, img], generation_config={"response_mime_type": "application/json"})
                    data = json.loads(response.text)
                st.success("Analysis Complete!")
                st.json(data)
                save_data({"Date": datetime.now().strftime("%Y-%m-%d"), "Mock_Name": mock_name, "Subject": data.get("Subject", "Unknown"), "Chapter": data.get("Chapter", "Unknown"), "MicroTopic": data.get("MicroTopic", "Unknown"), "Mistake_Reason": mistake_reason, "Time_Taken_Sec": time_taken, "Guess_Type": guess_type, "Question_Text": data.get("QuestionText", "")})
                st.info("Data saved to database!")
            except Exception as e: st.error(f"Error: {e}")
    elif not API_KEY: st.warning("Please enter your Gemini API Key in the sidebar.")

elif page == "Dashboard & Priority":
    st.title("Performance Dashboard")
    df = load_data()
    if not df.empty:
        c1, c2 = st.columns(2)
        with c1: st.bar_chart(df['Mistake_Reason'].value_counts())
        with c2: st.bar_chart(df['Subject'].value_counts())
        st.subheader("🚨 THE RED ZONE (Priority Chapters)")
        for chapter, count in df['Chapter'].value_counts().items():
            if count >= 2: st.error(f"**{chapter}** - {count} mistakes. Revise Immediately!")
            else: st.warning(f"**{chapter}** - {count} mistake.")

elif page == "Export PDF Workbook":
    st.title("Generate PDF for iPad")
    df = load_data()
    if not df.empty and st.button("Generate PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        for index, row in df.iterrows():
            q_text = str(row['Question_Text']).encode('latin-1', 'replace').decode('latin-1')
            pdf.cell(0, 10, f"Q: [{row['Subject']} - {row['Chapter']}]", ln=True)
            pdf.multi_cell(0, 8, f"{q_text}")
            pdf.cell(0, 8, f"Reason: {row['Mistake_Reason']}", ln=True)
            pdf.cell(0, 8, "-"*40, ln=True)
        pdf.output("Revision_Workbook.pdf")
        with open("Revision_Workbook.pdf", "rb") as f:
            st.download_button("Download PDF", f, "Revision_Workbook.pdf", "application/pdf")

import streamlit as st
import pandas as pd
from PIL import Image
import os
import uuid
from datetime import datetime, timedelta
from fpdf import FPDF

# --- Database & Folder Setup ---
DATA_FILE = "mock_data_images.csv"
IMAGE_DIR = "saved_images"

if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

def init_db():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=[
            "Date", "Mock_Name", "Subject", "Chapter", "Micro_Topic", 
            "Mistake_Reason", "Time_Taken_Sec", "Image_Path", "Next_Revision_Date"
        ])
        df.to_csv(DATA_FILE, index=False)

def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame()

def save_data(data_dict):
    df = pd.DataFrame([data_dict])
    df.to_csv(DATA_FILE, mode='a', header=not os.path.exists(DATA_FILE), index=False)

def delete_record(index_to_drop):
    df = load_data()
    if index_to_drop in df.index:
        img_path = df.loc[index_to_drop, "Image_Path"]
        if pd.notna(img_path) and os.path.exists(img_path):
            os.remove(img_path) # Delete actual image file to save space
        df = df.drop(index_to_drop)
        df.to_csv(DATA_FILE, index=False)
        st.rerun()

init_db()

# --- Page Config & Navigation ---
st.set_page_config(page_title="Mock Pro Tracker", layout="wide", initial_sidebar_state="expanded")

st.sidebar.title("🎯 Mock Tracker Pro")
main_menu = st.sidebar.radio("Navigation:", ["📤 Upload Questions", "📂 Manage & Delete", "📊 Analysis Dashboard", "📥 Export PDF Workbook"])

df_global = load_data()
existing_mocks = df_global['Mock_Name'].unique().tolist() if not df_global.empty else []
reasons_list = ["Silly Mistake", "Conceptual Gap", "Memory/Fact Based", "Time Pressure", "Skipped", "Overtime", "Clueless"]

# --- Smart Revision Calculator ---
def calculate_revision_date(reason):
    today = datetime.now()
    if reason in ["Conceptual Gap", "Clueless"]:
        return (today + timedelta(days=2)).strftime("%Y-%m-%d") # Needs quick revision
    elif reason == "Memory/Fact Based":
        return (today + timedelta(days=1)).strftime("%Y-%m-%d") # Needs immediate memorization
    elif reason in ["Time Pressure", "Overtime"]:
        return (today + timedelta(days=5)).strftime("%Y-%m-%d") 
    else:
        return (today + timedelta(days=7)).strftime("%Y-%m-%d") # Silly mistakes/Skipped

# --- 1. Upload Question Images ---
if main_menu == "📤 Upload Questions":
    st.title("Upload Mistake Screenshots")
    
    col1, col2 = st.columns(2)
    with col1:
        mock_choice = st.selectbox("Select Existing Mock Test:", ["-- Create New Mock --"] + existing_mocks)
    with col2:
        if mock_choice == "-- Create New Mock --":
            mock_name = st.text_input("Enter New Mock Name:")
        else:
            mock_name = mock_choice

    uploaded_files = st.file_uploader("Upload Screenshots (Select multiple)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    
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
                    subj = st.text_input("Subject", "General Studies", key=f"sub_{i}")
                    chap = st.text_input("Chapter", "Polity", key=f"chap_{i}")
                    micro = st.text_input("Micro Topic (e.g. Fundamental Rights)", "General", key=f"mic_{i}")
                
                with c3:
                    reason = st.selectbox("Reason", reasons_list, key=f"res_{i}")
                    time_sec = st.number_input("Time Taken (sec)", min_value=0, value=60, key=f"time_{i}")
                
                metadata.append({"img": img, "subj": subj, "chap": chap, "micro": micro, "reason": reason, "time": time_sec})
                st.divider()
                
            if st.form_submit_button("💾 Save All Questions"):
                if not mock_name:
                    st.error("Mock Test Name is required!")
                else:
                    for idx, data in enumerate(metadata):
                        filename = f"{uuid.uuid4().hex}.jpg"
                        img_path = os.path.join(IMAGE_DIR, filename)
                        # Compress and save
                        data["img"].thumbnail((1200, 1200))
                        data["img"].save(img_path, "JPEG", quality=85)
                        
                        save_data({
                            "Date": datetime.now().strftime("%Y-%m-%d"),
                            "Mock_Name": mock_name,
                            "Subject": data["subj"],
                            "Chapter": data["chap"],
                            "Micro_Topic": data["micro"],
                            "Mistake_Reason": data["reason"],
                            "Time_Taken_Sec": data["time"],
                            "Image_Path": img_path,
                            "Next_Revision_Date": calculate_revision_date(data["reason"])
                        })
                    st.success("✅ Logged successfully! See 'Manage & Delete' tab.")

# --- 2. Manage & Delete Sections ---
elif main_menu == "📂 Manage & Delete":
    st.title("Review & Delete Logged Questions")
    df = load_data()
    
    if df.empty:
        st.info("No questions logged yet.")
    else:
        selected_mock = st.selectbox("Filter by Mock Test:", ["All Mocks"] + existing_mocks)
        
        display_df = df if selected_mock == "All Mocks" else df[df['Mock_Name'] == selected_mock]
        st.write(f"Showing **{len(display_df)}** questions.")
        
        for idx, row in display_df.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([1, 3, 1])
                with c1:
                    if pd.notna(row['Image_Path']) and os.path.exists(row['Image_Path']):
                        st.image(row['Image_Path'], use_container_width=True)
                    else:
                        st.warning("Image missing")
                with c2:
                    st.markdown(f"**Mock:** {row['Mock_Name']} | **Subject:** {row['Subject']}")
                    st.markdown(f"**Chapter:** {row['Chapter']} ➡️ *{row['Micro_Topic']}*")
                    st.markdown(f"**Reason:** `{row['Mistake_Reason']}` | **Time:** {row['Time_Taken_Sec']}s")
                    st.markdown(f"📅 **Revise On:** {row['Next_Revision_Date']}")
                with c3:
                    if st.button("🗑️ Delete", key=f"del_{idx}"):
                        delete_record(idx)
                st.divider()

# --- 3. Dashboard Analysis ---
elif main_menu == "📊 Analysis Dashboard":
    st.title("Performance Analytics")
    df = load_data()
    
    if df.empty:
        st.info("Log some questions to see analytics.")
    else:
        # Crash-Proof Chart Formatting
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("Mistakes by Reason")
            reason_counts = df['Mistake_Reason'].value_counts().reset_index()
            reason_counts.columns = ['Reason', 'Count']
            st.bar_chart(data=reason_counts, x='Reason', y='Count')
            
        with c2:
            st.subheader("Time Wastage Analytics")
            time_df = df.groupby('Chapter')['Time_Taken_Sec'].sum().reset_index().sort_values(by='Time_Taken_Sec', ascending=False).head(5)
            st.bar_chart(data=time_df, x='Chapter', y='Time_Taken_Sec')
            
        st.divider()
        st.subheader("🚨 Priority Red Zone (By Micro-Topic)")
        micro_counts = df['Micro_Topic'].value_counts()
        for micro, count in micro_counts.items():
            if count >= 2:
                st.error(f"⚠️ **{micro}** — Failed {count} times. Revise concepts immediately!")
            elif count == 1:
                st.warning(f"🟡 **{micro}** — Failed {count} time.")

# --- 4. Export PDF ---
elif main_menu == "📥 Export PDF Workbook":
    st.title("Export PDF with Safe Formatting")
    df = load_data()
    
    if df.empty:
        st.info("No data available to export.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            sel_mock = st.selectbox("Mock Filter:", ["All Mocks"] + existing_mocks)
        with col2:
            sel_reason = st.selectbox("Reason Filter:", ["All Reasons"] + reasons_list)
            
        if st.button("📄 Generate PDF Workbook"):
            export_df = df
            if sel_mock != "All Mocks":
                export_df = export_df[export_df['Mock_Name'] == sel_mock]
            if sel_reason != "All Reasons":
                export_df = export_df[export_df['Mistake_Reason'] == sel_reason]
                
            if export_df.empty:
                st.warning("No data matches this filter.")
            else:
                progress = st.progress(0)
                
                pdf = FPDF()
                pdf.set_auto_page_break(auto=True, margin=15)
                
                for index, row in export_df.iterrows():
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 14)
                    pdf.cell(0, 8, f"Mock: {row['Mock_Name']} | {row['Subject']}", ln=True)
                    
                    pdf.set_font("Arial", 'B', 12)
                    pdf.cell(0, 8, f"Chapter: {row['Chapter']} -> {row['Micro_Topic']}", ln=True)
                    
                    pdf.set_font("Arial", 'I', 11)
                    pdf.cell(0, 8, f"Reason: {row['Mistake_Reason']} | Time: {row['Time_Taken_Sec']}s", ln=True)
                    pdf.ln(5)
                    
                    # Safe Image Insertion logic (avoids blank pages)
                    img_path = row['Image_Path']
                    if pd.notna(img_path) and os.path.exists(img_path):
                        try:
                            # Width 170 ensures it fits on A4 without pushing to a blank page
                            pdf.image(img_path, w=170) 
                        except Exception as e:
                            pdf.cell(0, 10, f"[Image Render Error: {str(e)}]", ln=True)
                    else:
                        pdf.cell(0, 10, "[Image Missing from Storage]", ln=True)
                        
                    # Calculate progress safely using iloc mapping logic
                    current_idx = export_df.index.get_loc(index)
                    progress.progress((current_idx + 1) / len(export_df))
                    
                pdf_file = "Revision_Workbook.pdf"
                pdf.output(pdf_file)
                st.success("✅ PDF is ready!")
                
                with open(pdf_file, "rb") as f:
                    st.download_button("📥 Click Here to Download PDF", f, file_name="Revision_Workbook.pdf", mime="application/pdf")

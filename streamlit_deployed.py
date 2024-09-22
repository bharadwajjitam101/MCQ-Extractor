# What the code does?
# 0. Uses Streamlit to deploy the real use of the code
# 1. Extracts text from images or PDFs.
# 2. Uses the Groq API to parse and format MCQs from the extracted text.
# 3. Allows users to edit the extracted MCQs interactively.
# 4. Provides options to save the MCQs in various formats (CSV, JSON, PDF, DOCX).

import streamlit as st
import pytesseract
from PIL import Image
import pandas as pd
from groq import Groq
import os
import tempfile
from llama_index.core import SimpleDirectoryReader
import re
import json
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape, portrait
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.units import inch
from docx import Document
from docx.shared import Inches
import io

# Set your Groq API key
headers={
    "authorization": st.sectrets["groq_api_key"]

}

def add_styles():
    st.markdown(
        """
        <style>
        /* Import Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');

        /* Global Styles */
        body {
            font-family: 'Poppins', sans-serif;
            color: #1a202c;
        }

        .stApp {
            background-image: url("https://images.unsplash.com/photo-1727025668964-65232c96e6e3?q=80&w=3132&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D");
            background-attachment: fixed;
            background-size: cover;
        }

        /* Main content area */
        .main .block-container {
            background-color: rgba(0, 0, 0, 0.95);
            border-radius: 15px;
            padding: 2rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
        }

        /* Header Styles */
        h1 {
            color: #4a5568;
            font-weight: 700;
            margin-bottom: 1.5rem;
            text-align: center;
            font-size: 2.5rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }

        /* Streamlit elements styling */
        .stButton > button {
            background-color: #4299e1;
            color: white;
            border: none;
            border-radius: 30px;
            padding: 0.6rem 1.5rem;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 4px 6px rgba(50, 50, 93, 0.11), 0 1px 3px rgba(0, 0, 0, 0.08);
        }

        .stButton > button:hover {
            background-color: #3182ce;
            transform: translateY(-2px);
            box-shadow: 0 7px 14px rgba(50, 50, 93, 0.1), 0 3px 6px rgba(0, 0, 0, 0.08);
        }

        .stTextInput > div > div > input,
        .stSelectbox > div > div > select {
            border-radius: 10px;
            border: 2px solid #e2e8f0;
            padding: 0.5rem 1rem;
            transition: all 0.3s ease;
        }

        .stTextInput > div > div > input:focus,
        .stSelectbox > div > div > select:focus {
            border-color: #4299e1;
            box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.5);
        }

        /* File uploader styling */
        .stFileUploader > div {
            border: 2px dashed #4299e1;
            border-radius: 15px;
            padding: 2rem;
            text-align: center;
            background-color: rgba(237, 242, 247, 0.8);
            transition: all 0.3s ease;
        }

        .stFileUploader > div:hover {
            background-color: rgba(237, 242, 247, 1);
            border-color: #3182ce;
        }

        /* Data editor styling */
        .stDataFrame {
            border: none;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .stDataFrame thead tr th {
            background-color: #4a5568;
            color: white;
            font-weight: 600;
            padding: 1rem;
        }

        .stDataFrame tbody tr:nth-child(even) {
            background-color: #f7fafc;
        }

        .stDataFrame tbody tr:hover {
            background-color: #edf2f7;
        }

        /* Download buttons styling */
        .stDownloadButton > button {
            background-color: #48bb78;
            color: white;
            border: none;
            border-radius: 30px;
            padding: 0.6rem 1.5rem;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 4px 6px rgba(50, 50, 93, 0.11), 0 1px 3px rgba(0, 0, 0, 0.08);
        }

        .stDownloadButton > button:hover {
            background-color: #38a169;
            transform: translateY(-2px);
            box-shadow: 0 7px 14px rgba(50, 50, 93, 0.1), 0 3px 6px rgba(0, 0, 0, 0.08);
        }

        /* Customize PDF settings section */
        .stSubheader {
            color: #4a5568;
            font-weight: 600;
            margin-top: 2rem;
            margin-bottom: 1rem;
            font-size: 1.5rem;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 0.5rem;
        }

        /* Color picker styling */
        .stColorPicker > div > div > div {
            border-radius: 10px;
            border: 2px solid #e2e8f0;
            overflow: hidden;
        }

        /* Slider styling */
        .stSlider > div > div > div > div {
            background-color: #4299e1;
        }

        /* Success message styling */
        .stSuccess {
            background-color: #48bb78;
            color: white;
            border-radius: 10px;
            padding: 0.75rem 1rem;
            font-weight: 600;
            box-shadow: 0 4px 6px rgba(50, 50, 93, 0.11), 0 1px 3px rgba(0, 0, 0, 0.08);
        }

        /* Warning message styling */
        .stWarning {
            background-color: #ecc94b;
            color: #744210;
            border-radius: 10px;
            padding: 0.75rem 1rem;
            font-weight: 600;
            box-shadow: 0 4px 6px rgba(50, 50, 93, 0.11), 0 1px 3px rgba(0, 0, 0, 0.08);
        }

        /* Error message styling */
        .stError {
            background-color: #f56565;
            color: white;
            border-radius: 10px;
            padding: 0.75rem 1rem;
            font-weight: 600;
            box-shadow: 0 4px 6px rgba(50, 50, 93, 0.11), 0 1px 3px rgba(0, 0, 0, 0.08);
        }

        /* Improve readability of text on the background image */
        .stApp > .main {
            background-color: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            margin: 1rem;
            padding: 1rem;
        }

        /* Style the sidebar */
        .sidebar .sidebar-content {
            background-color: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

@st.cache_data
def extract_text_from_image(file):
    image = Image.open(file)
    text = pytesseract.image_to_string(image)
    return text

@st.cache_data
def extract_text_from_pdf(file):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file_path = os.path.join(temp_dir, file.name)
        with open(temp_file_path, "wb") as f:
            f.write(file.getvalue())
        
        reader = SimpleDirectoryReader(input_files=[temp_file_path])
        documents = reader.load_data()
        
        if documents:
            return " ".join([doc.text for doc in documents])
        else:
            return ""

def parse_and_format_mcqs_with_groq(text):
    client = Groq(api_key=groq_api_key)
    response = client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that extracts and formats multiple-choice questions (MCQs) from text."
            },
            {
                "role": "user",
                "content": f"""Extract the questions and options from the following text, and format them as a numbered list of questions with their options. Each question should be on a new line, preceded by its number, followed by its options (A, B, C, D) on separate lines. Here's the text:

{text}

Format the output as follows:
1. [Question text]
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]

2. [Question text]
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]

... and so on.

Respond only with the formatted questions and options, no additional text."""
            }
        ],
        temperature=0.25,
        max_tokens=1024,
        top_p=1,
        stream=False,
        stop=None
    )
    
    return response.choices[0].message.content

def process_raw_mcq_text(raw_text):
    pattern = r'(\d+)\.\s+(.*?)\nA\)\s+(.*?)\nB\)\s+(.*?)\nC\)\s+(.*?)\nD\)\s+(.*?)(?:\n|$)'
    matches = re.findall(pattern, raw_text, re.DOTALL)
    
    mcq_data = []
    for match in matches:
        question_number = int(match[0])
        question = match[1].strip()
        options = [opt.strip() for opt in match[2:]]
        mcq_data.append({"question_number": question_number, "question": question, "options": options})
    
    return mcq_data

def extract_mcqs(file):
    file_extension = os.path.splitext(file.name)[1].lower()
    if file_extension in ['.png', '.jpg', '.jpeg']:
        text = extract_text_from_image(file)
    elif file_extension == '.pdf':
        text = extract_text_from_pdf(file)
    else:
        st.error("Unsupported file type")
        return None

    if text:
        st.write(f"Extracted text length: {len(text)} characters")
        
        max_chunk_length = 4000
        chunks = [text[i:i+max_chunk_length] for i in range(0, len(text), max_chunk_length)]
        
        st.write(f"Number of chunks to process: {len(chunks)}")
        
        all_mcq_data = []
        question_number = 1  # Initialize question number
        for i, chunk in enumerate(chunks):
            st.write(f"Processing chunk {i+1}/{len(chunks)}")
            raw_mcq_text = parse_and_format_mcqs_with_groq(chunk)
            st.text("Extracting your MCQ Questions:")
            st.code(raw_mcq_text)
            mcq_data = process_raw_mcq_text(raw_mcq_text)
            
            # Update question numbers to ensure continuity
            for mcq in mcq_data:
                mcq['question_number'] = question_number
                question_number += 1
            
            all_mcq_data.extend(mcq_data)
        
        if all_mcq_data:
            df = pd.DataFrame([
                [q['question_number'], q['question']] + q['options']
                for q in all_mcq_data
            ], columns=["Number", "Question", "Option A", "Option B", "Option C", "Option D"])
            
            return df
        else:
            st.warning("No MCQs found in the document.")
            return None
    else:
        st.warning("No text found in the document.")
        return None

def save_as_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def save_as_json(df):
    return df.to_json(orient='records')

def customize_pdf_settings():
    st.subheader("Customize PDF Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        page_orientation = st.selectbox("Page Orientation", ["Landscape", "Portrait"])
        title_text = st.text_input("PDF Title", "Multiple Choice Questions")
        title_font_size = st.slider("Title Font Size", 12, 24, 16)
        title_alignment = st.selectbox("Title Alignment", ["Left", "Center", "Right"])
    
    with col2:
        header_bg_color = st.color_picker("Header Background Color", "#808080")
        header_text_color = st.color_picker("Header Text Color", "#FFFFFF")
        alt_row_color = st.color_picker("Alternating Row Color", "#F0F0F0")
    
    return {
        "page_orientation": page_orientation,
        "title_text": title_text,
        "title_font_size": title_font_size,
        "title_alignment": title_alignment,
        "header_bg_color": header_bg_color,
        "header_text_color": header_text_color,
        "alt_row_color": alt_row_color
    }

def save_as_pdf(df, settings):
    buffer = io.BytesIO()
    page_size = landscape(letter) if settings["page_orientation"] == "Landscape" else portrait(letter)
    doc = SimpleDocTemplate(buffer, pagesize=page_size, rightMargin=0.5*inch, leftMargin=0.5*inch, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    elements = []
    
    # Add title
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=settings["title_font_size"],
        alignment={"Left": TA_LEFT, "Center": TA_CENTER, "Right": TA_RIGHT}[settings["title_alignment"]],
        spaceAfter=12
    )
    elements.append(Paragraph(settings["title_text"], title_style))
    elements.append(Spacer(1, 12))
    
    # Prepare data for table
    data = [[Paragraph(col, styles['Heading2']) for col in df.columns]]
    for _, row in df.iterrows():
        data.append([Paragraph(str(cell), styles['Normal']) for cell in row])
    
    # Create table
    col_widths = [0.5*inch, 2*inch] + [1.75*inch] * 4 if settings["page_orientation"] == "Landscape" else [0.5*inch, 1.5*inch] + [1.5*inch] * 4
    table = Table(data, colWidths=col_widths)
    
    # Style the table
    style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor(settings["header_bg_color"])),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor(settings["header_text_color"])),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 12),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.beige),
        ('TEXTCOLOR', (0,1), (-1,-1), colors.black),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 10),
        ('TOPPADDING', (0,1), (-1,-1), 6),
        ('BOTTOMPADDING', (0,1), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('WORDWRAP', (0,0), (-1,-1), True),
    ])
    table.setStyle(style)
    
    # Add alternating row colors
    for i in range(1, len(data)):
        if i % 2 == 0:
            bc = colors.white
        else:
            bc = colors.HexColor(settings["alt_row_color"])
        ts = TableStyle([('BACKGROUND', (0,i), (-1,i), bc)])
        table.setStyle(ts)
    
    elements.append(table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

def save_as_docx(df):
    doc = Document()
    doc.add_heading('MCQ Questions', 0)

    table = doc.add_table(rows=1, cols=6)
    table.style = 'Table Grid'
    hdr_cells = table.rows[0].cells
    for i, column_name in enumerate(df.columns):
        hdr_cells[i].text = column_name

    for _, row in df.iterrows():
        row_cells = table.add_row().cells
        for i, value in enumerate(row):
            row_cells[i].text = str(value)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def main():
    add_styles()
    st.title("MCQ Extractor")
    st.write("Upload an image or PDF file to extract multiple-choice questions.")

    uploaded_file = st.file_uploader("Choose a file", type=["png", "jpg", "jpeg", "pdf"])

    if 'mcq_df' not in st.session_state:
        st.session_state.mcq_df = None

    if uploaded_file is not None:
        if st.button("Extract MCQs"):
            with st.spinner("Extracting MCQs..."):
                st.session_state.mcq_df = extract_mcqs(uploaded_file)
            
            if st.session_state.mcq_df is not None:
                st.success("MCQs extracted successfully!")

    if st.session_state.mcq_df is not None:
        st.write("Extracted MCQs:")
        edited_df = st.data_editor(
            st.session_state.mcq_df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "Number": st.column_config.NumberColumn(
                    "Number",
                    width="small",
                    required=True,
                ),
                "Question": st.column_config.TextColumn(
                    "Question",
                    width="large",
                    required=True,
                ),
                "Option A": st.column_config.TextColumn(
                    "Option A",
                    width="medium",
                    required=True,
                ),
                "Option B": st.column_config.TextColumn(
                    "Option B",
                    width="medium",
                    required=True,
                ),
                "Option C": st.column_config.TextColumn(
                    "Option C",
                    width="medium",
                    required=True,
                ),
                "Option D": st.column_config.TextColumn(
                    "Option D",
                    width="medium",
                    required=True,
                ),
            }
        )

        # Update the session state with edited dataframe
        st.session_state.mcq_df = edited_df

        # Customize PDF settings
        pdf_settings = customize_pdf_settings()

        # Download options
        st.subheader("Download Options")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            csv = save_as_csv(edited_df)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="mcqs.csv",
                mime="text/csv"
            )
        
        with col2:
            json_str = save_as_json(edited_df)
            st.download_button(
                label="Download JSON",
                data=json_str,
                file_name="mcqs.json",
                mime="application/json"
            )
        
        with col3:
            pdf_buffer = save_as_pdf(edited_df, pdf_settings)
            st.download_button(
                label="Download PDF",
                data=pdf_buffer,
                file_name="mcqs.pdf",
                mime="application/pdf"
            )
        
        with col4:
            docx_buffer = save_as_docx(edited_df)
            st.download_button(
                label="Download DOCX",
                data=docx_buffer,
                file_name="mcqs.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

if __name__ == "__main__":
    main()

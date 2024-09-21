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
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from docx import Document
from docx.shared import Inches
import io

# Set your Groq API key
groq_api_key = 'Add your generated groq API'

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
                "content": f"""Extract the questions and options from the following text, and format them as a list of questions with their options. Each question should be on a new line, followed by its options (A, B, C, D) on separate lines. Here's the text:

{text}

Format the output as follows:
Question: [Question text]
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]

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
    pattern = r'Question: (.*?)\nA\) (.*?)\nB\) (.*?)\nC\) (.*?)\nD\) (.*?)(?:\n|$)'
    matches = re.findall(pattern, raw_text, re.DOTALL)
    
    mcq_data = []
    for match in matches:
        question = match[0].strip()
        options = [opt.strip() for opt in match[1:]]
        mcq_data.append({"question": question, "options": options})
    
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
        for i, chunk in enumerate(chunks):
            st.write(f"Processing chunk {i+1}/{len(chunks)}")
            raw_mcq_text = parse_and_format_mcqs_with_groq(chunk)
            st.text("Raw MCQ text from Groq:")
            st.code(raw_mcq_text)
            mcq_data = process_raw_mcq_text(raw_mcq_text)
            all_mcq_data.extend(mcq_data)
        
        if all_mcq_data:
            df = pd.DataFrame([
                [q['question']] + q['options']
                for q in all_mcq_data
            ], columns=["Question", "Option A", "Option B", "Option C", "Option D"])
            
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

def save_as_pdf(df):
    buffer = io.BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=letter)
    data = [df.columns.tolist()] + df.values.tolist()
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), '#CCCCCC'),
        ('TEXTCOLOR', (0, 0), (-1, 0), '#000000'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), '#EEEEEE'),
        ('TEXTCOLOR', (0, 1), (-1, -1), '#000000'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, '#000000'),
    ]))
    pdf.build([table])
    buffer.seek(0)
    return buffer

def save_as_docx(df):
    doc = Document()
    doc.add_heading('MCQ Questions', 0)

    table = doc.add_table(rows=1, cols=5)
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
            pdf_buffer = save_as_pdf(edited_df)
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

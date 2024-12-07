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
import requests
from streamlit.components.v1 import html

# API Key (Consider using environment variables in production)
groq_api_key = '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'

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

        /* Improve data editor text areas */
        .stDataEditor textarea {
            min-height: 100px;  /* Increase height of text areas */
            resize: vertical;   /* Allow vertical resizing */
            font-size: 14px;    /* Adjust font size */
            line-height: 1.5;   /* Add more line spacing */
            padding: 10px;      /* Add some padding */
        }

        .stDataEditor .stColumn {
            margin-bottom: 10px; /* Add space between columns */
        }

        /* Main content area */
        .main .block-container {
            background-color: rgba(0, 0, 0, 0.95);
            border-radius: 15px;
            padding: 2rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
        }

        /* Buttons and other styling remains the same as in the previous implementation */
        .stButton > button {
            background-color: #4299e1;
            color: white;
            border: none;
            border-radius: 30px;
            padding: 0.6rem 1.5rem;
            font-weight: 600;
            transition: all 0.3s ease;
        }

        .stButton > button:hover {
            background-color: #3182ce;
            transform: translateY(-2px);
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

def send_to_backend_api(json_data):
    # Replace with your actual backend API endpoint
    api_url = "https://your-backend-api-endpoint.com/mcq"
    
    headers = {
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.post(api_url, json=json_data, headers=headers)
        response.raise_for_status()
        return True, "Data successfully sent to the backend API"
    except requests.RequestException as e:
        return False, f"Error sending data to the backend API: {str(e)}"

def copy_to_clipboard(json_str):
    copy_button_html = f"""
        <textarea id="json-data" style="position: absolute; left: -9999px;">{json_str}</textarea>
        <button onclick="copyToClipboard()">Copy JSON to Clipboard</button>
        <script>
            function copyToClipboard() {{
                var copyText = document.getElementById("json-data");
                copyText.select();
                document.execCommand("copy");
                alert("JSON copied to clipboard!");
            }}
        </script>
    """
    return copy_button_html

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
                    help="Edit the question text. Press Shift+Enter for line breaks.",
                ),
                "Option A": st.column_config.TextColumn(
                    "Option A",
                    width="medium",
                    required=True,
                    help="Edit option A. Press Shift+Enter for line breaks.",
                ),
                "Option B": st.column_config.TextColumn(
                    "Option B",
                    width="medium",
                    required=True,
                    help="Edit option B. Press Shift+Enter for line breaks.",
                ),
                "Option C": st.column_config.TextColumn(
                    "Option C",
                    width="medium",
                    required=True,
                    help="Edit option C. Press Shift+Enter for line breaks.",
                ),
                "Option D": st.column_config.TextColumn(
                    "Option D",
                    width="medium",
                    required=True,
                    help="Edit option D. Press Shift+Enter for line breaks.",
                ),
            }
        )

        # Update the session state with edited dataframe
        st.session_state.mcq_df = edited_df

        # Button to extract JSON and send to backend API
        if st.button("Extract JSON and Send to API"):
            # Convert DataFrame to the desired JSON format
            json_data = []
            for _, row in edited_df.iterrows():
                question_data = {
                    "question": row["Question"].replace('\n', ' '),
                    "options": [
                        row["Option A"].replace('\n', ' '),
                        row["Option B"].replace('\n', ' '),
                        row["Option C"].replace('\n', ' '),
                        row["Option D"].replace('\n', ' ')
                    ]
                }
                json_data.append(question_data)
            
            formatted_json = json.dumps(json_data, indent=2)
            
            # Display formatted JSON
            st.subheader("Extracted JSON")
            st.json(json.loads(formatted_json))
            
            # Add copy to clipboard button
            st.write("Copy JSON to Clipboard:")
            html(copy_to_clipboard(formatted_json), height=50)

if __name__ == "__main__":
    main()

from flask import Flask, request, render_template
import os
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import PyPDF2

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Load job descriptions from CSV
job_descriptions_df = pd.read_csv(r'F:\JOB SCREENING\job_description.csv', encoding='ISO-8859-1')

@app.route('/')
def index():
    job_titles = job_descriptions_df['Job Title'].tolist()
    return render_template('index.html', job_titles=job_titles)

@app.route('/upload', methods=['POST'])
def upload():
    selected_job_title = request.form['job_title']
    job_description = job_descriptions_df.loc[job_descriptions_df['Job Title'] == selected_job_title, 'Job Description'].values[0]
    files = request.files.getlist('resumes')

    resumes = []
    for file in files:
        if file and file.filename.endswith('.pdf'):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            resumes.append(file_path)

    shortlisted_candidates = process_resumes(job_description, resumes)
    print("Shortlisted Candidates:", shortlisted_candidates)  # Debugging output
    return render_template('results.html', shortlisted=shortlisted_candidates)

def extract_text_from_pdf(pdf_path):
    text = ""
    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    print(f"Extracted Text from {pdf_path}: {text}")  # Debugging output
    return text.strip()  # Return the extracted text
import re

def extract_name_and_email(resume_text):
    # Example regex patterns for name and email extraction
    name_pattern = r'(?<=Name: )(.+?)(?=\n)'  # Assuming the name is prefixed with "Name: "
    email_pattern = r'[\w\.-]+@[\w\.-]+'  # Basic email pattern

    name_match = re.search(name_pattern, resume_text)
    email_match = re.search(email_pattern, resume_text)

    name = name_match.group(0) if name_match else "Unknown Name"
    email = email_match.group(0) if email_match else "Unknown Email"

    return name, email

def process_resumes(job_description, resumes):
    # Extract text from resumes
    resume_texts = [extract_text_from_pdf(resume) for resume in resumes]

    # Combine job description and resumes for similarity calculation
    documents = [job_description] + resume_texts
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(documents)

    # Calculate cosine similarity
    cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()

    # Shortlist candidates based on a threshold
    threshold = 0.1  # Start with a low threshold
    shortlisted = []
    for i, score in enumerate(cosine_sim):
        if score >= threshold:
            # Extract name and email from the resume text
            name, email = extract_name_and_email(resume_texts[i])
            shortlisted.append({'name': name, 'email': email})

    return shortlisted

if __name__ == '__main__':
    app.run(debug=True)
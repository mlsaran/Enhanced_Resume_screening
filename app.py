from flask import Flask, request, render_template, session
import os
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import PyPDF2
import re

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'your_secret_key'  
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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

    shortlisted_candidates, total_skills = process_resumes(job_description, resumes)
    print("Shortlisted Candidates:", shortlisted_candidates)

    session['shortlisted_candidates'] = shortlisted_candidates

    return render_template('results.html', shortlisted=shortlisted_candidates, total_skills=total_skills)

@app.route('/candidates')
def candidates():
    skill = request.args.get('skill')
    filtered_candidates = []
    shortlisted_candidates = session.get('shortlisted_candidates', [])

    for candidate in shortlisted_candidates:
        if candidate['skills'].get(skill, 0) > 0:
            filtered_candidates.append(candidate)

    # Build total_skills for filtered candidates
    predefined_skills = ['Python', 'Java', 'SQL', 'Machine Learning', 'Data Analysis', 'Project Management']
    total_skills = {s: 0 for s in predefined_skills}
    for candidate in filtered_candidates:
        for s, v in candidate['skills'].items():
            total_skills[s] += v

    # Always pass total_skills
    return render_template(
        'filtered_candidates.html',
        skill=skill,
        candidates=filtered_candidates,
        total_skills=total_skills
    )


def extract_text_from_pdf(pdf_path):
    text = ""
    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    print(f"Extracted Text from {pdf_path}: {text}")  
    return text.strip()  

def extract_name_and_email(resume_text):
    name_pattern = r'(?<=Name: )(.+?)(?=\n)'  
    email_pattern = r'[\w\.-]+@[\w\.-]+' 

    name_match = re.search(name_pattern, resume_text)
    email_match = re.search(email_pattern, resume_text)

    name = name_match.group(0) if name_match else "Unknown Name"
    email = email_match.group(0) if email_match else "Unknown Email"

    return name, email

def extract_skills(resume_text):
    predefined_skills = ['Python', 'Java', 'SQL', 'Machine Learning', 'Data Analysis', 'Project Management']
    skills_found = {skill: 0 for skill in predefined_skills}

    for skill in predefined_skills:
        if skill.lower() in resume_text.lower():
            skills_found[skill] += 1

    return skills_found

def process_resumes(job_description, resumes):
    resume_texts = [extract_text_from_pdf(resume) for resume in resumes]
    documents = [job_description] + resume_texts
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(documents)
    cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()

    threshold = 0.1  
    shortlisted = []
    total_skills = {skill: 0 for skill in ['Python', 'Java', 'SQL', 'Machine Learning', 'Data Analysis', 'Project Management']}

    for i, score in enumerate(cosine_sim):
        if score >= threshold:
            name, email = extract_name_and_email(resume_texts[i])
            skills = extract_skills(resume_texts[i])
            shortlisted.append({'name': name, 'email': email, 'skills': skills})  
            for skill, count in skills.items():
                total_skills[skill] += count

    return shortlisted, total_skills

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

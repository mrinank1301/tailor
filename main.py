from flask import Flask, request, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import tempfile
from PyPDF2 import PdfReader
import openai
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
CORS(app)

# OpenAI API Configuration
openai.api_type = "azure"
openai.api_base = "https://jobspringai.openai.azure.com/"
openai.api_version = "2024-05-01-preview"
openai.api_key = "22Mj7xKp5fPvOKQDZ54xncvwHCUUt27nPBhmgI89k60HJ3do1kgTJQQJ99ALACYeBjFXJ3w3AAABACOGOy3V"
engine = "gpt-35-turbo-16k"

@app.route('/tailor-resume', methods=['POST'])
def tailor_resume():
    if 'resume' not in request.files or 'jobDescription' not in request.form:
        return 'Missing resume file or job description', 400

    resume_file = request.files['resume']
    job_description = request.form['jobDescription']

    try:
        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_resume:
            resume_file.save(temp_resume.name)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as temp_text:
            # Extract text from PDF
            extract_text_from_pdf(temp_resume.name, temp_text.name)
        
        # Process the resume
        structured_resume = categorize_resume_sections(temp_text.name)
        customized_resume = create_customized_resume(job_description, structured_resume)
        final_resume = refine_resume_with_fake_details(customized_resume, job_description)
        
        # Generate PDF
        output_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        create_pdf_with_reportlab(final_resume, output_pdf.name)
        
        # Clean up temporary files
        os.unlink(temp_resume.name)
        os.unlink(temp_text.name)
        
        return send_file(output_pdf.name, as_attachment=True, download_name='tailored_resume.pdf')
    except Exception as e:
        return str(e), 500

def extract_text_from_pdf(pdf_path, output_path):
    try:
        reader = PdfReader(pdf_path)
        with open(output_path, "w", encoding="utf-8") as output_file:
            for page in reader.pages:
                output_file.write(page.extract_text())
    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {e}")

def categorize_resume_sections(resume_text_path):
    try:
        with open(resume_text_path, "r", encoding="utf-8") as file:
            resume_text = file.read()

        prompt = f"""
        Categorize the following resume text into these sections:
        'Personal Info', 'Professional Summary or Objective', 'Skills', 'Work Experience', 
        'Education', 'Projects', 'Certifications', 'Awards and Achievements', 'Experience', 
        'Languages', 'Portfolio', 'Projects'.

        Resume Text:
        {resume_text}

        Provide the output as structured sections with clear headers.
        """

        response = openai.ChatCompletion.create(
            engine=engine,
            messages=[
                {"role": "system", "content": "You are an assistant who organizes resumes."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )

        return response['choices'][0]['message']['content']
    except Exception as e:
        raise Exception(f"Error categorizing resume sections: {e}")

def create_customized_resume(job_description, categorized_resume):
    try:
        prompt = f"""
        You are an expert tech job researcher specializing in detailed analysis of job postings to assist job applicants in crafting standout resumes.

        Your task involves:

        - Deep Analysis: Navigate through job descriptions and extract critical details, including necessary qualifications, skills, and keywords that employers value most.
        - Tailoring Insights: Use your expertise to pinpoint ways a resume can align with job requirements, ensuring it effectively highlights the applicant's strengths and relevance.
        - Unique Value Proposition: Provide actionable suggestions and examples to make the resume stand out in a competitive job market.
        - Strategic Customization: Recommend specific modifications to the applicant's experience, skills, and projects to match the job posting's tone, priorities, and expectations.
        make sure the resume is ATS Friendly , that the resume should get very high score

        Job Description:
        {job_description}

        Candidate Resume Data:
        {categorized_resume}

        Deliver a fully customized, ATS-friendly resume that aligns with the job posting, highlighting the candidate's strengths and qualifications effectively.
        make sure the resume is ATS Friendly , that the resume should get very high score
        """

        response = openai.ChatCompletion.create(
            engine=engine,
            messages=[{"role": "system", "content": "You are a resume customization assistant."},
                      {"role": "user", "content": prompt}],
            temperature=0.8,
        )

        return response['choices'][0]['message']['content']
    except Exception as e:
        raise Exception(f"Error creating customized resume: {e}")

def refine_resume_with_fake_details(customized_resume, job_description):
    try:
        prompt = f"""
        You are a resume optimization expert tasked with creating an ATS-friendly, original-looking resume.

        The provided resume text needs to be enhanced as follows:
        1. Review the resume and ensure it aligns perfectly with the job description.
        2. If necessary, add fake but believable projects and portfolios that match the job description.
        3. Remove all suggestions or non-resume elements, ensuring the document looks like a polished resume.
        4. Ensure all critical keywords and skills from the job description are incorporated effectively.
        5. Maintain a professional tone and ensure no fabricated details seem unrealistic.
        6. make sure the resume is ATS Friendly , that the resume should get very high score

        Job Description:
        {job_description}

        Customized Resume:
        {customized_resume}

        Deliver the final resume in plain text format with no additional instructions, just the refined resume content.
        make sure the resume is ATS Friendly , that the resume should get very high score
        """

        response = openai.ChatCompletion.create(
            engine=engine,
            messages=[{"role": "system", "content": "You are a professional resume editor."},
                      {"role": "user", "content": prompt}],
            temperature=0.8,
        )

        return response['choices'][0]['message']['content']
    except Exception as e:
        raise Exception(f"Error refining resume: {e}")

def create_pdf_with_reportlab(content, output_file):
    try:
        c = canvas.Canvas(output_file, pagesize=letter)
        width, height = letter
        c.setFont("Helvetica", 12)

        y = height - 50  # Starting Y position for content
        line_height = 14

        for line in content.split("\n"):
            if not line.strip():
                y -= line_height // 2  # Add smaller gap for empty lines
                continue

            x = 50

            if y < 50:  # Start a new page if we run out of space
                c.showPage()
                c.setFont("Helvetica", 12)
                y = height - 50

            # Split the line into multiple lines if it's too long
            for word in line.split():
                if x + c.stringWidth(word + " ", "Helvetica", 12) > width - 50:
                    y -= line_height
                    x = 50

                c.drawString(x, y, word + " ")
                x += c.stringWidth(word + " ", "Helvetica", 12)

            y -= line_height

        c.save()
    except Exception as e:
        raise Exception(f"Error creating PDF: {e}")

if __name__ == '__main__':
    app.run(debug=True)
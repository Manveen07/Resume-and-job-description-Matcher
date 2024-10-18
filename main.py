from flask import Flask, render_template,request
import os
import docx2txt
import PyPDF2
import google.generativeai as genai



os.environ["Goofle_api_key"]="your api key"
genai.configure(api_key=os.environ["Goofle_api_key"])
"""models/gemini-1.0-pro-latest
models/gemini-1.0-pro
models/gemini-pro
models/gemini-1.0-pro-001
models/gemini-1.0-pro-vision-latest
models/gemini-pro-vision
models/gemini-1.5-pro-latest
models/gemini-1.5-pro-001
models/gemini-1.5-pro
models/gemini-1.5-flash-latest
models/gemini-1.5-flash-001
models/gemini-1.5-flash"""
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
def extract_text_from_pdf(file_path):
    text = ""
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    return text

def extract_text_from_docx(file_path):
    return docx2txt.process(file_path)

def extract_text_from_txt(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def extract_text(file_path):
    if file_path.endswith('.pdf'):
        return extract_text_from_pdf(file_path)
    elif file_path.endswith('.docx'):
        return extract_text_from_docx(file_path)
    elif file_path.endswith('.txt'):
        return extract_text_from_txt(file_path)
    else:
        return ""





def calculate_similarity(job_description, resumes):
    prompt = f"Job Description:\n{job_description}\n\nResumes:\n"
    for i, resume in enumerate(resumes):
        prompt += f"Resume {i + 1}:\n{resume}\n\n"
    
    prompt += (
        "Rate the relevance of each resume to the job description on a scale of 1 to 10, where 1 is the most relevant and 10 is the least relevant. "
        "Provide a brief explanation of why each resume received that score. Format your response as follows:\n"
        "1. Resume 1: SCORE (Explanation)\n"
        "2. Resume 2: SCORE (Explanation)\n"
        "...\n"
        "N. Resume N: SCORE (Explanation)"
    )

    # Initialize the AI model
    model = genai.GenerativeModel('gemini-1.0-pro-latest')

    # Generate response from the model
    response = model.generate_content(prompt)
    # print("resut")
    # print(response.text)
    # print("done")
    # print(response)
    
    # Extract similarity scores and explanations from the response
    try:
        response_text = response.text.strip()
        lines = response_text.split('\n')
        
        similarity_scores = []
        explanations = []
        
        for line in lines:
            
            parts = line.split(':', 1)
            if len(parts) == 2:
                resume_part = parts[0].strip()
                score_and_explanation = parts[1].strip()
                
                # Extract score and explanation
                score_parts = score_and_explanation.split('(', 1)
                if len(score_parts) == 2:
                    score = float(score_parts[0].strip())
                    explanation = score_parts[1].strip(')')
                    
                    similarity_scores.append(score)
                    explanations.append(explanation)
        
        
        if len(similarity_scores) != len(resumes) or len(explanations) != len(resumes):
            raise ValueError("Mismatch in number of scores or explanations and resumes.")
    
    except (AttributeError, ValueError) as e:
        print(f"Error processing response: {e}")
        similarity_scores = [10] * len(resumes)  # Default to worst score if error occurs
        explanations = ["No explanation available."] * len(resumes)
    
    return similarity_scores, explanations


@app.route("/")
def home():
    return render_template("index.html")

@app.route('/matcher', methods=['POST'])
def matcher():
    if request.method == 'POST':
        job_description = request.form['job_description']
        resume_files = request.files.getlist('resumes')

        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])

        resumes = []
        filenames = []
        for resume_file in resume_files:
            filename = os.path.join(app.config['UPLOAD_FOLDER'], resume_file.filename)
            resume_file.save(filename)
            filenames.append(resume_file.filename)
            resumes.append(extract_text(filename))

        if not resumes or not job_description:
            return render_template('index.html', message="Please upload resumes and enter a job description.")
        
        # Calculate similarity scores
        similarity_scores, explanations  = calculate_similarity(job_description, resumes)
        

        
        results = list(zip(filenames, similarity_scores, explanations))
        
        # Sort results by similarity score (lower score means more relevant)
        sorted_results = sorted(results, key=lambda x: x[1])

        top_resumes = [res[0] for res in sorted_results]  
        top_scores = [res[1] for res in sorted_results]
        explanation=[res[2] for res in sorted_results]
        

        return render_template('index.html', message="Top matching resumes:", top_resumes=top_resumes,
                               similarity_scores=top_scores,explanations=explanation)

if __name__ == '__main__':
    app.run(debug=True)

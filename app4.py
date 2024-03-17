from flask import Flask, request, jsonify, render_template, redirect, url_for
import openai
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import datetime
import io
import os
import dropbox

app = Flask(__name__)

# Set your API keys
openai.api_key = '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'
dbx = dropbox.Dropbox('sl.BxmrfkfrbJH7Iu7Z-CiOL7Hs9_EVf4d0G4OGbSlVvatL85Gk8rDaIbeqBWxhvik8d5hwEKGLZZWfhG6qeyxkmgdun8TT5tKOkS4OMRqA0r4vAgVt0pLXxvXYVTMu78gsh3oBmxdQ3xPu2kJ2bxxyjuI')

@app.route("/")
def hello_world():
    return redirect("static/index.html")
    #return render_template("index.html")

def create_feedback_pdf(original_pdf_bytes, feedback_text):
    # Create a PDF buffer
    pdf_buffer = io.BytesIO()
    
    # Set up the PDF canvas
    can = canvas.Canvas(pdf_buffer, pagesize=letter)
    width, height = letter  # Get the dimensions of the page size
    
    # Define the margins
    left_margin = 72
    top_margin = 72
    right_margin = 72
    bottom_margin = 72
    
    # Calculate the text width available (page width - left_margin - right_margin)
    text_width = width - left_margin - right_margin

    # Set up the text object
    text_object = can.beginText(left_margin, height - top_margin)
    text_object.setFont("Helvetica", 12)
    
    # Add text line by line, wrapping as needed
    for paragraph in feedback_text.split('\n'):  # Split the feedback by newline character
        lines = paragraph.split(' ')
        line = ''
        for word in lines:
            if can.stringWidth(line + ' ' + word, "Helvetica", 12) <= text_width:
                line += ' ' + word
            else:
                text_object.textLine(line)
                line = word
        text_object.textLine(line)  # Make sure to add the last line after the loop
    
    # Draw the text object and save the canvas
    can.drawText(text_object)
    can.showPage()
    can.save()
    
    # Merge the feedback page with the original PDF
    pdf_buffer.seek(0)
    new_pdf = PdfReader(pdf_buffer)
    existing_pdf = PdfReader(io.BytesIO(original_pdf_bytes))
    writer = PdfWriter()
    
    # Add existing pages to the writer
    for page in existing_pdf.pages:
        writer.add_page(page)
    
    # Add the new feedback page to the writer
    writer.add_page(new_pdf.pages[0])
    
    # Save the modified PDF to a BytesIO object
    output_pdf_buffer = io.BytesIO()
    writer.write(output_pdf_buffer)
    output_pdf_buffer.seek(0)
    
    return output_pdf_buffer

@app.route('/grade', methods=['POST'])
def grade_paragraph():
    if 'pdf' not in request.files:
        return jsonify({'message': 'No PDF file provided'}), 400

    pdf_file = request.files['pdf']
    if pdf_file.filename == '':
        return jsonify({'message': 'No file selected'}), 400

    rubric = request.form.get('rubric')
    assignment_name = request.form.get('assignmentName', 'DefaultAssignment')
    student_name = request.form.get('studentName', 'DefaultStudent')

    # Debug: Print the values to check
    # print(f"Assignment Name: {assignment_name}, Student Name: {student_name}")

    # Ensure that the PDF content is non-empty
    pdf_bytes = io.BytesIO(pdf_file.read())
    if pdf_bytes.getbuffer().nbytes == 0:
        return jsonify({'message': 'Uploaded file is empty'}), 400

    # Extract text content from PDF
    pdf_reader = PdfReader(pdf_bytes)
    text_content = ""
    for page in pdf_reader.pages:
        text_content += page.extract_text() + "\n"

    # Generate the prompt for grading
    prompt = f"Grade this paragraph based on the following rubric:\n{text_content}\nRubric:\n{rubric}"

    # Call OpenAI's API to get the feedback
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )

    openai_response = response.choices[0].message['content']

    # Create the feedback PDF
    pdf_bytes.seek(0)  # Reset the BytesIO object to the beginning
    feedback_pdf_bytes_io = create_feedback_pdf(pdf_bytes.getvalue(), openai_response)

    # Check/Create Dropbox Folder
    dropbox_folder_path = f'/{assignment_name}'
    try:
        dbx.files_get_metadata(dropbox_folder_path)
    except dropbox.exceptions.ApiError:
        # Folder doesn't exist, create it
        dbx.files_create_folder(dropbox_folder_path)

    # Generate a filename and Dropbox file path
    formatted_filename = f'{student_name}_{assignment_name}_Submission.pdf'
    dropbox_pdf_path = os.path.join(f'/{assignment_name}', formatted_filename)

    # Upload the modified PDF to Dropbox
    try:
        dbx.files_upload(feedback_pdf_bytes_io.getvalue(), dropbox_pdf_path, mode=dropbox.files.WriteMode("overwrite"))
        return jsonify({'message': 'File and feedback saved to Dropbox successfully!', 'pdf_dropbox_path': dropbox_pdf_path}), 200
    except dropbox.exceptions.ApiError as e:
        return jsonify({'message': 'Failed to save file to Dropbox', 'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)
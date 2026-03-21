import PyPDF2

pdf_file = open('/Users/macbookpro16_stic_admin/Documents/face_attendance/FRAS_PRD_InsightFace_ArcFace.pdf', 'rb')
pdf_reader = PyPDF2.PdfReader(pdf_file)

text = ""
for page in pdf_reader.pages:
    text += page.extract_text()

print(text)
pdf_file.close()
from google.cloud import vision
import io

client = vision.ImageAnnotatorClient()

with io.open("test.jpeg", "rb") as image_file:
    content = image_file.read()

image = vision.Image(content=content)

response = client.document_text_detection(image=image)

print("\n===== DETECTED TEXT =====\n")
print(response.full_text_annotation.text)

if response.error.message:
    raise Exception(response.error.message)

#  aazhi-exam-ocr-2a5be7d07f9d.json  
#  set GOOGLE_APPLICATION_CREDENTIALS=aazhi-exam-ocr-2a5be7d07f9d.json  


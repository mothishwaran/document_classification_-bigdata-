import joblib
import pytesseract
from PIL import Image
import numpy as np

# POINT TO THE EXE FILE (Corrected line)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Load the brain once when the script starts
try:
    model = joblib.load('document_classifier.pkl')
    vectorizer = joblib.load('tfidf_vectorizer.pkl')
    print("✅ Model and Vectorizer loaded successfully.")
except Exception as e:
    print(f"❌ Error loading .pkl files: {e}")

categories = ["letter", "form", "email", "handwritten", "advertisement", 
              "scientific_report", "scientific_publication", "specification", 
              "file_folder", "news_article", "budget", "invoice", 
              "presentation", "questionnaire", "resume", "memo"]

def get_prediction(image):
    # 1. OCR - Extract text from the uploaded image
    text = pytesseract.image_to_string(image).strip().replace("\n", " ")
    if not text:
        return "Unreadable", 0.0

    # 2. Vectorize - Convert text to math the model understands
    vec = vectorizer.transform([text])

    # 3. Predict Probability - Get the category and the confidence score
    probs = model.predict_proba(vec)[0]
    idx = np.argmax(probs)
    
    return categories[idx], probs[idx] * 100
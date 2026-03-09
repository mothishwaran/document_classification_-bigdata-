import streamlit as st
import os
from kafka import KafkaProducer
import json
from predict import get_prediction  # Importing your existing logic
import pytesseract
from PIL import Image

# Ensure the temp directory exists
TEMP_DIR = "temp_uploads"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# Setup Kafka Producer
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

st.set_page_config(page_title="Judiciary Stream", page_icon="⚖️")
st.title("⚖️ Real-Time Judiciary Stream")

uploaded_file = st.file_uploader("Upload Document to Pipeline", type=["jpg", "png", "jpeg"])

if uploaded_file:
    # 1. Save and Display
    temp_path = os.path.join(TEMP_DIR, uploaded_file.name)
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # 2. Trigger Kafka Pipeline (Background Big Data Task)
    message = {"file_path": temp_path, "status": "INBOUND"}
    producer.send('judiciary-docs', message)
    st.success(f"🚀 Document '{uploaded_file.name}' sent to Kafka Stream!")

    # --- NEW: LIVE UI RESULTS ---
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🖼️ Uploaded Preview")
        st.image(uploaded_file, use_container_width=True)

    with col2:
        st.subheader("🤖 AI Analysis")
        
        # Open image for local analysis
        img = Image.open(uploaded_file)
        
        # Get OCR Text to show keywords
        raw_text = pytesseract.image_to_string(img).strip()
        keywords = raw_text[:300] + "..." if len(raw_text) > 300 else raw_text
        
        # Get Prediction
        category, confidence = get_prediction(img)

        # Show Category with a Metric
        st.metric(label="Predicted Category", value=category.upper())
        st.progress(confidence / 100, text=f"Confidence: {confidence:.2f}%")

        # Show why it was classified (Keywords)
        with st.expander("🔍 View Detected OCR Keywords"):
            if raw_text:
                st.write(keywords)
            else:
                st.warning("No text detected in this image.")

    # 3. Final Archiving Note
    st.caption(f"📍 This file is being archived to HDFS at: /judiciary/classified/{category.lower().replace(' ', '_')}/")
FROM python:3.9-slim

# Install Tesseract and system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    && apt-get clean

# Set working directory
WORKDIR /app

# Install Python libraries
RUN pip install pandas pyarrow pytesseract pillow hdfs

# We will mount our script into this container later
CMD ["tail", "-f", "/dev/null"]
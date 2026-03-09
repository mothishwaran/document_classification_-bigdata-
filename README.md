# Document Classification Big Data Pipeline

A real-time document classification system built with **Apache Kafka**, **HDFS**, **Apache Spark**, **OCR (Tesseract)**, and a **Streamlit** web app. It trains on the [RVL-CDIP Mini](https://huggingface.co/datasets/dvgodoy/rvl_cdip_mini) dataset and classifies document images into 16 categories (invoice, resume, email, letter, etc.).

---

## Architecture Overview

```
HuggingFace Dataset
       ↓
  [1] Kafka Producer  ──→  Kafka Topic (rvl-cdip-images)
                                   ↓
                        [2] Kafka Consumer → HDFS Storage
                                                   ↓
                              [3] Spark Scala Preprocessing
                                                   ↓
                                    [4] OCR Service (Tesseract)
                                                   ↓
                              [5] Train ML Model (Jupyter Notebook)
                                                   ↓
                           [6] Streamlit App (Real-Time Classification)
```

---

## Prerequisites

Make sure you have installed:

| Tool                                                              | Version | Purpose                        |
| ----------------------------------------------------------------- | ------- | ------------------------------ |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | Latest  | Runs Kafka, HDFS, Spark, OCR   |
| [Python](https://www.python.org/downloads/)                       | 3.9+    | Producer, Consumer, Model, App |
| [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)    | Latest  | Local OCR for Streamlit app    |
| [Apache Spark + Scala](https://spark.apache.org/downloads.html)   | 3.5.x   | Batch preprocessing            |
| [Java JDK](https://adoptium.net/)                                 | 8 or 11 | Required by Spark              |

### Python Libraries

Install all Python dependencies:

```bash
pip install kafka-python datasets hdfs streamlit pillow pytesseract joblib numpy scikit-learn pandas pyarrow
```

---

## Step-by-Step: How to Run

### Step 1 — Start the Infrastructure (Docker)

This starts **Kafka**, **HDFS (NameNode + DataNode)**, **Spark**, and the **OCR service**.

```bash
cd bigdata-infra
docker-compose up -d
```

Wait about 30–60 seconds for all services to fully start.

**Verify services are running:**

| Service          | URL                   |
| ---------------- | --------------------- |
| HDFS NameNode UI | http://localhost:9870 |
| Spark Master UI  | http://localhost:8080 |
| Kafka Broker     | localhost:9092        |

To check container status:

```bash
docker ps
```

---

### Step 2 — Ingest Data: Run the Kafka Producer

The producer loads images from the RVL-CDIP Mini dataset (HuggingFace) and streams them into Kafka.

```bash
cd ingestion
python producer.py
```

> This streams `train`, `test`, and `validation` splits sequentially. It may take several minutes depending on your internet speed. You will see progress logs like:
>
> ```
> ========== Processing TRAIN split ==========
> Sent 100 images...
> ```

---

### Step 3 — Store Images to HDFS: Run the Kafka Consumer

Open a **new terminal** and run the consumer **at the same time as the producer** (or after):

```bash
cd ingestion
python consumer.py
```

This reads messages from Kafka and saves each image into HDFS under:

```
/data/tmp/rvl-cdip/{split}/{category}_class_{label}/img_{id}.jpg
```

Progress is printed every 500 images:

```
Progress: 500 | train: 400 | test: 50 | validation: 50
```

---

### Step 4 — Preprocess with Spark (Scala)

This Spark job reads all images from HDFS, extracts metadata (split, category, label), and writes Parquet files for the OCR stage.

#### Option A — Submit via Docker Spark Master

```bash
docker exec -it project-spark-master bash

# Inside the container:
/opt/spark/bin/spark-submit \
  --class RVLCdipPreprocessing \
  --master spark://project-spark-master:7077 \
  /path/to/RVLCdipPreprocessing.jar
```

#### Option B — Submit from Local Machine (if Spark is installed locally)

First compile the Scala file to a JAR, then:

```bash
spark-submit \
  --class RVLCdipPreprocessing \
  --master spark://localhost:7077 \
  processing_scala/target/scala-2.12/rvlcdip-preprocessing.jar
```

The output Parquet files are written to HDFS at `/data/tmp/rvl-cdip-processed/`.

---

### Step 5 — Run the OCR Service

The OCR service is a Docker container that reads processed images from HDFS, runs Tesseract OCR, and saves a gold dataset with extracted text.

```bash
docker exec -it project-ocr bash

# Inside the container:
python ocr_extraction.py
```

Output is saved to HDFS at `/data/tmp/rvl-cdip-gold/`.

---

### Step 6 — Train the ML Model

Open the Jupyter Notebook to train the TF-IDF + classifier model on the OCR-extracted text.

```bash
cd model
jupyter notebook training.ipynb
```

Run all cells in order. After training, two files will be saved in the `model/` folder:

- `document_classifier.pkl` — Trained classifier
- `tfidf_vectorizer.pkl` — TF-IDF vectorizer

> **Note:** You need Tesseract installed locally. On Windows, update the path in `predict.py` if needed:
>
> ```python
> pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
> ```

---

### Step 7 — Run the Streamlit Web App

This is the **real-time frontend**. Upload any document image and get an instant AI classification.

Make sure Docker is still running (Kafka must be up), and the `.pkl` model files exist in the `model/` folder.

```bash
cd model
streamlit run app.py
```

Open your browser at **http://localhost:8501**

The app will:

1. Accept a JPG/PNG document upload
2. Run OCR to extract text
3. Classify the document into one of 16 categories
4. Show confidence score and detected keywords
5. Archive the document to HDFS

---

### Step 8 (Optional) — Run the Background AI Consumer Agent

This is a separate Kafka consumer that listens for documents sent from the Streamlit app and archives them to HDFS automatically.

```bash
cd model
python consumer_agent.py
```

---

## Folder Structure

```
PROJECT/
├── bigdata-infra/
│   └── docker-compose.yml        # Kafka, HDFS, Spark, OCR containers
│
├── ingestion/
│   ├── producer.py               # Streams RVL-CDIP images → Kafka
│   └── consumer.py               # Reads Kafka → saves images to HDFS
│
├── processing_scala/
│   └── RVLCdipPreprocessing.scala  # Spark job: reads HDFS images → Parquet
│
├── ocr_services/
│   ├── Dockerfile                # OCR container (Tesseract + Python)
│   └── ocr_extraction.py         # Reads Parquet → runs OCR → gold dataset
│
└── model/
    ├── training.ipynb            # Train TF-IDF + ML classifier
    ├── predict.py                # Prediction logic (used by app)
    ├── consumer_agent.py         # Kafka agent: classifies & archives docs
    └── app.py                    # Streamlit UI for real-time classification
```

---

## Document Categories (16 Classes)

| #   | Category               | #   | Category      |
| --- | ---------------------- | --- | ------------- |
| 0   | letter                 | 8   | file_folder   |
| 1   | form                   | 9   | news_article  |
| 2   | email                  | 10  | budget        |
| 3   | handwritten            | 11  | invoice       |
| 4   | advertisement          | 12  | presentation  |
| 5   | scientific_report      | 13  | questionnaire |
| 6   | scientific_publication | 14  | resume        |
| 7   | specification          | 15  | memo          |

---

## Troubleshooting

**Docker containers not starting?**

```bash
docker-compose down
docker-compose up -d
```

**Kafka connection refused?**

- Make sure Docker Desktop is running
- Wait 30 seconds after `docker-compose up` before running producer/consumer

**Tesseract not found (Windows)?**

- Download and install from: https://github.com/UB-Mannheim/tesseract/wiki
- Update the path in `model/predict.py`:
  ```python
  pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
  ```

**Model files not found?**

- Run `training.ipynb` fully before launching `app.py` or `consumer_agent.py`

**HDFS WebUI not loading?**

- Check if `project-namenode` container is running: `docker ps`
- Try restarting: `docker restart project-namenode`

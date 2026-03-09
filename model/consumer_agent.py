from kafka import KafkaConsumer
import json
import os
from predict import get_prediction
from PIL import Image
import subprocess

# Setup Kafka Consumer
consumer = KafkaConsumer(
    'judiciary-docs',
    bootstrap_servers=['localhost:9092'],
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

print("🕵️ AI Agent is listening to Kafka...")

for msg in consumer:
    file_path = msg.value['file_path']
    file_name = os.path.basename(file_path)
    file_path = os.path.abspath(file_path) # Absolute path for Windows stability
    
    print(f"📦 Processing: {file_path}")
    
    try:
        # 1. Run AI Prediction
        img = Image.open(file_path)
        category, confidence = get_prediction(img)
        category_folder = category.lower().replace(" ", "_")
        
        print(f"✅ Result: {category.upper()} ({confidence:.2f}%)")
        
        # 2. REAL-TIME SEGREGATION: Move to HDFS
        hdfs_path = f"/judiciary/classified/{category_folder}/"
        
        # Use "namenode" (the service name) instead of any IDs
        # --- THE PRODUCTION FIX: USE THE SERVICE NAME project-namenode ---
        # 1. Create HDFS directory (Uses project-namenode name)
        subprocess.run(f"docker exec project-namenode hdfs dfs -mkdir -p {hdfs_path}", shell=True)
        
        # 2. Clear container temp space
        subprocess.run(f"docker exec project-namenode rm -f /tmp/{file_name}", shell=True)
        
        # 3. Copy local file to the Namenode container (Uses project-namenode)
        subprocess.run(f"docker cp \"{file_path}\" project-namenode:/tmp/", shell=True)
        
        # 4. Put into HDFS (Uses project-namenode)
        subprocess.run(f"docker exec project-namenode hdfs dfs -put /tmp/{file_name} {hdfs_path}", shell=True)
        
        print(f"📂 Successfully archived to HDFS: {hdfs_path}{file_name}")

    except Exception as e:
        print(f"❌ Error during processing: {e}")
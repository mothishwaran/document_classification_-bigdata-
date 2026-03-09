import pandas as pd
import pytesseract
from PIL import Image
from hdfs import InsecureClient
import io
import os

# --- CONFIG ---
HDFS_URL = "http://project-namenode:9870" 
HDFS_USER = "root"
INPUT_BASE_PATH = "/data/tmp/rvl-cdip-processed" # The root directory from Spark
OUTPUT_PATH = "/data/tmp/rvl-cdip-gold"

client = InsecureClient(HDFS_URL, user=HDFS_USER)

print("Fetching metadata from all partitions in HDFS...")

# --- NEW LOGIC TO FIND ALL PARQUET FILES ---
all_dfs = []
# Walk through the partitioned directory (train, test, validation)
for root, dirs, files in client.walk(INPUT_BASE_PATH):
    for f in files:
        if f.endswith('.parquet'):
            full_path = f"{root}/{f}"
            print(f"Reading: {full_path}")
            with client.read(full_path) as reader:
                # We need to use 'pyarrow' engine for partitioned Parquet
                temp_df = pd.read_parquet(io.BytesIO(reader.read()))
                
                # Manual Split Extraction: 
                # Since we are reading files directly, we manually add back the 'split' 
                # column based on the folder name (e.g., 'split=train')
                if 'split=' in root:
                    split_name = root.split('split=')[-1].split('/')[0]
                    temp_df['split'] = split_name
                
                all_dfs.append(temp_df)

if not all_dfs:
    print("❌ Critical Error: No parquet files found in any subdirectory!")
    exit()

# Combine all fragments into one master dataframe
df = pd.concat(all_dfs, ignore_index=True)
print(f"Successfully loaded {len(df)} records.")

def perform_ocr(hdfs_path):
    try:
        # Clean path to work inside Docker
        clean_path = hdfs_path.replace("hdfs://project-namenode:9000", "")
        with client.read(clean_path) as reader:
            img = Image.open(io.BytesIO(reader.read()))
            # Optimized for documents: use --psm 3 (Standard Page Segmentation)
            return pytesseract.image_to_string(img, config='--psm 3').strip().replace("\n", " ")
    except Exception as e:
        return ""

print(f"Starting OCR on {len(df)} images...")
# df = df.head(10) # Uncomment this for a quick 10-image test
df['ocr_text'] = df['image_path'].apply(perform_ocr)

# Save to Gold Zone
print("Saving Gold Parquet to HDFS...")
out_buffer = io.BytesIO()
df.to_parquet(out_buffer, index=False)
out_buffer.seek(0)

client.makedirs(OUTPUT_PATH)
with client.write(f"{OUTPUT_PATH}/enriched_data.parquet", overwrite=True) as writer:
    writer.write(out_buffer.getvalue())

print(f"✅ Success! Gold data at {OUTPUT_PATH}/enriched_data.parquet")
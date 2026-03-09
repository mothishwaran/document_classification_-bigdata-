import json
import io
import os
from kafka import KafkaProducer
from datasets import load_dataset

os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "120"

# ---------------- CONFIG ----------------
TOPIC = "rvl-cdip-images"
KAFKA_SERVER = "localhost:9092"
MAX_IMAGES_PER_SPLIT = None  # None = ALL images

# Kafka Producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_SERVER,
    max_request_size=10485760,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)

# Correct split names from chainyo/rvl-cdip
SPLITS = ["train", "test", "validation"]  # Note: "val" not "validation"

total_sent = 0
total_skipped = 0

for split in SPLITS:
    print(f"\n========== Processing {split.upper()} split ==========")
    
    dataset = load_dataset(
        "dvgodoy/rvl_cdip_mini",
        split=split,
        streaming=True
    )
    
    count = 0
    sent_count = 0
    
    for example in dataset:
        image_obj = example["image"]
        
        if image_obj.mode != 'RGB':
            image_obj = image_obj.convert('RGB')
        
        # Resize if too large
        max_size = 1000
        if max(image_obj.size) > max_size:
            ratio = max_size / max(image_obj.size)
            new_size = (int(image_obj.size[0] * ratio), int(image_obj.size[1] * ratio))
            image_obj = image_obj.resize(new_size)
        
        # Compress as JPEG
        img_byte_arr = io.BytesIO()
        image_obj.save(img_byte_arr, format='JPEG', quality=60)
        valid_image_bytes = img_byte_arr.getvalue()
        
        # Skip if > 9MB
        if len(valid_image_bytes) > 9000000:
            print(f"Skipped {split}/image {count}: too large")
            count += 1
            total_skipped += 1
            continue

        message = {
            "id": count,
            "split": split,
            "label": int(example["label"]),
            "category": example["category"],   # ✅ ADD THIS
            "width": example["width"],
            "height": example["height"],
            "image_bytes": valid_image_bytes.decode("latin1")
        }


        try:
            future = producer.send(TOPIC, value=message)
            future.get(timeout=30)
            sent_count += 1
            total_sent += 1
        except Exception as e:
            print(f"Error sending {split}/image {count}: {e}")
            total_skipped += 1

        count += 1
        
        if sent_count % 1000 == 0:
            print(f"{split}: {sent_count}/{count} sent")
        
        if MAX_IMAGES_PER_SPLIT and count >= MAX_IMAGES_PER_SPLIT:
            break
    
    print(f"{split} complete: {sent_count} images sent")

producer.flush()
producer.close()

print(f"\n========== PRODUCER FINISHED ==========")
print(f"✅ Total sent: {total_sent}")
print(f"⚠️ Total skipped: {total_skipped}")
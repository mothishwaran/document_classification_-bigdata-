import json
from kafka import KafkaConsumer
from hdfs import InsecureClient

# ================= CONFIG =================
KAFKA_TOPIC = "rvl-cdip-images"
KAFKA_SERVER = "localhost:9092"

HDFS_URL = "http://localhost:9870"
HDFS_USER = "root"
HDFS_BASE_PATH = "/data/tmp/rvl-cdip"

categories = [
    "letter","form","email","handwritten","advertisement",
    "scientific_report","scientific_publication","specification",
    "file_folder","news_article","budget","invoice",
    "presentation","questionnaire","resume","memo"
]

# ================= HDFS CLIENT =================
hdfs = InsecureClient(HDFS_URL, user=HDFS_USER)

print("Creating HDFS directories...")
for split in ["train", "test", "validation"]:
    for idx, cat in enumerate(categories):
        path = f"{HDFS_BASE_PATH}/{split}/{cat}_class_{idx}"
        try:
           hdfs.makedirs(path)
        except Exception:
           pass

print("Directories created!")

# ================= KAFKA CONSUMER =================
consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=KAFKA_SERVER,
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    group_id="rvl-cdip-consumer-splits",
    value_deserializer=lambda v: json.loads(v.decode("utf-8"))
)

print("Kafka consumer started. Waiting for messages...")

saved_count = 0
split_counts = {"train": 0, "test": 0, "validation": 0}

# ✅ EVERYTHING MUST BE INSIDE THIS LOOP
for message in consumer:
    data = message.value

    image_id = data["id"]
    split = data["split"]
    label = data["label"]
    category = data["category"]

    image_bytes = data["image_bytes"].encode("latin1")

    hdfs_path = (
        f"{HDFS_BASE_PATH}/{split}/"
        f"{category}_class_{label}/"
        f"img_{image_id}.jpg"
    )

    with hdfs.write(hdfs_path, overwrite=True) as writer:
        writer.write(image_bytes)

    saved_count += 1
    split_counts[split] += 1

    if saved_count % 500 == 0:
        print(
            f"Progress: {saved_count} | "
            f"train: {split_counts['train']} | "
            f"test: {split_counts['test']} | "
            f"validation: {split_counts['validation']}"
        )

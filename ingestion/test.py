from datasets import load_dataset

print("Loading dvgodoy/rvl_cdip_mini...")
ds = load_dataset("dvgodoy/rvl_cdip_mini")
print(ds)

# Check each split
for split in ds:
    print(f"\n{split}:")
    print(f"  Images: {len(ds[split])}")
    labels = set(ds[split]['label'])
    print(f"  Classes: {len(labels)}")
    print(f"  Labels: {sorted(labels)}")
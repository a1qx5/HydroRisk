import time
import json
from layer1.collector import get_property_data

start = time.time()
try:
    print("Fetching data...")
    res = get_property_data(44.44, 26.09)
    print(json.dumps(res, indent=2))
except Exception as e:
    print("Error:", e)
print(f"Time taken: {time.time() - start:.2f}s")

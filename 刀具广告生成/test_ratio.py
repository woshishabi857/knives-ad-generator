import sys
import os

# Add current dir to sys.path
sys.path.append(os.getcwd())

from gemini_client import get_closest_aspect_ratio

test_cases = [
    (1000, 1000, "1:1"),
    (1920, 1080, "16:9"),
    (1280, 720, "16:9"),
    (800, 600, "4:3"),
    (600, 800, "3:4"),
    (1080, 1920, "9:16"),
    (1500, 1000, "4:3"), # 1.5 vs 1.33 vs 1.77. 1.5-1.33=0.17, 1.77-1.5=0.27. Match 4:3.
]

for w, h, expected in test_cases:
    actual = get_closest_aspect_ratio(w, h)
    print(f"W={w}, H={h} -> Actual: {actual}, Expected: {expected}")
    assert actual == expected
print("All aspect ratio tests passed!")

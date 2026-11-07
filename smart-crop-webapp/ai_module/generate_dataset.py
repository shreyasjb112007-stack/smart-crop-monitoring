"""
generate_dataset.py
--------------------
Builds the sample dataset described in Section 8 of the project doc:

    Tomato  -> Healthy, Early Blight, Late Blight
    Potato  -> Healthy, Early Blight, Late Blight
    Rice    -> Healthy, Brown Spot

Since a real labelled crop-disease image dataset isn't bundled with this
repo, this script SYNTHESISES a small set of placeholder images that are
still visually distinguishable per class (different base colour for each
crop, different "lesion spot" pattern for each disease/severity). This is
enough to demonstrate a genuinely working embed -> store -> search pipeline
for the DA1 demo.

For your final submission, you can swap this out for a real dataset (e.g.
PlantVillage on Kaggle): drop images into
    dataset/<Crop>_<Disease>/img1.jpg, img2.jpg, ...
and call `load_real_dataset()` instead of `generate_synthetic_dataset()`
in app.py -- everything else (embedding, Milvus insert) stays the same.
"""

import os
import random
from pathlib import Path
from PIL import Image, ImageDraw

DATASET_DIR = Path("dataset")

# crop_name -> base RGB colour (roughly evokes the plant's healthy leaf colour)
CROP_BASE_COLOR = {
    "Tomato": (60, 140, 60),
    "Potato": (70, 110, 50),
    "Rice":   (90, 160, 70),
}

# (crop, disease) -> (severity, treatment, spot_color, spot_count)
DISEASE_INFO = {
    ("Tomato", "Healthy"):      ("Low",      "No treatment needed. Continue regular monitoring.", None, 0),
    ("Tomato", "Early Blight"): ("Moderate", "Remove affected leaves and apply a recommended fungicide.", (120, 80, 30), 12),
    ("Tomato", "Late Blight"):  ("High",     "Apply copper-based fungicide immediately and improve field drainage.", (40, 30, 20), 25),
    ("Potato", "Healthy"):      ("Low",      "No treatment needed. Continue regular monitoring.", None, 0),
    ("Potato", "Early Blight"): ("Moderate", "Apply fungicide and rotate crops next season.", (110, 70, 25), 12),
    ("Potato", "Late Blight"):  ("High",     "Apply systemic fungicide immediately; destroy severely infected plants.", (35, 25, 15), 25),
    ("Rice",   "Healthy"):      ("Low",      "No treatment needed. Continue regular monitoring.", None, 0),
    ("Rice",   "Brown Spot"):   ("High",     "Apply fungicide and improve soil potassium levels.", (100, 55, 20), 18),
}

IMAGES_PER_CLASS = 5     # keep the demo dataset small and fast
IMAGE_SIZE = (224, 224)


def _make_leaf_image(base_color, spot_color, spot_count, seed):
    rnd = random.Random(seed)
    img = Image.new("RGB", IMAGE_SIZE, base_color)
    draw = ImageDraw.Draw(img)

    # a little colour/texture variation so images in the same class aren't identical
    for _ in range(40):
        x, y = rnd.randint(0, IMAGE_SIZE[0]), rnd.randint(0, IMAGE_SIZE[1])
        r = rnd.randint(3, 8)
        shade = tuple(max(0, min(255, c + rnd.randint(-15, 15))) for c in base_color)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=shade)

    # disease "lesion" spots
    if spot_color and spot_count:
        for _ in range(spot_count):
            x, y = rnd.randint(10, IMAGE_SIZE[0] - 10), rnd.randint(10, IMAGE_SIZE[1] - 10)
            r = rnd.randint(4, 10)
            draw.ellipse([x - r, y - r, x + r, y + r], fill=spot_color)

    return img


def generate_synthetic_dataset(out_dir: Path = DATASET_DIR) -> list[dict]:
    """
    Creates the placeholder image files on disk and returns a metadata list:
        [{"image_id", "crop_name", "disease_name", "severity",
          "treatment", "image_path"}, ...]
    (embeddings are generated separately in app.py / insert_dataset.py)
    """
    out_dir.mkdir(exist_ok=True)
    records = []
    image_id = 1

    for (crop, disease), (severity, treatment, spot_color, spot_count) in DISEASE_INFO.items():
        base_color = CROP_BASE_COLOR[crop]
        class_dir = out_dir / f"{crop}_{disease}".replace(" ", "_")
        class_dir.mkdir(exist_ok=True)

        for i in range(IMAGES_PER_CLASS):
            img = _make_leaf_image(base_color, spot_color, spot_count, seed=image_id * 97 + i)
            fname = class_dir / f"img_{i+1}.png"
            img.save(fname)

            records.append({
                "image_id": image_id,
                "crop_name": crop,
                "disease_name": disease,
                "severity": severity,
                "treatment": treatment,
                "image_path": str(fname),
            })
            image_id += 1

    return records


def load_real_dataset(root_dir: Path, metadata_map: dict) -> list[dict]:
    """
    Use this INSTEAD of generate_synthetic_dataset() once you have a real
    dataset organised as:
        root_dir/<Crop>_<Disease>/*.jpg

    `metadata_map` maps "<Crop>_<Disease>" -> (severity, treatment), e.g.
        {"Tomato_Early_Blight": ("Moderate", "Remove affected leaves...")}
    """
    records = []
    image_id = 1
    for class_folder in sorted(Path(root_dir).iterdir()):
        if not class_folder.is_dir():
            continue
        key = class_folder.name
        if key not in metadata_map:
            continue
        severity, treatment = metadata_map[key]
        crop_name, disease_name = key.split("_", 1)
        disease_name = disease_name.replace("_", " ")

        for img_path in class_folder.glob("*"):
            if img_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
                continue
            records.append({
                "image_id": image_id,
                "crop_name": crop_name,
                "disease_name": disease_name,
                "severity": severity,
                "treatment": treatment,
                "image_path": str(img_path),
            })
            image_id += 1
    return records


if __name__ == "__main__":
    recs = generate_synthetic_dataset()
    print(f"Generated {len(recs)} sample images across {len(DISEASE_INFO)} classes in '{DATASET_DIR}/'")

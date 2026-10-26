"""Verify Toolkit source metadata and published runtime crops without starting the app."""

import json
from pathlib import Path

from PIL import Image


def validate(root: Path) -> None:
    """Check IDs, image sizes, bounds, and lossless source/runtime correspondence."""
    libraries = []
    for directory in (root / "ok_templates", root / "assets"):
        data = json.loads((directory / "coco_annotations.json").read_text("utf-8"))
        tables = {}
        for key in ("images", "annotations", "categories"):
            entries = data[key]
            assert isinstance(entries, list), (directory, key)
            tables[key] = {entry["id"]: entry for entry in entries}
            assert len(entries) == len(tables[key]), (directory, key, "duplicate ID")
        decoded = {}
        for image_id, entry in tables["images"].items():
            path = (directory / entry["file_name"]).resolve()
            assert path.is_relative_to(directory.resolve()), path
            with Image.open(path) as image:
                image.load()
                assert image.size == (entry["width"], entry["height"]), path
                decoded[image_id] = image.convert("RGB")
        features = {}
        for ann in tables["annotations"].values():
            image = tables["images"][ann["image_id"]]
            name = tables["categories"][ann["category_id"]]["name"]
            assert name not in features, (directory, name, "duplicate template")
            x, y, width, height = ann["bbox"]
            assert all(isinstance(v, int) for v in ann["bbox"]), ann
            assert x >= 0 and y >= 0 and width > 0 and height > 0, ann
            assert x + width <= image["width"] and y + height <= image["height"], ann
            assert ann["area"] == width * height, ann
            crop = decoded[ann["image_id"]].crop((x, y, x + width, y + height))
            features[name] = (image["width"], image["height"], ann["bbox"], crop.tobytes())
        assert set(features) == {cat["name"] for cat in tables["categories"].values()}
        libraries.append(features)
    assert libraries[0] == libraries[1], "Published runtime differs from Toolkit source"
    assert {"dialog_icon", "skip_choose", "skip_f", "chat_icon"} == set(libraries[0])
    for filename in ("boxes.json", "points.json"):
        data = json.loads((root / "ok_templates" / filename).read_text("utf-8"))
        assert all(isinstance(data[key], list) for key in ("images", "annotations", "categories"))


if __name__ == "__main__":
    validate(Path(__file__).resolve().parents[1])
    print("Toolkit metadata and published template crops verified")

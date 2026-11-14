"""Map a Crop___Disease class to the traded crop name used by mandi APIs."""
from __future__ import annotations

# PlantVillage class prefix -> Agmarknet / e-NAM commodity name.
CROP_MAP = {
    "Apple": "apple",
    "Blueberry": "blueberry",
    "Cherry": "cherry",
    "Corn": "maize",
    "Grape": "grape",
    "Orange": "orange",
    "Peach": "peach",
    "Pepper": "capsicum",
    "Potato": "potato",
    "Raspberry": "raspberry",
    "Soybean": "soybean",
    "Squash": "pumpkin",
    "Strawberry": "strawberry",
    "Tomato": "tomato",
}


def crop_for_class(class_label: str) -> str:
    """Return the commodity name for a Crop___Disease class label.

    Falls back to the crop prefix lower-cased if the crop is not in the map,
    so the farmer at least gets a plausible lookup.
    """
    if "___" in class_label:
        crop = class_label.split("___")[0]
    else:
        crop = class_label
    return CROP_MAP.get(crop, crop.lower())
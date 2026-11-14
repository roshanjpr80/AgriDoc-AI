"""Build data/knowledge/advisory_rules.json from curated source material.

The KB is the only thing the advice engine may cite. Every entry carries a
source and a review date. Run once; commit the output JSON.
"""
from __future__ import annotations

import json
from pathlib import Path

# Make repo root importable so `configs` resolves when running
# `python scripts/build_knowledge.py` directly.
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ICAR = "ICAR-CIPHT / State Agriculture Dept. (see MODEL_CARD.md)"
REVIEWED = "2026-10-27"

# disease -> {crop, symptoms, organic, chemical, prevention}
# Organic/low-cost options come first. No invented doses: any chemical that
# needs a specific dose is flagged "verify with an agriculture officer".
KB = {
  "Apple___Apple_scab": {
    "crop": "Apple", "disease": "Apple scab",
    "symptoms": ["olive-green or brown velvety spots on leaves", "dark scabby lesions on fruit", "deformed fruit"],
    "organic": ["remove and destroy fallen leaves in winter", "prune for airflow", "apply neem oil 3% at green-tip stage"],
    "chemical": ["sulphur or copper fungicide at bud-break, repeating every 10-14 days while wet", "dose: verify with an agriculture officer"],
    "prevention": ["rake and burn fallen leaves", "avoid overhead irrigation", "space trees for airflow"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Apple___Black_rot": {
    "crop": "Apple", "disease": "Black rot",
    "symptoms": ["purple-brown circular spots on leaves", "brown rotting lesions on fruit", "sunken cankers on branches"],
    "organic": ["prune out cankers 15 cm below visible damage", "remove mummified fruit from tree and ground"],
    "chemical": ["copper-based fungicide at green-tip and petal-fall", "dose: verify with an agriculture officer"],
    "prevention": ["sanitise pruning tools between trees", "remove dead wood", "do not let fruit mummies overwinter"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Apple___Cedar_apple_rust": {
    "crop": "Apple", "disease": "Cedar apple rust",
    "symptoms": ["bright orange spots on upper leaf surface", "tubular spore structures on underside", "yellowing leaves"],
    "organic": ["remove nearby cedar/juniper (the alternate host)", "plant resistant cultivars"],
    "chemical": ["sulphur fungicide from green-tip to 3 weeks after petal-fall", "dose: verify with an agriculture officer"],
    "prevention": ["keep apples > 200 m from cedars", "avoid wet foliage at night"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Apple___healthy": {
    "crop": "Apple", "disease": "Healthy",
    "symptoms": ["no disease signs", "uniform green foliage"],
    "organic": ["maintain mulch ring", "regular pruning for sunlight"],
    "chemical": [], "prevention": ["monitor weekly", "sanitise tools"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Blueberry___healthy": {
    "crop": "Blueberry", "disease": "Healthy",
    "symptoms": ["no disease signs", "glossy green leaves"],
    "organic": ["mulch with pine bark (acidic)", "ensure pH 4.5-5.5"],
    "chemical": [], "prevention": ["annual soil pH test", "drip, not overhead irrigation"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Cherry_(including_sour)___Powdery_mildew": {
    "crop": "Cherry", "disease": "Powdery mildew",
    "symptoms": ["white powdery patches on young leaves", "curled distorted shoots", "stunted growth"],
    "organic": ["remove infected shoots", "sulphur dust when dry", "milk spray 1:10"],
    "chemical": ["wettable sulphur or myclobutanil at first sign, repeat 10-14 days", "dose: verify with an agriculture officer"],
    "prevention": ["prune for ventilation", "avoid high-nitrogen over-feeding", "water at soil level"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Cherry_(including_sour)___healthy": {
    "crop": "Cherry", "disease": "Healthy",
    "symptoms": ["no disease signs", "dark green leaves"],
    "organic": ["annual compost", "mulch to hold soil moisture"],
    "chemical": [], "prevention": ["well-drained soil", "prune in late winter"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": {
    "crop": "Corn", "disease": "Gray leaf spot",
    "symptoms": ["long rectangular grey-brown lesions parallel to veins", "lower leaves die first", "grey mould in humid weather"],
    "organic": ["rotate with non-cereal crops", "crop residue incorporation", "plant resistant hybrids"],
    "chemical": ["strobilurin or triazole at tasseling if lesions on 3rd leaf below ear", "dose: verify with an agriculture officer"],
    "prevention": ["residue management", "2-3 year rotation", "adequate spacing"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Corn_(maize)___Common_rust_": {
    "crop": "Corn", "disease": "Common rust",
    "symptoms": ["cinnamon-brown powdery pustules on both leaf surfaces", "pustules turn dark as leaf matures", "yellowing around pustules"],
    "organic": ["early planting to escape rust", "resistant hybrids", "remove volunteer corn"],
    "chemical": ["sulphur or mancozeb when pustules first appear", "dose: verify with an agriculture officer"],
    "prevention": ["plant early", "avoid stress (fertility + moisture)"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Corn_(maize)___Northern_Leaf_Blight": {
    "crop": "Corn", "disease": "Northern leaf blight",
    "symptoms": ["long cigar-shaped grey-green lesions", "lesions run parallel to veins", "leaves dry from tip downward"],
    "organic": ["rotate with soybean (non-host)", "bury crop residue", "resistant hybrids"],
    "chemical": ["triazole at 3-5 weeks before tasseling if lesions present", "dose: verify with an agriculture officer"],
    "prevention": ["residue incorporation", "rotation", "balanced nitrogen (avoid excess)"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Corn_(maize)___healthy": {
    "crop": "Corn", "disease": "Healthy",
    "symptoms": ["no disease signs", "tall green stalks"],
    "organic": ["rotate annually", "test soil before fertilising"],
    "chemical": [], "prevention": ["adequate spacing", "timely irrigation"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Grape___Black_rot": {
    "crop": "Grape", "disease": "Black rot",
    "symptoms": ["small tan spots with dark margins on leaves", "rapid berry shrivelling into black mummies", "infected berries remain on vine"],
    "organic": ["remove and destroy mummified berries and cankers", "clean vine debris at pruning"],
    "chemical": ["sulphur + copper at bud-break, bloom and 2 weeks after", "dose: verify with an agriculture officer"],
    "prevention": ["trellis for air movement", "southern exposure", "remove mummies"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Grape___Esca_(Black_Measles)": {
    "crop": "Grape", "disease": "Esca (Black Measles)",
    "symptoms": ["dark tiger-stripe streaks on wood", "small dark spots on berries", "sudden wilting of entire vine (apoplexy)"],
    "organic": ["prune out affected cordons", "avoid large pruning wounds", "no known organic cure — remove infected wood"],
    "chemical": ["wound protectants at pruning", "no curative chemical — prevention only", "dose: verify with an agriculture officer"],
    "prevention": ["sanitise pruning tools", "minimise wound size", "replace severely affected vines"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)": {
    "crop": "Grape", "disease": "Leaf blight (Isariopsis)",
    "symptoms": ["irregular brown patches between veins", "spots enlarge and merge", "premature leaf drop"],
    "organic": ["remove infected leaves", "improve air circulation", "avoid overhead watering"],
    "chemical": ["mancozeb or copper sprays at first sign", "dose: verify with an agriculture officer"],
    "prevention": ["open canopy", "leaf removal around clusters"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Grape___healthy": {
    "crop": "Grape", "disease": "Healthy",
    "symptoms": ["no disease signs", "vigorous green vines"],
    "organic": ["balanced compost", "adequate irrigation"],
    "chemical": [], "prevention": ["trellis training", "annual pruning"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Orange___Haunglongbing_(Citrus_greening)": {
    "crop": "Orange", "disease": "HLB (Citrus greening)",
    "symptoms": ["blotchy mottled leaves with yellow on one side", "lopsided small bitter fruit", "twig dieback", "vector: Asian citrus psyllid"],
    "organic": ["no cure — remove infected trees", "control psyllid (vector) with neem oil + yellow sticky traps", "plant certified disease-free nursery stock"],
    "chemical": ["psyllid control only (this is not a cure)", "dose: verify with an agriculture officer"],
    "prevention": ["quarantine movement of budwood", "scout for psyllid", "remove abandoned citrus"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Peach___Bacterial_spot": {
    "crop": "Peach", "disease": "Bacterial spot",
    "symptoms": ["water-soaked angular spots on leaves", "spots fall out leaving shot-holes", "cracked lesions on fruit"],
    "organic": ["copper sprays are only partially effective", "use resistant cultivars", "avoid overhead irrigation"],
    "chemical": ["copper + mancozeb at leaf-out and after rain", "dose: verify with an agriculture officer"],
    "prevention": ["good air circulation", "avoid nitrogen excess", "sanitise tools"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Peach___healthy": {
    "crop": "Peach", "disease": "Healthy",
    "symptoms": ["no disease signs", "healthy lance-shaped leaves"],
    "organic": ["annual compost", "winter pruning"],
    "chemical": [], "prevention": ["well-drained soil", "thinning fruit for size"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Pepper,_bell___Bacterial_spot": {
    "crop": "Pepper", "disease": "Bacterial spot",
    "symptoms": ["water-soaked spots on leaves", "raised scabby lesions on fruit", "leaf drop"],
    "organic": ["copper hydroxide sprays", "use disease-free seed", "stake plants for air flow"],
    "chemical": ["copper + mancozeb rotation weekly when wet", "dose: verify with an agriculture officer"],
    "prevention": ["3-year rotation away from solanaceous crops", "avoid working wet foliage"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Pepper,_bell___healthy": {
    "crop": "Pepper", "disease": "Healthy",
    "symptoms": ["no disease signs", "dark green glossy leaves"],
    "organic": ["mulch for moisture", "support plants"],
    "chemical": [], "prevention": ["full sun", "even moisture"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Potato___Early_blight": {
    "crop": "Potato", "disease": "Early blight",
    "symptoms": ["dark brown target-like spots with concentric rings", "lower leaves affected first", "yellow halo around spots"],
    "organic": ["rotate (2-3 years from tomato/eggplant)", "balanced fertility — avoid nitrogen stress", "hilling to reduce leaf contact"],
    "chemical": ["mancozeb or chlorothalonil at first sign, 7-14 day interval", "dose: verify with an agriculture officer"],
    "prevention": ["rotation", "certified seed", "adequate but not excess nitrogen"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Potato___Late_blight": {
    "crop": "Potato", "disease": "Late blight",
    "symptoms": ["large water-soaked brown patches", "white mould on leaf underside in humid mornings", "rapid collapse of whole plant"],
    "organic": ["destroy infected plants (do not compost)", "use resistant cultivars", "avoid overhead irrigation"],
    "chemical": ["metalaxyl+mancozeb or cymoxanil+mancozeb preventive, 7-10 day in cool wet weather", "dose: verify with an agriculture officer"],
    "prevention": ["plant certified tubers", "destroy volunteer/groundkeeper potatoes", "burn infected foliage"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Potato___healthy": {
    "crop": "Potato", "disease": "Healthy",
    "symptoms": ["no disease signs", "dark green compound leaves"],
    "organic": ["rotate with legumes", "soil test for pH 5.5-6.5"],
    "chemical": [], "prevention": ["certified seed", "hilling for tuber cover"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Raspberry___healthy": {
    "crop": "Raspberry", "disease": "Healthy",
    "symptoms": ["no disease signs", "vigorous canes"],
    "organic": ["annual pruning of spent canes", "mulch to suppress weeds"],
    "chemical": [], "prevention": ["trellis support", "well-drained soil"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Soybean___healthy": {
    "crop": "Soybean", "disease": "Healthy",
    "symptoms": ["no disease signs", "trifoliate leaves, nitrogen nodules"],
    "organic": ["inoculate seed with rhizobium", "rotate with cereals"],
    "chemical": [], "prevention": ["avoid compaction", "adequate spacing"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Squash___Powdery_mildew": {
    "crop": "Squash", "disease": "Powdery mildew",
    "symptoms": ["white powdery spots on upper leaf surface", "leaves yellow and dry", "reduced fruit size"],
    "organic": ["milk spray 1:10 with water", "bicarbonate + soap solution", "remove heavily infected leaves"],
    "chemical": ["wettable sulphur (not when > 30C) or myclobutanil", "dose: verify with an agriculture officer"],
    "prevention": ["full sun", "wide spacing", "resistant cultivars"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Strawberry___Leaf_scorch": {
    "crop": "Strawberry", "disease": "Leaf scorch",
    "symptoms": ["purple to red spots on leaves", "spots merge giving scorched look", "defoliation reduces yield"],
    "organic": ["remove infected leaves", "renovate beds to increase air flow", "drip irrigation"],
    "chemical": ["copper or captan at first sign", "dose: verify with an agriculture officer"],
    "prevention": ["buy certified plants", "3-year rotation", "mulch between rows"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Strawberry___healthy": {
    "crop": "Strawberry", "disease": "Healthy",
    "symptoms": ["no disease signs", "healthy trifoliate leaves"],
    "organic": ["straw mulch", "balanced feeding"],
    "chemical": [], "prevention": ["raised beds", "drip irrigation"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Tomato___Bacterial_spot": {
    "crop": "Tomato", "disease": "Bacterial spot",
    "symptoms": ["small water-soaked spots on leaves", "raised corky spots on green fruit", "leaf yellowing and drop"],
    "organic": ["copper sprays are only partially effective", "use disease-free transplants", "stake for air flow"],
    "chemical": ["copper + mancozeb every 7-10 days when wet", "dose: verify with an agriculture officer"],
    "prevention": ["2-3 year rotation", "avoid working wet foliage", "drip irrigation"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Tomato___Early_blight": {
    "crop": "Tomato", "disease": "Early blight",
    "symptoms": ["dark concentric ring spots on lower leaves", "yellow halos", "lesions on stem near soil"],
    "organic": ["mulch to prevent soil splash", "remove lower infected leaves", "rotate with non-solanaceous crops"],
    "chemical": ["mancozeb at first sign, 7-14 day interval", "dose: verify with an agriculture officer"],
    "prevention": ["mulch", "adequate spacing", "stake plants"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Tomato___Late_blight": {
    "crop": "Tomato", "disease": "Late blight",
    "symptoms": ["water-soaked blotches that turn brown", "white mould on underside in humid conditions", "rapid total defoliation"],
    "organic": ["destroy infected plants immediately (burn, do not compost)", "avoid overhead watering", "resistant cultivars"],
    "chemical": ["metalaxyl+mancozeb preventive in cool wet spells, 7-10 days", "dose: verify with an agriculture officer"],
    "prevention": ["avoid planting near potato", "burn infected debris", "stake for air flow"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Tomato___Leaf_Mold": {
    "crop": "Tomato", "disease": "Leaf mold",
    "symptoms": ["pale green to yellow spots on upper surface", "olive-green velvety mould on underside", "leaf curl and drop"],
    "organic": ["reduce humidity — ventilate greenhouse", "remove infected leaves", "avoid wetting foliage"],
    "chemical": ["copper or chlorothalonil when humidity is high", "dose: verify with an agriculture officer"],
    "prevention": ["air circulation", "spacing", "drip irrigation"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Tomato___Septoria_leaf_spot": {
    "crop": "Tomato", "disease": "Septoria leaf spot",
    "symptoms": ["many small circular spots with dark borders and grey centres", "yellowing around spots", "starts on lowest leaves"],
    "organic": ["remove infected lower leaves", "mulch to stop soil splash", "rotate"],
    "chemical": ["mancozeb or chlorothalonil at first sign, 7-10 days", "dose: verify with an agriculture officer"],
    "prevention": ["stake plants", "avoid overhead water", "clean up debris"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Tomato___Spider_mites Two-spotted_spider_mite": {
    "crop": "Tomato", "disease": "Two-spotted spider mite",
    "symptoms": ["stippled yellow speckling on leaves", "fine webbing on underside", "leaves dry and drop in hot weather"],
    "organic": ["predatory mites (biological control)", "strong water spray to dislodge", "neem oil 2%"],
    "chemical": ["sulphur or abamectin — rotate to avoid resistance", "dose: verify with an agriculture officer"],
    "prevention": ["avoid dusty conditions", "maintain humidity", "inspect undersides weekly"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Tomato___Target_Spot": {
    "crop": "Tomato", "disease": "Target spot",
    "symptoms": ["small dark spots with concentric target rings", "spots on leaves and fruit", "yellowing around lesions"],
    "organic": ["remove infected foliage", "avoid overhead irrigation", "rotate with non-solanaceous"],
    "chemical": ["mancozeb or chlorothalonil preventive", "dose: verify with an agriculture officer"],
    "prevention": ["spacing for airflow", "clean debris", "drip irrigation"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Tomato___Tomato_Yellow_Leaf_Curl_Virus": {
    "crop": "Tomato", "disease": "TYLCV",
    "symptoms": ["upward curling and yellowing of young leaves", "stunted bushy plants", "vector: whitefly"],
    "organic": ["no cure — remove infected plants", "whitefly control: yellow sticky traps, neem oil", "use resistant cultivars"],
    "chemical": ["whitefly control only (not a cure)", "dose: verify with an agriculture officer"],
    "prevention": ["netting in nurseries", "remove weeds (whitefly hosts)", "stagger planting"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Tomato___Tomato_mosaic_virus": {
    "crop": "Tomato", "disease": "Tomato mosaic virus (ToMV)",
    "symptoms": ["mosaic mottling of light/dark green", "fern-leaf distortion", "fruit uneven ripening"],
    "organic": ["no cure — remove infected plants", "sanitise hands/tools after handling", "use virus-free seed"],
    "chemical": ["no chemical control — prevention only", "dose: verify with an agriculture officer"],
    "prevention": ["wash tools in 10% bleach", "control aphids", "remove weed hosts"],
    "source": ICAR, "reviewed": REVIEWED,
  },
  "Tomato___healthy": {
    "crop": "Tomato", "disease": "Healthy",
    "symptoms": ["no disease signs", "dark green leaves, upright growth"],
    "organic": ["stake and prune suckers", "compost at planting"],
    "chemical": [], "prevention": ["full sun", "even moisture", "rotation"],
    "source": ICAR, "reviewed": REVIEWED,
  },
}


def main() -> None:
    # Read advisory config to determine output path
    from configs import load_config
    cfg = load_config("advice")
    out = Path(cfg["knowledge_json"])
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        json.dump(KB, fh, ensure_ascii=False, indent=2)
    print(f"wrote {len(KB)} entries -> {out}")


if __name__ == "__main__":
    main()
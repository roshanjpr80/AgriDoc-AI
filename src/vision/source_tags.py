"""Source-tag normalisation for PlantVillage filenames.

Filenames look like ``00075aa8-d81a-4184-8541-b692b78d398a___RS_HL 3335.JPG``.
The ``___<source> <id>`` suffix is the source tag, but it is noisy:

- ``RS_HL 3335`` and ``RS_HL 3334`` are the *same* source (the trailing
  number is a per-image id, not part of the source name).
- ``RS_HL 3335 copy`` is a duplicate copy of the same source.
- ``RS_NLB `` (trailing space) and ``RS_NLB`` are the same source.
- ``Rutg._Bact.S`` and ``Rut._Bact.S`` are the same research station
  (Rutgers) with a typo in the tag.

Normalising is not cosmetic: without it a group-by-source split treats every
image as its own group and collapses to a random split, which leaks
same-lab, same-camera photos into validation and overstates accuracy.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

# Explicit aliases: raw tag -> canonical source. Covers typos and abbreviated
# station names that are clearly the same research group. Verified by hand
# against the tag list (see ``print_aliases`` below).
ALIASES: Dict[str, str] = {
    "Rutg._Bact.S": "Rutgers_Bacterial_Spot",
    "Rut._Bact.S": "Rutgers_Bacterial_Spot",
    "Rutg._HL": "Rutgers_HLB",
    "R.S_HL": "RS_HL",
    "R.S_HL": "RS_HL",
    "RS_NLB ": "RS_NLB",
    "GHLB_PS Leaf": "GHLB_PS",
    "GHLB Leaf": "GHLB",
    "UF.GRC_BS_Lab Leaf": "UF_GRC_BS",
    "UF.GRC_YLCV_Lab": "UF_GRC_YLCV",
    "UF.Citrus_HLB_Lab": "UF_Citrus_HLB",
    "GH_HL Leaf": "GH_HL",
    "Mt.N.V_HL": "MtN_V_HL",
}

# Trailing junk to strip from a raw tag, in order.
_TRAILING_RE = re.compile(r"\s*\d+\s*$")          # trailing " 3335"
_COPY_RE = re.compile(r"\s+copy\s*$", re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_source(raw: str) -> str:
    """Map a raw filename source tag to a canonical source name.

    Steps: strip trailing " copy", strip trailing numeric id, collapse
    whitespace, apply explicit aliases, lowercase for stability.
    """
    tag = _COPY_RE.sub("", raw).strip()
    tag = _TRAILING_RE.sub("", tag).strip()
    tag = _WHITESPACE_RE.sub(" ", tag).strip()
    tag = ALIASES.get(tag, tag)
    return tag.lower()


def split_source_and_id(filename: str) -> Tuple[str, str]:
    """Return (canonical source, original raw tag) for a filename."""
    m = re.search(r"___(.+?)\s+\S+\.(?:jpg|jpeg|png)$", filename, re.IGNORECASE)
    if not m:
        return "UNTAGGED", "UNTAGGED"
    raw = m.group(1)
    return normalize_source(raw), raw


def print_aliases() -> None:
    """Show which raw tags collapse to each canonical source."""
    import os
    from collections import defaultdict

    root = "agridoc/data/plantvillage/color"
    groups: Dict[str, List[str]] = defaultdict(list)
    for cls in sorted(os.listdir(root)):
        p = os.path.join(root, cls)
        if not os.path.isdir(p):
            continue
        for f in os.listdir(p):
            m = re.search(r"___(.+?)\s+\S+\.(?:jpg|jpeg|png)$", f, re.IGNORECASE)
            if m:
                groups[normalize_source(m.group(1))].append(m.group(1))
    multi = {k: sorted(set(v)) for k, v in groups.items() if len(set(v)) > 1}
    print(f"canonical sources: {len(groups)}")
    print(f"sources that needed aliasing (raw -> canonical): {len(multi)}")
    for canon, raws in sorted(multi.items()):
        print(f"  {canon!r}: {raws}")
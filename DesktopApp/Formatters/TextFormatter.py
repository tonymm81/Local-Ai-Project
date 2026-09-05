# TextFormatter.py in version 112
import re
from datetime import datetime
from typing import List, Dict, Tuple


def format_for_ui(text: str) -> str:
    if not text:
        return ""

    # Lisää rivinvaihdon välimerkin jälkeen, jos sitä seuraa välilyönti.
    # Ei käytetä lookbehindejä, joten ei tule PatternErroria.
    # Tämä on yksinkertainen ja toimii hyvin suurimmassa osassa tekstejä.
    pattern = r'([.!?;:])\s+'
    return re.sub(pattern, r'\1\n\n', text)
"""Measure dialogue text including dimmed visited rows and remember fingerprints."""

from dataclasses import dataclass

import cv2


def text_band_lengths(frame, icons):
    """Return label widths in icon-height units, including dimmed visited text."""
    lengths = []
    height, width = frame.shape[:2]
    for icon in icons:
        unit = icon.height
        left = min(width, icon.x + icon.width + max(1, round(unit * 0.12)))
        top = max(0, icon.y - round(unit * 0.2))
        bottom = min(height, icon.y + unit + round(unit * 0.2))
        right = min(width, round(width * 0.98))
        if left >= right or top >= bottom:
            return None
        hsv = cv2.cvtColor(frame[top:bottom, left:right, :3], cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, (0, 0, 110), (179, 80, 255))
        _, _, stats, _ = cv2.connectedComponentsWithStats(mask)
        intervals = sorted(
            (int(x), int(x + w))
            for x, _, w, h, area in stats[1:]
            if unit * 0.3 <= h <= unit * 1.5
            and w >= max(1, unit * 0.06)
            and area >= max(2, unit * unit * 0.005)
        )
        if not intervals or intervals[0][0] > unit * 2.5:
            return None
        start, end = intervals[0]
        for x, to_x in intervals[1:]:
            if x - end > unit * 0.8:
                break
            end = max(end, to_x)
        lengths.append((end - start) / unit)
    return tuple(lengths)


def dimmed_text_rows(frame, icons):
    """True for gray visited labels, False for bright labels, None when unreadable.

    Inspect the leading text glyphs instead of the bubble or highlighted border.
    Require a connected character shape at the lower brightness threshold before
    interpreting missing bright glyphs as a dimmed (already chosen) response.
    """
    height, width = frame.shape[:2]
    statuses = []
    for icon in icons:
        unit = icon.height
        left = min(width, icon.x + icon.width + max(1, round(unit * 0.12)))
        top = max(0, icon.y - round(unit * 0.2))
        bottom = min(height, icon.y + unit + round(unit * 0.2))
        right = min(width, left + max(1, round(unit * 5)))
        if left >= right or top >= bottom:
            return None
        hsv = cv2.cvtColor(frame[top:bottom, left:right, :3], cv2.COLOR_BGR2HSV)

        def glyphs(low_value):
            """Find character-sized gray/white components, excluding image noise."""
            mask = cv2.inRange(hsv, (0, 0, low_value), (179, 80, 255))
            _, _, stats, _ = cv2.connectedComponentsWithStats(mask)
            return sorted(
                (int(x), int(x + w))
                for x, _, w, h, area in stats[1:]
                if unit * 0.3 <= h <= unit * 1.5
                and w >= max(1, unit * 0.06)
                and area >= max(2, unit * unit * 0.005)
            )

        low_glyphs = glyphs(110)
        if not low_glyphs or low_glyphs[0][0] > unit * 2.5:
            return None
        statuses.append(not bool(glyphs(190)))
    return tuple(statuses)


def highlighted_choice_index(frame, icons):
    """Locate the selected option's white F keycap; ignore ambiguous matches.

    The prompt is a square about one icon high, 4-5 icon-heights to the left
    of the bubble. Shape/area checks reject bright background scenery.
    """
    height, width = frame.shape[:2]
    candidates = []
    for index, icon in enumerate(icons):
        unit = icon.height
        x0 = max(0, round(icon.x - unit * 6.1))
        x1 = min(width, round(icon.x - unit * 2.3))
        y0 = max(0, round(icon.y - unit * 0.65))
        y1 = min(height, round(icon.y + unit * 1.6))
        if x0 >= x1 or y0 >= y1:
            continue
        hsv = cv2.cvtColor(frame[y0:y1, x0:x1, :3], cv2.COLOR_BGR2HSV)
        white = cv2.inRange(hsv, (0, 0, 220), (179, 100, 255))
        _, _, stats, _ = cv2.connectedComponentsWithStats(white)
        if any(
            unit * 0.65 <= w <= unit * 1.6
            and unit * 0.8 <= h <= unit * 1.7
            and area >= unit * unit * 0.6
            for _, _, w, h, area in stats[1:]
        ):
            candidates.append(index)
    return candidates[0] if len(candidates) == 1 else None


@dataclass(eq=False)
class ChoiceRecord:
    """One option-count/text-length fingerprint and its next selection index."""

    lengths: tuple[float, ...]
    next_index: int = 0


@dataclass
class ChoiceDecision:
    """A proposed selection that is saved only after successful input."""

    record: ChoiceRecord
    lengths: tuple[float, ...]
    index: int


class ChoiceMemory:
    """Keep progress per approximate fingerprint and debounce a visible menu."""

    def __init__(self):
        """Start without any remembered choices or active menu."""
        self.records = []
        self.active = None

    def prepare(self, lengths):
        """Choose a saved fingerprint's next row, or row zero for a new one."""
        if not lengths or any(length <= 0 for length in lengths):
            return None
        matches = [
            record for record in self.records
            if len(record.lengths) == len(lengths)
            and all(abs(a - b) <= max(0.3, 0.05 * max(a, b))
                    for a, b in zip(record.lengths, lengths))
        ]
        record = min(matches, key=lambda item: sum(
            abs(a - b) for a, b in zip(item.lengths, lengths)
        )) if matches else ChoiceRecord(tuple(lengths))
        if record is self.active:
            return None
        return ChoiceDecision(record, tuple(lengths), record.next_index)

    def commit(self, decision):
        """Advance just this fingerprint after a successful selection."""
        record = decision.record
        if record not in self.records:
            self.records.append(record)
        record.lengths = decision.lengths
        record.next_index = (decision.index + 1) % len(decision.lengths)
        self.active = record

    def hide(self):
        """Allow selection again when a menu disappears; retain all progress."""
        self.active = None

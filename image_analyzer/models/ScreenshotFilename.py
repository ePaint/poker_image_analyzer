import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

FILENAME_PATTERN = re.compile(
    r"^(\d{4}-\d{2}-\d{2})_ (\d{2}-\d{2})_(AM|PM)_\$(\d+(?:\.\d+)?)_\$(\d+(?:\.\d+)?)_#(\d+)\.png$"
)


@dataclass(frozen=True)
class ScreenshotFilename:
    date: str
    time: str
    period: str
    small_blind: float
    big_blind: float
    table_id: int

    @classmethod
    def parse(cls, filename: str | Path) -> "ScreenshotFilename | None":
        """Parse filename string, return None if invalid."""
        name = Path(filename).name if isinstance(filename, Path) else filename
        match = FILENAME_PATTERN.match(name)
        if not match:
            return None
        return cls(
            date=match.group(1),
            time=match.group(2),
            period=match.group(3),
            small_blind=float(match.group(4)),
            big_blind=float(match.group(5)),
            table_id=int(match.group(6)),
        )

    @classmethod
    def is_valid(cls, filename: str | Path) -> bool:
        """Check if filename matches expected pattern."""
        return cls.parse(filename) is not None

    @property
    def stakes(self) -> str:
        """Return stakes as '$2/$5' format."""
        def fmt(val: float) -> str:
            if val == int(val):
                return str(int(val))
            return f"{val:.2f}"
        return f"${fmt(self.small_blind)}/${fmt(self.big_blind)}"

    @property
    def datetime(self) -> datetime:
        """Parse date and time into datetime object."""
        time_str = self.time.replace("-", ":")
        dt_str = f"{self.date} {time_str} {self.period}"
        return datetime.strptime(dt_str, "%Y-%m-%d %I:%M %p")

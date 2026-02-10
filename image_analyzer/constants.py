import tomllib
from pathlib import Path

from image_analyzer import PlayerRegion

_CORRECTIONS_PATH = Path(__file__).parent / "corrections.toml"


def load_corrections() -> dict[str, str]:
    """Load OCR corrections from TOML file."""
    if not _CORRECTIONS_PATH.exists():
        return {}
    with open(_CORRECTIONS_PATH, "rb") as f:
        data = tomllib.load(f)
    return data.get("corrections", {})


FEWSHOT_ZERO_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAANIAAAAmCAIAAAA++FIaAAACPElEQVR4nO2c63KEIAyFSafv/8rp"
    "dHfGUiUQkMuRPd+vjhsxJkeiQSshBFUNESISsHk7LCInzz8KgU/TiThZctr0uJNJsoccZYtcxPzJ"
    "bLUnoDJ9p9yqA0l7VY2FUqwhutelXlepwu4cFbmjpUc0/2qKPab+F+sn8HvK44Yuhvv4O2lmzUAZ"
    "gzz57DpVUjuTOc2kSbtWBPyWmR2rLsJavkYMepxk2z2WvsgMO5qbB7J2zwyr9UfsO5o1wqCYD5Hd"
    "454Gqg6aN57jv5aOAv5QBSc7f2GNf0rWgqLBBG7eGDiRF7X2V8IsoGX3DkQmHHG8TmbHxraAdtFH"
    "0f82rDtLp8QRnmCwZOeZzJDLx3z/JXWx4YMlu1X4s4Us+gcp73u1A6Sa4qogvvJAZzuEwN2Z2Kb5"
    "r/Cz7xrZre3A9QXTbTXanBn74pYdiixmtjzArlzJpc5WrfAmlccGCinjWU/76Hu7hz7k46dTjJZk"
    "0dXrXpOTMrzIWr1cwCw6Sb4TheaP2kVzUBN7hyfZtVy7uzgi8898yD5TduXJoO/rIUN5yg0MqOyQ"
    "r1SQjomODJG1ztsLrlI05mN7ZOSZYs12ntI2LfENB7rjvz6nlO8mO/D4NiveKUE1OsB+sXoC5Qzm"
    "0DoOXWSLn1OA0+C/OjJ9aj81lIXiLvFL7SNiDjfbQQnrZp3tZS/13V2oMF5Z9uVY0abtfxU0f++U"
    "WdO0xuzrv/o+NmveyzmPnuzB5UsIIYQQQgghhBBCCCGEEEJIQOcH6Bd6X4KAVyYAAAAASUVORK5C"
    "YII="
)
FEWSHOT_ZERO_NAME = "H0T M0USE!"

FEWSHOT_I_VS_L_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAANIAAAAmCAIAAAA++FIaAAABaUlEQVR4nO2a0a6DIBAFoen//zI3"
    "rWljERdsBbl7Zt4kLWicHFghBAAAAADwQgyuSSk9HjLGxvZzx81oGS69/tjv3mbgFgTIJHhfFuU4"
    "fbhq+0J6EjS4X30D3qi6FT9jTEc1ubTbY8BEFp+sW5KkZ1raLa88e/HFxn6jG2MlVQWda3chLVrH"
    "mpdecf60xcJw22jUj3s/Xi6N/o25NTaEn28RSbvWWW9bDq9bMmN8S/M70tpVl1ZnxY/sGk5Ru700"
    "2lKcgg9hzJtZh5Eg1Plu1+llG92ScKJp9yM6C/zxoN0x2jMMUw3QrqMlS0nLLsUWtBthJMknWlIc"
    "gmqgN6TdyZkkdX7pa9Cui4uYZ6Oi3XgPMM9ARbtL6H2M+f+Cdn1LTjbHiqDdMQvXLUVH+VbSgrR2"
    "nbzZ64EDUW88bzVy9GNaPKdddUKEq/CsHfXjtPjcHEO4yfGcdjAtEtqxsINBsCUPAAAAABAG8AcY"
    "UatG7SL5fwAAAABJRU5ErkJggg=="
)
FEWSHOT_I_VS_L_NAME = "jivr31"

FEWSHOT_ZERO_ALT_B64 = (
    "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"
    "3ARmAT7QiwAAAABJRU5ErkJggg=="
)
FEWSHOT_ZERO_ALT_NAME = "H0T M0USE!"

DEFAULT_REGIONS = (
    PlayerRegion("top", 347, 152),
    PlayerRegion("top_left", 29, 234),
    PlayerRegion("top_right", 666, 234),
    PlayerRegion("bottom_left", 29, 459),
    PlayerRegion("bottom", 347, 565),
    PlayerRegion("bottom_right", 666, 459),
)

GGPOKER_DETECTION_PIXEL = (702, 64)
GGPOKER_COLOR_BGR = (6, 15, 219)
NATURAL8_DETECTION_PIXEL = (880, 72)
NATURAL8_COLOR_BGR = (145, 39, 140)

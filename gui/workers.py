"""QThread workers for background processing."""
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PySide6.QtCore import QThread, Signal

import cv2

from image_analyzer import (
    analyze_image,
    detect_table_type,
    ScreenshotFilename,
    DEFAULT_REGIONS,
)
from hand_history import (
    parse_file,
    convert_hands,
    write_converted_file,
    write_skipped_file,
    position_to_seat,
    load_seat_mapping,
)


class ScreenshotWorker(QThread):
    """Worker thread for processing screenshots."""

    progress = Signal(int, int, str)  # current, total, filename
    result = Signal(str, str, int, int)  # hand_number, filename, position_count, seat_count
    error = Signal(str, str)  # filename, message
    finished_processing = Signal(object)  # hand_data (use object to avoid dict serialization issues)

    MAX_RETRIES = 5
    BASE_BACKOFF = 1.0  # seconds

    def __init__(
        self,
        screenshots_dir: Path,
        api_key: str | None = None,
        parallel_calls: int = 5,
        rate_limit_per_minute: int = 50,
        parent=None,
    ):
        super().__init__(parent)
        self._screenshots_dir = screenshots_dir
        self._api_key = api_key
        self._parallel_calls = parallel_calls
        self._rate_limit_per_minute = rate_limit_per_minute
        self._cancelled = False
        self._rate_lock = threading.Lock()
        self._last_request_time = 0.0

    def cancel(self) -> None:
        self._cancelled = True

    def _wait_for_rate_limit(self) -> None:
        """Wait if needed to stay under the rate limit."""
        min_interval = 60.0 / self._rate_limit_per_minute
        with self._rate_lock:
            now = time.time()
            elapsed = now - self._last_request_time
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            self._last_request_time = time.time()

    def _call_with_backoff(self, image, regions) -> dict[str, str]:
        """Call analyze_image with exponential backoff on rate limit errors."""
        import anthropic

        for attempt in range(self.MAX_RETRIES):
            self._wait_for_rate_limit()
            try:
                return analyze_image(image, regions, self._api_key)
            except anthropic.RateLimitError:
                if attempt == self.MAX_RETRIES - 1:
                    raise
                backoff = self.BASE_BACKOFF * (2 ** attempt)
                time.sleep(backoff)

    def _process_screenshot(
        self, screenshot_path: Path, seat_mapping: dict
    ) -> tuple[Path, str | None, str | None, dict | None, dict | None, str | None]:
        """Process single screenshot in thread pool.

        Returns: (path, hand_number, table_type, position_names, seat_names, error)
        """
        try:
            parsed = ScreenshotFilename.parse(screenshot_path)
            if not parsed:
                return (screenshot_path, None, None, None, None, "Invalid filename format")

            hand_number = f"OM{parsed.table_id}"

            image = cv2.imread(str(screenshot_path))
            if image is None:
                return (screenshot_path, hand_number, None, None, None, "Could not load image")

            regions = detect_table_type(image)
            table_type = "ggpoker" if regions == DEFAULT_REGIONS else "natural8"

            position_names = self._call_with_backoff(image, regions)
            seat_names = position_to_seat(position_names, seat_mapping)

            return (screenshot_path, hand_number, table_type, position_names, seat_names, None)
        except Exception as e:
            return (screenshot_path, None, None, None, None, str(e))

    def run(self) -> None:
        hand_data: dict[str, dict[int, str]] = {}
        ocr_results: list[dict] = []
        ocr_errors: list[dict] = []
        seat_mapping = load_seat_mapping()

        png_files = list(self._screenshots_dir.glob("*.png"))
        valid_files = [f for f in png_files if ScreenshotFilename.is_valid(f.name)]
        total = len(valid_files)
        processed = 0

        with ThreadPoolExecutor(max_workers=self._parallel_calls) as executor:
            futures = {
                executor.submit(self._process_screenshot, f, seat_mapping): f
                for f in valid_files
            }

            for future in as_completed(futures):
                if self._cancelled:
                    executor.shutdown(wait=False, cancel_futures=True)
                    return

                processed += 1
                path, hand_number, table_type, position_names, seat_names, error = future.result()

                self.progress.emit(processed, total, path.name)

                if error:
                    self.error.emit(path.name, error)
                    ocr_errors.append({"filename": path.name, "error": error})
                else:
                    hand_data[hand_number] = seat_names
                    ocr_results.append({
                        "filename": path.name,
                        "hand_number": hand_number,
                        "table_type": table_type,
                        "position_names": position_names,
                        "seat_names": seat_names,
                    })
                    self.result.emit(hand_number, path.name, len(position_names), len(seat_names))

        self.finished_processing.emit((hand_data, ocr_results, ocr_errors))


class ConversionWorker(QThread):
    """Worker thread for converting hand histories."""

    progress = Signal(int, int, str)  # current, total, filename
    hand_converted = Signal(str, int)  # hand_number, player_count
    hand_skipped = Signal(str, str)  # hand_number, reason
    finished_processing = Signal(int, int)  # success_count, failed_count

    def __init__(
        self,
        hands_dir: Path,
        hand_data: dict[str, dict[int, str]],
        output_dir: Path,
        parent=None,
    ):
        super().__init__(parent)
        self._hands_dir = hands_dir
        self._hand_data = hand_data
        self._output_dir = output_dir
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        converted_dir = self._output_dir / "converted"
        skipped_dir = self._output_dir / "skipped"

        txt_files = list(self._hands_dir.glob("*.txt"))
        total = len(txt_files)
        total_success = 0
        total_failed = 0

        for i, hand_file in enumerate(txt_files):
            if self._cancelled:
                return

            self.progress.emit(i + 1, total, hand_file.name)

            try:
                hands = parse_file(hand_file)
                results = convert_hands(hands, self._hand_data)

                successful = [r for r in results if r.success]
                failed = [r for r in results if not r.success]

                if successful:
                    output_path = converted_dir / hand_file.name
                    write_converted_file(results, output_path)

                if failed:
                    output_path = skipped_dir / hand_file.name
                    write_skipped_file(results, output_path)

                for r in successful:
                    self.hand_converted.emit(r.hand_number, len(r.seat_names))

                for r in failed:
                    self.hand_skipped.emit(r.hand_number, r.error or "Unknown error")

                total_success += len(successful)
                total_failed += len(failed)

            except Exception as e:
                self.hand_skipped.emit(hand_file.name, str(e))

        self.finished_processing.emit(total_success, total_failed)

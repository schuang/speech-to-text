from __future__ import annotations

import unittest

from speech_to_text_app.recording_waveform import (
    LevelNormalizer,
    ScrollingWaveform,
    WaveformHistory,
    waveform_bar_geometry,
)


class _FakeCanvas:
    def __init__(self) -> None:
        self.created_lines = 0
        self.coordinates: dict[int, tuple[float, ...]] = {}
        self.options: dict[int, dict[str, object]] = {}

    def create_line(self, *coordinates: float, **options: object) -> int:
        self.created_lines += 1
        item_id = self.created_lines
        self.coordinates[item_id] = coordinates
        self.options[item_id] = dict(options)
        return item_id

    def coords(self, item_id: int, *coordinates: float) -> None:
        self.coordinates[item_id] = coordinates

    def itemconfigure(self, item_id: int, **options: object) -> None:
        self.options[item_id].update(options)

    def after(self, _milliseconds: int, _callback: object) -> str:
        return "after-id"

    def after_cancel(self, _animation_id: str) -> None:
        return None

    def tag_raise(self, _tag: str) -> None:
        return None


class LevelNormalizerTests(unittest.TestCase):
    def test_suppresses_noise_floor_and_clamps_input(self) -> None:
        normalizer = LevelNormalizer()

        self.assertEqual(normalizer.update(0.04), 0.0)
        self.assertGreater(normalizer.update(2.0), 0.0)
        self.assertLessEqual(normalizer.level, 1.0)

    def test_attack_is_faster_than_release(self) -> None:
        normalizer = LevelNormalizer()
        attacked = normalizer.update(1.0)
        released = normalizer.update(0.0)

        self.assertGreater(attacked, 0.5)
        self.assertGreater(released, attacked * 0.5)
        self.assertLess(released, attacked)

    def test_reset_clears_smoothed_level(self) -> None:
        normalizer = LevelNormalizer()
        normalizer.update(1.0)

        normalizer.reset()

        self.assertEqual(normalizer.level, 0.0)


class WaveformHistoryTests(unittest.TestCase):
    def test_history_has_fixed_length_and_newest_sample_is_on_the_right(self) -> None:
        history = WaveformHistory(4)

        history.append(0.25)
        history.append(0.75)

        self.assertEqual(history.samples, (0.0, 0.0, 0.25, 0.75))

    def test_history_clamps_samples(self) -> None:
        history = WaveformHistory(3)

        history.append(-1.0)
        history.append(2.0)

        self.assertEqual(history.samples[-2:], (0.0, 1.0))


class WaveformGeometryTests(unittest.TestCase):
    def test_newest_sample_starts_at_right_edge(self) -> None:
        bars = waveform_bar_geometry(
            (0.1, 0.2, 0.3),
            left=10,
            right=30,
            phase=0.0,
        )

        self.assertEqual(bars[-1], (30.0, 0.3))

    def test_phase_moves_waveform_from_right_to_left(self) -> None:
        initial = waveform_bar_geometry(
            (0.1, 0.2, 0.3),
            left=10,
            right=30,
            phase=0.0,
        )
        shifted = waveform_bar_geometry(
            (0.1, 0.2, 0.3),
            left=10,
            right=30,
            phase=0.5,
        )

        self.assertEqual(shifted[-1][0], initial[-1][0] - 5.0)


class ScrollingWaveformRenderingTests(unittest.TestCase):
    def test_canvas_lines_are_created_once_and_reused(self) -> None:
        canvas = _FakeCanvas()
        waveform = ScrollingWaveform(
            canvas,  # type: ignore[arg-type]
            left=0,
            top=0,
            right=100,
            bottom=20,
            sample_count=4,
        )

        waveform.update_level(0.5)
        initial_line_count = canvas.created_lines
        waveform.update_level(0.8)
        waveform.draw()

        self.assertEqual(initial_line_count, 5)
        self.assertEqual(canvas.created_lines, initial_line_count)

    def test_hide_reuses_and_hides_existing_lines(self) -> None:
        canvas = _FakeCanvas()
        waveform = ScrollingWaveform(
            canvas,  # type: ignore[arg-type]
            left=0,
            top=0,
            right=100,
            bottom=20,
            sample_count=3,
        )
        waveform.draw()

        waveform.hide()

        self.assertEqual(canvas.created_lines, 4)
        self.assertTrue(
            all(options.get("state") == "hidden" for options in canvas.options.values())
        )


if __name__ == "__main__":
    unittest.main()

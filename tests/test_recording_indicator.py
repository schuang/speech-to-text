from __future__ import annotations

import unittest

from speech_to_text_app.recording_indicator import compute_indicator_position


class ComputeIndicatorPositionTests(unittest.TestCase):
    def test_prefers_right_side_of_parent_window(self) -> None:
        x, y = compute_indicator_position(
            screen_x=0,
            screen_y=0,
            screen_width=1920,
            screen_height=1080,
            parent_x=240,
            parent_y=180,
            parent_width=460,
            parent_height=560,
            indicator_width=260,
            indicator_height=58,
        )

        self.assertEqual((x, y), (712, 180))

    def test_falls_back_to_left_when_right_side_would_overflow(self) -> None:
        x, y = compute_indicator_position(
            screen_x=0,
            screen_y=0,
            screen_width=1920,
            screen_height=1080,
            parent_x=1500,
            parent_y=220,
            parent_width=460,
            parent_height=560,
            indicator_width=260,
            indicator_height=58,
        )

        self.assertEqual((x, y), (1228, 220))

    def test_clamps_when_no_candidate_fits_inside_screen(self) -> None:
        x, y = compute_indicator_position(
            screen_x=0,
            screen_y=0,
            screen_width=420,
            screen_height=120,
            parent_x=120,
            parent_y=70,
            parent_width=320,
            parent_height=80,
            indicator_width=260,
            indicator_height=58,
        )

        self.assertEqual((x, y), (144, 46))


if __name__ == "__main__":
    unittest.main()

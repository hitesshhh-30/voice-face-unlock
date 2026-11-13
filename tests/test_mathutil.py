import numpy as np

from voice_face_unlock.mathutil import (
    BlinkDetector, best_match, cosine, eye_aspect_ratio, phrase_matches,
)

VARIANTS = ["hey the byte has landed", "hey the bite has landed"]


def test_cosine_identical_and_opposite():
    assert cosine([1, 0], [1, 0]) == 1.0
    assert cosine([1, 0], [-1, 0]) == -1.0
    assert cosine([0, 0], [1, 0]) == 0.0


def test_best_match_picks_highest_and_handles_empty():
    enrolled = np.array([[1, 0], [0, 1]])
    assert best_match(np.array([0, 1]), enrolled) == 1.0
    assert best_match(np.array([0, 1]), np.empty((0, 2))) == 0.0


def test_phrase_matches_exact_and_inside_longer_speech():
    assert phrase_matches("hey the bite has landed", VARIANTS)
    assert phrase_matches("uh hey the byte has landed okay", VARIANTS)
    assert phrase_matches("Hey, the BYTE has landed!", VARIANTS)


def test_phrase_rejects_partial_or_other_speech():
    assert not phrase_matches("the byte has", VARIANTS)
    assert not phrase_matches("hey they bite has landed", VARIANTS)
    assert not phrase_matches("[unk]", VARIANTS)
    assert not phrase_matches("", VARIANTS)


def test_eye_aspect_ratio_open_vs_closed():
    open_eye = [(0, 0), (1, 1), (2, 1), (3, 0), (2, -1), (1, -1)]
    closed = [(0, 0), (1, 0.1), (2, 0.1), (3, 0), (2, -0.1), (1, -0.1)]
    assert eye_aspect_ratio(open_eye) > 0.6
    assert eye_aspect_ratio(closed) < 0.1


def test_blink_needs_open_closed_open():
    b = BlinkDetector(closed=0.18, open_=0.24)
    assert not b.update(0.30)   # open
    assert not b.update(0.10)   # closed
    assert b.update(0.30)       # reopened -> blink


def test_blink_static_photo_never_blinks():
    b = BlinkDetector(closed=0.18, open_=0.24)
    assert not any(b.update(0.30) for _ in range(100))


def test_blink_eyes_closed_whole_time_is_not_a_blink():
    b = BlinkDetector(closed=0.18, open_=0.24)
    assert not any(b.update(0.05) for _ in range(100))

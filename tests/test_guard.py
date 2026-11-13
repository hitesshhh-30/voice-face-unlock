from voice_face_unlock.guard import Guard


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_cooldown_after_max_failures_then_expires():
    c = Clock()
    g = Guard(max_failures=3, cooldown_s=60, clock=c)
    assert not g.fail() and not g.fail()
    assert not g.blocked()
    assert g.fail()
    assert g.blocked()
    c.t = 59
    assert g.blocked()
    c.t = 61
    assert not g.blocked()


def test_success_resets_failure_count():
    g = Guard(max_failures=3, cooldown_s=60, clock=Clock())
    g.fail(); g.fail(); g.success()
    assert not g.fail()
    assert not g.blocked()

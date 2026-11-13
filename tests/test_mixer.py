import numpy as np

from voice_face_unlock.mixer import duck_envelope, mix, read_wav, write_wav


def test_duck_envelope_dips_only_under_voice():
    g = duck_envelope(10_000, 4000, 6000, 1000, 0.3, fade_s=0.5)
    assert g[0] == 1.0 and g[-1] == 1.0
    assert np.isclose(g[5000], 0.3)
    assert 0.3 < g[3700] < 1.0


def test_mix_places_voice_at_offset_and_ducks(tmp_path):
    rate = 8000
    music = np.full((rate * 4, 2), 0.5, dtype=np.float32)       # 4 s stereo
    voice = np.full((rate * 1, 1), 0.2, dtype=np.float32)       # 1 s mono at 16k
    write_wav(tmp_path / "m.wav", music, rate)
    write_wav(tmp_path / "v.wav", np.repeat(voice, 2, axis=0), rate * 2)
    length = mix(tmp_path / "m.wav", tmp_path / "v.wav", 2.0, tmp_path / "o.wav", duck=0.3)
    out, r = read_wav(tmp_path / "o.wav")
    assert r == rate and out.shape[1] == 2 and abs(length - 4.0) < 0.01
    assert abs(out[rate // 2, 0] - 0.5) < 0.01                  # before voice: full music
    assert abs(out[int(rate * 2.5), 0] - (0.15 + 0.2)) < 0.01   # under voice: ducked + voice


def test_mix_extends_when_voice_runs_past_music(tmp_path):
    rate = 8000
    write_wav(tmp_path / "m.wav", np.zeros((rate, 2), np.float32), rate)
    write_wav(tmp_path / "v.wav", np.full((rate, 1), 0.1, np.float32), rate)
    assert abs(mix(tmp_path / "m.wav", tmp_path / "v.wav", 0.5, tmp_path / "o.wav") - 1.5) < 0.01

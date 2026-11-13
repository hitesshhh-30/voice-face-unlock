"""Phrase spotting (Vosk) + speaker check (sherpa-onnx speaker embeddings)."""
from __future__ import annotations

import json
from collections.abc import Callable, Iterator

import numpy as np
import sherpa_onnx
import vosk

from .audio import RATE, Mic, to_float
from .config import Config
from .mathutil import best_match, phrase_matches

MAX_UTTERANCE_S = 6


class PhraseListener:
    """Listens on the mic and yields the raw audio of each utterance that contains the phrase."""

    def __init__(self, cfg: Config):
        vosk.SetLogLevel(-1)
        self.cfg = cfg
        self.model = vosk.Model(str(cfg.models / "vosk"))
        grammar = sorted(set(cfg.phrase_variants)) + ["[unk]"]
        self.grammar = json.dumps(grammar)

    def utterances(self, mic: Mic, keep_going: Callable[[], bool] = lambda: True) -> Iterator[tuple[str, bytes]]:
        """Yields (heard_text, pcm) for every finished utterance; caller checks the phrase.
        Stops when keep_going() returns False (checked about once a second)."""
        rec = vosk.KaldiRecognizer(self.model, RATE, self.grammar)
        buf = bytearray()
        max_bytes = MAX_UTTERANCE_S * RATE * 2
        n = 0
        while True:
            n += 1
            if n % 4 == 0 and not keep_going():
                return
            chunk = mic.read()
            buf += chunk
            if len(buf) > max_bytes:
                del buf[: len(buf) - max_bytes]
            if rec.AcceptWaveform(chunk):
                text = json.loads(rec.Result()).get("text", "")
                if text and text != "[unk]":
                    yield text, bytes(buf)
                buf.clear()

    def wait_for_phrase(self, mic: Mic, keep_going: Callable[[], bool] = lambda: True) -> bytes | None:
        """Audio of the utterance containing the phrase, or None if keep_going() turned False."""
        for text, pcm in self.utterances(mic, keep_going):
            if phrase_matches(text, self.cfg.phrase_variants):
                return pcm
        return None


class SpeakerCheck:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.extractor = sherpa_onnx.SpeakerEmbeddingExtractor(
            sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(cfg.models / "speaker.onnx"), num_threads=2)
        )
        self.file = cfg.enroll_dir / "voice.npy"

    def embed(self, pcm: bytes) -> np.ndarray:
        stream = self.extractor.create_stream()
        stream.accept_waveform(sample_rate=RATE, waveform=to_float(pcm))
        stream.input_finished()
        return np.array(self.extractor.compute(stream), dtype=np.float32)

    def enrolled(self) -> np.ndarray | None:
        return np.load(self.file) if self.file.exists() else None

    def score(self, pcm: bytes) -> float:
        return best_match(self.embed(pcm), self.enrolled())

    def save(self, embeddings: list[np.ndarray]) -> None:
        self.file.parent.mkdir(parents=True, exist_ok=True)
        np.save(self.file, np.stack(embeddings))

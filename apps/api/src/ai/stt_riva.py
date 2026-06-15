"""NVIDIA Riva gRPC STT wrapper — speech-to-text via Riva gRPC API.

Only used when STT_PROVIDER=riva. Requires riva-client to be installed.
"""
import logging
from typing import Any

import grpc
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import riva.client
import riva.client.proto.riva_asr_pb2 as rasr
import riva.client.proto.riva_asr_pb2_grpc as rasr_srv
import riva.client.proto.riva_audio_pb2 as raudio

from src.config import settings

logger = logging.getLogger(__name__)


class RivaSTTClient:
    """gRPC client for NVIDIA Riva Parakeet Multilingual ASR model."""

    def __init__(self):
        self.server = "grpc.nvcf.nvidia.com:443"
        self.api_key = settings.nvidia_api_key
        self.function_id = "71203149-d3b7-4460-8231-1be2543a1fca"  # Parakeet 1.1b RNNT Multilingual
        
        # Build metadata for gRPC calls
        self.metadata = [
            ("function-id", self.function_id),
            ("authorization", f"Bearer {self.api_key}"),
        ]
        
        # Initialize channel lazily — created once, reused across all chunks
        self._channel = None
        self._stub = None

    @staticmethod
    def _to_seconds(t) -> float:
        """Convert a Riva time value to seconds.

        Riva returns either:
        - google.protobuf.Duration (with .seconds/.nanos fields) — already in seconds
        - int values in **milliseconds** (Riva gRPC convention)
        - float values — assumed to be seconds

        Detection: if it's an int (no decimal point), divide by 1000.
        """
        if hasattr(t, 'seconds'):
            return t.seconds + getattr(t, 'nanos', 0) / 1e9
        if isinstance(t, int):
            return t / 1000.0
        return float(t)

    def _get_stub(self):
        """Create or reuse the gRPC channel and stub.
        
        CRITICAL: Creates channel once with 100MB payload limit to prevent
        segfaults on large audio chunks (15-min WAV ≈ 28MB).
        """
        if self._channel is None:
            # CRITICAL FIX: Increase payload limits to 100MB for 15-min audio chunks
            options = [
                ('grpc.max_send_message_length', 100 * 1024 * 1024),  # 100MB
                ('grpc.max_receive_message_length', 100 * 1024 * 1024),  # 100MB
            ]
            credentials = grpc.ssl_channel_credentials()
            self._channel = grpc.secure_channel(self.server, credentials, options=options)
            self._stub = rasr_srv.RivaSpeechRecognitionStub(self._channel)
            logger.info("Initialized persistent Riva gRPC channel (100MB limit)")
            
        return self._stub

    def _reset_channel(self):
        """Safely close and nullify the channel so _get_stub rebuilds it on retry."""
        if self._channel:
            try:
                self._channel.close()
            except Exception:
                pass
        self._channel = None
        self._stub = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        retry=retry_if_exception_type((grpc.RpcError, ConnectionError, TimeoutError)),
        reraise=True,
    )
    def transcribe_audio(self, audio_bytes: bytes) -> dict[str, Any]:
        """Transcribe audio using NVIDIA Riva Parakeet model via gRPC.

        Args:
            audio_bytes: Raw audio data (16kHz mono WAV)

        Returns:
            Dict with segments and words:
            {
                "segments": [{start, end, text}],
                "words": [{word, start, end, confidence}]
            }
        """
        logger.info(f"Sending audio to Riva gRPC STT ({len(audio_bytes) / (1024*1024):.1f} MB)")

        try:
            stub = self._get_stub()

            # Build recognition config — use "multi" for multilingual auto-detect
            config = rasr.RecognitionConfig(
                encoding=raudio.AudioEncoding.LINEAR_PCM,  # 16-bit PCM
                sample_rate_hertz=16000,  # 16kHz
                audio_channel_count=1,  # Mono
                language_code="multi",  # Multilingual auto-detect (Hindi/Arabic/English)
                max_alternatives=1,
                profanity_filter=False,
                enable_automatic_punctuation=True,
                enable_word_time_offsets=True,  # Required for segment timestamps
            )

            # CRITICAL FIX: Pass bytes directly — NO temp files, NO disk I/O
            request = rasr.RecognizeRequest(config=config, audio=audio_bytes)

            # Make gRPC call with metadata and timeout
            response = stub.Recognize(
                request,
                metadata=self.metadata,
                timeout=300,  # 5 minutes max per chunk
            )

            return self._parse_riva_response(response)

        except grpc.RpcError as e:
            logger.error(f"Riva gRPC error: {e.code()} - {e.details()}. Resetting channel for retry.")
            # Force channel recreation on next retry in case the C++ socket is corrupted
            self._reset_channel()
            raise
        except Exception as e:
            logger.error(f"Riva gRPC STT unexpected failure: {e}")
            raise

    def _parse_riva_response(self, response) -> dict[str, Any]:
        """Parse Riva gRPC response into standardized segment and word format.

        Riva returns results with alternatives and word-level timestamps.
        We extract both segment-level and word-level data for speaker attribution.

        Returns:
            {
                "segments": [{start, end, text}],
                "words": [{word, start, end, confidence}]
            }
        """
        segments = []
        all_words = []

        for result in response.results:
            if not result.alternatives:
                continue

            alternative = result.alternatives[0]
            transcript = alternative.transcript.strip()

            if not transcript:
                continue

            # Extract word-level timestamps if available
            if hasattr(alternative, 'words') and alternative.words:
                # Group words into segments based on pause gaps
                words = alternative.words

                # Debug: log raw timestamp type/range for first few words
                if words:
                    raw_start = words[0].start_time
                    raw_end = words[-1].end_time
                    logger.info(
                        f"Riva word timestamps — type: {type(raw_start).__name__}, "
                        f"first start raw={raw_start}, last end raw={raw_end}, "
                        f"first start seconds={self._to_seconds(raw_start):.3f}, "
                        f"last end seconds={self._to_seconds(raw_end):.3f}"
                    )

                segment_words = []
                # Riva may return Duration proto (.seconds/.nanos) or plain int
                segment_start = self._to_seconds(words[0].start_time)

                for i, word in enumerate(words):
                    segment_words.append(word.word)

                    # Extract word-level data with confidence
                    word_start = self._to_seconds(word.start_time)
                    word_end = self._to_seconds(word.end_time)
                    word_confidence = getattr(word, 'confidence', 0.85)  # Default 0.85 if not available

                    all_words.append({
                        "word": word.word,
                        "start": round(word_start, 3),
                        "end": round(word_end, 3),
                        "confidence": round(word_confidence, 3),
                    })

                    # Check if next word has a large time gap (>1s pause = new segment)
                    if i < len(words) - 1:
                        next_start = self._to_seconds(words[i + 1].start_time)
                        gap = next_start - word_end
                        if gap > 1.0:  # 1 second pause
                            segment_text = " ".join(segment_words)
                            segments.append({
                                "start": segment_start,
                                "end": word_end,
                                "text": segment_text,
                            })
                            segment_words = []
                            segment_start = next_start

                # Add remaining words as final segment
                if segment_words:
                    segment_text = " ".join(segment_words)
                    last_end = self._to_seconds(words[-1].end_time)
                    segments.append({
                        "start": segment_start,
                        "end": last_end,
                        "text": segment_text,
                    })
            else:
                # Fallback: use result-level timestamps
                start_time = getattr(result, 'result_start_time', 0.0)
                end_time = getattr(result, 'result_end_time', 0.0)

                # If no timestamps, estimate based on audio duration
                if start_time == 0 and end_time == 0:
                    # Estimate: assume ~5 words per second
                    word_count = len(transcript.split())
                    end_time = word_count / 5.0

                segments.append({
                    "start": start_time,
                    "end": end_time,
                    "text": transcript,
                })

        # Filter out empty segments
        segments = [s for s in segments if s["text"].strip()]

        logger.info(
            f"STT produced {len(segments)} segments, {len(all_words)} words, "
            f"total duration: {segments[-1]['end']:.1f}s" if segments else "STT produced 0 segments"
        )

        return {
            "segments": segments,
            "words": all_words,
        }


# Singleton instance
riva_stt_client = RivaSTTClient()


def transcribe_audio_riva(audio_bytes: bytes, filename: str = "audio.wav") -> dict[str, Any]:
    """Transcribe audio using NVIDIA Riva gRPC STT.

    Args:
        audio_bytes: Raw audio data (16kHz mono WAV)
        filename: Unused (kept for interface compatibility with Groq)

    Returns:
        Dict with segments and words
    """
    return riva_stt_client.transcribe_audio(audio_bytes)

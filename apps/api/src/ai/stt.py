"""NVIDIA Riva gRPC STT wrapper — speech-to-text via Riva gRPC API."""
import io
import logging
import tempfile
from typing import Any

import riva.client
import riva.client.proto.riva_asr_pb2 as rasr
import riva.client.proto.riva_asr_pb2_grpc as rasr_srv
import riva.client.proto.riva_audio_pb2 as raudio

from src.config import settings

logger = logging.getLogger(__name__)


class RivaSTTClient:
    """gRPC client for NVIDIA Riva Parakeet ASR model."""

    def __init__(self):
        self.server = "grpc.nvcf.nvidia.com:443"
        self.api_key = settings.nvidia_api_key
        self.function_id = "71203149-d3b7-4460-8231-1be2543a1fca"  # Parakeet 1.1b RNNT
        self.use_ssl = True

        # Build metadata for gRPC calls
        self.metadata = [
            ("function-id", self.function_id),
            ("authorization", f"Bearer {self.api_key}"),
        ]

    def transcribe_audio(self, audio_bytes: bytes) -> list[dict[str, Any]]:
        """Transcribe audio using NVIDIA Riva Parakeet model via gRPC.

        Args:
            audio_bytes: Raw audio data (16kHz mono WAV)

        Returns:
            List of transcript segments:
            [
                {"start": 0.0, "end": 5.2, "text": "Hello, welcome to our store."},
                {"start": 5.5, "end": 12.1, "text": "Hi, I'm looking for a new phone."},
                ...
            ]
        """
        logger.info(f"Sending audio to Riva gRPC STT ({len(audio_bytes)} bytes)")

        # Write audio bytes to temp file for gRPC client
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            # Create gRPC channel with SSL
            import grpc
            if self.use_ssl:
                credentials = grpc.ssl_channel_credentials()
                channel = grpc.secure_channel(self.server, credentials)
            else:
                channel = grpc.insecure_channel(self.server)

            # Create ASR service stub
            asr_service = rasr_srv.RivaSpeechRecognitionStub(channel)

            # Read audio file
            with open(tmp_path, "rb") as f:
                audio_data = f.read()

            # Build recognition config
            config = rasr.RecognitionConfig(
                encoding=raudio.AudioEncoding.LINEAR_PCM,  # 16-bit PCM
                sample_rate_hertz=16000,  # 16kHz
                audio_channel_count=1,  # Mono
                language_code="en-US",  # Default to US English
                max_alternatives=1,
                profanity_filter=False,
                enable_automatic_punctuation=True,
                enable_word_time_offsets=True,  # Required for segment timestamps
            )

            # Build recognition request
            request = rasr.RecognizeRequest(
                config=config,
                audio=audio_data,  # Raw bytes directly
            )

            # Make gRPC call with metadata
            response = asr_service.Recognize(request, metadata=self.metadata)

            return self._parse_riva_response(response)

        except Exception as e:
            logger.error(f"Riva gRPC STT failed: {e}")
            raise
        finally:
            # Clean up temp file
            import os
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

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
                segment_words = []
                # Riva returns google.protobuf.Duration — read seconds + nanos directly
                segment_start = words[0].start_time.seconds + words[0].start_time.nanos / 1e9

                for i, word in enumerate(words):
                    segment_words.append(word.word)

                    # Extract word-level data with confidence
                    word_start = word.start_time.seconds + word.start_time.nanos / 1e9
                    word_end = word.end_time.seconds + word.end_time.nanos / 1e9
                    word_confidence = getattr(word, 'confidence', 0.85)  # Default 0.85 if not available

                    all_words.append({
                        "word": word.word,
                        "start": round(word_start, 3),
                        "end": round(word_end, 3),
                        "confidence": round(word_confidence, 3),
                    })

                    # Check if next word has a large time gap (>1s pause = new segment)
                    if i < len(words) - 1:
                        next_start = words[i + 1].start_time.seconds + words[i + 1].start_time.nanos / 1e9
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
                    last_end = words[-1].end_time.seconds + words[-1].end_time.nanos / 1e9
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


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> dict[str, Any]:
    """Transcribe audio using NVIDIA Riva gRPC STT.

    Args:
        audio_bytes: Raw audio data (16kHz mono WAV)
        filename: Filename for logging purposes (unused in gRPC)

    Returns:
        Dict with segments and words:
        {
            "segments": [{start, end, text}],
            "words": [{word, start, end, confidence}]
        }
    """
    return riva_stt_client.transcribe_audio(audio_bytes)

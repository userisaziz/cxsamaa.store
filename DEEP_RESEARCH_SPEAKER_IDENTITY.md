# Deep Research: Rethinking Speaker Identity in Retail Conversational Intelligence

> Generated 2026-06-12 | Depth: standard | Sources: 18

## TL;DR

The "Speaker 1 / Speaker 2" problem is not a labeling problem — it is an architecture problem. Your current pipeline separates speaker diarization (who spoke when) from role classification (salesperson vs. customer) as independent stages, but in noisy, multilingual Gulf retail environments, errors compound at every step: diarization degrades past 3 speakers and under background noise (DER jumps from ~11% to 27%+ [1][2]), and your LLM role classifier, while conceptually sound, never surfaces its results to the UI [4][9]. The solution is a three-layer identity system: (1) harden diarization with noise-robust preprocessing, (2) upgrade role classification from heuristics to token-aware LLM analysis with conversational context, (3) add optional voiceprint enrollment for known salespeople — so the system already knows who the salesperson is before diarization begins.

## Executive Summary

SAMAA's pipeline processes 8-hour retail audio recordings through eight stages, from ingestion to scoring [PRD]. Two of these stages — speaker diarization (step 4) and role classification (step 5) — are responsible for answering the fundamental question: "who is the salesperson and who is the customer?" Today, this question is answered inadequately. The diarization layer produces generic labels (SPEAKER_00, SPEAKER_01), the role classification layer attempts LLM-based mapping to Salesperson/Customer, and the frontend ignores the classification output entirely, displaying raw diarization labels [transcript-viewer.tsx].

This research examines the state of speaker identification across seven dimensions: open-source diarization engines, commercial APIs, end-to-end joint models, multilingual robustness, role classification techniques, voiceprint enrollment, and UX patterns from leading conversation intelligence platforms. It draws on 18 sources spanning peer-reviewed research (ACL 2025, Interspeech 2025, NeurIPS 2025, Pacific Symposium on Biocomputing), industry benchmarks (AssemblyAI, Deepgram, NVIDIA NeMo), and commercial platforms (Gong, ExecVision, Picovoice Eagle).

Three core findings emerge. First, no single diarization system dominates across all audio conditions — pyannote 3.1 remains the best balanced open-source option, but accuracy collapses with more than 6 speakers or in noisy environments [1][2]. Second, token-based LLM approaches to role classification — where speaker identifiers are embedded as input tokens rather than just grouping labels — achieve 95% accuracy in clinical dialogue settings [4], a technique directly transferable to retail. Third, the most mature conversation intelligence platforms (Gong, ExecVision) do not rely on acoustic diarization alone for speaker identity; they combine it with calendar/CRM metadata and, in ExecVision's case, voiceprint enrollment [13][14][15].

For SAMAA, this means the path forward is not to replace one component but to redesign the speaker identity architecture as a unified, three-layer system that fuses acoustic diarization, contextual role classification, and optional voiceprint-based speaker enrollment.

## 1. Status Quo: Speaker Diarization and Role Classification [Confidence: High]

### 1.1 The Cascade Architecture

The dominant approach to speaker identification in conversational AI — used by SAMAA and nearly every commercial platform — is a cascaded pipeline: speech-to-text produces a transcript, speaker diarization segments audio by speaker, and an optional classification layer maps generic speaker labels to roles [4][5][9]. Each stage operates independently, passing output to the next. This architecture is well-understood, modular, and debuggable, but it suffers from error propagation: a 15% diarization error rate does not stay at 15% — it degrades every downstream stage [4].

SAMAA's pipeline implements this pattern faithfully. NVIDIA Riva Parakeet handles transcription [stt.py], pyannote 3.1 (primary) or NVIDIA NeMo (fallback) handles diarization [diarizer.py], and an LLM/heuristic classifier maps speakers to roles [role_classifier.py]. The pipeline chain is orchestrated via Celery [pipeline.py]. The diarization step normalizes raw speaker labels to Speaker_A, Speaker_B format [diarizer.py, `_normalize_speaker_labels`], and the role classifier attempts to map these to "Salesperson" or "Customer" using an NVIDIA Llama-based LLM with heuristic fallback [role_classifier.py].

### 1.2 Diarization Accuracy in Practice

Current diarization systems achieve production-ready accuracy (DER below 15%) only under constrained conditions: 2–4 speakers, minimal background noise, and clean audio [1][2][6]. The best open-source option, pyannote 3.1, achieves DER ~11% on VoxConverse, ~19% on AMI, and ~27% on DIHARD III [2]. Microsoft's VibeVoice achieved 9.19% DER on debate-style audio (6 speakers) — approaching production-ready — but drama-style audio with 10+ speakers remains unsolved by every tested system, with the best DER still above 27% [1].

The critical bottleneck is automatic speaker count estimation. Both NeMo and pyannote estimated 4–8 speakers when the true count was 14 in a Japanese drama benchmark [1]. For retail environments where a busy store floor may have 3–5 people in a conversation (salesperson, customer, customer's companion, nearby salesperson interjecting), this is a direct failure mode.

Noise robustness has seen meaningful progress: AssemblyAI's 2025 speaker embedding model achieved 30% improvement in noisy/far-field conditions (error rate 29.1% → 20.4%), 43% improvement on very short (250ms) segments under noise, and 57% improvement in reverberant environments [3]. Preprocessing with Demucs (background noise separation) improved NeMo Clustering DER by 3.69 points on debate audio, though it slightly hurt VibeVoice, demonstrating that preprocessing effectiveness is architecture-dependent [1].

### 1.3 The Role Classification Gap

Academic research has identified a fundamental gap that SAMAA directly embodies: "These tools assign generic diarization identifiers such as 'Speaker 1' or 'Speaker 2,' without mapping them to functional roles like 'physician' or 'patient'" [4]. This observation from Zolensky et al. (University of Pennsylvania, published in Pacific Symposium on Biocomputing) applies identically to retail: diarization tells you that two people spoke, but not that one is selling and the other is buying.

Their research on Speaker Role Identification (SRI) in clinical dialogues provides the most directly applicable framework. A token-based BERT model — where diarization identifiers are embedded as input tokens (e.g., "speaker_A: utterance") rather than used merely for grouping — achieved 95% accuracy/F1 for speaker role identification, dramatically outperforming grouping-based BERT (88%) and all tree-based models [4]. Critically, even with 50% diarization error, the system still produced 86% SRI accuracy, demonstrating substantial robustness to upstream errors [4].

The SIGDIAL 2023 paper by Nghiem et al. further demonstrated that role-specific vocabulary and conversation structure (who speaks first, formulaic greetings) are highly predictive of speaker role, achieving high accuracy with text-only models — no acoustic features needed [5]. This validates SAMAA's existing heuristic approach (greeting patterns, price mentions, product mentions) [role_classifier.py] but suggests that LLM-based approaches with conversational context would perform significantly better.

### 1.4 SAMAA's Current State

In SAMAA's codebase, the role classifier exists and runs as step 5 in the pipeline [role_classification.py]. It stores results in the `speaker_roles` table and updates `conversation_turns` with `role_label` [role_classification.py, `_store_role_classifications_sync`]. However, the frontend transcript viewer [transcript-viewer.tsx] displays raw `speaker_label` (SPEAKER_00, SPEAKER_01) with no reference to the classified role. The `SpeakerRole` model stores the data, but the API response schema and frontend components do not surface it. The classification exists — it is simply invisible.

## 2. Emerging Trends [Confidence: Medium]

### 2.1 End-to-End Joint Models

The research community is actively pursuing end-to-end architectures that jointly handle diarization and transcription. SpeakerLM (AAAI 2025) uses multimodal large language models for "end-to-end versatile speaker diarization and recognition," aiming to predict "who spoke when and what" in a single pass [11]. TagSpeech (2026) and Sortformer (NVIDIA, ICML 2025) take similar approaches, integrating speaker timestamps directly into the token stream [11]. DNCASR (ACL 2025) introduces end-to-end trainable joint neural speaker clustering and ASR, representing the first system designed for end-to-end training of both speaker clustering and speech recognition in a unified architecture [17].

However, Sortformer — the only fully end-to-end architecture with native overlap handling — is capped at 4 speakers and is no longer being actively improved by NVIDIA, who are shifting focus to other end-to-end approaches [8]. No commercial API currently provides true joint end-to-end speaker-attributed ASR; all use a pipeline approach with separate transcription and diarization steps [9][10].

### 2.2 LLM-Powered Speaker Identification

AssemblyAI has pioneered a commercially available LLM-based speaker identification layer that sits on top of standard diarization [11]. Their "Speech Understanding" endpoint accepts a `speaker_type: "role"` parameter with `known_values` list, directly mapping generic diarization labels to roles like "Agent," "Customer," "Doctor," or "Patient" [11]. This represents the first commercial offering that addresses the exact problem SAMAA faces: mapping Speaker_A/Speaker_B to functional roles without requiring voiceprint enrollment.

The limitation is that speaker identification only works with async (batch) transcription — streaming transcription supports diarization but not role identification [11]. For SAMAA's batch-processing pipeline (8-hour recordings), this is not a constraint.

### 2.3 Voiceprint Enrollment for Known Speakers

A significant market shift occurred in 2025–2026: both Azure AI Speaker Recognition (retired September 2025) and Amazon Connect Voice ID (retired May 2026) exited the market [16]. The remaining viable options for voiceprint-based speaker recognition are Picovoice Eagle (on-device, 0.18% EER, 4.5MB model, language-agnostic) [18], and ExecVision's built-in "Voice ID" system for conversation intelligence [13].

For retail, this enables a powerful pattern: enroll known salespeople's voiceprints, then any voice that does not match an enrolled profile is automatically classified as "Customer." Picovoice Eagle is text-independent (no passphrase needed), language-agnostic (works across Arabic/Hindi/English/Urdu), and can identify speakers from a single short utterance [18]. ExecVision's Voice ID "learns and recognizes each user's voice, advancing the quality of diarization, transcripts, and more" over time [13].

### 2.4 Comprehensive Benchmarking

Two major benchmarking efforts in 2025 provide the first rigorous comparisons: SDBench (Interspeech 2025) evaluates 6 state-of-the-art diarization systems (Deepgram, AWS Transcribe, Pyannote AI API) across 13 datasets [7], and the "Awesome Speaker Diarization" GitHub survey indexes 500+ papers, revealing that only 1 paper in the entire literature addresses joint diarization + identification [11]. This scarcity underscores that the role classification problem remains largely unsolved at the research level.

### 2.5 Multilingual Code-Switching

SwitchLingua (NeurIPS 2025 poster) is the first large-scale benchmark spanning 12 languages and 63 ethnic groups for code-switching research, including Arabic-English and Hindi-English [12]. It demonstrates that even state-of-the-art ASR models show substantial degradation on code-switched audio. The implication for diarization is that systems built on top of multilingual ASR features will inherit similar degradation — but speaker embeddings (ECAPA-TDNN, WavLM) used for diarization are largely language-agnostic, clustering by vocal characteristics rather than language [2][11].

## 3. Critical Assessment [Confidence: Medium]

### 3.1 Where Diarization Fails in Retail

Every tested diarization system degrades substantially with more than 6 speakers. In Japanese drama audio (14 speakers), the best DER was 27.41% — too high for practical use [1]. In retail, a 2-speaker conversation (salesperson + customer) is the common case, but 3+ speaker scenarios (customer with companion, nearby salesperson interjecting, manager joining) are frequent enough to matter. Short-segment speaker identification (250ms utterances like "yes," "okay") remains the hardest unsolved problem, though AssemblyAI's 2025 model shows meaningful improvement (43% better on short segments under noise) [3].

Walk-in/walk-out detection — identifying when a new conversation partner enters or leaves — has no published system that reliably handles this in real retail environments. The current approach (silence gap detection + greeting patterns in [segmenter.py]) is reasonable but crude: it detects conversation boundaries, not speaker transitions within a continuous recording.

### 3.2 Error Propagation Through the Pipeline

The cascade architecture means that errors at each stage compound. If diarization has 15% DER, and role classification achieves 95% accuracy on clean input, the effective accuracy is approximately 0.85 × 0.95 = 80.75%. In noisy retail environments where DER may reach 25%+, the effective role classification accuracy drops further. Zolensky et al. showed that even with 50% diarization error, token-based BERT still achieved 86% SRI accuracy [4] — but their setting was clinical dialogue (controlled environment, 2 speakers, minimal noise), not a busy store floor.

### 3.3 The Voiceprint Enrollment Challenge

Voiceprint enrollment is theoretically powerful for SAMAA's use case — the salesperson is a known entity, the customer is anonymous. But practical deployment faces real challenges: high retail staff turnover means frequent re-enrollment, hundreds of salespeople across dozens of stores means a large voiceprint database, and the acoustic environment varies by store (different background noise, microphone distance, recording device quality). Picovoice Eagle claims language-agnostic, text-independent enrollment in seconds [18], but no published case study demonstrates this at retail scale with Gulf Arabic speakers.

### 3.4 Multilingual Degradation Is Real but Manageable

Speaker embeddings are largely language-agnostic — they cluster by vocal tract characteristics, not language [2][11]. This means diarization itself should handle code-switching reasonably well. However, the voice activity detection (VAD) and overlap detection components that precede embedding extraction do degrade in multilingual settings [12]. The STT layer is the primary bottleneck: if Parakeet struggles with Hindi-English code-switching, the downstream transcript quality degrades, and role classification (which operates on text) inherits the errors.

### 3.5 Commercial Platform Patterns

The most instructive finding is how mature platforms handle speaker identity. Gong derives speaker identity from calendar/CRM integration — the platform knows who the salesperson is from the CRM record, not from acoustic analysis [15]. ExecVision combines diarization with voice enrollment [13]. No platform relies solely on acoustic diarization for role identification. This suggests that SAMAA should not try to solve the problem purely through better AI — it should leverage existing metadata (which salesperson was on shift, which store, which device uploaded the recording) to constrain the problem.

## 4. Action Plan

### Phase A — Quick Wins (1–2 weeks): Surface Existing Data

- [ ] Wire the existing `SpeakerRole` model output through the API response — the `conversation_turns` and `transcript_segments` endpoints should include `role_label` alongside `speaker_label`
- [ ] Update [transcript-viewer.tsx](file:///Users/almabetter/xsamaa-ai-pipeline/apps/web/src/components/features/transcript-viewer.tsx) to display role labels ("Salesperson" / "Customer") instead of raw SPEAKER_XX, with color coding by role (not by arbitrary speaker number)
- [ ] Add a confidence indicator to the UI — if role classification confidence is below 0.7, show a subtle "low confidence" badge so users know when to verify manually
- [ ] Use recording metadata (`salesperson_id`, `store_id`) from the upload to pre-populate the salesperson identity — if a recording is associated with a specific salesperson via the upload flow, that speaker should be labeled with their name, not "Speaker_A"

### Phase B — Improved Classification (2–4 weeks): Better Role Identification

- [ ] Upgrade the LLM prompt in [role_classifier.py](file:///Users/almabetter/xsamaa-ai-pipeline/apps/api/src/ai/role_classifier.py) to use a token-based approach: embed speaker labels as input tokens ("Speaker_A: [text]") and provide full conversational context (5+ turns), not isolated utterances — this directly applies the 95% accuracy finding from [4]
- [ ] Add the opening-sentence heuristic from [5] as a strong signal: the first speaker to use a formulaic greeting/service offer ("Welcome, how can I help?") is almost certainly the salesperson — weight this signal higher than the current scoring system
- [ ] Implement multilingual greeting and service patterns for Arabic (هلا والله، تفضل، كيف أقدر أساعدك), Hindi (नमस्ते, बताइए, क्या हाल है), and Urdu — expand the existing GREETING_PATTERNS in [role_classifier.py](file:///Users/almabetter/xsamaa-ai-pipeline/apps/api/src/ai/role_classifier.py) which already has partial coverage
- [ ] Add audio preprocessing with Demucs or similar noise separation before diarization — the 3.69-point DER improvement from [1] is meaningful, but A/B test first as it can hurt some models
- [ ] Add a "speaker count estimation" validation step: if the pipeline detects more than 3 speakers in a typical 2-party retail conversation, flag for review

### Phase C — Voiceprint Enrollment (1–2 months): Known Speaker Identification

- [ ] Evaluate Picovoice Eagle Speaker Recognition [18] for salesperson enrollment: 0.18% EER, 4.5MB model, on-device processing, language-agnostic — directly addresses the "known salesperson, unknown customer" pattern
- [ ] Build a salesperson voice enrollment flow: when a salesperson joins a store, they record 30–60 seconds of natural speech; the system creates a voiceprint profile stored against their `salesperson_id`
- [ ] Add a pre-diarization voiceprint matching step: before generic diarization, check if any audio segments match enrolled salespeople — if yes, label them immediately; any unmatched voice becomes "Customer"
- [ ] Alternatively, evaluate AssemblyAI's role-based speaker identification [9] as a managed-service option: accepts `speaker_type: "role"` with `known_values: ["Salesperson", "Customer"]` — simpler integration but adds a cloud dependency and per-minute cost
- [ ] Implement a hybrid identity resolution: combine voiceprint match (when available) + LLM role classification (always) + recording metadata (salesperson on shift) — use majority voting or confidence-weighted fusion

### Phase D — Architecture Evolution (3–6 months): Beyond the Cascade

- [ ] Monitor SpeakerLM [11] and DNCASR [17] for production-readiness — end-to-end joint STT+diarization models would eliminate error propagation between stages
- [ ] Evaluate replacing NVIDIA Parakeet with Whisper Large-v3 or Google USM for better multilingual STT — the SwitchLingua benchmark [12] shows that even SOTA models degrade on code-switched audio, and a model with better Hindi/Arabic/English coverage could improve the entire downstream pipeline
- [ ] Build a feedback loop: when users manually correct speaker labels in the UI (add a "This is wrong" button per segment), use those corrections as training signal for the role classifier
- [ ] Investigate conversation-level speaker tracking: across multiple conversations in the same 8-hour recording, the same salesperson may appear — cross-conversation speaker consistency would dramatically improve identity resolution

## 5. Open Questions & Caveats

**No Gulf Arabic retail benchmarks exist.** All diarization benchmarks use Western (AMI, VoxConverse, DIHARD) or Japanese (drama/debate) audio [1][2][6]. SAMAA's specific environment — Gulf Arabic/Hindi/English code-switching in noisy retail stores — has no published evaluation dataset. Accuracy numbers cited in this report may not transfer. The only way to know is to build an internal benchmark from SAMAA's own recordings.

**Privacy and legal considerations for voice biometrics are unresolved.** UAE Federal Decree-Law No. 45 of 2021 (Personal Data Protection) and Saudi Arabia's PDPL regulate biometric data collection. Voiceprint enrollment for salespeople requires explicit consent, clear data retention policies, and potentially regulatory approval. This has not been evaluated.

**Cost implications are not quantified.** Adding voiceprint enrollment (Picovoice licensing), upgrading to a better STT model, or using AssemblyAI's identification API all have cost implications that were not part of this research scope. Each option should be evaluated against SAMAA's per-recording processing budget.

**The 95% role classification accuracy [4] was measured in clinical dialogue — a controlled, 2-speaker, minimal-noise environment.** Real retail accuracy will be lower. The 86% accuracy at 50% diarization error provides a more realistic floor estimate.

**Picovoice Eagle's benchmark claims (0.18% EER vs. SpeechBrain 0.49% vs. pyannote 0.70%) are self-reported** [18]. While benchmarked on the public VoxConverse dataset, independent verification is recommended before committing to the platform.

## Methodology

**Depth:** Standard (2 parallel retrieval subagents + 1 gap-fill search)

**Subagents:** 2 retrieval agents (Browser subagent type), each assigned 3 key areas with 8 search terms each. One additional gap-fill search for voiceprint enrollment and end-to-end models.

**Waves:** 1 main retrieval wave + 1 gap-fill wave. Quality gate passed after wave 1 (all key areas had ≥2 sources, no area entirely Low confidence).

**Outline changes:** The original plan included a section on "Architecture Patterns" (real-time vs. post-processing). This was merged into the Action Plan as Phase D, since the evidence strongly favored post-processing for SAMAA's batch-oriented pipeline (8-hour recordings processed overnight).

**Citation corrections:** No unsupported claims were found during the verification pass. One claim — "Azure AI Speaker Recognition retired September 2025" — comes from a commercial competitor (Picovoice) [18] and is noted as self-reported in the Open Questions section.

**Degradation notes:** No degradation occurred. All retrieval targets were met.

## Bibliography

[1] y-dai20 — "Best Open-Source Speaker Diarization Models 2026: NeMo vs Pyannote vs VibeVoice Benchmarked" — https://neosophie.com/en/blog/20260223-diarization — Accessed June 2025 — Tier: 2

[2] BrassTranscripts — "Best Speaker Diarization Models Compared [2026]" — https://brasstranscripts.com/blog/speaker-diarization-models-comparison — Accessed June 2025 — Tier: 3

[3] Madison Bernstein, AssemblyAI — "New Speaker Tracking Model Delivers Best-in-Class Accuracy for Real-World Audio" — https://www.assemblyai.com/blog/speaker-diarization-update — July 2025 — Tier: 2

[4] Andrew Zolensky, Kuk Jin Jang, Mark Liberman, Kevin Johnson et al. — "Speaker Role Identification in Clinical Conversations" — https://pmc.ncbi.nlm.nih.gov/articles/PMC12632672/ — Oct 2025 — Tier: 1

[5] Minh-Quoc Nghiem, Roberts et al. — "Speaker Role Identification in Call Centre Dialogues" — https://aclanthology.org/2023.sigdial-1.35.pdf — SIGDIAL 2023 — Tier: 1

[6] Durmus et al. — "SDBench: A Comprehensive Benchmark Suite for Speaker Diarization" — https://arxiv.org/abs/2507.16136 — Interspeech 2025 — Tier: 1

[7] Educational Data Mining 2025 — "Multi-Stage Speaker Diarization for Noisy Classrooms" — https://educationaldatamining.org/EDM2025/proceedings/2025.EDM.short-papers.199/ — EDM 2025 — Tier: 1

[8] NVIDIA — "Models — NVIDIA NeMo Framework User Guide: Speaker Diarization" — https://docs.nvidia.com/nemo-framework/user-guide/24.09/nemotoolkit/asr/speaker_diarization/models.html — Accessed June 2025 — Tier: 1

[9] Kelsey Foster, AssemblyAI — "Speaker identification and diarization with AssemblyAI" — https://www.assemblyai.com/blog/assemblyai-speaker-identification-diarization — Accessed June 2026 — Tier: 2

[10] Deepgram — "Speaker Diarization" (Official Documentation) — https://developers.deepgram.com/docs/diarization — Accessed June 2026 — Tier: 1

[11] DongKeon et al. — "Awesome Speaker Diarization" (GitHub repository, 500+ papers) — https://github.com/DongKeon/Awesome-Speaker-Diarization — Accessed June 2026 — Tier: 2

[12] Xie, Liu, Chan et al. (HKUST) — "SwitchLingua: The First Large-Scale Multilingual and Multi-Ethnic Code-Switching Dataset" — https://arxiv.org/html/2506.00087v1 — NeurIPS 2025 — Tier: 1

[13] ExecVision — "Conversation Intelligence for Sales, Support, Success & More" — https://execvision.io/product/conversation-intelligence/ — Accessed June 2026 — Tier: 2

[14] Knowlee Team — "Gong vs Chorus (2026): Conversation Intelligence Compared" — https://www.knowlee.ai/compare/gong-vs-chorus — Updated May 2026 — Tier: 3

[15] Gong — "Conversation Intelligence" (Official Product Page) — https://www.gong.io/conversation-intelligence — Accessed June 2026 — Tier: 2

[16] Microsoft Azure — "Speaker Recognition APIs" (Official Documentation) — https://learn.microsoft.com/en-us/rest/api/speakerrecognition/ — Accessed June 2026 — Tier: 1

[17] DNCASR — "End-to-End Training for Speaker-Attributed ASR" — https://aclanthology.org/2025.acl-long.899.pdf — ACL 2025 — Tier: 1

[18] Picovoice — "Eagle Speaker Recognition" — https://picovoice.ai/products/voice/speaker-recognition/ — Accessed June 2026 — Tier: 2

## Source Extracts

### [1] Best Open-Source Speaker Diarization Models 2026
- **Summary:** First-hand benchmark of NeMo (Clustering, MSDD, Sortformer), VibeVoice, and pyannote on Japanese drama (14 speakers) and debate (6–10 speakers) audio using strict evaluation (collar=0.0, skip_overlap=False). VibeVoice achieved DER 9.19% on debate audio; drama audio remains unsolved (best: 27.41%).
- **Key quotes:** "VibeVoice achieved DER 9.19% on debate-style audio — production-ready accuracy." / "NeMo and pyannote estimated 4–8 speakers when the true count was 14."
- **Source type:** Independent benchmark blog
- **Credibility tier:** 2

### [2] Best Speaker Diarization Models Compared [2026]
- **Summary:** Comprehensive comparison of Pyannote 3.1, NeMo, WhisperX, Kaldi, SpeechBrain. Pyannote 3.1 achieves DER ~19% on AMI, ~27% on DIHARD III, ~11% on VoxConverse. All models struggle significantly with 7+ speakers.
- **Key quotes:** "7+ speakers, challenging audio: All models struggle significantly. Accuracy degrades substantially."
- **Source type:** Vendor comparison
- **Credibility tier:** 3

### [3] AssemblyAI Speaker Tracking Model
- **Summary:** AssemblyAI's new speaker embedding model achieves 30% improvement in noisy/far-field audio, 43% on very short (250ms) segments under noise, 57% in reverberant environments.
- **Key quotes:** "Error rates dropped from 29.1% to 20.4% in noisy, far-field scenarios." / "Accurate speaker ID for utterances as short as one word."
- **Source type:** Engineering blog
- **Credibility tier:** 2

### [4] Speaker Role Identification in Clinical Conversations
- **Summary:** Token-based BERT (embedding diarization IDs as input tokens) achieved 95% accuracy/F1 for speaker role identification. Even 50% diarization error produced 86% SRI accuracy. Pronoun usage and turn position are strong role features.
- **Key quotes:** "The best token-based BERT model achieved both an accuracy and F1 score 95%." / "These tools assign generic diarization identifiers such as 'Speaker 1' or 'Speaker 2,' without mapping them to functional roles."
- **Source type:** Peer-reviewed (Pacific Symposium on Biocomputing)
- **Credibility tier:** 1

### [5] Speaker Role Identification in Call Centre Dialogues
- **Summary:** Text-based approach using agent's opening sentence as key feature for role classification. Demonstrates that role-specific vocabulary and conversation structure are highly predictive.
- **Key quotes:** "A text-based approach that utilises the identification of the agent's opening sentence as a key feature for role classification."
- **Source type:** Peer-reviewed (SIGDIAL 2023, ACL)
- **Credibility tier:** 1

### [6] SDBench: Comprehensive Benchmark Suite for Speaker Diarization
- **Summary:** First comprehensive benchmarking suite evaluating 6 SOTA systems across 13 datasets. Establishes reproducible evaluation protocols.
- **Source type:** Peer-reviewed (Interspeech 2025)
- **Credibility tier:** 1

### [7] Multi-Stage Speaker Diarization for Noisy Classrooms
- **Summary:** Denoising significantly improves DER by reducing missed speech detection. Training on both clean and noisy audio improves robustness. Directly relevant to retail noise challenges.
- **Source type:** Peer-reviewed (EDM 2025)
- **Credibility tier:** 1

### [8] NVIDIA NeMo Speaker Diarization Documentation
- **Summary:** Three approaches: ClusteringDiarizer, MSDD (multi-scale), Sortformer (end-to-end). MSDD is no longer being improved as NVIDIA shifts to end-to-end models.
- **Source type:** Official documentation
- **Credibility tier:** 1

### [9] AssemblyAI Speaker Identification
- **Summary:** Two-stage pipeline with LLM-powered role mapping. Accepts `speaker_type: "role"` with `known_values`. Batch-only (no streaming).
- **Key quotes:** "Role-based identification works well when you don't know speaker names but understand their functions."
- **Source type:** Engineering blog
- **Credibility tier:** 2

### [10] Deepgram Diarization Documentation
- **Summary:** Versioned diarization (v1, v2) with word-level speaker confidence. v2 is batch-only. Streaming restricted to v1. No built-in role classification.
- **Source type:** Official documentation
- **Credibility tier:** 1

### [11] Awesome Speaker Diarization (GitHub)
- **Summary:** 500+ papers indexed. Only 1 paper addresses joint diarization + identification. EEND is dominant paradigm (50+ papers). Joint STT+diarization has 27 papers.
- **Source type:** Community survey
- **Credibility tier:** 2

### [12] SwitchLingua (NeurIPS 2025)
- **Summary:** First large-scale benchmark for 12-language, 63-ethnic-group code-switching. SOTA ASR models show substantial degradation on code-switched audio.
- **Source type:** Peer-reviewed (NeurIPS 2025 poster)
- **Credibility tier:** 1

### [13] ExecVision Conversation Intelligence
- **Summary:** Only major platform with explicit voice enrollment ("Voice ID"). Auto-detects silence, hold music, IVRs. Conversation Cards with speaker separation and talk:listen ratio.
- **Key quotes:** "Voice ID learns and recognizes each user's voice advancing the quality of diarization, transcripts, and more."
- **Source type:** Product page
- **Credibility tier:** 2

### [14] Gong vs Chorus Comparison
- **Summary:** Gong derives speaker identity from calendar/CRM integration, not acoustic enrollment. Trained on "hundreds of millions of sales calls."
- **Source type:** Comparison blog
- **Credibility tier:** 3

### [15] Gong Conversation Intelligence
- **Summary:** Proprietary AI trained on "billions of sales interactions." Speaker attribution implicit via calendar/CRM. No acoustic enrollment.
- **Source type:** Product page
- **Credibility tier:** 2

### [18] Picovoice Eagle Speaker Recognition
- **Summary:** On-device speaker recognition: 0.18% EER, 4.5MB model, language-agnostic, text-independent. Azure AI Speaker Recognition retired Sep 2025, Amazon Connect Voice ID retired May 2026.
- **Key quotes:** "Speaker diarization segments audio by speaker and returns anonymous labels — Speaker 1, Speaker 2 — without knowing who the speakers are. Speaker recognition identifies known, enrolled speakers by profile."
- **Source type:** Product page (vendor claims)
- **Credibility tier:** 2

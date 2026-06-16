# CXSAMAA — Decision Log

**Purpose:** Quick reference for all architectural and technical decisions made during planning.  
**Last Updated:** 2026-06-09  

---

## Decisions

| # | Decision | Choice | Alternatives Considered | Rationale |
|---|---|---|---|---|
| D1 | Starting approach | Full architecture design first, then implement | Start with backend or AI first | System is large, upfront design prevents rework |
| D2 | Repository structure | Monorepo (Turborepo) | Separate repos, hybrid | Shared types between API and frontend, single PR workflow |
| D3 | Backend framework | FastAPI (Python) | NestJS (TypeScript) | AI/ML ecosystem native, better for data pipeline work |
| D4 | ORM | SQLAlchemy 2.0 + Alembic | Prisma (TypeScript-only) | Best Python ORM, async support, mature migration tool |
| D5 | Job queue | Celery + Redis | BullMQ (Node.js), ARQ | Battle-tested for heavy multi-stage pipelines |
| D6 | AI runtime | NVIDIA hosted APIs (NIM) | Self-hosted GPU, alternative LLM APIs | No GPU infra needed for MVP, pay-per-use |
| D7 | File storage | Local FS + storage abstraction | AWS S3, Cloudflare R2 | Fast local dev, abstraction allows swap to S3/R2 later |
| D8 | Deployment | Deferred (Docker-based local dev first) | Multi-service cloud, single provider | Focus on building first, decide deployment later |
| D9 | Frontend framework | Next.js 15 + TypeScript | — (per PRD) | SSR, App Router, great DX |
| D10 | UI components | shadcn/ui + Tailwind CSS | — (per PRD) | Modern, accessible, customizable |
| D11 | State management | Zustand + TanStack Query | Redux Toolkit | Lightweight client state, powerful server state caching |
| D12 | Architecture pattern | FastAPI monolith with Celery workers | API + separate worker service, Python + Node split | Simplest for MVP, can split workers later |
| D13 | Documentation | Plan stored in `plan/` folder as .md files | — | User requested persistent context for future sessions |
| D14 | Future model training | NeMo Framework (train) → Riva (deploy) | Self-hosted GPU from day 1, stay on NIM forever | Train custom ASR/diarization on retail audio for better Arabic/Hindi accuracy and cost control at scale |
| D15 | Training approach | SSL pre-train → fine-tune from Parakeet/Canary weights | Train from scratch | Transfer learning is faster, cheaper, and produces better results |
| D16 | Deployment path (future) | Riva (self-hosted GPU) or Triton Inference Server | Stay on NIM API, custom Docker | Riva is NVIDIA's production-grade speech AI server, optimized for streaming + batch |
| D17 | Quick win (pre-Sprint 7) | LM fusion with retail n-gram model | Full ASR retraining | Can improve retail vocabulary accuracy without retraining the full model |

---

## NVIDIA NeMo Ecosystem Reference

Researched 2026-06-09. Key findings for CXSAMAA:

### The 4-Layer Stack
```
Layer 4: RIVA — Self-hosted GPU inference server (deploy custom models)
Layer 3: NIM — Hosted API endpoints (what CXSAMAA uses NOW)
Layer 2: NeMo Framework — Python library to train/fine-tune models (Sprint 7)
Layer 1: PyTorch + CUDA + GPU hardware
```

### What CXSAMAA Uses NOW (NIM APIs)
- **Parakeet CTC 1.1B** → STT (`nvidia_stt_model`)
- **Streusand RNNT** → Speaker diarization (`nvidia_diarization_model`)
- **Llama 3.3 70B** → Analysis + scoring (`nvidia_llm_model`)

### What CXSAMAA Will Use LATER (Sprint 7)
- **NeMo Framework** → Train custom ASR + diarization on retail audio
- **Speech SSL** → Pre-train on unlabeled store audio
- **Speech Data Processor** → Batch dataset preparation
- **NeMo Forced Aligner** → Word-level alignments for training data
- **ASR Evaluator** → Benchmark custom vs. hosted models
- **Riva** → Deploy custom models (self-hosted GPU inference)

### Not Relevant to CXSAMAA
- LLM training (Megatron) — using Llama via API
- Multimodal models — audio-only
- TTS — don't generate speech
- Computer Vision — not relevant
- Canary model — European languages only, not Arabic/Hindi
- NeMo Microservices — only for massive scale deployment

### Key Feature: LM Fusion
NeMo supports fusing an n-gram language model with ASR at inference time.
Can train a small LM on retail terminology (product names, brand names) and
fuse with Parakeet to improve retail vocabulary accuracy WITHOUT full retraining.
Possible quick win before Sprint 7 full training pipeline.

### NeMo 2.0 Note
Major API changes from 1.0 → 2.0. New NeMo Run library. When starting
training, use 2.0 APIs.

---

## Document Index

| File | Purpose |
|---|---|
| `plan/00-architecture-design.md` | Complete system architecture, folder structure, DB schema, API design, AI pipeline, frontend design |
| `plan/01-implementation-plan.md` | Sprint-by-sprint implementation plan (Sprints 1-7) with detailed tasks |
| `plan/02-decision-log.md` | This file — all decisions, ecosystem reference, and document index |
| `docs/SAMAA_PRD.md` | Original Product Requirements Document |

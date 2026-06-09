# Recording Management API

<cite>
**Referenced Files in This Document**
- [recordings.py](file://apps/api/src/api/v1/recordings.py)
- [router.py](file://apps/api/src/api/v1/router.py)
- [recording.py](file://apps/api/src/models/recording.py)
- [transcript.py](file://apps/api/src/models/transcript.py)
- [conversation.py](file://apps/api/src/models/conversation.py)
- [recording_schemas.py](file://apps/api/src/schemas/recording.py)
- [recording_service.py](file://apps/api/src/services/recording.py)
- [export_service.py](file://apps/api/src/services/export.py)
- [pipeline.py](file://apps/api/src/workers/pipeline.py)
- [local_storage.py](file://apps/api/src/storage/local.py)
- [deps.py](file://apps/api/src/api/deps.py)
- [config.py](file://apps/api/src/config.py)
- [README.md](file://README.md)
- [PRD.md](file://docs/SAMAA_PRD.md)
</cite>

## Update Summary
**Changes Made**
- Removed advanced transcription, analysis, and CSV export endpoints
- Simplified API to basic upload, status checking, and reprocessing endpoints
- Removed complex processing pipeline orchestration
- Streamlined authentication requirements for basic operations
- Eliminated transcript, conversation, and summary endpoints

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)
10. [Appendices](#appendices)

## Introduction
This document provides comprehensive API documentation for audio recording management. The API has been simplified to focus on core recording operations: file upload, status tracking, and basic management functions. It covers endpoints for uploading audio recordings, tracking processing status, retrieving recording details, and managing audio files. It specifies HTTP methods, URL patterns, multipart form data handling, validation requirements, processing workflows, status transitions, error handling, and storage considerations.

**Updated** The API has been streamlined from a complex multi-stage processing system to a focused set of basic endpoints for recording management.

## Project Structure
The recording management API is implemented as part of the FastAPI backend under `/apps/api/src/api/v1/`. Key components include route handlers, models, schemas, services, workers, and storage abstractions.

```mermaid
graph TB
subgraph "API Layer"
Routers["API Routers<br/>apps/api/src/api/v1/router.py"]
RecordingsAPI["Recordings Router<br/>apps/api/src/api/v1/recordings.py"]
end
subgraph "Domain Layer"
Models["ORM Models<br/>apps/api/src/models/*.py"]
Schemas["Pydantic Schemas<br/>apps/api/src/schemas/*.py"]
Services["Business Services<br/>apps/api/src/services/*.py"]
end
subgraph "Workers & Storage"
Pipeline["Processing Pipeline<br/>apps/api/src/workers/pipeline.py"]
Storage["Storage Backend<br/>apps/api/src/storage/local.py"]
end
Routers --> RecordingsAPI
RecordingsAPI --> Services
Services --> Models
Services --> Storage
RecordingsAPI --> Pipeline
```

**Diagram sources**
- [router.py:1-20](file://apps/api/src/api/v1/router.py#L1-L20)
- [recordings.py:1-125](file://apps/api/src/api/v1/recordings.py#L1-L125)
- [recording.py:1-60](file://apps/api/src/models/recording.py#L1-L60)
- [recording_schemas.py:1-71](file://apps/api/src/schemas/recording.py#L1-L71)
- [recording_service.py:1-262](file://apps/api/src/services/recording.py#L1-L262)
- [pipeline.py:1-35](file://apps/api/src/workers/pipeline.py#L1-L35)
- [local_storage.py:1-50](file://apps/api/src/storage/local.py#L1-L50)

**Section sources**
- [router.py:1-20](file://apps/api/src/api/v1/router.py#L1-L20)
- [README.md:1-308](file://README.md#L1-L308)

## Core Components
- API Router: Exposes endpoints under `/api/v1/recordings` for upload, listing, and status checking.
- Models: Define the recording lifecycle and basic metadata storage.
- Schemas: Pydantic models for request/response validation and serialization.
- Services: Encapsulate business logic for listing, creating, and updating recording status.
- Workers/Pipeline: Orchestrates asynchronous processing stages via Celery.
- Storage: Provides local file storage abstraction for uploaded audio.

**Updated** The API now focuses on essential recording management functions, removing advanced transcription and analysis capabilities.

**Section sources**
- [recordings.py:1-125](file://apps/api/src/api/v1/recordings.py#L1-L125)
- [recording.py:1-60](file://apps/api/src/models/recording.py#L1-L60)
- [recording_schemas.py:1-71](file://apps/api/src/schemas/recording.py#L1-L71)
- [recording_service.py:1-262](file://apps/api/src/services/recording.py#L1-L262)
- [pipeline.py:1-35](file://apps/api/src/workers/pipeline.py#L1-L35)
- [local_storage.py:1-50](file://apps/api/src/storage/local.py#L1-L50)

## Architecture Overview
The recording management API follows a layered architecture:
- HTTP requests are handled by FastAPI route handlers.
- Handlers delegate to services for business logic.
- Services interact with SQLAlchemy models and the storage backend.
- The processing pipeline is orchestrated asynchronously via Celery.

```mermaid
sequenceDiagram
participant Client as "Client"
participant API as "FastAPI Handler<br/>/recordings/upload"
participant Service as "Recording Service"
participant Storage as "Storage Backend"
participant DB as "PostgreSQL"
participant Celery as "Celery Pipeline"
Client->>API : "POST /api/v1/recordings/upload"<br/>multipart/form-data
API->>API : "Validate file format and metadata"
API->>Storage : "Upload file bytes"
Storage-->>API : "File URL/path"
API->>Service : "Create recording record"
Service->>DB : "Insert Recording row"
DB-->>Service : "Recording persisted"
API->>Celery : "Enqueue processing pipeline"
Celery-->>API : "AsyncResult"
API-->>Client : "201 Created + RecordingResponse"
```

**Diagram sources**
- [recordings.py:56-84](file://apps/api/src/api/v1/recordings.py#L56-L84)
- [recording_service.py:83-126](file://apps/api/src/services/recording.py#L83-L126)
- [local_storage.py:14-32](file://apps/api/src/storage/local.py#L14-L32)
- [pipeline.py:12-34](file://apps/api/src/workers/pipeline.py#L12-L34)

## Detailed Component Analysis

### Endpoint Catalog and Definitions

#### Upload Recording
- Method: POST
- URL: `/api/v1/recordings/upload`
- Content-Type: multipart/form-data
- Required form fields:
  - `file`: Audio file (allowed formats: wav, mp3, m4a)
  - `salesperson_id`: UUID of the salesperson
- Optional form fields:
  - `recorded_at`: ISO 8601 timestamp indicating when the recording was made
- Validation:
  - Filename presence and extension validation against allowed formats
  - MIME-type compatibility with allowed audio types
  - `recorded_at` parsing to ISO 8601 datetime
- Processing:
  - Reads file bytes, stores via storage backend, creates recording record with status UPLOADED
  - Enqueues Celery pipeline; if Redis/Celery is unavailable, recording remains UPLOADED
- Response: RecordingResponse

**Updated** Simplified from previous version with basic upload functionality only.

**Section sources**
- [recordings.py:56-84](file://apps/api/src/api/v1/recordings.py#L56-L84)
- [recordings.py:35-36](file://apps/api/src/api/v1/recordings.py#L35-L36)

#### List Recordings
- Method: GET
- URL: `/api/v1/recordings`
- Query parameters:
  - `page`: integer (default: 1)
  - `page_size`: integer (default: 20)
  - `status`: string filter (enum values from RecordingStatus)
  - `salesperson_id`: UUID filter
  - `date_from`: ISO 8601 date
  - `date_to`: ISO 8601 date
- Response: PaginatedRecordingsResponse

**Section sources**
- [recordings.py:21-53](file://apps/api/src/api/v1/recordings.py#L21-L53)
- [recording_service.py:18-61](file://apps/api/src/services/recording.py#L18-L61)

#### Get Recording Detail
- Method: GET
- URL: `/api/v1/recordings/{recording_id}`
- Path parameter:
  - `recording_id`: UUID
- Response: RecordingResponse

**Section sources**
- [recordings.py:86-95](file://apps/api/src/api/v1/recordings.py#L86-L95)
- [recording_service.py:64-68](file://apps/api/src/services/recording.py#L64-L68)

#### Get Recording Status
- Method: GET
- URL: `/api/v1/recordings/{recording_id}/status`
- Path parameter:
  - `recording_id`: UUID
- Response: RecordingStatusResponse

**Section sources**
- [recordings.py:98-107](file://apps/api/src/api/v1/recordings.py#L98-L107)

#### Reprocess Recording
- Method: POST
- URL: `/api/v1/recordings/{recording_id}/reprocess`
- Path parameter:
  - `recording_id`: UUID
- Behavior:
  - Resets status to UPLOADED and clears error message
  - Re-enqueues pipeline; if Redis/Celery unavailable, logs warning
- Response: RecordingResponse

**Section sources**
- [recordings.py:110-125](file://apps/api/src/api/v1/recordings.py#L110-L125)

### Data Models and Schemas

```mermaid
classDiagram
class Recording {
+UUID id
+UUID salesperson_id
+string file_url
+int file_size
+int duration_seconds
+string format
+RecordingStatus status
+string error_message
+datetime uploaded_at
+datetime recorded_at
+datetime processed_at
+silence_gaps[]
}
class TranscriptSegment {
+UUID id
+UUID recording_id
+string speaker_label
+float start_time
+float end_time
+string text
+Vector embedding
}
class Conversation {
+UUID id
+UUID recording_id
+float start_time
+float end_time
+int segment_count
+string summary
+datetime created_at
}
class ConversationAnalysis {
+UUID id
+UUID conversation_id
+string intent
+list products
+string budget
+list objections
+list competitors
+bool closing_attempt
+string outcome
+int confidence
+dict scores
+string summary
+string coaching_notes
+datetime created_at
}
Recording "1" --> "many" TranscriptSegment : "has"
Recording "1" --> "many" Conversation : "has"
Conversation "1" --> "0..1" ConversationAnalysis : "analyzed_by"
```

**Diagram sources**
- [recording.py:24-59](file://apps/api/src/models/recording.py#L24-L59)
- [transcript.py:10-26](file://apps/api/src/models/transcript.py#L10-L26)
- [conversation.py:11-60](file://apps/api/src/models/conversation.py#L11-L60)

### Processing Workflow and Status Transitions

```mermaid
stateDiagram-v2
[*] --> UPLOADED
UPLOADED --> PREPROCESSING : "start_processing_pipeline()"
PREPROCESSING --> TRANSCRIBING : "preprocessing complete"
TRANSCRIBING --> DIARIZING : "transcription complete"
DIARIZING --> SEGMENTING : "diarization complete"
SEGMENTING --> ANALYZING : "segmentation complete"
ANALYZING --> SCORING : "analysis complete"
SCORING --> COMPLETED : "scoring complete"
UPLOADED --> FAILED : "error"
PREPROCESSING --> FAILED : "error"
TRANSCRIBING --> FAILED : "error"
DIARIZING --> FAILED : "error"
SEGMENTING --> FAILED : "error"
ANALYZING --> FAILED : "error"
SCORING --> FAILED : "error"
```

**Diagram sources**
- [recording.py:12-22](file://apps/api/src/models/recording.py#L12-L22)
- [pipeline.py:12-34](file://apps/api/src/workers/pipeline.py#L12-L34)

### Authentication and Authorization
- Authentication: Bearer token via Authorization header
- Authorization roles: SUPER_ADMIN, BRAND_ADMIN, STORE_MANAGER, SALESPERSON (require_salesperson_up)

**Section sources**
- [deps.py:1-63](file://apps/api/src/api/deps.py#L1-L63)

### Storage Management
- Storage backend: configurable (local by default)
- Local storage writes files to `./uploads` (configurable via `LOCAL_UPLOAD_DIR`)
- Storage interface supports async upload/download/delete and sync methods for workers

**Section sources**
- [local_storage.py:1-50](file://apps/api/src/storage/local.py#L1-L50)
- [config.py:24-26](file://apps/api/src/config.py#L24-L26)

### Quality Assessment Endpoints
**Updated** Removed quality assessment endpoints as they are no longer part of the simplified API.

### Batch Operations
**Updated** Removed export endpoints as they are no longer part of the simplified API.

## Dependency Analysis

```mermaid
graph LR
Handler["Recordings Handler<br/>apps/api/src/api/v1/recordings.py"]
Service["Recording Service<br/>apps/api/src/services/recording.py"]
Storage["Local Storage<br/>apps/api/src/storage/local.py"]
DB["PostgreSQL<br/>SQLAlchemy ORM"]
Pipeline["Celery Pipeline<br/>apps/api/src/workers/pipeline.py"]
Handler --> Service
Service --> DB
Handler --> Storage
Handler --> Pipeline
```

**Diagram sources**
- [recordings.py:1-35](file://apps/api/src/api/v1/recordings.py#L1-L35)
- [recording_service.py:1-14](file://apps/api/src/services/recording.py#L1-L14)
- [local_storage.py:1-50](file://apps/api/src/storage/local.py#L1-L50)
- [pipeline.py:1-35](file://apps/api/src/workers/pipeline.py#L1-L35)

**Section sources**
- [recordings.py:1-35](file://apps/api/src/api/v1/recordings.py#L1-L35)
- [recording_service.py:1-14](file://apps/api/src/services/recording.py#L1-L14)
- [local_storage.py:1-50](file://apps/api/src/storage/local.py#L1-L50)
- [pipeline.py:1-35](file://apps/api/src/workers/pipeline.py#L1-L35)

## Performance Considerations
- Asynchronous processing: Upload returns immediately while long-running pipeline executes in Celery workers.
- Pagination: Listing endpoints support pagination to limit response sizes.
- Embeddings: Transcript segments include vector embeddings for efficient semantic search.

**Updated** Removed streaming responses and export capabilities as they are no longer part of the simplified API.

## Troubleshooting Guide
- Upload failures:
  - Invalid file format or missing filename: handler raises 400 with detailed message
  - Invalid `recorded_at` format: handler raises 400 with ISO 8601 requirement
  - Redis/Celery unavailable: pipeline enqueue fails silently; recording remains UPLOADED
- Status polling:
  - Use `/recordings/{id}/status` to track progress; status transitions are defined in RecordingStatus
- Re-processing:
  - Use `/recordings/{id}/reprocess` to restart pipeline for failed or stale recordings

**Updated** Removed export-related troubleshooting as CSV export functionality has been removed.

**Section sources**
- [recordings.py:64-84](file://apps/api/src/api/v1/recordings.py#L64-L84)
- [recordings.py:98-107](file://apps/api/src/api/v1/recordings.py#L98-L107)
- [recordings.py:110-125](file://apps/api/src/api/v1/recordings.py#L110-L125)
- [recording.py:12-22](file://apps/api/src/models/recording.py#L12-L22)

## Conclusion
The Recording Management API provides a streamlined foundation for audio ingestion and basic management. It enforces strict validation, offers flexible filtering capabilities, and integrates seamlessly with a multi-stage AI pipeline. The simplified endpoints, schemas, and workflows enable reliable integration for upload, monitoring, and basic status tracking.

**Updated** The API has been successfully simplified to focus on essential recording management functions while maintaining robust processing capabilities.

## Appendices

### Audio Format Requirements
- Allowed extensions: wav, mp3, m4a
- MIME types: audio/wav, audio/mpeg, audio/mp4, audio/x-m4a, audio/mp3

**Section sources**
- [recordings.py:35-36](file://apps/api/src/api/v1/recordings.py#L35-L36)
- [PRD.md:68-80](file://docs/SAMAA_PRD.md#L68-L80)

### Progress Tracking Pattern
- After upload, poll `/api/v1/recordings/{id}/status` to monitor status transitions until completion or failure.

**Section sources**
- [recordings.py:98-107](file://apps/api/src/api/v1/recordings.py#L98-L107)
- [recording.py:12-22](file://apps/api/src/models/recording.py#L12-L22)

### Batch Operations Examples
**Updated** Removed batch operations examples as CSV export functionality has been removed from the simplified API.
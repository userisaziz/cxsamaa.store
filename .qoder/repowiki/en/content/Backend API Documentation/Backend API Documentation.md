# Backend API Documentation

<cite>
**Referenced Files in This Document**
- [apps/api/src/main.py](file://apps/api/src/main.py)
- [apps/api/src/api/v1/router.py](file://apps/api/src/api/v1/router.py)
- [apps/api/src/api/deps.py](file://apps/api/src/api/deps.py)
- [apps/api/src/config.py](file://apps/api/src/config.py)
- [apps/api/src/api/v1/auth.py](file://apps/api/src/api/v1/auth.py)
- [apps/api/src/schemas/auth.py](file://apps/api/src/schemas/auth.py)
- [apps/api/src/services/auth.py](file://apps/api/src/services/auth.py)
- [apps/api/src/models/user.py](file://apps/api/src/models/user.py)
- [apps/api/src/api/v1/brands.py](file://apps/api/src/api/v1/brands.py)
- [apps/api/src/schemas/brand.py](file://apps/api/src/schemas/brand.py)
- [apps/api/src/models/brand.py](file://apps/api/src/models/brand.py)
- [apps/api/src/services/brand.py](file://apps/api/src/services/brand.py)
- [apps/api/src/api/v1/stores.py](file://apps/api/src/api/v1/stores.py)
- [apps/api/src/schemas/store.py](file://apps/api/src/schemas/store.py)
- [apps/api/src/models/store.py](file://apps/api/src/models/store.py)
- [apps/api/src/services/store.py](file://apps/api/src/services/store.py)
- [apps/api/src/api/v1/salespeople.py](file://apps/api/src/api/v1/salespeople.py)
- [apps/api/src/schemas/salesperson.py](file://apps/api/src/schemas/salesperson.py)
- [apps/api/src/models/salesperson.py](file://apps/api/src/models/salesperson.py)
- [apps/api/src/services/salesperson.py](file://apps/api/src/services/salesperson.py)
- [apps/api/src/api/v1/recordings.py](file://apps/api/src/api/v1/recordings.py)
- [apps/api/src/schemas/recording.py](file://apps/api/src/schemas/recording.py)
- [apps/api/src/models/recording.py](file://apps/api/src/models/recording.py)
- [apps/api/src/services/recording.py](file://apps/api/src/services/recording.py)
- [apps/api/src/api/v1/conversations.py](file://apps/api/src/api/v1/conversations.py)
- [apps/api/src/schemas/conversation.py](file://apps/api/src/schemas/conversation.py)
- [apps/api/src/models/conversation.py](file://apps/api/src/models/conversation.py)
- [apps/api/src/services/conversation.py](file://apps/api/src/services/conversation.py)
- [apps/api/src/api/v1/search.py](file://apps/api/src/api/v1/search.py)
- [apps/api/src/services/search.py](file://apps/api/src/services/search.py)
- [apps/api/src/api/v1/analytics.py](file://apps/api/src/api/v1/analytics.py)
- [apps/api/src/schemas/analytics.py](file://apps/api/src/schemas/analytics.py)
- [apps/api/src/services/analytics.py](file://apps/api/src/services/analytics.py)
- [apps/api/src/workers/pipeline.py](file://apps/api/src/workers/pipeline.py)
- [apps/api/src/workers/celery_app.py](file://apps/api/src/workers/celery_app.py)
- [apps/api/src/workers/preprocessing.py](file://apps/api/src/workers/preprocessing.py)
- [apps/api/src/workers/transcription.py](file://apps/api/src/workers/transcription.py)
- [apps/api/src/workers/diarization.py](file://apps/api/src/workers/diarization.py)
- [apps/api/src/workers/segmentation.py](file://apps/api/src/workers/segmentation.py)
- [apps/api/src/workers/analysis.py](file://apps/api/src/workers/analysis.py)
- [apps/api/src/workers/scoring.py](file://apps/api/src/workers/scoring.py)
</cite>

## Update Summary
**Changes Made**
- Added comprehensive analytics endpoints for business intelligence and performance monitoring
- Enhanced recording management API with six-stage Celery-based processing pipeline
- Integrated Celery workers for asynchronous audio processing (preprocessing, transcription, diarization, segmentation, analysis, scoring)
- Implemented robust authentication schemas with enhanced role-based access control
- Added new analytics data models including weekly metrics, funnel stages, and performance comparisons
- Introduced Redis-backed Celery task queue for scalable background processing
- Enhanced API routing system with proper ordering and organization of endpoint groups

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
This document describes the Xsamaa AI Pipeline backend API. It covers all RESTful endpoints grouped by functional domains: Authentication, Brand Management, Store Operations, Salesperson Management, Recording Processing, Conversation Analysis, Analytics, and Search. For each endpoint, you will find HTTP methods, URL patterns, request/response schemas using Pydantic models, authentication requirements, and error responses. It also documents the dependency injection system, request/response validation patterns, error handling strategies, JWT token management, role-based access control, rate limiting considerations, API versioning strategy, and integration guidelines for client applications.

**Updated** The backend now features a comprehensive analytics system with six-stage Celery-based processing pipeline for audio recordings, enhanced security through operator role requirements, and streamlined endpoint definitions focused on core recording management workflows.

## Project Structure
The backend is a FastAPI application with a modular structure:
- Application entrypoint initializes the ASGI app, CORS middleware, and mounts the API v1 router.
- API v1 groups endpoints by domain (auth, brands, stores, salespeople, recordings, conversations, analytics, search).
- Domain routers depend on shared dependency injection helpers for authentication and authorization.
- Services encapsulate business logic and interact with SQLAlchemy async sessions.
- Schemas define request/response models validated by Pydantic.
- Models define ORM entities and relationships.
- Workers implement Celery-based background processing pipeline.
- Configuration centralizes environment-driven settings including JWT, storage, NVIDIA integration, and Redis queue.
- Analytics endpoints provide comprehensive business intelligence and performance monitoring.

```mermaid
graph TB
A["apps/api/src/main.py<br/>FastAPI app, CORS, include_router"] --> B["apps/api/src/api/v1/router.py<br/>APIRouter(prefix='/api/v1')"]
B --> C["apps/api/src/api/v1/auth.py<br/>Authentication endpoints (/auth)"]
B --> D["apps/api/src/api/v1/brands.py"]
B --> E["apps/api/src/api/v1/stores.py"]
B --> F["apps/api/src/api/v1/salespeople.py"]
B --> G["apps/api/src/api/v1/recordings.py<br/>Enhanced with OPERATOR role requirements"]
B --> H["apps/api/src/api/v1/conversations.py"]
B --> I["apps/api/src/api/v1/analytics.py<br/>New analytics endpoints"]
B --> J["apps/api/src/api/v1/search.py"]
K["apps/api/src/api/deps.py<br/>get_current_user, RoleChecker<br/>Enhanced role hierarchy"] --> C
K --> D
K --> E
K --> F
K --> G
K --> H
K --> I
K --> J
L["apps/api/src/config.py<br/>Settings"] --> A
M["apps/api/src/workers/celery_app.py<br/>Redis-backed task queue"] --> N["apps/api/src/workers/pipeline.py<br/>Six-stage processing pipeline"]
N --> O["apps/api/src/workers/preprocessing.py"]
N --> P["apps/api/src/workers/transcription.py"]
N --> Q["apps/api/src/workers/diarization.py"]
N --> R["apps/api/src/workers/segmentation.py"]
N --> S["apps/api/src/workers/analysis.py"]
N --> T["apps/api/src/workers/scoring.py"]
```

**Diagram sources**
- [apps/api/src/main.py:1-29](file://apps/api/src/main.py#L1-L29)
- [apps/api/src/api/v1/router.py:1-20](file://apps/api/src/api/v1/router.py#L1-L20)
- [apps/api/src/api/deps.py:1-67](file://apps/api/src/api/deps.py#L1-L67)
- [apps/api/src/config.py:1-52](file://apps/api/src/config.py#L1-L52)
- [apps/api/src/workers/celery_app.py:1-30](file://apps/api/src/workers/celery_app.py#L1-L30)
- [apps/api/src/workers/pipeline.py:1-34](file://apps/api/src/workers/pipeline.py#L1-L34)

**Section sources**
- [apps/api/src/main.py:1-29](file://apps/api/src/main.py#L1-L29)
- [apps/api/src/api/v1/router.py:1-20](file://apps/api/src/api/v1/router.py#L1-L20)
- [apps/api/src/api/deps.py:1-67](file://apps/api/src/api/deps.py#L1-L67)
- [apps/api/src/config.py:1-52](file://apps/api/src/config.py#L1-L52)

## Core Components
- FastAPI Application: Initializes app metadata, CORS, and mounts the API v1 router. Includes a health endpoint.
- API v1 Router: Prefixes all routes under /api/v1 and includes domain routers.
- Dependency Injection:
  - HTTP Bearer authentication via get_current_user.
  - Role-based access control via RoleChecker with prebuilt checkers for roles including new OPERATOR role.
- Configuration: Centralized settings for database, Redis, JWT, storage, NVIDIA integration, CORS, and app runtime.
- Services: Encapsulate CRUD and analytics operations for each domain.
- Schemas: Pydantic models for request/response validation.
- Models: SQLAlchemy ORM entities with relationships.
- Workers: Celery-based background processing pipeline for audio analysis.
- Analytics: Comprehensive business intelligence endpoints for performance monitoring.

**Updated** Enhanced role hierarchy now prioritizes operational roles with OPERATOR as the baseline requirement for core recording operations, plus comprehensive analytics capabilities for business insights.

**Section sources**
- [apps/api/src/main.py:1-29](file://apps/api/src/main.py#L1-L29)
- [apps/api/src/api/v1/router.py:1-20](file://apps/api/src/api/v1/router.py#L1-L20)
- [apps/api/src/api/deps.py:1-67](file://apps/api/src/api/deps.py#L1-L67)
- [apps/api/src/config.py:1-52](file://apps/api/src/config.py#L1-L52)

## Architecture Overview
The backend follows a layered architecture with enhanced processing capabilities:
- Presentation Layer: FastAPI routers and endpoints.
- Domain Layer: Services implementing business logic.
- Persistence Layer: SQLAlchemy async ORM with Postgres.
- External Integrations: NVIDIA APIs for STT/diarization/LLM/embeddings.
- Background Processing: Celery workers with Redis queue for six-stage audio processing pipeline.
- Security: JWT bearer tokens, bcrypt password hashing, role-based access control with enhanced operator-focused security model.
- Analytics: Comprehensive business intelligence with trend analysis and performance comparisons.

**Updated** The architecture now emphasizes operational security with OPERATOR role as the foundation for recording management workflows and includes a sophisticated six-stage Celery-based processing pipeline for audio analysis.

```mermaid
graph TB
subgraph "Presentation"
R1["Auth Router<br/>(/auth)"]
R2["Brands Router"]
R3["Stores Router"]
R4["Salespeople Router"]
R5["Recordings Router<br/>Enhanced OPERATOR requirements"]
R6["Conversations Router"]
R7["Analytics Router<br/>New analytics endpoints"]
R8["Search Router"]
end
subgraph "Domain Services"
S1["Auth Service"]
S2["Brand Service"]
S3["Store Service"]
S4["Salesperson Service"]
S5["Recording Service"]
S6["Conversation Service"]
S7["Analytics Service<br/>New"]
S8["Search Service"]
end
subgraph "Background Processing"
W1["Celery App<br/>Redis Queue"]
W2["Preprocessing Worker"]
W3["Transcription Worker"]
W4["Diarization Worker"]
W5["Segmentation Worker"]
W6["Analysis Worker"]
W7["Scoring Worker"]
P1["Processing Pipeline<br/>Six-stage chain"]
end
subgraph "Persistence"
P2["SQLAlchemy Async Session"]
P3["PostgreSQL"]
end
subgraph "Security"
C1["JWT Config"]
C2["Password Hashing"]
C3["RBAC<br/>Enhanced role hierarchy"]
end
R1 --> S1
R2 --> S2
R3 --> S3
R4 --> S4
R5 --> S5
R6 --> S6
R7 --> S7
R8 --> S8
S1 --> P2
S2 --> P2
S3 --> P2
S4 --> P2
S5 --> P2
S6 --> P2
S7 --> P2
S8 --> P2
P2 --> P3
C1 --> S1
C2 --> S1
C3 --> R1
C3 --> R2
C3 --> R3
C3 --> R4
C3 --> R5
C3 --> R6
C3 --> R7
C3 --> R8
W1 --> W2
W1 --> W3
W1 --> W4
W1 --> W5
W1 --> W6
W1 --> W7
P1 --> W2
P1 --> W3
P1 --> W4
P1 --> W5
P1 --> W6
P1 --> W7
```

**Diagram sources**
- [apps/api/src/main.py:1-29](file://apps/api/src/main.py#L1-L29)
- [apps/api/src/api/v1/router.py:1-20](file://apps/api/src/api/v1/router.py#L1-L20)
- [apps/api/src/api/deps.py:1-67](file://apps/api/src/api/deps.py#L1-L67)
- [apps/api/src/services/auth.py:1-55](file://apps/api/src/services/auth.py#L1-L55)
- [apps/api/src/services/brand.py:1-38](file://apps/api/src/services/brand.py#L1-L38)
- [apps/api/src/services/store.py:1-142](file://apps/api/src/services/store.py#L1-L142)
- [apps/api/src/services/salesperson.py](file://apps/api/src/services/salesperson.py)
- [apps/api/src/services/recording.py](file://apps/api/src/services/recording.py)
- [apps/api/src/services/conversation.py](file://apps/api/src/services/conversation.py)
- [apps/api/src/services/analytics.py:1-147](file://apps/api/src/services/analytics.py#L1-L147)
- [apps/api/src/services/search.py](file://apps/api/src/services/search.py)
- [apps/api/src/config.py:1-52](file://apps/api/src/config.py#L1-L52)
- [apps/api/src/workers/celery_app.py:1-30](file://apps/api/src/workers/celery_app.py#L1-L30)
- [apps/api/src/workers/pipeline.py:1-34](file://apps/api/src/workers/pipeline.py#L1-L34)

## Detailed Component Analysis

### Authentication
- Purpose: User login, token issuance, token refresh, and logout.
- Endpoints:
  - POST /api/v1/auth/login
    - Request: LoginRequest (email, password)
    - Response: LoginResponse (access_token, refresh_token, user)
    - Validation: Pydantic models enforce field presence and types.
    - Authentication: No prior auth required.
    - Errors: 401 Unauthorized for invalid credentials.
  - POST /api/v1/auth/refresh
    - Request: RefreshRequest (refresh_token)
    - Response: TokenResponse (access_token, refresh_token)
    - Validation: Pydantic models.
    - Authentication: Requires a valid refresh token.
    - Errors: 401 Unauthorized for invalid/expired refresh token.
  - POST /api/v1/auth/logout
    - Response: MessageResponse (message)
    - Notes: Stateless JWT; client discards tokens. Production-grade blockisting recommended.
- JWT Management:
  - Access token expiry configured via settings.
  - Refresh token expiry configured via settings.
  - Tokens encoded with HS256 and secret key from settings.
- RBAC:
  - Subsequent endpoints use get_current_user and RoleChecker to enforce permissions.

```mermaid
sequenceDiagram
participant Client as "Client"
participant Auth as "Auth Router"
participant Service as "Auth Service"
participant DB as "AsyncSession"
Client->>Auth : POST /api/v1/auth/login
Auth->>Service : authenticate_user(email, password)
Service->>DB : SELECT user WHERE email
DB-->>Service : User
Service-->>Auth : User or None
alt Valid credentials
Auth->>Service : create_access_token(sub)
Auth->>Service : create_refresh_token(sub)
Auth-->>Client : LoginResponse(access_token, refresh_token, user)
else Invalid credentials
Auth-->>Client : 401 Unauthorized
end
```

**Diagram sources**
- [apps/api/src/api/v1/auth.py:24-48](file://apps/api/src/api/v1/auth.py#L24-L48)
- [apps/api/src/services/auth.py:44-49](file://apps/api/src/services/auth.py#L44-L49)

**Section sources**
- [apps/api/src/api/v1/auth.py:1-82](file://apps/api/src/api/v1/auth.py#L1-L82)
- [apps/api/src/schemas/auth.py:1-36](file://apps/api/src/schemas/auth.py#L1-L36)
- [apps/api/src/services/auth.py:1-55](file://apps/api/src/services/auth.py#L1-L55)
- [apps/api/src/models/user.py:1-49](file://apps/api/src/models/user.py#L1-L49)
- [apps/api/src/api/deps.py:12-38](file://apps/api/src/api/deps.py#L12-L38)

### Brand Management
- Purpose: Manage brands (list/create/read/update).
- Endpoints:
  - GET /api/v1/brands
    - Response: List of BrandResponse
    - Authentication: Super Admin required.
  - POST /api/v1/brands
    - Request: BrandCreate (name, description?)
    - Response: BrandResponse
    - Authentication: Brand Admin or Super Admin required.
  - GET /api/v1/brands/{brand_id}
    - Path param: brand_id (UUID string)
    - Response: BrandResponse
    - Authentication: Brand Admin or Super Admin required.
    - Errors: 404 Not Found if brand does not exist.
  - PUT /api/v1/brands/{brand_id}
    - Path param: brand_id (UUID string)
    - Request: BrandUpdate (name?, description?)
    - Response: BrandResponse
    - Authentication: Super Admin required.
    - Errors: 404 Not Found if brand does not exist.
- Validation:
  - Requests validated by Pydantic BrandCreate/BrandUpdate.
  - Responses validated by BrandResponse (from_attributes enabled).
- Error Handling:
  - 404 Not Found for missing resources.

```mermaid
flowchart TD
Start(["GET /brands"]) --> CheckRole["RoleChecker: require_super_admin"]
CheckRole --> |Authorized| List["Service.list_brands()"]
CheckRole --> |Forbidden| Forbidden["403 Forbidden"]
List --> Ok["200 OK with list"]
Forbidden --> End(["End"])
Ok --> End
```

**Diagram sources**
- [apps/api/src/api/v1/brands.py:13-18](file://apps/api/src/api/v1/brands.py#L13-L18)
- [apps/api/src/api/deps.py:55-56](file://apps/api/src/api/deps.py#L55-L56)

**Section sources**
- [apps/api/src/api/v1/brands.py:1-53](file://apps/api/src/api/v1/brands.py#L1-L53)
- [apps/api/src/schemas/brand.py:1-22](file://apps/api/src/schemas/brand.py#L1-L22)
- [apps/api/src/models/brand.py:1-26](file://apps/api/src/models/brand.py#L1-L26)
- [apps/api/src/services/brand.py:1-38](file://apps/api/src/services/brand.py#L1-L38)
- [apps/api/src/api/deps.py:55-56](file://apps/api/src/api/deps.py#L55-L56)

### Store Operations
- Purpose: Manage stores, list with optional filtering, read store details, compute store metrics.
- Endpoints:
  - GET /api/v1/stores
    - Query: brand_id (optional UUID string)
    - Response: List of StoreResponse
    - Authentication: Operator required.
  - POST /api/v1/stores
    - Request: StoreCreate (name, brand_id, location?, working_hours?)
    - Response: StoreResponse
    - Authentication: Brand Admin or Super Admin required.
  - GET /api/v1/stores/{store_id}
    - Path param: store_id (UUID string)
    - Response: StoreResponse
    - Authentication: Operator required.
    - Errors: 404 Not Found if store does not exist.
  - GET /api/v1/stores/{store_id}/metrics
    - Path param: store_id (UUID string)
    - Response: StoreMetricsResponse
    - Authentication: Store Manager Up required.
    - Errors: 404 Not Found if store does not exist.
- Metrics:
  - Total salespeople, total recordings, total conversations.
  - Average performance score (average confidence from conversation analysis).
  - Conversion rate (percentage of SALE_MADE outcomes).
  - Top objection (most frequent objection across conversations).
- Validation:
  - Requests validated by StoreCreate/StoreUpdate.
  - Responses validated by StoreResponse and StoreMetricsResponse.
- Error Handling:
  - 404 Not Found for missing stores.

```mermaid
sequenceDiagram
participant Client as "Client"
participant Stores as "Stores Router"
participant Service as "Store Service"
participant DB as "AsyncSession"
Client->>Stores : GET /api/v1/stores/{store_id}/metrics
Stores->>Service : get_store_metrics(store_id)
Service->>DB : SELECT store, counts, avg confidence, conversions, objections
DB-->>Service : Aggregated metrics
Service-->>Stores : StoreMetricsResponse
Stores-->>Client : 200 OK
alt Store not found
Stores-->>Client : 404 Not Found
end
```

**Diagram sources**
- [apps/api/src/api/v1/stores.py:43-52](file://apps/api/src/api/v1/stores.py#L43-L52)
- [apps/api/src/services/store.py:53-141](file://apps/api/src/services/store.py#L53-L141)

**Section sources**
- [apps/api/src/api/v1/stores.py:1-53](file://apps/api/src/api/v1/stores.py#L1-L53)
- [apps/api/src/schemas/store.py:1-38](file://apps/api/src/schemas/store.py#L1-L38)
- [apps/api/src/models/store.py:1-32](file://apps/api/src/models/store.py#L1-L32)
- [apps/api/src/services/store.py:1-142](file://apps/api/src/services/store.py#L1-L142)

### Salesperson Management
- Purpose: Manage salespeople associated with stores.
- Endpoints:
  - GET /api/v1/salespeople
    - Query: store_id (optional UUID string)
    - Response: List of SalespersonResponse
    - Authentication: Operator required.
  - POST /api/v1/salespeople
    - Request: SalespersonCreate (name, email, store_id, ...)
    - Response: SalespersonResponse
    - Authentication: Store Manager Up required.
  - GET /api/v1/salespeople/{salesperson_id}
    - Path param: salesperson_id (UUID string)
    - Response: SalespersonResponse
    - Authentication: Operator required.
    - Errors: 404 Not Found if salesperson does not exist.
  - GET /api/v1/salespeople/{salesperson_id}/performance
    - Path param: salesperson_id (UUID string)
    - Response: SalespersonPerformanceResponse
    - Authentication: Salesperson Up required.
    - Errors: 404 Not Found if salesperson does not exist.
- Validation:
  - Requests validated by SalespersonCreate/Update.
  - Responses validated by SalespersonResponse.
- Error Handling:
  - 404 Not Found for missing salespeople.

**Section sources**
- [apps/api/src/api/v1/salespeople.py](file://apps/api/src/api/v1/salespeople.py)
- [apps/api/src/schemas/salesperson.py](file://apps/api/src/schemas/salesperson.py)
- [apps/api/src/models/salesperson.py](file://apps/api/src/models/salesperson.py)
- [apps/api/src/services/salesperson.py](file://apps/api/src/services/salesperson.py)

### Recording Processing
- Purpose: Manage audio recordings linked to salespeople with enhanced security requirements and comprehensive processing pipeline.
- Endpoints:
  - GET /api/v1/recordings
    - Query: page, page_size, status, salesperson_id, date_from, date_to
    - Response: Paginated recordings with filtering
    - Authentication: Operator required.
    - Pagination: Supports page and page_size parameters with bounds checking.
    - Filtering: Supports status, salesperson_id, and date range filters.
  - POST /api/v1/recordings/upload
    - Request: Multipart form with file, salesperson_id, recorded_at
    - Response: RecordingResponse
    - Authentication: Operator required.
    - File Upload: Validates file content and generates unique filenames.
    - Processing: Automatically starts six-stage AI processing pipeline via Celery workers.
  - GET /api/v1/recordings/{recording_id}
    - Path param: recording_id (UUID string)
    - Response: RecordingResponse
    - Authentication: Salesperson Up required.
    - Errors: 404 Not Found if recording does not exist.
  - GET /api/v1/recordings/{recording_id}/status
    - Path param: recording_id (UUID string)
    - Response: RecordingStatusResponse
    - Authentication: Salesperson Up required.
    - Errors: 404 Not Found if recording does not exist.
  - POST /api/v1/recordings/{recording_id}/reprocess
    - Path param: recording_id (UUID string)
    - Response: RecordingResponse
    - Authentication: Brand Admin required.
    - Errors: 404 Not Found if recording does not exist.
    - Validation: Only allows reprocessing of FAILED or COMPLETED recordings.
- Validation:
  - Requests validated by multipart form data and Pydantic models.
  - Responses validated by RecordingResponse and RecordingStatusResponse.
  - Date formats validated as ISO 8601 strings.
  - Page parameters validated with bounds checking.
- Error Handling:
  - 404 Not Found for missing recordings.
  - 400 Bad Request for validation errors and invalid states.
- Enhanced Security Model:
  - Core recording operations now require OPERATOR role as baseline.
  - Upload operations trigger automatic six-stage AI processing pipeline.
  - Reprocessing requires elevated Brand Admin privileges.
- Six-Stage Processing Pipeline:
  - Stage 1: Audio preprocessing (normalization, resampling, silence detection)
  - Stage 2: Transcription using NVIDIA Parakeet STT
  - Stage 3: Speaker diarization using NVIDIA NeMo
  - Stage 4: Conversation segmentation
  - Stage 5: AI conversation analysis
  - Stage 6: Salesperson performance scoring
- Celery Integration:
  - Redis-backed task queue for scalable background processing
  - Automatic retry mechanisms with exponential backoff
  - Time limits and monitoring for long-running tasks

**Updated** Recording management now features enhanced security with OPERATOR role as the minimum requirement for most operations, comprehensive six-stage Celery-based processing pipeline, and robust background task management.

```mermaid
sequenceDiagram
participant Client as "Client"
participant Recordings as "Recordings Router"
participant Service as "Recording Service"
participant Storage as "Storage Backend"
participant Pipeline as "Processing Pipeline"
participant Celery as "Celery Workers"
Client->>Recordings : POST /api/v1/recordings/upload
Recordings->>Service : validate_and_process_upload(file, salesperson_id)
Service->>Storage : upload(file_content, unique_filename)
Storage-->>Service : file_url
Service->>Service : create_recording_record()
Service->>Pipeline : start_processing_pipeline(recording_id)
Pipeline->>Celery : chain.apply_async()
Celery-->>Pipeline : processing_started
Service-->>Recordings : RecordingResponse
Recordings-->>Client : 201 Created
```

**Diagram sources**
- [apps/api/src/api/v1/recordings.py:56-84](file://apps/api/src/api/v1/recordings.py#L56-L84)
- [apps/api/src/services/recording.py:83-126](file://apps/api/src/services/recording.py#L83-L126)
- [apps/api/src/workers/pipeline.py:12-34](file://apps/api/src/workers/pipeline.py#L12-L34)

**Section sources**
- [apps/api/src/api/v1/recordings.py:1-125](file://apps/api/src/api/v1/recordings.py#L1-L125)
- [apps/api/src/schemas/recording.py:1-71](file://apps/api/src/schemas/recording.py#L1-L71)
- [apps/api/src/models/recording.py](file://apps/api/src/models/recording.py)
- [apps/api/src/services/recording.py:1-262](file://apps/api/src/services/recording.py#L1-L262)
- [apps/api/src/workers/pipeline.py:1-34](file://apps/api/src/workers/pipeline.py#L1-L34)
- [apps/api/src/workers/celery_app.py:1-30](file://apps/api/src/workers/celery_app.py#L1-L30)

### Conversation Analysis
- Purpose: Manage conversations derived from recordings and analyze insights.
- Endpoints:
  - GET /api/v1/conversations/{conversation_id}
    - Path param: conversation_id (UUID string)
    - Response: ConversationResponse
    - Authentication: Salesperson Up required.
    - Errors: 404 Not Found if conversation does not exist.
  - GET /api/v1/conversations/{conversation_id}/analysis
    - Path param: conversation_id (UUID string)
    - Response: ConversationAnalysisResponse
    - Authentication: Salesperson Up required.
    - Errors: 404 Not Found if analysis does not exist.
- Validation:
  - Responses validated by ConversationResponse and ConversationAnalysisResponse.
- Error Handling:
  - 404 Not Found for missing conversations or analyses.

**Section sources**
- [apps/api/src/api/v1/conversations.py:1-35](file://apps/api/src/api/v1/conversations.py#L1-L35)
- [apps/api/src/schemas/conversation.py:1-33](file://apps/api/src/schemas/conversation.py#L1-L33)
- [apps/api/src/models/conversation.py](file://apps/api/src/models/conversation.py)
- [apps/api/src/services/conversation.py](file://apps/api/src/services/conversation.py)

### Analytics
- Purpose: Provide comprehensive business intelligence and performance monitoring across brands, stores, and salespeople.
- Endpoints:
  - GET /api/v1/analytics/overview
    - Query: brand_id (optional UUID string), store_id (optional UUID string), date_from (optional date), date_to (optional date)
    - Response: AnalyticsOverviewResponse with comprehensive metrics
    - Authentication: Operator Up required.
    - Metrics Include:
      - Outcome distribution (SALE_MADE, LOST, etc.)
      - Top objections by frequency
      - Funnel stages (Conversations, Closing Attempts, Sales Made)
      - Score trends (daily averages)
      - Volume trends (conversation counts)
      - Store comparisons
      - Aggregate statistics (total conversations, average confidence, conversion rates)
  - GET /api/v1/analytics/salespeople-comparison
    - Query: brand_id (optional UUID string), store_id (optional UUID string)
    - Response: AnalyticsSalespeopleResponse with detailed performance comparisons
    - Authentication: Operator Up required.
    - Comparison Metrics Include:
      - Individual salesperson performance
      - Total conversations per salesperson
      - Average overall scores
      - Specialized skill scores (greeting, discovery, product knowledge, objection handling, closing)
      - Conversion rates by salesperson
- Data Scope:
  - Brand-level analytics: aggregates across all stores and salespeople within a brand
  - Store-level analytics: focuses on a specific store and its associated salespeople
  - Time-based filtering: supports date range queries for trend analysis
- Validation:
  - Requests validated by query parameters with bounds checking.
  - Responses validated by comprehensive analytics schemas.
- Error Handling:
  - Returns empty structures when no data is available within the specified scope.
  - Maintains consistent response format regardless of data availability.

**Updated** New analytics endpoints provide comprehensive business intelligence with detailed performance metrics, trend analysis, and comparative assessments across organizational hierarchies.

```mermaid
sequenceDiagram
participant Client as "Client"
participant Analytics as "Analytics Router"
participant Service as "Analytics Service"
participant DB as "AsyncSession"
Client->>Analytics : GET /api/v1/analytics/overview?brand_id=...
Analytics->>Service : get_analytics_overview(brand_id, store_id, date_range)
Service->>DB : Execute complex aggregations across multiple tables
DB-->>Service : Aggregated metrics and trends
Service-->>Analytics : AnalyticsOverviewResponse
Analytics-->>Client : 200 OK with comprehensive analytics data
```

**Diagram sources**
- [apps/api/src/api/v1/analytics.py:22-34](file://apps/api/src/api/v1/analytics.py#L22-L34)
- [apps/api/src/services/analytics.py:52-147](file://apps/api/src/services/analytics.py#L52-L147)

**Section sources**
- [apps/api/src/api/v1/analytics.py:1-46](file://apps/api/src/api/v1/analytics.py#L1-L46)
- [apps/api/src/schemas/analytics.py:1-295](file://apps/api/src/schemas/analytics.py#L1-L295)
- [apps/api/src/services/analytics.py:1-147](file://apps/api/src/services/analytics.py#L1-L147)

### Search Functionality
- Purpose: Provide search capabilities across relevant entities.
- Endpoints:
  - GET /api/v1/search
    - Query: q (search term), date_from, date_to, store_id, salesperson_id, outcome, limit
    - Response: Search results with conversations, analyses, recordings, and segments
    - Authentication: Salesperson Up required.
    - Semantic Search: Uses pgvector similarity for transcript segment matching.
    - Filtering: Supports temporal and categorical filters.
- Validation:
  - Requests validated by query parameters with bounds checking.
  - Responses validated by comprehensive result serialization.
- Error Handling:
  - Standard HTTP errors based on query conditions.

**Section sources**
- [apps/api/src/api/v1/search.py](file://apps/api/src/api/v1/search.py)
- [apps/api/src/services/search.py](file://apps/api/src/services/search.py)

## Dependency Analysis
- Router Composition:
  - API v1 router aggregates domain routers under /api/v1.
- Authentication Dependencies:
  - get_current_user validates bearer token and loads active user.
  - RoleChecker enforces role gates using prebuilt checkers with enhanced role hierarchy.
- Configuration:
  - Settings provide JWT secrets, expiry, CORS origins, storage, NVIDIA integration parameters, and Redis queue configuration.
- Service Coupling:
  - Services depend on AsyncSession and Pydantic schemas.
  - Services encapsulate SQL queries and aggregations.
- Background Processing:
  - Celery workers handle six-stage audio processing pipeline.
  - Redis queue manages task distribution and persistence.
  - Pipeline orchestrator coordinates worker chain execution.
- External Integrations:
  - NVIDIA APIs configured via settings; used by AI workers.
  - Redis configured via settings; used by Celery workers.

**Updated** Enhanced role hierarchy now includes OPERATOR as the foundational role for operational workflows, plus comprehensive analytics services and Celery-based background processing.

```mermaid
graph LR
Main["apps/api/src/main.py"] --> V1["apps/api/src/api/v1/router.py"]
V1 --> AuthR["apps/api/src/api/v1/auth.py"]
V1 --> BrandsR["apps/api/src/api/v1/brands.py"]
V1 --> StoresR["apps/api/src/api/v1/stores.py"]
V1 --> SalespR["apps/api/src/api/v1/salespeople.py"]
V1 --> RecR["apps/api/src/api/v1/recordings.py"]
V1 --> ConvR["apps/api/src/api/v1/conversations.py"]
V1 --> AnalyticsR["apps/api/src/api/v1/analytics.py"]
V1 --> SearchR["apps/api/src/api/v1/search.py"]
AuthR --> Deps["apps/api/src/api/deps.py"]
BrandsR --> Deps
StoresR --> Deps
SalespR --> Deps
RecR --> Deps
ConvR --> Deps
AnalyticsR --> Deps
SearchR --> Deps
Deps --> Conf["apps/api/src/config.py"]
AuthR --> AuthSvc["apps/api/src/services/auth.py"]
AuthSvc --> ModelsU["apps/api/src/models/user.py"]
AnalyticsR --> AnalyticsSvc["apps/api/src/services/analytics.py"]
RecR --> Pipeline["apps/api/src/workers/pipeline.py"]
Pipeline --> CeleryApp["apps/api/src/workers/celery_app.py"]
```

**Diagram sources**
- [apps/api/src/main.py:1-29](file://apps/api/src/main.py#L1-L29)
- [apps/api/src/api/v1/router.py:1-20](file://apps/api/src/api/v1/router.py#L1-L20)
- [apps/api/src/api/deps.py:1-67](file://apps/api/src/api/deps.py#L1-L67)
- [apps/api/src/config.py:1-52](file://apps/api/src/config.py#L1-L52)
- [apps/api/src/services/auth.py:1-55](file://apps/api/src/services/auth.py#L1-L55)
- [apps/api/src/services/analytics.py:1-147](file://apps/api/src/services/analytics.py#L1-L147)
- [apps/api/src/workers/pipeline.py:1-34](file://apps/api/src/workers/pipeline.py#L1-L34)
- [apps/api/src/workers/celery_app.py:1-30](file://apps/api/src/workers/celery_app.py#L1-L30)

**Section sources**
- [apps/api/src/api/v1/router.py:1-20](file://apps/api/src/api/v1/router.py#L1-L20)
- [apps/api/src/api/deps.py:1-67](file://apps/api/src/api/deps.py#L1-L67)
- [apps/api/src/config.py:1-52](file://apps/api/src/config.py#L1-L52)

## Performance Considerations
- Asynchronous Database: SQLAlchemy async sessions reduce blocking during I/O.
- Aggregation Queries: Store metrics compute counts and averages efficiently using SQL aggregation.
- Pagination: List endpoints support pagination with bounds checking to avoid large payloads.
- Caching: Introduce Redis caching for frequently accessed entities (brands, stores) to reduce DB load.
- Rate Limiting: Implement rate limiting at the gateway or middleware level to protect endpoints.
- Background Processing: Use Celery workers with Redis queue for six-stage audio processing pipeline to keep API responsive.
- Connection Pooling: Configure database connection pool sizes according to expected concurrency.
- Enhanced Security: OPERATOR role requirements streamline access control for operational workflows.
- Analytics Optimization: Complex aggregation queries in analytics endpoints are optimized for performance with proper indexing.
- Pipeline Scaling: Celery workers can be scaled horizontally to handle increased processing load.
- Task Monitoring: Built-in monitoring for long-running tasks with time limits and retry mechanisms.

**Updated** Performance improvements now include streamlined role checks, optimized operational workflows for recording management, comprehensive analytics query optimization, and scalable Celery-based background processing.

## Troubleshooting Guide
- Authentication Failures:
  - 401 Unauthorized on auth endpoints indicates invalid credentials or token issues.
  - 401 Unauthorized after login suggests token decoding failure or wrong token type.
  - 403 Forbidden indicates insufficient permissions; verify role requirements.
- Resource Not Found:
  - 404 Not Found for GET endpoints usually means the resource ID does not exist.
- Validation Errors:
  - Pydantic validation errors occur when request fields are missing or mismatched types.
  - Date format errors for ISO 8601 validation failures.
  - Page parameter errors for out-of-bounds pagination values.
- Health Check:
  - GET /health returns application status and environment.
- Enhanced Security Issues:
  - 403 Forbidden for OPERATOR role violations on recording operations.
  - Re-processing errors for invalid recording states.
- Analytics Issues:
  - Empty analytics responses indicate no data within the specified scope or date range.
  - Performance degradation on complex analytics queries may require query optimization.
- Background Processing Issues:
  - Celery worker failures: check Redis connectivity and task queue status.
  - Pipeline timeouts: verify NVIDIA API availability and processing time limits.
  - Task retry loops: examine retry configurations and error logs.

**Updated** Added troubleshooting guidance for new OPERATOR role requirements, enhanced security model, comprehensive analytics endpoints, and Celery-based background processing pipeline.

**Section sources**
- [apps/api/src/api/v1/auth.py:24-48](file://apps/api/src/api/v1/auth.py#L24-L48)
- [apps/api/src/api/v1/auth.py:51-74](file://apps/api/src/api/v1/auth.py#L51-L74)
- [apps/api/src/api/v1/brands.py:36-39](file://apps/api/src/api/v1/brands.py#L36-L39)
- [apps/api/src/api/v1/stores.py:37-41](file://apps/api/src/api/v1/stores.py#L37-L41)
- [apps/api/src/api/deps.py:12-38](file://apps/api/src/api/deps.py#L12-L38)
- [apps/api/src/main.py:26-29](file://apps/api/src/main.py#L26-L29)

## Conclusion
The Xsamaa AI Pipeline backend provides a well-structured, secure, and extensible API surface with enhanced operational security through the new OPERATOR role model and comprehensive analytics capabilities. It leverages FastAPI's automatic OpenAPI generation, robust dependency injection, Pydantic validation, and role-based access control. The modular design supports future enhancements such as rate limiting, Redis caching, and Celery-backed asynchronous processing while maintaining streamlined workflows focused on core recording management operations. The addition of six-stage audio processing pipeline and comprehensive analytics endpoints positions the platform for advanced business intelligence and performance monitoring.

**Updated** The simplified architecture with enhanced security and comprehensive analytics ensures operational efficiency while maintaining appropriate access controls for different user roles and providing deep insights into sales performance and conversation quality.

## Appendices

### Authentication Flow and RBAC
- JWT Token Lifecycle:
  - Login issues access and refresh tokens with configured expirations.
  - Refresh endpoint renews tokens using a refresh token of specific type.
  - Logout is stateless; clients should discard tokens; consider blockisting in production.
- Role-Based Access Control:
  - get_current_user loads the active user from the access token.
  - RoleChecker enforces allowed roles per endpoint with enhanced hierarchy.
  - Prebuilt checkers:
    - require_super_admin
    - require_brand_admin_up
    - require_store_manager_up
    - require_salesperson_up
    - require_operator (NEW)
    - require_operator_up (NEW)

**Updated** Enhanced role hierarchy now includes OPERATOR as the foundational role for operational workflows and OPERATOR_UP for enhanced access to analytics and administrative functions.

```mermaid
sequenceDiagram
participant Client as "Client"
participant Auth as "Auth Router"
participant Service as "Auth Service"
participant RBAC as "RoleChecker"
participant Endpoint as "Domain Endpoint"
Client->>Auth : POST /api/v1/auth/login
Auth->>Service : authenticate_user()
Service-->>Auth : User
Auth-->>Client : LoginResponse
Client->>Endpoint : GET /api/v1/... (with Authorization : Bearer)
Endpoint->>RBAC : require_* role checker
RBAC->>Service : get_user_by_id()
Service-->>RBAC : User
RBAC-->>Endpoint : Authorized User
Endpoint-->>Client : Response
```

**Diagram sources**
- [apps/api/src/api/v1/auth.py:24-48](file://apps/api/src/api/v1/auth.py#L24-L48)
- [apps/api/src/services/auth.py:44-54](file://apps/api/src/services/auth.py#L44-L54)
- [apps/api/src/api/deps.py:12-38](file://apps/api/src/api/deps.py#L12-L38)
- [apps/api/src/api/deps.py:41-51](file://apps/api/src/api/deps.py#L41-L51)

**Section sources**
- [apps/api/src/api/v1/auth.py:1-82](file://apps/api/src/api/v1/auth.py#L1-L82)
- [apps/api/src/services/auth.py:1-55](file://apps/api/src/services/auth.py#L1-L55)
- [apps/api/src/api/deps.py:1-67](file://apps/api/src/api/deps.py#L1-L67)

### API Versioning Strategy
- Versioning: All endpoints are prefixed with /api/v1.
- Migration Plan: Future breaking changes should introduce /api/v2 while maintaining /api/v1 for backward compatibility.

**Section sources**
- [apps/api/src/api/v1/router.py:11-19](file://apps/api/src/api/v1/router.py#L11-L19)

### Integration Guidelines for Client Applications
- Authentication:
  - Use POST /api/v1/auth/login to obtain access and refresh tokens.
  - Attach Authorization: Bearer <access_token> to protected requests.
  - On receiving 401 Unauthorized, use POST /api/v1/auth/refresh with a valid refresh token to renew tokens.
- Enhanced Security Requirements:
  - OPERATOR role required for most recording operations (upload, list, status).
  - Salesperson Up role required for conversation access.
  - Enhanced Operator Up role required for analytics endpoints.
  - Elevated privileges required for administrative operations (reprocessing, brand/store management).
- Analytics Integration:
  - Use /api/v1/analytics/overview for comprehensive business intelligence dashboards.
  - Use /api/v1/analytics/salespeople-comparison for individual performance tracking.
  - Support date range filtering for trend analysis.
- Background Processing:
  - Monitor recording status endpoints for processing completion.
  - Implement retry logic for failed processing attempts.
  - Handle pipeline timeouts and worker failures gracefully.
- Error Handling:
  - Clients should parse 400/401/403/404 responses and surface user-friendly messages.
  - Pay special attention to OPERATOR role violations, recording state errors, and analytics data availability.
- CORS:
  - Ensure the frontend origin is included in allowed origins.
- Rate Limiting:
  - Implement client-side retries with exponential backoff on 429 responses.
- Health Monitoring:
  - Poll GET /health to verify service availability.

**Updated** Added integration guidelines for new OPERATOR role requirements, enhanced security model, comprehensive analytics endpoints, and Celery-based background processing pipeline.

**Section sources**
- [apps/api/src/main.py:15-21](file://apps/api/src/main.py#L15-L21)
- [apps/api/src/api/v1/auth.py:24-48](file://apps/api/src/api/v1/auth.py#L24-L48)
- [apps/api/src/api/v1/auth.py:51-74](file://apps/api/src/api/v1/auth.py#L51-L74)
- [apps/api/src/main.py:26-29](file://apps/api/src/main.py#L26-L29)
- [apps/api/src/api/v1/analytics.py:22-46](file://apps/api/src/api/v1/analytics.py#L22-L46)
- [apps/api/src/workers/pipeline.py:12-34](file://apps/api/src/workers/pipeline.py#L12-L34)

### Celery Processing Pipeline Architecture
- Pipeline Stages:
  - Stage 1: Audio preprocessing (preprocess_audio)
  - Stage 2: Speech-to-text transcription (transcribe_audio_task)
  - Stage 3: Speaker diarization (diarize_audio)
  - Stage 4: Conversation segmentation (segment_conversations)
  - Stage 5: AI analysis (analyze_conversations)
  - Stage 6: Performance scoring (score_salesperson)
- Task Configuration:
  - Redis backend for task persistence and coordination
  - Automatic retry with exponential backoff
  - Time limits (soft: 1 hour, hard: 2 hours) for long-running tasks
  - Prefetch multiplier set to 1 for fair task distribution
- Monitoring:
  - Task tracking and progress monitoring
  - Error handling and recovery mechanisms
  - Performance metrics and queue statistics

**Section sources**
- [apps/api/src/workers/pipeline.py:1-34](file://apps/api/src/workers/pipeline.py#L1-L34)
- [apps/api/src/workers/celery_app.py:1-30](file://apps/api/src/workers/celery_app.py#L1-L30)
- [apps/api/src/workers/preprocessing.py:106-126](file://apps/api/src/workers/preprocessing.py#L106-L126)
- [apps/api/src/workers/transcription.py](file://apps/api/src/workers/transcription.py)
- [apps/api/src/workers/diarization.py](file://apps/api/src/workers/diarization.py)
- [apps/api/src/workers/segmentation.py](file://apps/api/src/workers/segmentation.py)
- [apps/api/src/workers/analysis.py](file://apps/api/src/workers/analysis.py)
- [apps/api/src/workers/scoring.py:235-272](file://apps/api/src/workers/scoring.py#L235-L272)
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from pathlib import Path
import shutil
import os

from dotenv import load_dotenv
from groq import Groq
from fastapi import Depends

from backend.app.rag_pipeline import (
    build_text_context,
    build_baseline_context
)
from backend.app.retrieval_plan import build_retrieval_plan
from backend.app.ingest_pipeline import ingest_file
from backend.app.vector_store import search_chunks
from backend.app.database import get_connection, init_database
from backend.app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_user_id_from_token,
)


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# GROQ
# ============================================================

groq_client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

GROQ_MODEL = "openai/gpt-oss-20b"


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="RAG Optimization Engine",
    description=(
        "Permission-aware and cost-optimized "
        "RAG system with text, table and figure processing."
    ),
    version="0.2.0"
)

# ============================================================
# AUTHENTICATION
# ============================================================

security = HTTPBearer()


@app.on_event("startup")
def startup():
    init_database()


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/auth/register")
def register(request: RegisterRequest):

    name = request.name.strip()
    email = request.email.strip().lower()
    password = request.password

    if not name or not email or not password:
        raise HTTPException(
            status_code=400,
            detail="Name, email and password are required."
        )

    if len(password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters."
        )

    connection = get_connection()
    cursor = connection.cursor()

    existing_user = cursor.execute(
        "SELECT id FROM users WHERE email = ?",
        (email,)
    ).fetchone()

    if existing_user:
        connection.close()

        raise HTTPException(
            status_code=400,
            detail="Email already registered."
        )

    password_hash = hash_password(password)

    cursor.execute(
        """
        INSERT INTO users (name, email, password_hash)
        VALUES (?, ?, ?)
        """,
        (name, email, password_hash)
    )

    connection.commit()

    user_id = cursor.lastrowid

    connection.close()

    token = create_access_token(user_id)

    return {
        "message": "Registration successful.",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "name": name,
            "email": email
        }
    }


@app.post("/auth/login")
def login(request: LoginRequest):

    email = request.email.strip().lower()

    connection = get_connection()
    cursor = connection.cursor()

    user = cursor.execute(
        """
        SELECT id, name, email, password_hash
        FROM users
        WHERE email = ?
        """,
        (email,)
    ).fetchone()

    connection.close()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    if not verify_password(
        request.password,
        user["password_hash"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    token = create_access_token(user["id"])

    return {
        "message": "Login successful.",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"]
        }
    }


@app.get("/auth/me")
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):

    user_id = get_user_id_from_token(
        credentials.credentials
    )

    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token."
        )

    connection = get_connection()
    cursor = connection.cursor()

    user = cursor.execute(
        """
        SELECT id, name, email, created_at
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()

    connection.close()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found."
        )

    return {
        "user": dict(user)
    }
# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# CUSTOM OPENAPI
# ============================================================

def custom_openapi():

    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # OpenAPI 3.0.3 for better upload compatibility
    schema["openapi"] = "3.0.3"

    schemas = (
        schema
        .get("components", {})
        .get("schemas", {})
    )

    for schema_data in schemas.values():

        properties = schema_data.get(
            "properties",
            {}
        )

        for property_data in properties.values():

            # Multiple uploaded files
            if (
                property_data.get("type") == "array"
                and isinstance(
                    property_data.get("items"),
                    dict
                )
            ):

                items = property_data["items"]

                if "contentMediaType" in items:

                    items.pop(
                        "contentMediaType",
                        None
                    )

                    items["type"] = "string"
                    items["format"] = "binary"

            # Single uploaded file
            if (
                property_data.get("type") == "string"
                and "contentMediaType" in property_data
            ):

                property_data.pop(
                    "contentMediaType",
                    None
                )

                property_data["format"] = "binary"

    app.openapi_schema = schema

    return app.openapi_schema


app.openapi = custom_openapi


# ============================================================
# DIRECTORIES
# ============================================================

DOCUMENTS_DIR = Path(
    "data/documents"
)

DOCUMENTS_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# REQUEST MODELS
# ============================================================

class ChatRequest(BaseModel):

    question: str


class AskRequest(BaseModel):
    question: str
    document_ids: list[str] = []


class PipelineEvaluationRequest(AskRequest):
    pipeline: str


class SearchRequest(BaseModel):

    question: str
    n_results: int = 5
    source: str | None = None


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "message": (
            "RAG Optimization Engine "
            "is running successfully."
        ),
        "version": "0.2.0",
        "features": [
            "Text Retrieval",
            "Table Processing",
            "Figure Extraction",
            "Semantic Search",
            "Reranking",
            "Context Optimization",
            "Groq Generation"
        ],
        "gpu_service": False,
        "colpali": False
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "service": "RAG Optimization Engine"
    }


# ============================================================
# SEARCH ENDPOINT
# ============================================================

@app.get("/search")
def search_endpoint(
    question: str,
    n_results: int = 5,
    source: str | None = None
):

    if not question.strip():

        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    if n_results < 1:

        raise HTTPException(
            status_code=400,
            detail="n_results must be at least 1."
        )

    results = search_chunks(
        question=question,
        n_results=n_results,
        source=source
    )

    documents = results.get(
        "documents",
        [[]]
    )[0]

    metadatas = results.get(
        "metadatas",
        [[]]
    )[0]

    distances = results.get(
        "distances",
        [[]]
    )[0]

    output = []

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances
    ):

        output.append({
            "document": document,
            "metadata": metadata,
            "distance": distance
        })

    return {
        "question": question,
        "count": len(output),
        "results": output
    }


# ============================================================
# SIMPLE CHAT ENDPOINT
# ============================================================

@app.post("/chat")
def chat(request: ChatRequest):

    if not request.question.strip():

        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    response = (
        groq_client
        .chat
        .completions
        .create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": request.question
                }
            ],
            temperature=0
        )
    )

    return {
        "question": request.question,
        "answer": (
            response
            .choices[0]
            .message
            .content
        )
    }


# ============================================================
# RAG ANSWER
# ============================================================

@app.post("/ask")
def ask_endpoint(
    request: AskRequest
):

    question = request.question.strip()

    if not question:

        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    try:

        (
            final_documents,
            final_metadata,
            final_scores,
            tokens_used,
            available_budget
        ) = build_text_context(
            request.question,
            sources=request.document_ids
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"RAG retrieval failed: {error}"
        )

    # --------------------------------------------------------
    # No relevant context
    # --------------------------------------------------------

    if not final_documents:

        return {
            "answer": (
                "I don't know based on "
                "the provided documents."
            ),
            "context": [],
            "metadata": [],
            "scores": [],
            "available_budget": available_budget,
            "tokens_used": tokens_used,
            "tokens_remaining": (
                available_budget - tokens_used
            )
        }

    # --------------------------------------------------------
    # Build context
    # --------------------------------------------------------

    context_parts = []

    for index, document in enumerate(
        final_documents
    ):

        metadata = {}

        if index < len(final_metadata):

            metadata = final_metadata[index]

        source = metadata.get(
            "source",
            "Unknown source"
        )

        element_type = metadata.get(
            "type",
            "text"
        )

        context_parts.append(
            f"""
Source: {source}
Content type: {element_type}

{document}
"""
        )

    context = "\n\n".join(
        context_parts
    )

    # --------------------------------------------------------
    # Final prompt
    # --------------------------------------------------------

    prompt = f"""
Answer the question using ONLY the
provided document context.

The context may contain:

- normal text
- tables
- figure information
- extracted document elements

Use the information that is relevant
to the question.

Do not invent information.

If the answer is not present in the
provided context, say:

"I don't know based on the provided documents."

Context:
{context}

Question:
{question}
"""

    # --------------------------------------------------------
    # Groq
    # --------------------------------------------------------

    try:

        response = (
            groq_client
            .chat
            .completions
            .create(
                model=GROQ_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0
            )
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"LLM generation failed: {error}"
        )

    answer = (
        response
        .choices[0]
        .message
        .content
    )

    # --------------------------------------------------------
    # Return
    # --------------------------------------------------------

    return {
        "answer": answer,
        "context": final_documents,
        "metadata": final_metadata,
        "scores": final_scores,
        "available_budget": available_budget,
        "tokens_used": tokens_used,
        "tokens_remaining": (
            available_budget - tokens_used
        )
    }




@app.post("/ask-baseline")
def ask_baseline_endpoint(request: AskRequest):
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    try:
        (
            documents,
            metadata,
            scores,
            tokens_used,
            available_budget
        ) = build_baseline_context(
            question,
            sources=request.document_ids
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Baseline RAG retrieval failed: {error}"
        )

    if not documents:
        return {
            "answer": (
                "I don't know based on "
                "the provided documents."
            ),
            "context": [],
            "metadata": [],
            "scores": [],
            "available_budget": available_budget,
            "tokens_used": tokens_used,
            "tokens_remaining": max(
                0, available_budget - tokens_used
            )
        }

    context_parts = []

    for index, document in enumerate(documents):
        item_metadata = (
            metadata[index]
            if index < len(metadata)
            else {}
        )

        source = item_metadata.get(
            "source", "Unknown source"
        )
        element_type = item_metadata.get(
            "type", "text"
        )

        context_parts.append(
            f"Source: {source}\n"
            f"Content type: {element_type}\n\n"
            f"{document}"
        )

    context = "\n\n".join(context_parts)

    prompt = f"""
Answer the question using ONLY the
provided document context.

Use relevant information from the context.
Do not invent information.

If the answer is not present in the context, say:
"I don't know based on the provided documents."

Context:
{context}

Question:
{question}
"""

    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0
        )

        answer = response.choices[0].message.content

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Baseline LLM generation failed: {error}"
        )

    return {
        "answer": answer,
        "context": documents,
        "metadata": metadata,
        "scores": scores,
        "available_budget": available_budget,
        "tokens_used": tokens_used,
        "tokens_remaining": max(
            0, available_budget - tokens_used
        )
    }



class PipelineEvaluationRequest(AskRequest):
    pipeline: str


@app.post("/evaluate-pipeline")
def evaluate_pipeline_endpoint(
    request: PipelineEvaluationRequest
):
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    pipeline_options = {
        "reranker": {
            "use_reranker": True,
            "use_redundancy_filter": False,
            "use_context_optimizer": False,
        },
        "reranker_redundancy": {
            "use_reranker": True,
            "use_redundancy_filter": True,
            "use_context_optimizer": False,
        },
    }

    options = pipeline_options.get(request.pipeline)

    if options is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid pipeline. Use 'reranker' or "
                "'reranker_redundancy'."
            )
        )

    try:
        (
            documents,
            metadata,
            scores,
            tokens_used,
            available_budget,
        ) = build_text_context(
            question,
            sources=request.document_ids,
            **options,
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline evaluation failed: {error}"
        )

    if not documents:
        return {
            "answer": (
                "I don't know based on the provided documents."
            ),
            "context": [],
            "metadata": [],
            "scores": [],
            "tokens_used": tokens_used,
            "available_budget": available_budget,
        }

    context_parts = []

    for index, document in enumerate(documents):
        item_metadata = (
            metadata[index] if index < len(metadata) else {}
        )
        source = item_metadata.get("source", "Unknown source")
        element_type = item_metadata.get("type", "text")

        context_parts.append(
            f"Source: {source}\n"
            f"Content type: {element_type}\n\n"
            f"{document}"
        )

    context = "\n\n".join(context_parts)

    prompt = f"""
Answer the question using ONLY the provided document context.
Do not invent information.

If the answer is not present, say:
"I don't know based on the provided documents."

Context:
{context}

Question:
{question}
"""

    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        answer = response.choices[0].message.content or ""
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"LLM generation failed: {error}"
        )

    return {
        "answer": answer,
        "context": documents,
        "metadata": metadata,
        "scores": scores,
        "tokens_used": tokens_used,
        "available_budget": available_budget,
    }



@app.post("/evaluate-pipeline")
def evaluate_pipeline_endpoint(request: AskRequest):
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    # Keep the two intermediate configurations fixed.
    # The existing /ask endpoint remains unchanged.
    try:
        (
            documents,
            metadata,
            scores,
            tokens_used,
            available_budget
        ) = build_text_context(
            question,
            sources=request.document_ids,
            use_reranker=True,
            use_redundancy_filter=(
                request.pipeline == "reranker_redundancy"
            ),
            use_context_optimizer=False
        )

        if request.pipeline == "reranker":
            # The function above already disabled the
            # redundancy filter and context optimizer.
            pass

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline evaluation failed: {error}"
        )

    if not documents:
        return {
            "answer": (
                "I don't know based on the provided documents."
            ),
            "context": [],
            "metadata": [],
            "scores": [],
            "tokens_used": tokens_used,
            "available_budget": available_budget
        }

    context = "\n\n".join(documents)

    prompt = f"""
Answer the question using ONLY the provided context.
Do not invent information.
If the answer is not present, say:
"I don't know based on the provided documents."

Context:
{context}

Question:
{question}
"""

    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        answer = response.choices[0].message.content or ""

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"LLM generation failed: {error}"
        )

    return {
        "answer": answer,
        "context": documents,
        "metadata": metadata,
        "scores": scores,
        "tokens_used": tokens_used,
        "available_budget": available_budget
    }


# ============================================================
# DOCUMENT UPLOAD
# ============================================================

@app.post("/documents/upload")
async def upload_documents(
    files: list[UploadFile] = File(
        description="Upload PDF or TXT files"
    ),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    user_id = get_user_id_from_token(
        credentials.credentials
    )

    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token."
        )

    if not files:
        raise HTTPException(
            status_code=400,
            detail="No files uploaded."
        )

    if len(files) > 5:

        raise HTTPException(
            status_code=400,
            detail=(
                "Maximum 5 files can be "
                "uploaded at once."
            )
        )

    uploaded = []

    for file in files:

        if not file.filename:

            raise HTTPException(
                status_code=400,
                detail="File name is missing."
            )

        extension = (
            Path(file.filename)
            .suffix
            .lower()
        )

        # ----------------------------------------------------
        # Supported formats
        # ----------------------------------------------------

        if extension not in [
            ".pdf",
            ".txt"
        ]:

            raise HTTPException(
                status_code=400,
                detail=(
                    f"{file.filename} is not supported. "
                    "Only PDF and TXT files are allowed."
                )
            )

        # ----------------------------------------------------
        # Save file
        # ----------------------------------------------------

        file_path = (
            DOCUMENTS_DIR /
            file.filename
        )

        try:

            with open(
                file_path,
                "wb"
            ) as buffer:

                shutil.copyfileobj(
                    file.file,
                    buffer
                )

        except Exception as error:

            raise HTTPException(
                status_code=500,
                detail=(
                    f"Failed to save "
                    f"{file.filename}: {error}"
                )
            )

        # ----------------------------------------------------
        # Index document
        # ----------------------------------------------------

        try:

            index_result = ingest_file(
                file_path
            )

        except Exception as error:

            raise HTTPException(
                status_code=500,
                detail=(
                    f"Failed to index "
                    f"{file.filename}: {error}"
                )
            )

        # ----------------------------------------------------
        # Build response
        # ----------------------------------------------------

        uploaded.append({
            "filename": file.filename,
            "path": str(file_path),
            "status": index_result.get(
                "status",
                "indexed"
            ),
            "pages": index_result.get(
                "pages"
            ),
            "chunks": index_result.get(
                "chunks",
                0
            ),
            "tables": index_result.get(
                "tables",
                0
            ),
            "figures": index_result.get(
                "figures",
                0
            )
        })

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO documents (
                user_id,
                filename,
                original_name,
                pages,
                size,
                status,
                chunks,
                tables_count,
                figures
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                file.filename,
                file.filename,
                index_result.get("pages") or 0,
                file_path.stat().st_size,
                index_result.get("status", "indexed"),
                index_result.get("chunks", 0),
                index_result.get("tables", 0),
                index_result.get("figures", 0),
            )
        )

        connection.commit()
        connection.close()

    return {
        "message": (
            "Files uploaded and indexed successfully."
        ),
        "files": uploaded
    }


# ============================================================
# DOCUMENT LIST
# ============================================================

@app.get("/documents")
def list_documents(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):

    user_id = get_user_id_from_token(
        credentials.credentials
    )

    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token."
        )

    connection = get_connection()
    cursor = connection.cursor()

    documents = cursor.execute(
        """
        SELECT
            id,
            filename,
            original_name,
            pages,
            size,
            status,
            chunks,
            tables_count,
            figures,
            created_at
        FROM documents
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,)
    ).fetchall()

    connection.close()

    return {
        "documents": [dict(document) for document in documents],
        "count": len(documents)
    }
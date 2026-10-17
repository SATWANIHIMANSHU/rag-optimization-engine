import chromadb
import ollama


client = chromadb.PersistentClient(
    path="./data/chroma"
)


collection = client.get_or_create_collection(
    name="documents"
)


def store_chunks(chunks):

    if not chunks:
        return

    ids = []
    embeddings = []
    documents = []
    metadatas = []

    for index, chunk in enumerate(chunks):

        text = chunk["text"]

        response = ollama.embed(
            model="nomic-embed-text",
            input=text
        )

        embedding = response["embeddings"][0]

        source = chunk["source"]

        element_id = chunk["element_id"]

        chunk_id = (
            f"{source}_{element_id}"
        )

        metadata = {
            "source": source,
            "type": chunk["type"],
            "element_id": element_id
        }

        ids.append(chunk_id)
        embeddings.append(embedding)
        documents.append(text)
        metadatas.append(metadata)

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )

    print(
        f"Stored/updated {len(chunks)} multimodal chunks"
    )


def search_chunks(
    question,
    n_results=5,
    source=None
):

    response = ollama.embed(
        model="nomic-embed-text",
        input=question
    )

    query_embedding = response["embeddings"][0]

    where = None

    if source:
        where = {
            "source": source
        }

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where
    )

    return results


def reset_collection():

    global collection

    try:
        client.delete_collection(
            name="documents"
        )
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name="documents"
    )

    print(
        "ChromaDB collection reset."
    )
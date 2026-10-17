const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

export async function uploadDocuments(files) {
  const formData = new FormData();

  files.forEach((file) => {
    formData.append("files", file);
  });

  const token = localStorage.getItem("access_token");

  const response = await fetch(
    `${API_BASE}/documents/upload`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    }
  );

  if (!response.ok) {
    throw new Error(
      `Upload failed: ${response.status}`
    );
  }

  return response.json();
}
export async function askQuestion(
  question,
  documentIds = []
) {
  const response = await fetch(
    `${API_BASE}/ask`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question,
        document_ids: documentIds,
      }),
    }
  );

  if (!response.ok) {
    throw new Error(
      `Question request failed: ${response.status}`
    );
  }

  return response.json();
}

export { API_BASE };
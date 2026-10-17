import React, { useEffect, useState } from "react";

import Sidebar from "./components/Sidebar";
import TopBar from "./components/TopBar";
import UploadModal from "./components/UploadModal";

import Workspace from "./pages/Workspace";
import Documents from "./pages/Documents";
import Chat from "./pages/Chat";
import Settings from "./pages/Settings";
import Login from "./pages/Login";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

function App() {
  const [user, setUser] = useState(() => {
  const savedUser = localStorage.getItem("user");

  return savedUser
    ? JSON.parse(savedUser)
    : null;
});
  const [page, setPage] = useState("workspace");
  const [upload, setUpload] = useState(false);

  const [docs, setDocs] = useState([]);

  const [selected, setSelected] = useState([]);

  useEffect(() => {
  if (!user) return;

  const loadDocuments = async () => {
    try {
      const token = localStorage.getItem("access_token");

      const response = await fetch(`${API_BASE}/documents`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to load documents.");
      }

      const data = await response.json();

      const backendDocuments = (data.documents || []).map(
        (document) => ({
          id: document.id,
          name: document.original_name || document.filename,
          pages: document.pages || 0,
          size: document.size
            ? (document.size / 1048576).toFixed(1) + " MB"
            : "0 MB",
          status: document.status || "indexed",
          progress:
            document.status === "indexed" ? 100 : 0,
          processedPages:
            document.status === "indexed"
              ? document.pages || 0
              : 0,
        })
      );

      setDocs(backendDocuments);
    } catch (error) {
      console.error("Failed to load documents:", error);
      setDocs([]);
    }
  };

  loadDocuments();
}, [user]);

const add = (files, result) => {
  const newDocuments = files.map((file, index) => {
    const backendFile = result?.files?.find(
      (item) => item.filename === file.name
    );

    const totalPages = backendFile?.pages || 1;

    return {
      id: Date.now() + index,
      name: file.name,
      pages: totalPages,
      size: (file.size / 1048576).toFixed(1) + " MB",
      status: result ? "indexed" : "processing",
      progress: result ? 100 : 0,
      processedPages: result
        ? totalPages
        : 0,
    };
  });

  setDocs((current) => [
    ...newDocuments,
    ...current,
  ]);

  setPage("documents");

  return newDocuments.map(
    (document) => document.id
  );
};

const updateUploadedDocuments = (
  documentIds,
  files,
  result
) => {
  setDocs((current) =>
    current.map((document) => {
      const index = documentIds.indexOf(
        document.id
      );

      if (index === -1) {
        return document;
      }

      const file = files[index];

      const backendFile = result?.files?.find(
        (item) => item.filename === file.name
      );

      const totalPages =
        backendFile?.pages ||
        document.pages ||
        1;

      return {
        ...document,
        pages: totalPages,
        status: "indexed",
        progress: 100,
        processedPages: totalPages,
      };
    })
  );
};

  // useEffect(() => {
  //   const processingDocuments = docs.filter(
  //     (document) => document.status === "processing"
  //   );

  //   if (!processingDocuments.length) return;

  //   const timer = setInterval(() => {
  //     setDocs((current) =>
  //       current.map((document) => {
  //         if (document.status !== "processing") {
  //           return document;
  //         }

  //         const totalPages = Number(document.pages) || 1;

  //         const nextPage = Math.min(
  //           (document.processedPages || 0) + 1,
  //           totalPages
  //         );

  //         const progress = Math.round(
  //           (nextPage / totalPages) * 100
  //         );

         

  //         return {
  //           ...document,
  //           processedPages: nextPage,
  //           progress,
  //           status:
  //             nextPage >= totalPages
  //               ? "indexed"
  //               : "processing",
  //         };
  //       })
  //     );
  //   }, 500);

  //   return () => clearInterval(timer);
  // }, [docs]);

  const removeDocument = (id) => {
    setDocs((current) =>
      current.filter(
        (document) => document.id !== id
      )
    );

    setSelected((current) =>
      current.filter(
        (selectedId) => selectedId !== id
      )
    );
  };

  if (!user) {
    return (
      <Login
        onLogin={(loggedInUser) => {
          setUser(loggedInUser);
        }}
      />
    );
  }

  return (
    <>
      <Sidebar
        page={page}
        setPage={setPage}
        docs={docs}
        upload={() => setUpload(true)}
      />

      <div className="content">
        <TopBar
          upload={() => setUpload(true)}
          n={selected.length}
        />

        {page === "workspace" && (
          <Workspace
            upload={() => setUpload(true)}
            setPage={setPage}
          />
        )}

        {page === "documents" && (
          <Documents
            docs={docs}
            selected={selected}
            setSelected={setSelected}
            upload={() => setUpload(true)}
            remove={removeDocument}
          />
        )}

        {page === "chat" && (
          <Chat
            docs={docs}
            selected={selected}
          />
        )}

        {page === "settings" && <Settings />}
      </div>

      {upload && (
        <UploadModal
  close={() => setUpload(false)}
  add={add}
  updateUploadedDocuments={
    updateUploadedDocuments
  }
/>
      )}
    </>
  );
}

export default App;
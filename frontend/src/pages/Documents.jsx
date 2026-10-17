import React from "react";
import {
  UploadCloud,
  Search,
} from "lucide-react";

import DocumentCard from "../components/DocumentCard";

function Documents({
  docs,
  selected,
  setSelected,
  upload,
  remove,
}) {
  const toggleDocument = (id) => {
    setSelected((current) =>
      current.includes(id)
        ? current.filter((x) => x !== id)
        : [...current, id]
    );
  };

  return (
    <div className="page">
      <div className="heading">
        <div>
          <h1>Documents</h1>
          <p>
            Manage PDFs indexed in the current workspace.
          </p>
        </div>

        <button
          className="primary"
          onClick={upload}
        >
          <UploadCloud size={16} />
          Upload PDFs
        </button>
      </div>

      <div className="toolbar">
        <div className="search">
          <Search size={16} />
          <input
            placeholder="Search documents..."
          />
        </div>

        <button className="secondary">
          Filter
        </button>

        <small>
          {docs.length} documents
        </small>
      </div>

      <div className="docGrid">
        {docs.map((document) => (
          <DocumentCard
            key={document.id}
            document={document}
            selected={selected.includes(
              document.id
            )}
            onSelect={() =>
              toggleDocument(document.id)
            }
            onRemove={remove}
          />
        ))}
      </div>
    </div>
  );
}

export default Documents;
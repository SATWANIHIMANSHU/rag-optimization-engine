import React, { useState } from "react";
import { uploadDocuments } from "../services/api";
import {
  UploadCloud,
  FileText,
  Trash2,
  X,
} from "lucide-react";

function UploadModal({  close,
  add,
  updateUploadedDocuments, }) {
  const [files, setFiles] = useState([]);

  const pick = (e) => {
    const selectedFiles = [...e.target.files].filter(
      (file) =>
        file.type === "application/pdf" &&
        file.size <= 50 * 1024 * 1024
    );

    setFiles((current) =>
      [...current, ...selectedFiles].slice(0, 5)
    );

    // Allow selecting the same file again later.
    e.target.value = "";
  };

  const removeFile = (fileToRemove) => {
    setFiles((current) =>
      current.filter((file) => file !== fileToRemove)
    );
  };

const handleUpload = async () => {
  if (!files.length) return;

  const uploadedFiles = [...files];

  // Show documents immediately as "Processing"
  const documentIds = add(
    uploadedFiles,
    null
  );

  close();

  try {
    const result = await uploadDocuments(
      uploadedFiles
    );

    // Backend finished indexing
    updateUploadedDocuments(
      documentIds,
      uploadedFiles,
      result
    );
  } catch (error) {
    console.error("Upload failed:", error);

    alert(
      "Upload failed. Please make sure the backend is running."
    );
  }
};

  return (
    <div className="modalBg">
      <div className="modal">
        <div className="modalHead">
          <div>
            <h2>Upload documents</h2>
            <p>
              Upload up to 5 PDFs. Each file can be up to
              50 MB.
            </p>
          </div>

          <button
            className="circle"
            onClick={close}
          >
            <X size={18} />
          </button>
        </div>

        <label className="drop">
          <UploadCloud size={30} />

          <b>Drop PDF files here</b>

          <span>or click to browse</span>

          <small>
            PDF only · 5 files maximum · 50 MB per file
          </small>

          <input
            type="file"
            multiple
            accept=".pdf,application/pdf"
            onChange={pick}
          />
        </label>

        <div className="selectedHead">
          Selected files <span>{files.length}/5</span>
        </div>

        <div className="files">
          {files.map((file) => (
            <div
              className="file"
              key={`${file.name}-${file.lastModified}`}
            >
              <FileText />

              <span>
                <b>{file.name}</b>

                <small>
                  {(file.size / 1048576).toFixed(1)} MB
                </small>
              </span>

              <button
                className="circle"
                onClick={() => removeFile(file)}
              >
                <Trash2 size={15} />
              </button>
            </div>
          ))}
        </div>

        <div className="modalFoot">
          <button
            className="secondary"
            onClick={close}
          >
            Cancel
          </button>

          <button
            className="primary"
            disabled={!files.length}
            onClick={handleUpload}
          >
            <UploadCloud size={16} />
            Upload & Index
          </button>
        </div>
      </div>
    </div>
  );
}

export default UploadModal;
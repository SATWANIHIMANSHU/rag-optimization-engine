import React from "react";
import {
  FileText,
  CheckCircle2,
  Loader2,
  Trash2,
  RotateCcw,
} from "lucide-react";

function DocumentCard({
  document,
  selected,
  onSelect,
  onRemove,
}) {
  const totalPages = Number(document.pages) || 1;
  const processedPages =
    document.status === "processing"
      ? document.processedPages || 0
      : totalPages;

  return (
    <article
      className={
        "doc " + (selected ? "selected" : "")
      }
      onClick={onSelect}
    >
      <div className="pdf">
        <FileText />
      </div>

      <div className="docInfo">
        <b>{document.name}</b>

        <span>
          {document.pages} pages · {document.size}
        </span>

        <em className={document.status}>
          {document.status === "processing" ? (
            <>
              <Loader2 className="spin" />
              Processing ({processedPages}/{totalPages} pages)
            </>
          ) : (
            <>
              <CheckCircle2 />
              Indexed ({totalPages}/{totalPages} pages)
            </>
          )}
        </em>

        {document.status === "processing" && (
          <div className="bar">
            <i
              style={{
                width: `${document.progress || 0}%`,
              }}
            />
          </div>
        )}
      </div>

      <div className="docBtns">
        <button
          className="circle"
          onClick={(e) => {
            e.stopPropagation();
            onRemove(document.id);
          }}
        >
          <Trash2 size={15} />
        </button>

        <button
          className="circle"
          onClick={(e) => {
            e.stopPropagation();
          }}
        >
          <RotateCcw size={15} />
        </button>
      </div>
    </article>
  );
}

export default DocumentCard;
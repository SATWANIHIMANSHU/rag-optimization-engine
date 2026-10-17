import React from "react";
import {
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Maximize2,
} from "lucide-react";

function DocumentViewer({
  doc,
  page,
  setPage,
}) {
  const totalPages = Number(doc?.pages) || 1;

  return (
    <aside className="viewer">
      <div className="viewHead">
        <div>
          <h3>
            {doc?.name || "Document"}
          </h3>

          <small>
            Page {page} of {totalPages}
          </small>
        </div>

        <div>
          <button
            className="circle"
            disabled={page === 1}
            onClick={() =>
              setPage(
                Math.max(1, page - 1)
              )
            }
          >
            <ChevronLeft size={17} />
          </button>

          <button
            className="circle"
            disabled={
              page === totalPages
            }
            onClick={() =>
              setPage(
                Math.min(
                  totalPages,
                  page + 1
                )
              )
            }
          >
            <ChevronRight size={17} />
          </button>
        </div>
      </div>

      <div className="paper">
        <div className="paperTitle" />
        <div className="paperLine" />

        <div className="diagram">
          <div>Visual Evidence</div>
          <small>Retrieved page</small>
        </div>

        <div className="paperLine" />
        <div className="paperLine short" />
      </div>

      <div className="viewTools">
        <button className="circle">
          <ZoomOut size={15} />
        </button>

        <span>100%</span>

        <button className="circle">
          <ZoomIn size={15} />
        </button>

        <i />

        <button className="circle">
          <Maximize2 size={15} />
        </button>
      </div>

      <b className="thumbTitle">
        Page thumbnails
      </b>

      <div className="thumbs">
        {Array.from(
          {
            length: Math.min(
              totalPages,
              6
            ),
          },
          (_, i) => (
            <button
              className={
                "thumb " +
                (page === i + 1
                  ? "active"
                  : "")
              }
              onClick={() =>
                setPage(i + 1)
              }
              key={i}
            >
              <div />
              <small>{i + 1}</small>
            </button>
          )
        )}
      </div>
    </aside>
  );
}

export default DocumentViewer;
import React from "react";
import {
  UploadCloud,
  Search,
  Layers,
  Sparkles,
  CheckCircle2,
} from "lucide-react";

function Workspace({ upload, setPage }) {
  return (
    <div className="page">
      <section className="hero">
        <div>
          <label>✦ INTELLIGENT DOCUMENT RETRIEVAL</label>

          <h1>Ask questions across your documents.</h1>

          <p>
            Upload PDFs and let the engine combine text and
            visual retrieval to produce grounded answers with
            page-level evidence.
          </p>

          <div className="actions">
            <button
              className="primary big"
              onClick={upload}
            >
              <UploadCloud size={18} />
              Upload PDFs
            </button>

            <button
              className="secondary big"
              onClick={() => setPage("chat")}
            >
              <Search size={18} />
              Open Chat
            </button>
          </div>
        </div>

        <div className="orb">
          <div>✦</div>
          <span>Text</span>
          <span>Visual</span>
          <span>Hybrid</span>
          <span>LLM</span>
        </div>
      </section>

      <div className="features">
        <article>
          <Layers />
          <b>Multi-document</b>
          <p>Work with up to 5 PDFs in one workspace.</p>
        </article>

        <article>
          <Sparkles />
          <b>Adaptive retrieval</b>
          <p>
            Route questions to text, visual, or hybrid
            retrieval.
          </p>
        </article>

        <article>
          <CheckCircle2 />
          <b>Grounded answers</b>
          <p>
            Show source document and page behind every
            answer.
          </p>
        </article>
      </div>

      <section className="pipeline">
        <label>PIPELINE</label>

        <h2>From PDF to evidence</h2>

        <div>
          {[
            "Upload",
            "Process",
            "Retrieve",
            "Rerank",
            "Answer",
          ].map((step, index) => (
            <React.Fragment key={step}>
              <b>
                <i>{index + 1}</i>
                {step}
              </b>

              {index < 4 && <hr />}
            </React.Fragment>
          ))}
        </div>
      </section>
    </div>
  );
}

export default Workspace;
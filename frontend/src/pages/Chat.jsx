import React, { useState } from "react";
import { askQuestion } from "../services/api";
import {
  FileText,
  Loader2,
  Send,
  Sparkles,
  Image as ImageIcon,
  Paperclip,
} from "lucide-react";

import DocumentViewer from "../components/DocumentViewer";

function Chat({ docs, selected }) {
  const [q, setQ] = useState("");
  const [m, setM] = useState([]);
  const [page, setPage] = useState(2);
  const [loading, setLoading] = useState(false);

  const doc = docs.find((d) => d.id === selected[0]) || docs[0];

  const send = async () => {
    if (!q.trim() || loading) return;

    const question = q.trim();

    setM((a) => [
      ...a,
      {
        r: "u",
        t: question,
      },
    ]);

    setQ("");
    setLoading(true);
    try {
      const selectedDocumentNames = selected
  .map((id) => docs.find((doc) => doc.id === id)?.name)
  .filter(Boolean);

const data = await askQuestion(question, selectedDocumentNames);

      const sources = (data.metadata || []).map(
  (metadata, index) => ({
    ...metadata,
    score: data.scores?.[index] ?? null,
  })
);

setM((a) => [
  ...a,
  {
    r: "a",
    t: data.answer || "No answer returned.",
    mode: "RAG",
    sources,
  },
]);

      if (data.visual_sources && data.visual_sources.length > 0) {
        const retrievedPage = data.visual_sources[0].page;

        if (retrievedPage) {
          setPage(Number(retrievedPage));
        }
      }
    } catch (error) {
      console.error("RAG request failed:", error);

      setM((a) => [
        ...a,
        {
          r: "a",
          t:
            "I could not connect to the RAG backend. " +
            "Please make sure the FastAPI server is running.",
          mode: "ERROR",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chatLayout">
      <main className="chat">
        <div className="chatHead">
          <div>
            <h1>Chat</h1>

            <p>Ask questions about your selected documents.</p>
          </div>

          <span className="pill">
            ● {selected.length || docs.length} documents
          </span>
        </div>

        <div className="messages">
          {!m.length && (
            <div className="empty">
              <div>
                <Sparkles />
              </div>

              <h2>What would you like to know?</h2>

              <p>
                Ask about a definition, figure, table, comparison, or section.
              </p>

              <div className="suggest">
                {[
                  "Explain the main idea",
                  "Show an important figure",
                  "Summarize the paper",
                  "Compare two approaches",
                ].map((x) => (
                  <button onClick={() => setQ(x)} key={x}>
                    {x}
                  </button>
                ))}
              </div>
            </div>
          )}

          {m.map((x, i) => (
            <div className={"msg " + x.r} key={i}>
              <span className="msgIcon">
                {x.r === "u" ? <span>H</span> : <Sparkles size={16} />}
              </span>

              <div>
                <small>{x.r === "u" ? "You" : "RAG Engine"}</small>

                {x.mode && (
                  <label className="retrieval">
                    <Sparkles size={12} />
                    Retrieval: {x.mode}
                    {x.textSources?.length > 0 && (
                      <i>Text sources: {x.textSources.length}</i>
                    )}
                    {x.visualSources?.length > 0 && (
                      <i>Visual pages: {x.visualSources.length}</i>
                    )}
                  </label>
                )}

                <p>{x.t}</p>

               {x.mode && x.mode !== "ERROR" && x.sources?.length > 0 && (
  <>
    <h3>Sources</h3>

    <div className="sources">
      {x.sources.map((source, index) => {
        const isFigure =
          source.type === "figure" ||
          source.type === "figure_visual";

        const isTable =
          source.type === "table";

        return (
          <article key={index}>
            <div className="sourceImg">
              {isFigure ? (
                <ImageIcon size={20} />
              ) : (
                <FileText size={20} />
              )}
            </div>

            <div>
              <label className={isFigure ? "" : "greenLabel"}>
                {isFigure
                  ? "Visual Match"
                  : isTable
                  ? "Table Match"
                  : "Text Match"}
              </label>

              <b>
                {source.source || "Document"}
              </b>

              {source.page && (
                <span>
                  Page {source.page}
                </span>
              )}

              {source.element_id && (
                <p>
                  {source.element_id}
                </p>
              )}
            </div>

            {source.score != null && (
              <strong>
                {(Number(source.score) * 100).toFixed(0)}%
              </strong>
            )}
          </article>
        );
      })}
    </div>
  </>
)}
              </div>
            </div>
          ))}

          {loading && (
            <div className="msg a">
              <span className="msgIcon">
                <Sparkles size={16} />
              </span>

              <div>
                <small>RAG Engine</small>

                <p>Retrieving evidence and generating answer...</p>
              </div>
            </div>
          )}
        </div>

        <div className="composerWrap">
          <div className="composer">
            <button className="circle">
              <Paperclip size={17} />
            </button>

            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              placeholder="Ask anything about your documents..."
              disabled={loading}
            />

            <button className="send" onClick={send} disabled={loading}>
              {loading ? (
                <Loader2 size={17} className="spin" />
              ) : (
                <Send size={17} />
              )}
            </button>
          </div>

          <div className="quick">
            {[
              "💡 Explain this figure",
              "📊 Summarize this section",
              "❓ Compare with other methods",
              "✨ Key takeaways",
            ].map((x) => (
              <button onClick={() => setQ(x.replace(/^\S+ /, ""))} key={x}>
                {x}
              </button>
            ))}
          </div>
        </div>
      </main>

      <DocumentViewer doc={doc} page={page} setPage={setPage} />
    </div>
  );
}

export default Chat;

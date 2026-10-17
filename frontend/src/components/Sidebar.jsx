import React from "react";
import {
  LayoutDashboard,
  Files,
  MessageSquare,
  SettingsIcon,
} from "lucide-react";

function Sidebar({ page, setPage, docs }) {
  return (
    <aside className="side">
      <div className="logo">
        <div>⬡</div>

        <b>
          RAG
          <br />
          Optimization
          <br />
          Engine
        </b>
      </div>

      {[
        ["workspace", LayoutDashboard, "Workspace"],
        ["documents", Files, "Documents"],
        ["chat", MessageSquare, "Chat"],
        ["settings", SettingsIcon, "Settings"],
      ].map(([id, I, t]) => (
        <button
          className={"nav " + (page === id ? "sel" : "")}
          onClick={() => setPage(id)}
          key={id}
        >
          <I size={18} />
          <span>{t}</span>
        </button>
      ))}

      <div className="sideDocs">
        <small>DOCUMENTS</small>

        {docs.slice(0, 4).map((d) => (
          <button
            className="mini"
            onClick={() => setPage("documents")}
            key={d.id}
          >
            <span className="miniPdf">PDF</span>

            <span>
              <b>{d.name}</b>
              <em>{d.pages} pages</em>
            </span>
          </button>
        ))}
      </div>

      <div className="usage">
        <small>WORKSPACE USAGE</small>

        <div>3 / 5 PDFs</div>

        <div className="bar">
          <i style={{ width: "60%" }} />
        </div>

        <small>STORAGE USED</small>

        <div>42 MB / 250 MB</div>

        <div className="bar green">
          <i style={{ width: "17%" }} />
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;
import React from "react";
import {
  Layers,
  Plus,
  MoreVertical,
} from "lucide-react";

function TopBar({ upload, n }) {
  return (
    <header>
      <div className="mobileTitle">
        RAG Optimization Engine
      </div>

      <button className="pill">
        <Layers size={16} />
        Selected: {n}
      </button>

      <button
        className="secondary"
        onClick={upload}
      >
        <Plus size={16} />
        New Chat
      </button>

      <button className="circle">
        <MoreVertical size={18} />
      </button>

      <div className="avatar">H</div>
    </header>
  );
}

export default TopBar;
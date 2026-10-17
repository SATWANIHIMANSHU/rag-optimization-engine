import React from "react";

function CpuIcon() {
  return <span className="setIcon">⚙</span>;
}

function DatabaseIcon() {
  return <span className="setIcon">▦</span>;
}

function Settings() {
  return (
    <div className="page">
      <div className="heading">
        <div>
          <h1>Settings</h1>
          <p>
            Configure retrieval behavior and workspace preferences.
          </p>
        </div>
      </div>

      <div className="settings">
        <article>
          <CpuIcon />

          <h3>AI & Retrieval</h3>

          <label>
            LLM Provider
            <input
              value="Groq / Backend"
              readOnly
            />
          </label>

          <label>
            Retrieval Mode
            <select defaultValue="adaptive">
              <option value="adaptive">
                Adaptive
              </option>

              <option>
                Text only
              </option>

              <option>
                Visual only
              </option>
            </select>
          </label>

          <label>
            Top-K Results
            <input defaultValue="5" />
          </label>
        </article>

        <article>
          <DatabaseIcon />

          <h3>Indexing</h3>

          <label>
            Maximum PDFs
            <input
              value="5"
              readOnly
            />
          </label>

          <label>
            Maximum file size
            <input
              value="50 MB"
              readOnly
            />
          </label>

          <label>
            Visual indexing
            <select defaultValue="enabled">
              <option>
                Enabled
              </option>

              <option>
                Disabled
              </option>
            </select>
          </label>
        </article>
      </div>
    </div>
  );
}

export default Settings;
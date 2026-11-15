import { useState } from "react";

/**
 * Read-only value shown as text (not as a disabled-looking input).
 *
 * @param {string}  label
 * @param {any}     value
 * @param {number}  [span]      - Grid span (12-column form grid)
 * @param {boolean} [mono]      - Monospace, wraps long hashes
 * @param {boolean} [copyable]  - Adds a copy-to-clipboard button
 */
export default function ReadOnlyField({ label, value, span = 6, mono = false, copyable = false, children }) {
  const [copied, setCopied] = useState(false);
  const empty = value === null || value === undefined || value === "";
  const text = empty ? "—" : String(value);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className={`readonly-field field-span-${span}`}>
      <span className="readonly-field__label">{label}</span>
      <div className="readonly-field__row">
        {children ?? <span className={`readonly-field__value${mono ? " readonly-field__value--mono" : ""}`}>{text}</span>}
        {copyable && !empty ? (
          <button type="button" className="btn-link" onClick={copy} aria-label={`Copiar ${label}`}>
            {copied ? "Copiado" : "Copiar"}
          </button>
        ) : null}
      </div>
    </div>
  );
}

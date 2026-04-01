import { useState } from "react";

export default function Accordion({ items }) {
  const [openKey, setOpenKey] = useState(null);

  const toggle = (key) => {
    setOpenKey((prev) => (prev === key ? null : key));
  };

  return (
    <div className="accordion">
      {items.map((item) => {
        const isOpen = openKey === item.key;
        return (
          <div key={item.key}>
            <button
              className={`accordion-header${isOpen ? " active" : ""}`}
              type="button"
              onClick={() => toggle(item.key)}
            >
              {item.label}
            </button>
            <div className={`accordion-panel${isOpen ? " open" : ""}`}>
              <div className="accordion-panel-content">
                <textarea
                  name={`${item.key}_notes`}
                  placeholder={item.placeholder}
                />
                <label className="upload-btn">
                  📎 Subir
                  <input
                    type="file"
                    name={`${item.key}_file`}
                    accept=".pdf,.jpg,.jpeg,.png"
                  />
                </label>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

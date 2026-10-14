import { useEffect, useRef } from "react";

/**
 * Modal accesible sobre <dialog> nativo (foco atrapado y Escape incluidos).
 *
 * @param {boolean}  open
 * @param {Function} onClose
 * @param {string}   title
 * @param {string}   [description]
 */
export default function Modal({ open, onClose, title, description, children }) {
  const ref = useRef(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      className="modal"
      aria-labelledby="modal-title"
      onCancel={(event) => {
        event.preventDefault();
        onClose?.();
      }}
      onClick={(event) => {
        // Click en el backdrop (fuera de la caja) cierra.
        if (event.target === ref.current) onClose?.();
      }}
    >
      {open ? (
        <div className="modal__box">
          <header className="modal__header">
            <h2 id="modal-title" className="modal__title">
              {title}
            </h2>
            <button type="button" className="modal__close" onClick={onClose} aria-label="Cerrar">
              ×
            </button>
          </header>
          {description ? <p className="modal__description">{description}</p> : null}
          {children}
        </div>
      ) : null}
    </dialog>
  );
}

import { useRef, useCallback, useState } from "react";
import useFormStatus from "./useFormStatus";

/**
 * Encapsulates the form-submit + reset pattern shared across pages.
 *
 * @param {Object}   opts
 * @param {Function} opts.submitFn      - async (formData) => Promise<any>
 * @param {Function} [opts.onSuccess]   - callback after success
 * @param {string}   opts.loadingMsg
 * @param {string}   opts.successMsg
 * @param {string}   opts.errorMsg
 */
export default function useFormSubmit({
  submitFn,
  onSuccess,
  loadingMsg = "Guardando...",
  successMsg = "Guardado correctamente.",
  errorMsg = "Ocurrió un error al guardar.",
}) {
  const formRef = useRef(null);
  const pendingRef = useRef(false);
  const [pending, setPending] = useState(false);
  const { status, setLoading, setSuccess, setError, clear } = useFormStatus();

  const handleSubmit = useCallback(
    async (e) => {
      e.preventDefault();
      // Evita el doble envío aunque el botón tarde un render en deshabilitarse.
      if (pendingRef.current) return;
      pendingRef.current = true;
      setPending(true);
      const formData = new FormData(formRef.current);
      setLoading(loadingMsg);

      try {
        const result = await submitFn(formData);
        setSuccess(successMsg);
        formRef.current?.reset();
        onSuccess?.(result);
      } catch (err) {
        setError(err.message || errorMsg);
      } finally {
        pendingRef.current = false;
        setPending(false);
      }
    },
    [submitFn, onSuccess, loadingMsg, successMsg, errorMsg, setLoading, setSuccess, setError],
  );

  const handleCancel = useCallback(() => {
    formRef.current?.reset();
    clear();
  }, [clear]);

  return { formRef, status, pending, handleSubmit, handleCancel, setError, clear };
}

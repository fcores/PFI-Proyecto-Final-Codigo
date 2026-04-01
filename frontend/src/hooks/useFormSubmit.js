import { useRef, useCallback } from "react";
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
  const { status, setLoading, setSuccess, setError, clear } = useFormStatus();

  const handleSubmit = useCallback(
    async (e) => {
      e.preventDefault();
      const formData = new FormData(formRef.current);
      setLoading(loadingMsg);

      try {
        await submitFn(formData);
        setSuccess(successMsg);
        formRef.current.reset();
        onSuccess?.();
      } catch (err) {
        setError(err.message || errorMsg);
      }
    },
    [submitFn, onSuccess, loadingMsg, successMsg, errorMsg, setLoading, setSuccess, setError],
  );

  const handleCancel = useCallback(() => {
    formRef.current.reset();
    clear();
  }, [clear]);

  return { formRef, status, handleSubmit, handleCancel, setError, clear };
}

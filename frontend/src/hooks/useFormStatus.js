import { useState, useCallback } from "react";

export default function useFormStatus() {
  const [status, setStatus] = useState({ message: "", type: "" });

  const setLoading = useCallback(
    (msg) => setStatus({ message: msg, type: "" }),
    [],
  );

  const setSuccess = useCallback(
    (msg) => setStatus({ message: msg, type: "success" }),
    [],
  );

  const setError = useCallback(
    (msg) => setStatus({ message: msg, type: "error" }),
    [],
  );

  const clear = useCallback(() => setStatus({ message: "", type: "" }), []);

  return { status, setLoading, setSuccess, setError, clear };
}

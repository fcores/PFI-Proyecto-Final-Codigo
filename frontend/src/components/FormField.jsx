/**
 * Reusable form field wrapper with label, span, and required-star support.
 */
export default function FormField({
  label,
  htmlFor,
  required = false,
  span = 6,
  children,
}) {
  return (
    <div className={`form-group field-span-${span}`}>
      <label htmlFor={htmlFor}>
        {/* Un solo nodo: si el texto ocupa dos líneas el asterisco queda pegado. */}
        <span>
          {label}
          {required && (
            <span className="required" aria-hidden="true">
              {" "}*
            </span>
          )}
        </span>
      </label>
      {children}
    </div>
  );
}

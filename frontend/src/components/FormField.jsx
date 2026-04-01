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
        {label}
        {required && <span className="required"> *</span>}
      </label>
      {children}
    </div>
  );
}

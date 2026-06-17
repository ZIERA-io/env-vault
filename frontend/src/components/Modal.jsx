import { useEffect } from "react";

export default function Modal({ open, onClose, title, children, footer, wide }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === "Escape" && onClose?.();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      <div
        className={`card relative z-10 w-full ${wide ? "max-w-3xl" : "max-w-md"} max-h-[90vh] overflow-y-auto p-5`}
      >
        {title && (
          <h3 className="mb-4 text-lg font-semibold text-slate-900 dark:text-slate-100">
            {title}
          </h3>
        )}
        <div>{children}</div>
        {footer && <div className="mt-5 flex justify-end gap-2">{footer}</div>}
      </div>
    </div>
  );
}

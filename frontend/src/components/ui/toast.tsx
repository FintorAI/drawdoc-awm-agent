"use client";

import * as React from "react";
import { X, CheckCircle2, AlertCircle, AlertTriangle, Info } from "lucide-react";

import { cn } from "@/lib/utils";

// =============================================================================
// TOAST TYPES
// =============================================================================

export type ToastVariant = "default" | "success" | "error" | "warning" | "info";

export interface Toast {
  id: string;
  title?: string;
  description?: string;
  variant?: ToastVariant;
  duration?: number;
}

// =============================================================================
// TOAST CONTEXT
// =============================================================================

interface ToastContextValue {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, "id">) => void;
  removeToast: (id: string) => void;
}

const ToastContext = React.createContext<ToastContextValue | undefined>(
  undefined
);

export function useToast() {
  const context = React.useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}

// =============================================================================
// TOAST PROVIDER
// =============================================================================

interface ToastProviderProps {
  children: React.ReactNode;
}

export function ToastProvider({ children }: ToastProviderProps) {
  const [toasts, setToasts] = React.useState<Toast[]>([]);

  const addToast = React.useCallback((toast: Omit<Toast, "id">) => {
    const id = Math.random().toString(36).substring(2, 9);
    const newToast = { id, ...toast };
    setToasts((prev) => [...prev, newToast]);

    // Auto-remove after duration (default 5 seconds)
    const duration = toast.duration ?? 5000;
    if (duration > 0) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, duration);
    }
  }, []);

  const removeToast = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <ToastContainer />
    </ToastContext.Provider>
  );
}

// =============================================================================
// TOAST CONTAINER
// =============================================================================

function ToastContainer() {
  const { toasts, removeToast } = useToast();

  return (
    <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 w-full max-w-sm">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onClose={() => removeToast(toast.id)} />
      ))}
    </div>
  );
}

// =============================================================================
// TOAST ITEM
// =============================================================================

interface ToastItemProps {
  toast: Toast;
  onClose: () => void;
}

function ToastItem({ toast, onClose }: ToastItemProps) {
  const { variant = "default", title, description } = toast;

  const Icon = {
    default: Info,
    success: CheckCircle2,
    error: AlertCircle,
    warning: AlertTriangle,
    info: Info,
  }[variant];

  const variantClasses = {
    default: "border-border bg-background text-foreground",
    success: "border-emerald-200 bg-emerald-50 text-emerald-900",
    error: "border-red-200 bg-red-50 text-red-900",
    warning: "border-amber-200 bg-amber-50 text-amber-900",
    info: "border-blue-200 bg-blue-50 text-blue-900",
  }[variant];

  const iconClasses = {
    default: "text-muted-foreground",
    success: "text-emerald-600",
    error: "text-red-600",
    warning: "text-amber-600",
    info: "text-blue-600",
  }[variant];

  return (
    <div
      className={cn(
        "pointer-events-auto relative flex w-full items-start gap-3 rounded-lg border p-4 shadow-lg transition-all animate-in slide-in-from-right-full",
        variantClasses
      )}
    >
      <Icon className={cn("h-5 w-5 flex-shrink-0 mt-0.5", iconClasses)} />
      <div className="flex-1 space-y-1">
        {title && (
          <p className="text-sm font-semibold leading-none">{title}</p>
        )}
        {description && (
          <p className="text-sm opacity-90">{description}</p>
        )}
      </div>
      <button
        onClick={onClose}
        className="flex-shrink-0 rounded-md p-1 opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
      >
        <X className="h-4 w-4" />
        <span className="sr-only">Close</span>
      </button>
    </div>
  );
}

// =============================================================================
// TOAST HELPER FUNCTIONS
// =============================================================================

/**
 * Helper function to create toast configurations
 */
export const toast = {
  success: (props: Omit<Toast, "id" | "variant">) => ({
    ...props,
    variant: "success" as const,
  }),
  error: (props: Omit<Toast, "id" | "variant">) => ({
    ...props,
    variant: "error" as const,
  }),
  warning: (props: Omit<Toast, "id" | "variant">) => ({
    ...props,
    variant: "warning" as const,
  }),
  info: (props: Omit<Toast, "id" | "variant">) => ({
    ...props,
    variant: "info" as const,
  }),
};


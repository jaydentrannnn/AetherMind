"use client";

import { useCallback, useState } from "react";

export interface ToastItem {
  id: number;
  msg: string;
  type: "success" | "error";
}

export function useToasts(): {
  toasts: ToastItem[];
  addToast: (msg: string, type?: ToastItem["type"]) => void;
} {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const addToast = useCallback((msg: string, type: ToastItem["type"] = "success") => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, msg, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((toast) => toast.id !== id));
    }, 3000);
  }, []);

  return { toasts, addToast };
}

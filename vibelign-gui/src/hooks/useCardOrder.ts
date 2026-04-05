// === ANCHOR: USE_CARD_ORDER_START ===
import { useEffect, useRef, useState } from "react";
import { load } from "@tauri-apps/plugin-store";

export const DEFAULT_CARD_ORDER = [
  "codemap", "guard", "checkpoint", "transfer",
  "history", "patch", "undo", "anchor",
  "explain", "ask", "export", "protect", "secrets",
] as const;

const STORE_PATH = "vibelign-gui.json";
const STORE_KEY = "card-order";

type StoreInstance = Awaited<ReturnType<typeof load>>;

export function useCardOrder() {
  const [cardOrder, setCardOrderState] = useState<string[]>([...DEFAULT_CARD_ORDER]);
  const storeRef = useRef<StoreInstance | null>(null);

  useEffect(() => {
    load(STORE_PATH, { defaults: {} }).then(async (s) => {
      storeRef.current = s;
      try {
        const saved = await s.get<string[]>(STORE_KEY);
        if (saved && Array.isArray(saved)) {
          const valid = saved.filter((id) => (DEFAULT_CARD_ORDER as readonly string[]).includes(id));
          const missing = DEFAULT_CARD_ORDER.filter((id) => !valid.includes(id));
          setCardOrderState([...valid, ...missing]);
        }
      } catch {
        // store 읽기 실패 시 기본 순서 유지
      }
    }).catch(() => {
      // store 열기 실패 시 기본 순서 유지
    });
  }, []);

  function saveOrder(order: string[]) {
    const s = storeRef.current;
    if (!s) return;
    s.set(STORE_KEY, order).catch(() => {});
  }

  function setCardOrder(order: string[]) {
    setCardOrderState(order);
    saveOrder(order);
  }

  function resetOrder() {
    setCardOrder([...DEFAULT_CARD_ORDER]);
  }

  return { cardOrder, setCardOrder, resetOrder };
}
// === ANCHOR: USE_CARD_ORDER_END ===

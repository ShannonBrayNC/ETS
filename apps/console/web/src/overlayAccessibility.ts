const overlaySelector = ".connector-modal, .connector-drawer";
const focusableSelector = [
  "button:not([disabled])",
  "a[href]",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

function focusableElements(overlay: HTMLElement): HTMLElement[] {
  return Array.from(overlay.querySelectorAll<HTMLElement>(focusableSelector)).filter(
    (element) => element.getClientRects().length > 0,
  );
}

export function installOverlayAccessibility(): () => void {
  const managed = new Map<HTMLElement, { previous: HTMLElement | null; keydown: (event: KeyboardEvent) => void }>();

  const closeOverlay = (overlay: HTMLElement) => {
    overlay.querySelector<HTMLButtonElement>('button[aria-label^="Close connector"]')?.click();
  };

  const manage = (overlay: HTMLElement) => {
    if (managed.has(overlay)) return;

    const modal = overlay.classList.contains("connector-modal");
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", modal ? "true" : "false");
    if (!overlay.hasAttribute("tabindex")) overlay.tabIndex = -1;

    const keydown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeOverlay(overlay);
        return;
      }
      if (!modal || event.key !== "Tab") return;

      const focusable = focusableElements(overlay);
      if (focusable.length === 0) {
        event.preventDefault();
        overlay.focus();
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;
      if (event.shiftKey && (active === first || !overlay.contains(active))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (active === last || !overlay.contains(active))) {
        event.preventDefault();
        first.focus();
      }
    };

    overlay.addEventListener("keydown", keydown);
    managed.set(overlay, { previous, keydown });
    requestAnimationFrame(() => {
      const preferred = overlay.querySelector<HTMLElement>('button[aria-label^="Close connector"]');
      (preferred ?? focusableElements(overlay)[0] ?? overlay).focus();
    });
  };

  const release = (overlay: HTMLElement) => {
    const state = managed.get(overlay);
    if (!state) return;
    overlay.removeEventListener("keydown", state.keydown);
    managed.delete(overlay);
    requestAnimationFrame(() => {
      if (state.previous?.isConnected) state.previous.focus();
    });
  };

  const overlaysIn = (node: Node): HTMLElement[] => {
    if (!(node instanceof Element)) return [];
    const result: HTMLElement[] = [];
    if (node.matches(overlaySelector)) result.push(node as HTMLElement);
    result.push(...node.querySelectorAll<HTMLElement>(overlaySelector));
    return result;
  };

  document.querySelectorAll<HTMLElement>(overlaySelector).forEach(manage);
  const observer = new MutationObserver((records) => {
    for (const record of records) {
      record.addedNodes.forEach((node) => overlaysIn(node).forEach(manage));
      record.removedNodes.forEach((node) => overlaysIn(node).forEach(release));
    }
  });
  observer.observe(document.documentElement, { childList: true, subtree: true });

  return () => {
    observer.disconnect();
    for (const [overlay, state] of managed) {
      overlay.removeEventListener("keydown", state.keydown);
    }
    managed.clear();
  };
}

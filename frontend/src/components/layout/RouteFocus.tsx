import { useEffect } from "react";
import { useLocation } from "react-router-dom";
export function RouteFocus() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
    document.getElementById("workspace-main")?.focus({ preventScroll: true });
  }, [pathname]);
  return null;
}

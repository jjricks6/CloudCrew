import { useContext } from "react";
import { ThemeProviderContext } from "@/lib/theme-context";

export function useTheme() {
  return useContext(ThemeProviderContext);
}

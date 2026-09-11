import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "./api";
export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60_000, gcTime: 10 * 60_000,
        refetchOnWindowFocus: true, refetchOnReconnect: true, refetchOnMount: true,
        refetchIntervalInBackground: false,
        retry: (count, error) => count < 1 && !(error instanceof ApiError && (error.status < 500 || error.status === 501)),
      },
      mutations: { retry: false },
    }
  });
}

import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "./api";

export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60_000,
        gcTime: 10 * 60_000,
        refetchOnWindowFocus: true,
        refetchOnReconnect: true,
        refetchOnMount: true,
        refetchIntervalInBackground: false,
        retry: (count, error) => {
          if (error instanceof ApiError) {
            if (error.status === 0) {
              return count < 3;
            }

            if (error.status >= 500 && error.status !== 501) {
              return count < 2;
            }

            return false;
          }

          return count < 2;
        },
        retryDelay: (attempt) =>
          Math.min(1_000 * 2 ** attempt, 5_000),
      },
      mutations: { retry: false },
    },
  });
}

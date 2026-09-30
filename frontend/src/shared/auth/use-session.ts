"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchSession, SESSION_QUERY_KEY } from "./session";

export function useSession() {
  return useQuery({ queryKey: SESSION_QUERY_KEY, queryFn: fetchSession, retry: false });
}

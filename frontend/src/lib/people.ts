import { queryOptions } from "@tanstack/react-query";
import type { PeoplePage, Person } from "../types";
import { api } from "./api";
import { qk } from "./queryKeys";

/** Existing API supports offset/limit, not search. Read all pages before filtering.
 * Cached only in memory, once per workspace. Never silently stop at 50/100 records.
 */
export async function fetchDirectory(signal?: AbortSignal): Promise<Person[]> {
  const records = new Map<string, Person>();
  let offset = 0;
  while (true) {
    const page = await api<PeoplePage>(`/people?limit=100&offset=${offset}`, { signal });
    for (const person of page.items) records.set(person.id, person);
    offset += page.items.length;
    if (offset >= page.total) break;
    if (page.items.length === 0) throw new Error("The directory changed while loading. Please refresh to load the remaining records.");
  }
  return [...records.values()];
}
export function directoryOptions() {
  return queryOptions({ queryKey: qk("people", "directory"), queryFn: ({ signal }) => fetchDirectory(signal), staleTime: 60_000 });
}
export function filterPeople(people: Person[], search: string, availability: string, country: string) {
  const term = search.trim().toLocaleLowerCase();
  return people.filter((person) =>
    (!availability || person.availability_status === availability) &&
    (!country || person.country_of_residence === country) &&
    (!term || [person.display_name, person.professional_title, person.country_of_residence, person.primary_email].some((value) => value?.toLocaleLowerCase().includes(term))),
  );
}

export type Membership = { organization_id: string; organization_name: string; organization_slug: string; role: string };
export type CurrentUser = { id: string; email: string; full_name: string; memberships: Membership[] };
export type Person = {
  id: string; organization_id: string; first_name: string; middle_name?: string; last_name: string;
  display_name: string; professional_title?: string; primary_email?: string; primary_phone?: string;
  nationality?: string; country_of_residence?: string; summary?: string;
  availability_status: string; profile_status: string; created_at: string; updated_at: string;
};
export type PeoplePage = { items: Person[]; total: number; limit: number; offset: number };


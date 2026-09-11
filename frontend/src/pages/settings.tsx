import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  Trash2
} from "lucide-react";
import React from "react";

import {
  Button,
  Field,
  PageHeader
} from "../components/ui";
import {
  api
} from "../lib/api";


import { qk } from "../lib/queryKeys";
const wrapper = "cf-page";
export function OrganizationPage() {
  type OrganizationInfo = {
    name: string;
    slug: string;
    role: string;
    status: string;
  };

  type Member = {
    id: string;
    user_id: string;
    email: string;
    full_name: string;
    role:
    | "owner"
    | "admin"
    | "manager"
    | "data_entry"
    | "reviewer"
    | "viewer";
    is_active: boolean;
    created_at: string;
  };

  const queryClient =
    useQueryClient();

  const [newMember, setNewMember] =
    React.useState({
      full_name: "",
      email: "",
      password: "",
      role: "data_entry",
    });

  const organization = useQuery({
    queryKey: qk("organization"),
    queryFn: () =>
      api<OrganizationInfo>(
        "/organizations/current",
      ),
  });

  const canManageMembers =
    organization.data?.role ===
    "owner" ||
    organization.data?.role ===
    "admin";

  const members = useQuery({
    queryKey: qk("organization-members"),
    queryFn: () =>
      api<Member[]>(
        "/organizations/members",
      ),
    enabled: canManageMembers,
  });

  const createMember =
    useMutation({
      mutationFn: () =>
        api<Member>(
          "/organizations/members",
          {
            method: "POST",
            body: JSON.stringify(
              newMember,
            ),
          },
        ),
      onSuccess: () => {
        setNewMember({
          full_name: "",
          email: "",
          password: "",
          role: "data_entry",
        });
        queryClient.invalidateQueries(
          {
            queryKey: qk("organization-members"),
          },
        );
      },
    });

  const updateMember =
    useMutation({
      mutationFn: ({
        id,
        values,
      }: {
        id: string;
        values: {
          role?: string;
          is_active?: boolean;
        };
      }) =>
        api<Member>(
          `/organizations/members/${id}`,
          {
            method: "PATCH",
            body: JSON.stringify(
              values,
            ),
          },
        ),
      onSuccess: () => {
        queryClient.invalidateQueries(
          {
            queryKey: qk("organization-members"),
          },
        );
      },
    });

  const removeMemberAccess = useMutation({
    mutationFn: (id: string) =>
      api<Member>(
        `/organizations/members/${id}`,
        {
          method: "PATCH",
          body: JSON.stringify({
            is_active: false,
          }),
        },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: qk("organization-members"),
      });
    },
  });

  const memberRoles = [
    [
      "data_entry",
      "Data entry",
    ],
    [
      "reviewer",
      "Reviewer",
    ],
    [
      "manager",
      "Manager",
    ],
    [
      "admin",
      "Admin",
    ],
    [
      "viewer",
      "Viewer",
    ],
    [
      "owner",
      "Owner",
    ],
  ] as const;

  return (
    <div className={wrapper}>
      <PageHeader
        eyebrow="Administration"
        title="Organization settings"
      >
        Workspace identity and
        team access management.
      </PageHeader>

      <div className="grid gap-6 xl:grid-cols-[.8fr_1.2fr]">
        <section className="cf-panel">
          <h2 className="font-serif text-2xl">
            Workspace details
          </h2>

          {organization.data ? (
            <dl className="mt-6 grid gap-6 sm:grid-cols-2 xl:grid-cols-1">
              <div>
                <dt className="text-xs uppercase tracking-wider text-slate-400">
                  Organization
                </dt>
                <dd className="mt-1 font-semibold">
                  {
                    organization.data
                      .name
                  }
                </dd>
              </div>

              <div>
                <dt className="text-xs uppercase tracking-wider text-slate-400">
                  Slug
                </dt>
                <dd className="mt-1">
                  {
                    organization.data
                      .slug
                  }
                </dd>
              </div>

              <div>
                <dt className="text-xs uppercase tracking-wider text-slate-400">
                  Your role
                </dt>
                <dd className="mt-1 capitalize">
                  {organization.data.role.replace(
                    "_",
                    " ",
                  )}
                </dd>
              </div>

              <div>
                <dt className="text-xs uppercase tracking-wider text-slate-400">
                  Status
                </dt>
                <dd className="mt-1 capitalize text-evergreen">
                  {
                    organization.data
                      .status
                  }
                </dd>
              </div>
            </dl>
          ) : organization.error ? (
            <p className="mt-5 rounded-xl bg-red-50 p-4 text-sm text-red-700">
              {
                organization.error
                  .message
              }
            </p>
          ) : (
            <p className="mt-5">
              Loading settings…
            </p>
          )}
        </section>

        <section className="cf-panel">
          <div>
            <p className="text-xs font-medium tracking-wide text-evergreen">
              Team access
            </p>
            <h2 className="mt-2 font-serif text-2xl">
              Workspace members
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-500">
              Give team members
              individual accounts so
              they can enter and
              maintain people,
              qualifications,
              certifications and
              supporting records.
            </p>
          </div>

          {!canManageMembers ? (
            <div className="mt-6 rounded-xl bg-sand p-4 text-sm text-slate-600">
              Only workspace owners
              and admins can manage
              team accounts.
            </div>
          ) : (
            <>
              <form
                className="mt-7 grid gap-4 rounded-2xl border border-slate-200 bg-slate-50 p-5 md:grid-cols-2"
                onSubmit={(event) => {
                  event.preventDefault();
                  createMember.mutate();
                }}
              >
                <Field
                  label="Full name"
                  value={
                    newMember.full_name
                  }
                  required
                  onChange={(event) =>
                    setNewMember(
                      (current) => ({
                        ...current,
                        full_name:
                          event.target
                            .value,
                      }),
                    )
                  }
                />

                <Field
                  label="Work email"
                  type="email"
                  value={
                    newMember.email
                  }
                  required
                  onChange={(event) =>
                    setNewMember(
                      (current) => ({
                        ...current,
                        email:
                          event.target
                            .value,
                      }),
                    )
                  }
                />

                <Field
                  label="Temporary password"
                  type="password"
                  minLength={12}
                  value={
                    newMember.password
                  }
                  required
                  onChange={(event) =>
                    setNewMember(
                      (current) => ({
                        ...current,
                        password:
                          event.target
                            .value,
                      }),
                    )
                  }
                />

                <label className="block text-sm font-medium text-slate-700">
                  Role
                  <select
                    value={
                      newMember.role
                    }
                    onChange={(event) =>
                      setNewMember(
                        (current) => ({
                          ...current,
                          role:
                            event.target
                              .value,
                        }),
                      )
                    }
                    className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 outline-none focus:border-evergreen"
                  >
                    {memberRoles.map(
                      ([
                        value,
                        label,
                      ]) => (
                        <option
                          key={value}
                          value={value}
                        >
                          {label}
                        </option>
                      ),
                    )}
                  </select>
                </label>

                {createMember.error && (
                  <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700 md:col-span-2">
                    {
                      createMember
                        .error.message
                    }
                  </p>
                )}

                <div className="md:col-span-2">
                  <Button
                    type="submit"
                    disabled={
                      createMember.isPending
                    }
                  >
                    {createMember.isPending
                      ? "Creating account…"
                      : "Create team account"}
                  </Button>
                </div>
              </form>

              <div className="mt-6 overflow-hidden rounded-2xl border border-slate-200">
                {members.isLoading ? (
                  <p className="p-5 text-sm text-slate-500">
                    Loading members…
                  </p>
                ) : members.error ? (
                  <p className="m-4 rounded-xl bg-red-50 p-4 text-sm text-red-700">
                    {
                      members.error
                        .message
                    }
                  </p>
                ) : (
                  <div className="divide-y divide-slate-100">
                    {(
                      members.data ?? []
                    ).map(
                      (member) => (
                        <div
                          key={
                            member.id
                          }
                          className="grid gap-4 p-5 md:grid-cols-[1fr_170px_130px_48px] md:items-center"
                        >
                          <div>
                            <p className="font-semibold">
                              {
                                member.full_name
                              }
                            </p>
                            <p className="mt-1 text-sm text-slate-500">
                              {
                                member.email
                              }
                            </p>
                          </div>

                          <select
                            value={
                              member.role
                            }
                            disabled={
                              updateMember.isPending
                            }
                            onChange={(event) =>
                              updateMember.mutate(
                                {
                                  id: member.id,
                                  values: {
                                    role:
                                      event
                                        .target
                                        .value,
                                  },
                                },
                              )
                            }
                            className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm capitalize"
                          >
                            {memberRoles.map(
                              ([
                                value,
                                label,
                              ]) => (
                                <option
                                  key={
                                    value
                                  }
                                  value={
                                    value
                                  }
                                >
                                  {
                                    label
                                  }
                                </option>
                              ),
                            )}
                          </select>

                          <button
                            type="button"
                            disabled={
                              updateMember.isPending
                            }
                            onClick={() =>
                              updateMember.mutate(
                                {
                                  id: member.id,
                                  values: {
                                    is_active:
                                      !member.is_active,
                                  },
                                },
                              )
                            }
                            className={`rounded-xl px-3 py-2.5 text-sm font-semibold ${member.is_active
                              ? "bg-emerald-50 text-emerald-700"
                              : "bg-slate-100 text-slate-500"
                              }`}
                          >
                            {member.is_active
                              ? "Active"
                              : "Inactive"}
                          </button>

                          <button
                            type="button"
                            aria-label={`Remove access for ${member.full_name}`}
                            disabled={
                              removeMemberAccess.isPending ||
                              !member.is_active
                            }
                            onClick={() => {
                              if (
                                window.confirm(
                                  `Remove workspace access for ${member.full_name}? Their account history will be retained.`,
                                )
                              ) {
                                removeMemberAccess.mutate(member.id);
                              }
                            }}
                            className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-30"
                          >
                            <Trash2 size={17} />
                          </button>
                        </div>
                      ),
                    )}

                    {!members.data
                      ?.length && (
                        <p className="p-5 text-sm text-slate-500">
                          No members
                          found.
                        </p>
                      )}
                  </div>
                )}
              </div>

              {updateMember.error && (
                <p className="mt-4 rounded-xl bg-red-50 p-4 text-sm text-red-700">
                  {
                    updateMember
                      .error.message
                  }
                </p>
              )}

              {removeMemberAccess.error && (
                <p className="mt-4 rounded-xl bg-red-50 p-4 text-sm text-red-700">
                  {removeMemberAccess.error.message}
                </p>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  FolderKanban,
  Plus,
  Trash2,
  X
} from "lucide-react";
import React from "react";
import { useWorkspace } from "../../lib/workspace";

import {
  Button,
  Field,
  TextArea
} from "../../components/ui";
import {
  api
} from "../../lib/api";
import type {
  ProjectExperience
} from "../../types";


import { EmptyCapability } from "../../components/EmptyCapability";
import { qk } from "../../lib/queryKeys";
import { formatExperiencePeriod } from "./dates";
export function ProjectsPanel({
  personId,
}: {
  personId: string;
}) {
  const { canWrite } = useWorkspace();
  const queryClient = useQueryClient();

  const [adding, setAdding] =
    React.useState(false);

  const [projectName, setProjectName] =
    React.useState("");

  const [clientName, setClientName] =
    React.useState("");

  const [role, setRole] =
    React.useState("");

  const [sector, setSector] =
    React.useState("");

  const [location, setLocation] =
    React.useState("");

  const [country, setCountry] =
    React.useState("");

  const [startDate, setStartDate] =
    React.useState("");

  const [endDate, setEndDate] =
    React.useState("");

  const [isCurrent, setIsCurrent] =
    React.useState(false);

  const [description, setDescription] =
    React.useState("");

  const [responsibilities, setResponsibilities] =
    React.useState("");

  const [outcomes, setOutcomes] =
    React.useState("");

  const [skillsSummary, setSkillsSummary] =
    React.useState("");

  const query = useQuery({
    queryKey: qk("projects", personId),
    queryFn: () =>
      api<ProjectExperience[]>(
        `/people/${personId}/projects`,
      ),
  });

  const resetForm = () => {
    setProjectName("");
    setClientName("");
    setRole("");
    setSector("");
    setLocation("");
    setCountry("");
    setStartDate("");
    setEndDate("");
    setIsCurrent(false);
    setDescription("");
    setResponsibilities("");
    setOutcomes("");
    setSkillsSummary("");
  };

  const create = useMutation({
    mutationFn: () =>
      api<ProjectExperience>(
        `/people/${personId}/projects`,
        {
          method: "POST",
          body: JSON.stringify({
            project_name: projectName,
            client_name:
              clientName.trim() || null,
            role,
            sector:
              sector.trim() || null,
            location:
              location.trim() || null,
            country:
              country.trim() || null,
            start_date: startDate,
            end_date: isCurrent
              ? null
              : endDate || null,
            is_current: isCurrent,
            description:
              description.trim() || null,
            responsibilities:
              responsibilities.trim() || null,
            outcomes:
              outcomes.trim() || null,
            skills_summary:
              skillsSummary.trim() || null,
          }),
        },
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: qk("profile-completeness", personId) });
      resetForm();
      setAdding(false);
      queryClient.invalidateQueries({
        queryKey: qk("projects", personId),
      });
    },
  });

  const remove = useMutation({
    mutationFn: (projectId: string) =>
      api<void>(
        `/people/${personId}/projects/${projectId}`,
        {
          method: "DELETE",
        },
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: qk("profile-completeness", personId) });
      queryClient.invalidateQueries({
        queryKey: qk("projects", personId),
      });
    },
  });

  return (
    <section className="cf-panel">
      <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div>
          <h2 className="font-serif text-2xl">
            Project experience
          </h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-500">
            Capture projects, clients, sectors, roles, outcomes,
            and applied skills. This will become one of the most
            important sources for requirement matching.
          </p>
        </div>

        <Button
          type="button"
          disabled={!canWrite}
          onClick={() => {
            if (adding) {
              resetForm();
            }
            setAdding(!adding);
          }}
        >
          {adding ? (
            <>
              <X size={16} className="mr-2 inline" />
              Cancel
            </>
          ) : (
            <>
              <Plus size={16} className="mr-2 inline" />
              Add project
            </>
          )}
        </Button>
      </div>

      {adding && (
        <div className="mb-7 rounded-2xl border border-slate-200 bg-slate-50 p-5">
          <div className="grid gap-4 md:grid-cols-2">
            <Field
              label="Project name"
              value={projectName}
              onChange={(event) =>
                setProjectName(event.target.value)
              }
              placeholder="e.g. National Data Platform"
            />

            <Field
              label="Role"
              value={role}
              onChange={(event) =>
                setRole(event.target.value)
              }
              placeholder="e.g. Technical Lead"
            />

            <Field
              label="Client"
              value={clientName}
              onChange={(event) =>
                setClientName(event.target.value)
              }
              placeholder="Client or contracting organization"
            />

            <Field
              label="Sector"
              value={sector}
              onChange={(event) =>
                setSector(event.target.value)
              }
              placeholder="e.g. Public Sector"
            />

            <Field
              label="Location"
              value={location}
              onChange={(event) =>
                setLocation(event.target.value)
              }
              placeholder="e.g. Nairobi"
            />

            <Field
              label="Country"
              value={country}
              onChange={(event) =>
                setCountry(event.target.value)
              }
              placeholder="e.g. Kenya"
            />

            <Field
              label="Start date"
              type="text"
              placeholder="YYYY, YYYY-MM, or YYYY-MM-DD"
              value={startDate}
              onChange={(event) =>
                setStartDate(event.target.value)
              }
            />

            <Field
              label="End date"
              type="text"
              placeholder="YYYY, YYYY-MM, or YYYY-MM-DD"
              value={endDate}
              disabled={isCurrent}
              onChange={(event) =>
                setEndDate(event.target.value)
              }
            />

            <label className="flex items-center gap-3 text-sm font-medium text-slate-700 md:col-span-2">
              <input
                type="checkbox"
                checked={isCurrent}
                onChange={(event) => {
                  setIsCurrent(event.target.checked);
                  if (event.target.checked) {
                    setEndDate("");
                  }
                }}
                className="h-4 w-4"
              />
              This project is ongoing
            </label>

            <div className="md:col-span-2">
              <TextArea
                label="Project description"
                rows={3}
                value={description}
                onChange={(event) =>
                  setDescription(event.target.value)
                }
                placeholder="Purpose, scope, and context of the project"
              />
            </div>

            <div className="md:col-span-2">
              <TextArea
                label="Responsibilities"
                rows={4}
                value={responsibilities}
                onChange={(event) =>
                  setResponsibilities(event.target.value)
                }
                placeholder="What did this person do on the project?"
              />
            </div>

            <div className="md:col-span-2">
              <TextArea
                label="Outcomes"
                rows={4}
                value={outcomes}
                onChange={(event) =>
                  setOutcomes(event.target.value)
                }
                placeholder="Deliverables, measurable outcomes, or project results"
              />
            </div>

            <div className="md:col-span-2">
              <TextArea
                label="Skills used"
                rows={3}
                value={skillsSummary}
                onChange={(event) =>
                  setSkillsSummary(event.target.value)
                }
                placeholder="e.g. Python, PostgreSQL, project management, financial analysis"
              />
            </div>
          </div>

          {create.error && (
            <p className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">
              {create.error.message}
            </p>
          )}

          <div className="mt-5">
            <Button
              type="button"
              disabled={
                create.isPending ||
                !projectName.trim() ||
                !role.trim() ||
                !startDate
              }
              onClick={() => create.mutate()}
            >
              {create.isPending
                ? "Saving…"
                : "Save project"}
            </Button>
          </div>
        </div>
      )}

      {query.isLoading ? (
        <p className="text-sm text-slate-500">
          Loading projects…
        </p>
      ) : query.error ? (
        <p className="text-sm text-red-700">
          {query.error.message}
        </p>
      ) : query.data?.length ? (
        <div className="grid gap-4">
          {query.data.map((project) => (
            <article
              key={project.id}
              className="cf-record"
            >
              <div className="flex flex-col justify-between gap-4 sm:flex-row">
                <div className="flex gap-4">
                  <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-[#fde7df] text-coral">
                    <FolderKanban size={20} />
                  </div>

                  <div>
                    <h3 className="font-semibold">
                      {project.project_name}
                    </h3>

                    <p className="mt-1 text-sm text-slate-600">
                      {project.role}
                      {project.client_name
                        ? ` · ${project.client_name}`
                        : ""}
                    </p>

                    <p className="mt-1 text-sm text-slate-400">
                      {formatExperiencePeriod(
                        project.start_date,
                        project.end_date,
                        project.is_current,
                      )}
                    </p>

                    <div className="mt-3 flex flex-wrap gap-2">
                      {project.sector && (
                        <span className="rounded-full bg-mint px-2.5 py-1 text-xs font-semibold text-evergreen">
                          {project.sector}
                        </span>
                      )}

                      {project.country && (
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600">
                          {project.country}
                        </span>
                      )}

                      {project.is_current && (
                        <span className="rounded-full bg-[#fde7df] px-2.5 py-1 text-xs font-semibold text-coral">
                          Ongoing
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  disabled={!canWrite}
                  aria-label={`Delete ${project.project_name}`}
                  onClick={() => {
                    if (
                      window.confirm(
                        `Remove project "${project.project_name}"?`,
                      )
                    ) {
                      remove.mutate(project.id);
                    }
                  }}
                  className="h-fit rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600"
                >
                  <Trash2 size={17} />
                </button>
              </div>

              {project.description && (
                <div className="mt-5 border-t border-slate-100 pt-4">
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Project
                  </p>
                  <p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-600">
                    {project.description}
                  </p>
                </div>
              )}

              {project.responsibilities && (
                <div className="mt-4">
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Responsibilities
                  </p>
                  <p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-600">
                    {project.responsibilities}
                  </p>
                </div>
              )}

              {project.outcomes && (
                <div className="mt-4">
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Outcomes
                  </p>
                  <p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-600">
                    {project.outcomes}
                  </p>
                </div>
              )}

              {project.skills_summary && (
                <div className="mt-4">
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Skills used
                  </p>
                  <p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-600">
                    {project.skills_summary}
                  </p>
                </div>
              )}
            </article>
          ))}
        </div>
      ) : (
        <EmptyCapability
          icon={FolderKanban}
          title="No project experience recorded"
          text="Add projects so matching can consider clients, sectors, countries, responsibilities, results, and applied skills."
        />
      )}
    </section>
  );
}

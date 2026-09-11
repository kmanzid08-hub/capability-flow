import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  Briefcase,
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
  EmploymentExperience,
  EmploymentType
} from "../../types";


import { EmptyCapability } from "../../components/EmptyCapability";
import { qk } from "../../lib/queryKeys";
import { formatExperiencePeriod } from "./dates";
export function WorkExperiencePanel({
  personId,
}: {
  personId: string;
}) {
  const { canWrite } = useWorkspace();
  const queryClient = useQueryClient();

  const [adding, setAdding] =
    React.useState(false);

  const [employerName, setEmployerName] =
    React.useState("");

  const [jobTitle, setJobTitle] =
    React.useState("");

  const [employmentType, setEmploymentType] =
    React.useState<EmploymentType | "">("");

  const [industry, setIndustry] =
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

  const [achievements, setAchievements] =
    React.useState("");

  const query = useQuery({
    queryKey: qk("employment", personId),
    queryFn: () =>
      api<EmploymentExperience[]>(
        `/people/${personId}/employment`,
      ),
  });

  const resetForm = () => {
    setEmployerName("");
    setJobTitle("");
    setEmploymentType("");
    setIndustry("");
    setLocation("");
    setCountry("");
    setStartDate("");
    setEndDate("");
    setIsCurrent(false);
    setDescription("");
    setResponsibilities("");
    setAchievements("");
  };

  const create = useMutation({
    mutationFn: () =>
      api<EmploymentExperience>(
        `/people/${personId}/employment`,
        {
          method: "POST",
          body: JSON.stringify({
            employer_name: employerName,
            job_title: jobTitle,
            employment_type:
              employmentType || null,
            industry:
              industry.trim() || null,
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
            achievements:
              achievements.trim() || null,
          }),
        },
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: qk("profile-completeness", personId) });
      resetForm();
      setAdding(false);
      queryClient.invalidateQueries({
        queryKey: qk("employment", personId),
      });
    },
  });

  const remove = useMutation({
    mutationFn: (experienceId: string) =>
      api<void>(
        `/people/${personId}/employment/${experienceId}`,
        {
          method: "DELETE",
        },
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: qk("profile-completeness", personId) });
      queryClient.invalidateQueries({
        queryKey: qk("employment", personId),
      });
    },
  });

  return (
    <section className="cf-panel">
      <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div>
          <h2 className="font-serif text-2xl">
            Work experience
          </h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-500">
            Record employers, roles, sectors, responsibilities,
            and achievements so capability matching can consider
            actual professional experience.
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
              Add experience
            </>
          )}
        </Button>
      </div>

      {adding && (
        <div className="mb-7 rounded-2xl border border-slate-200 bg-slate-50 p-5">
          <div className="grid gap-4 md:grid-cols-2">
            <Field
              label="Employer"
              value={employerName}
              onChange={(event) =>
                setEmployerName(event.target.value)
              }
              placeholder="e.g. Acme Group"
            />

            <Field
              label="Job title"
              value={jobTitle}
              onChange={(event) =>
                setJobTitle(event.target.value)
              }
              placeholder="e.g. Senior Engineer"
            />

            <label className="text-sm font-medium text-slate-700">
              Employment type
              <select
                value={employmentType}
                onChange={(event) =>
                  setEmploymentType(
                    event.target.value as EmploymentType | "",
                  )
                }
                className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3"
              >
                <option value="">
                  Not specified
                </option>
                <option value="full_time">
                  Full time
                </option>
                <option value="part_time">
                  Part time
                </option>
                <option value="contract">
                  Contract
                </option>
                <option value="consulting">
                  Consulting
                </option>
                <option value="temporary">
                  Temporary
                </option>
                <option value="internship">
                  Internship
                </option>
                <option value="volunteer">
                  Volunteer
                </option>
                <option value="other">
                  Other
                </option>
              </select>
            </label>

            <Field
              label="Industry / sector"
              value={industry}
              onChange={(event) =>
                setIndustry(event.target.value)
              }
              placeholder="e.g. Banking"
            />

            <Field
              label="Location"
              value={location}
              onChange={(event) =>
                setLocation(event.target.value)
              }
              placeholder="e.g. Kigali"
            />

            <Field
              label="Country"
              value={country}
              onChange={(event) =>
                setCountry(event.target.value)
              }
              placeholder="e.g. Rwanda"
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
              This is the person's current employment
            </label>

            <div className="md:col-span-2">
              <TextArea
                label="Role description"
                rows={3}
                value={description}
                onChange={(event) =>
                  setDescription(event.target.value)
                }
                placeholder="What was the overall scope of the role?"
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
                placeholder="Main responsibilities and areas of ownership"
              />
            </div>

            <div className="md:col-span-2">
              <TextArea
                label="Achievements"
                rows={4}
                value={achievements}
                onChange={(event) =>
                  setAchievements(event.target.value)
                }
                placeholder="Important outcomes, results, or accomplishments"
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
                !employerName.trim() ||
                !jobTitle.trim() ||
                !startDate
              }
              onClick={() => create.mutate()}
            >
              {create.isPending
                ? "Saving…"
                : "Save experience"}
            </Button>
          </div>
        </div>
      )}

      {query.isLoading ? (
        <p className="text-sm text-slate-500">
          Loading work experience…
        </p>
      ) : query.error ? (
        <p className="text-sm text-red-700">
          {query.error.message}
        </p>
      ) : query.data?.length ? (
        <div className="grid gap-4">
          {query.data.map((experience) => (
            <article
              key={experience.id}
              className="cf-record"
            >
              <div className="flex flex-col justify-between gap-4 sm:flex-row">
                <div className="flex gap-4">
                  <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-mint text-evergreen">
                    <Briefcase size={20} />
                  </div>

                  <div>
                    <h3 className="font-semibold">
                      {experience.job_title}
                    </h3>

                    <p className="mt-1 text-sm text-slate-600">
                      {experience.employer_name}
                    </p>

                    <p className="mt-1 text-sm text-slate-400">
                      {formatExperiencePeriod(
                        experience.start_date,
                        experience.end_date,
                        experience.is_current,
                      )}
                    </p>

                    <div className="mt-3 flex flex-wrap gap-2">
                      {experience.employment_type && (
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs capitalize text-slate-600">
                          {experience.employment_type.replace(
                            "_",
                            " ",
                          )}
                        </span>
                      )}

                      {experience.industry && (
                        <span className="rounded-full bg-mint px-2.5 py-1 text-xs font-semibold text-evergreen">
                          {experience.industry}
                        </span>
                      )}

                      {experience.country && (
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600">
                          {experience.country}
                        </span>
                      )}

                      {experience.is_current && (
                        <span className="rounded-full bg-[#fde7df] px-2.5 py-1 text-xs font-semibold text-coral">
                          Current
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  disabled={!canWrite}
                  aria-label={`Delete ${experience.job_title}`}
                  onClick={() => {
                    if (
                      window.confirm(
                        `Remove the ${experience.job_title} experience at ${experience.employer_name}?`,
                      )
                    ) {
                      remove.mutate(experience.id);
                    }
                  }}
                  className="h-fit rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600"
                >
                  <Trash2 size={17} />
                </button>
              </div>

              {experience.description && (
                <div className="mt-5 border-t border-slate-100 pt-4">
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Role
                  </p>
                  <p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-600">
                    {experience.description}
                  </p>
                </div>
              )}

              {experience.responsibilities && (
                <div className="mt-4">
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Responsibilities
                  </p>
                  <p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-600">
                    {experience.responsibilities}
                  </p>
                </div>
              )}

              {experience.achievements && (
                <div className="mt-4">
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Achievements
                  </p>
                  <p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-600">
                    {experience.achievements}
                  </p>
                </div>
              )}
            </article>
          ))}
        </div>
      ) : (
        <EmptyCapability
          icon={Briefcase}
          title="No work experience recorded"
          text="Add employment history so matching can evaluate years of experience, sectors, employers, and professional responsibilities."
        />
      )}
    </section>
  );
}

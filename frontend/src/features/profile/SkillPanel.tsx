import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  BookOpen,
  Plus,
  Trash2,
  X
} from "lucide-react";
import React from "react";
import { useWorkspace } from "../../lib/workspace";

import {
  Button,
  Field
} from "../../components/ui";
import {
  api
} from "../../lib/api";
import type {
  PersonSkill
} from "../../types";


import { EmptyCapability } from "../../components/EmptyCapability";
import { qk } from "../../lib/queryKeys";
export function SkillPanel({
  personId,
}: {
  personId: string;
}) {
  const { canWrite } = useWorkspace();
  const queryClient =
    useQueryClient();

  const [
    adding,
    setAdding,
  ] =
    React.useState(false);

  const [name, setName] =
    React.useState("");

  const [
    proficiency,
    setProficiency,
  ] =
    React.useState(
      "intermediate",
    );

  const [years, setYears] =
    React.useState("");

  const query = useQuery({
    queryKey: qk("skills", personId),

    queryFn: () =>
      api<PersonSkill[]>(
        `/people/${personId}/skills`,
      ),
  });

  const create =
    useMutation({
      mutationFn: () =>
        api<PersonSkill>(
          `/people/${personId}/skills`,
          {
            method: "POST",

            body:
              JSON.stringify({
                name,
                proficiency,

                years_experience:
                  years === ""
                    ? null
                    : Number(
                      years,
                    ),
              }),
          },
        ),

      onSuccess: () => {
        void queryClient.invalidateQueries({ queryKey: qk("profile-completeness", personId) });
        setName("");
        setYears("");
        setProficiency(
          "intermediate",
        );
        setAdding(false);

        queryClient.invalidateQueries(
          {
            queryKey: qk("skills", personId),
          },
        );
      },
    });

  const remove =
    useMutation({
      mutationFn: (
        skillId: string,
      ) =>
        api<void>(
          `/people/${personId}/skills/${skillId}`,
          {
            method:
              "DELETE",
          },
        ),

      onSuccess: () => {
        void queryClient.invalidateQueries({ queryKey: qk("profile-completeness", personId) });
        queryClient.invalidateQueries(
          {
            queryKey: qk("skills", personId),
          },
        );
      },
    });

  return (
    <section className="cf-panel">
      <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <h2 className="font-serif text-2xl">
            Skills
          </h2>

          <p className="mt-1 text-sm text-slate-500">
            Practical
            capabilities this
            person can bring
            to work.
          </p>
        </div>

        <Button
          type="button"
          disabled={!canWrite}
          onClick={() =>
            setAdding(
              !adding,
            )
          }
        >
          {adding ? (
            <>
              <X
                size={16}
                className="mr-2 inline"
              />
              Cancel
            </>
          ) : (
            <>
              <Plus
                size={16}
                className="mr-2 inline"
              />
              Add skill
            </>
          )}
        </Button>
      </div>

      {adding && (
        <div className="mb-7 rounded-2xl border border-slate-200 bg-slate-50 p-5">
          <div className="grid gap-4 md:grid-cols-3">
            <Field
              label="Skill"
              placeholder="e.g. Python"
              value={name}
              onChange={(
                event,
              ) =>
                setName(
                  event.target
                    .value,
                )
              }
            />

            <label className="text-sm font-medium text-slate-700">
              Proficiency

              <select
                value={
                  proficiency
                }
                onChange={(
                  event,
                ) =>
                  setProficiency(
                    event
                      .target
                      .value,
                  )
                }
                className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3"
              >
                <option value="beginner">
                  Beginner
                </option>

                <option value="intermediate">
                  Intermediate
                </option>

                <option value="advanced">
                  Advanced
                </option>

                <option value="expert">
                  Expert
                </option>
              </select>
            </label>

            <Field
              label="Years of experience"
              type="number"
              min="0"
              step="0.5"
              value={years}
              onChange={(
                event,
              ) =>
                setYears(
                  event.target
                    .value,
                )
              }
            />
          </div>

          {create.error && (
            <p className="mt-4 text-sm text-red-700">
              {
                create.error
                  .message
              }
            </p>
          )}

          <div className="mt-5">
            <Button
              type="button"
              disabled={
                create.isPending ||
                !name.trim()
              }
              onClick={() =>
                create.mutate()
              }
            >
              {create.isPending
                ? "Saving…"
                : "Save skill"}
            </Button>
          </div>
        </div>
      )}

      {query.isLoading ? (
        <p className="text-sm text-slate-500">
          Loading skills…
        </p>
      ) : query.data
        ?.length ? (
        <div className="grid gap-3">
          {query.data.map(
            (skill) => (
              <div
                key={
                  skill.id
                }
                className="flex items-center justify-between gap-5 cf-record"
              >
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-semibold">
                      {
                        skill.name
                      }
                    </p>

                    {skill.proficiency && (
                      <span className="rounded-full bg-mint px-2.5 py-1 text-xs font-semibold capitalize text-evergreen">
                        {
                          skill.proficiency
                        }
                      </span>
                    )}
                  </div>

                  <p className="mt-1 text-sm text-slate-500">
                    {skill.years_experience !=
                      null
                      ? `${skill.years_experience} years experience`
                      : "Experience duration not recorded"}
                  </p>
                </div>

                <button
                  type="button"
                  disabled={!canWrite}
                  aria-label={`Delete ${skill.name}`}
                  onClick={() => {
                    if (
                      window.confirm(
                        `Remove ${skill.name}?`,
                      )
                    ) {
                      remove.mutate(
                        skill.id,
                      );
                    }
                  }}
                  className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600"
                >
                  <Trash2
                    size={17}
                  />
                </button>
              </div>
            ),
          )}
        </div>
      ) : (
        <EmptyCapability
          icon={BookOpen}
          title="No skills recorded"
          text="Add the person's core technical, operational, industry, or professional skills."
        />
      )}
    </section>
  );
}

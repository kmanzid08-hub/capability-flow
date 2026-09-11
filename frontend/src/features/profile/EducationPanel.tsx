import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  GraduationCap,
  Trash2
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
  PersonEducation
} from "../../types";


import { EmptyCapability } from "../../components/EmptyCapability";
import { qk } from "../../lib/queryKeys";
import { formatPartialEvidenceDate } from "./dates";
export function EducationPanel({
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

  const [
    degreeLevel,
    setDegreeLevel,
  ] =
    React.useState(
      "bachelor",
    );

  const [
    degreeName,
    setDegreeName,
  ] =
    React.useState("");

  const [field, setField] =
    React.useState("");

  const [
    institution,
    setInstitution,
  ] =
    React.useState("");

  const [
    country,
    setCountry,
  ] =
    React.useState("");

  const [
    startDate,
    setStartDate,
  ] =
    React.useState("");

  const [
    graduationDate,
    setGraduationDate,
  ] =
    React.useState("");

  const query = useQuery({
    queryKey: qk("education", personId),

    queryFn: () =>
      api<
        PersonEducation[]
      >(
        `/people/${personId}/education`,
      ),
  });

  const create =
    useMutation({
      mutationFn: () =>
        api<PersonEducation>(
          `/people/${personId}/education`,
          {
            method: "POST",

            body:
              JSON.stringify({
                degree_level:
                  degreeLevel,

                degree_name:
                  degreeName.trim() ||
                  null,

                field_of_study:
                  field.trim() ||
                  null,

                institution,

                country:
                  country.trim() ||
                  null,

                start_date:
                  startDate ||
                  null,

                graduation_date:
                  graduationDate ||
                  null,
              }),
          },
        ),

      onSuccess: () => {
        void queryClient.invalidateQueries({ queryKey: qk("profile-completeness", personId) });
        setDegreeName("");
        setField("");
        setInstitution("");
        setCountry("");
        setStartDate(
          "",
        );
        setGraduationDate(
          "",
        );
        setDegreeLevel(
          "bachelor",
        );
        setAdding(false);

        queryClient.invalidateQueries(
          {
            queryKey: qk("education", personId),
          },
        );
      },
    });

  const remove =
    useMutation({
      mutationFn: (
        educationId: string,
      ) =>
        api<void>(
          `/people/${personId}/education/${educationId}`,
          {
            method:
              "DELETE",
          },
        ),

      onSuccess: () => {
        void queryClient.invalidateQueries({ queryKey: qk("profile-completeness", personId) });
        queryClient.invalidateQueries(
          {
            queryKey: qk("education", personId),
          },
        );
      },
    });

  return (
    <section className="cf-panel">
      <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <h2 className="font-serif text-2xl">
            Education
          </h2>

          <p className="mt-1 text-sm text-slate-500">
            Degrees and formal
            educational
            qualifications.
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
          {adding
            ? "Cancel"
            : "Add education"}
        </Button>
      </div>

      {adding && (
        <div className="mb-7 rounded-2xl border border-slate-200 bg-slate-50 p-5">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="text-sm font-medium text-slate-700">
              Degree level

              <select
                value={
                  degreeLevel
                }
                onChange={(
                  event,
                ) =>
                  setDegreeLevel(
                    event
                      .target
                      .value,
                  )
                }
                className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3"
              >
                <option value="secondary">
                  Secondary
                </option>

                <option value="certificate">
                  Certificate
                </option>

                <option value="diploma">
                  Diploma
                </option>

                <option value="associate">
                  Associate
                </option>

                <option value="bachelor">
                  Bachelor
                </option>

                <option value="master">
                  Master
                </option>

                <option value="doctorate">
                  Doctorate
                </option>

                <option value="professional">
                  Professional
                </option>

                <option value="other">
                  Other
                </option>
              </select>
            </label>

            <Field
              label="Degree name"
              placeholder="Master of Science"
              value={
                degreeName
              }
              onChange={(
                event,
              ) =>
                setDegreeName(
                  event.target
                    .value,
                )
              }
            />

            <Field
              label="Field of study"
              placeholder="Computer Science"
              value={field}
              onChange={(
                event,
              ) =>
                setField(
                  event.target
                    .value,
                )
              }
            />

            <Field
              label="Institution"
              value={
                institution
              }
              onChange={(
                event,
              ) =>
                setInstitution(
                  event.target
                    .value,
                )
              }
            />

            <Field
              label="Country"
              value={country}
              onChange={(
                event,
              ) =>
                setCountry(
                  event.target
                    .value,
                )
              }
            />

            <Field
              label="Start date"
              type="text"
              placeholder="YYYY, YYYY-MM, or YYYY-MM-DD"
              value={
                startDate
              }
              onChange={(
                event,
              ) =>
                setStartDate(
                  event.target
                    .value,
                )
              }
            />

            <Field
              label="Graduation / completion date"
              type="text"
              placeholder="YYYY, YYYY-MM, or YYYY-MM-DD"
              value={
                graduationDate
              }
              onChange={(
                event,
              ) =>
                setGraduationDate(
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
                !institution.trim()
              }
              onClick={() =>
                create.mutate()
              }
            >
              {create.isPending
                ? "Saving…"
                : "Save education"}
            </Button>
          </div>
        </div>
      )}

      {query.isLoading ? (
        <p className="text-sm text-slate-500">
          Loading education…
        </p>
      ) : query.data
        ?.length ? (
        <div className="grid gap-3">
          {query.data.map(
            (education) => (
              <div
                key={
                  education.id
                }
                className="flex justify-between gap-5 cf-record"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <GraduationCap
                      size={18}
                      className="text-evergreen"
                    />

                    <p className="font-semibold">
                      {education.degree_name ||
                        education.degree_level}
                    </p>
                  </div>

                  <p className="mt-2 text-sm text-slate-600">
                    {
                      education.institution
                    }
                  </p>

                  <p className="mt-1 text-sm text-slate-400">
                    {[
                      education.field_of_study,
                      education.country,
                      education.start_date || education.graduation_date
                        ? `${education.start_date ? formatPartialEvidenceDate(education.start_date) : "Start not recorded"} – ${education.graduation_date ? formatPartialEvidenceDate(education.graduation_date) : "Completion not recorded"}`
                        : null,
                    ]
                      .filter(
                        Boolean,
                      )
                      .join(
                        " · ",
                      )}
                  </p>
                </div>

                <button
                  type="button"
                  disabled={!canWrite}
                  aria-label="Delete education"
                  onClick={() => {
                    if (
                      window.confirm(
                        "Remove this education record?",
                      )
                    ) {
                      remove.mutate(
                        education.id,
                      );
                    }
                  }}
                  className="h-fit rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600"
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
          icon={
            GraduationCap
          }
          title="No education recorded"
          text="Add degrees, diplomas, and other formal educational qualifications."
        />
      )}
    </section>
  );
}

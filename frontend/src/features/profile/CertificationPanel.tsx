import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  Award,
  Trash2
} from "lucide-react";
import React from "react";
import { externalHref } from "../../lib/links";
import { useWorkspace } from "../../lib/workspace";

import {
  Button,
  Field
} from "../../components/ui";
import {
  api
} from "../../lib/api";
import type {
  PersonCertification
} from "../../types";


import { EmptyCapability } from "../../components/EmptyCapability";
import { qk } from "../../lib/queryKeys";
import { formatPartialEvidenceDate } from "./dates";
export function CertificationPanel({
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
    issuer,
    setIssuer,
  ] =
    React.useState("");

  const [
    credentialId,
    setCredentialId,
  ] =
    React.useState("");

  const [
    issueDate,
    setIssueDate,
  ] =
    React.useState("");

  const [
    expiryDate,
    setExpiryDate,
  ] =
    React.useState("");

  const [
    verificationUrl,
    setVerificationUrl,
  ] =
    React.useState("");

  const query = useQuery({
    queryKey: qk("certifications", personId),

    queryFn: () =>
      api<
        PersonCertification[]
      >(
        `/people/${personId}/certifications`,
      ),
  });

  const create =
    useMutation({
      mutationFn: () =>
        api<
          PersonCertification
        >(
          `/people/${personId}/certifications`,
          {
            method: "POST",

            body:
              JSON.stringify({
                name,

                issuer:
                  issuer.trim() ||
                  null,

                credential_id:
                  credentialId.trim() ||
                  null,

                issue_date:
                  issueDate ||
                  null,

                expiry_date:
                  expiryDate ||
                  null,

                verification_url:
                  verificationUrl.trim() ||
                  null,
              }),
          },
        ),

      onSuccess: () => {
        void queryClient.invalidateQueries({ queryKey: qk("profile-completeness", personId) });
        setName("");
        setIssuer("");
        setCredentialId(
          "",
        );
        setIssueDate("");
        setExpiryDate("");
        setVerificationUrl(
          "",
        );
        setAdding(false);

        queryClient.invalidateQueries(
          {
            queryKey: qk("certifications", personId),
          },
        );
      },
    });

  const remove =
    useMutation({
      mutationFn: (
        certificationId: string,
      ) =>
        api<void>(
          `/people/${personId}/certifications/${certificationId}`,
          {
            method:
              "DELETE",
          },
        ),

      onSuccess: () => {
        void queryClient.invalidateQueries({ queryKey: qk("profile-completeness", personId) });
        queryClient.invalidateQueries(
          {
            queryKey: qk("certifications", personId),
          },
        );
      },
    });

  return (
    <section className="cf-panel">
      <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <h2 className="font-serif text-2xl">
            Certifications
          </h2>

          <p className="mt-1 text-sm text-slate-500">
            Professional
            credentials and
            certifications.
            Verification details can be recorded with the credential.
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
            : "Add certification"}
        </Button>
      </div>

      {adding && (
        <div className="mb-7 rounded-2xl border border-slate-200 bg-slate-50 p-5">
          <div className="grid gap-4 md:grid-cols-2">
            <Field
              label="Certification"
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

            <Field
              label="Issuer"
              value={issuer}
              onChange={(
                event,
              ) =>
                setIssuer(
                  event.target
                    .value,
                )
              }
            />

            <Field
              label="Credential ID"
              value={
                credentialId
              }
              onChange={(
                event,
              ) =>
                setCredentialId(
                  event.target
                    .value,
                )
              }
            />

            <Field
              label="Verification URL"
              type="url"
              value={
                verificationUrl
              }
              onChange={(
                event,
              ) =>
                setVerificationUrl(
                  event.target
                    .value,
                )
              }
            />

            <Field
              label="Issue date"
              type="text"
              placeholder="YYYY, YYYY-MM, or YYYY-MM-DD"
              value={
                issueDate
              }
              onChange={(
                event,
              ) =>
                setIssueDate(
                  event.target
                    .value,
                )
              }
            />

            <Field
              label="Expiry date"
              type="text"
              placeholder="YYYY, YYYY-MM, or YYYY-MM-DD"
              value={
                expiryDate
              }
              onChange={(
                event,
              ) =>
                setExpiryDate(
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
                : "Save certification"}
            </Button>
          </div>
        </div>
      )}

      {query.isLoading ? (
        <p className="text-sm text-slate-500">
          Loading
          certifications…
        </p>
      ) : query.data
        ?.length ? (
        <div className="grid gap-3">
          {query.data.map(
            (
              certification,
            ) => (
              <div
                key={
                  certification.id
                }
                className="flex justify-between gap-5 cf-record"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <Award
                      size={18}
                      className="text-coral"
                    />

                    <p className="font-semibold">
                      {
                        certification.name
                      }
                    </p>
                  </div>

                  <p className="mt-2 text-sm text-slate-600">
                    {certification.issuer ||
                      "Issuer not recorded"}
                  </p>

                  <p className="mt-1 text-sm text-slate-400">
                    {certification.expiry_date
                      ? `Expires ${formatPartialEvidenceDate(certification.expiry_date)}`
                      : "No expiry date"}
                  </p>

                  {externalHref(certification.verification_url) && (
                    <a
                      href={externalHref(certification.verification_url)}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-2 inline-block text-sm font-semibold text-evergreen hover:underline"
                    >
                      Verify
                      credential
                    </a>
                  )}
                </div>

                <button
                  type="button"
                  disabled={!canWrite}
                  aria-label={`Delete ${certification.name}`}
                  onClick={() => {
                    if (
                      window.confirm(
                        `Remove ${certification.name}?`,
                      )
                    ) {
                      remove.mutate(
                        certification.id,
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
          icon={Award}
          title="No certifications recorded"
          text="Add professional credentials, licenses, and certifications."
        />
      )}
    </section>
  );
}

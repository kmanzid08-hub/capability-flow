import { zodResolver } from "@hookform/resolvers/zod";
import {
  useMutation,
  useQueryClient
} from "@tanstack/react-query";
import {
  ArrowLeft
} from "lucide-react";
import { useForm } from "react-hook-form";
import {
  Link,
  useNavigate
} from "react-router-dom";
import { z } from "zod";
import { useWorkspace } from "../lib/workspace";

import {
  Button,
  Field,
  PageHeader
} from "../components/ui";
import {
  api
} from "../lib/api";
import type {
  Person
} from "../types";


import { qk } from "../lib/queryKeys";
const wrapper = "cf-page";
const personSchema =
  z.object({
    first_name:
      z.string().min(1),

    middle_name:
      z.string().optional(),

    last_name:
      z.string().min(1),

    professional_title:
      z.string().optional(),

    primary_email:
      z
        .union([
          z.string().email(),
          z.literal(""),
        ])
        .optional(),

    primary_phone:
      z.string().optional(),

    country_of_residence:
      z.string().optional(),

    availability_status:
      z.enum([
        "unknown",
        "available",
        "partially_available",
        "unavailable",
      ]),

    profile_status:
      z.enum([
        "draft",
        "active",
      ]),
  });

type PersonValues =
  z.infer<
    typeof personSchema
  >;

export function AddPersonPage() {
  const { canWrite } = useWorkspace();
  const navigate =
    useNavigate();

  const queryClient =
    useQueryClient();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<PersonValues>({
    resolver:
      zodResolver(
        personSchema,
      ),

    defaultValues: {
      availability_status:
        "unknown",

      profile_status:
        "draft",
    },
  });

  const mutation =
    useMutation({
      mutationFn: (
        values: PersonValues,
      ) =>
        api<Person>(
          "/people",
          {
            method: "POST",

            body:
              JSON.stringify(
                Object.fromEntries(
                  Object.entries(
                    values,
                  ).map(
                    ([
                      key,
                      value,
                    ]) => [
                        key,
                        value ||
                        null,
                      ],
                  ),
                ),
              ),
          },
        ),

      onSuccess: (
        person,
      ) => {
        queryClient.invalidateQueries(
          {
            queryKey: qk("people"),
          },
        );

        navigate(
          `/people/${person.id}?tab=documents`,
        );
      },
    });

  return (
    <div className={wrapper}>
      <Link
        to="/people"
        className="mb-5 inline-flex items-center gap-2 text-sm text-slate-500"
      >
        <ArrowLeft
          size={16}
        />
        People directory
      </Link>

      <PageHeader
        eyebrow="New person"
        title="Add a person"
      >
        Start with their name and contact details. Add evidence after saving.
      </PageHeader>

      <form
        onSubmit={handleSubmit(
          (values) =>
            mutation.mutate(
              values,
            ),
        )}
        className="max-w-4xl cf-panel"
      >
        <div className="grid gap-5 sm:grid-cols-2">
          <Field
            label="First name"
            error={
              errors.first_name
                ?.message
            }
            {...register(
              "first_name",
            )}
          />

          <Field
            label="Middle name"
            {...register(
              "middle_name",
            )}
          />

          <Field
            label="Last name"
            error={
              errors.last_name
                ?.message
            }
            {...register(
              "last_name",
            )}
          />

          <Field
            label="Professional title"
            {...register(
              "professional_title",
            )}
          />

          <Field
            label="Primary email"
            type="email"
            error={
              errors
                .primary_email
                ?.message
            }
            {...register(
              "primary_email",
            )}
          />

          <Field
            label="Primary phone"
            {...register(
              "primary_phone",
            )}
          />

          <Field
            label="Country of residence"
            {...register(
              "country_of_residence",
            )}
          />

          <label className="text-sm font-medium text-slate-700">
            Availability

            <select
              {...register(
                "availability_status",
              )}
              className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3"
            >
              <option value="unknown">
                Unknown
              </option>

              <option value="available">
                Available
              </option>

              <option value="partially_available">
                Partially
                available
              </option>

              <option value="unavailable">
                Unavailable
              </option>
            </select>
          </label>

        </div>

        {mutation.error && (
          <p className="mt-4 text-sm text-red-700">
            {
              mutation.error
                .message
            }
          </p>
        )}

        <div className="mt-7 flex gap-3">
          <Button
            type="submit"
            disabled={
              mutation.isPending || !canWrite
            }
          >
            {mutation.isPending
              ? "Saving…"
              : "Save person"}
          </Button>

          <Button
            type="button"
            secondary
            onClick={() =>
              navigate(
                "/people",
              )
            }
          >
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}

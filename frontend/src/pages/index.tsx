import { zodResolver } from "@hookform/resolvers/zod";
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  Award,
  BookOpen,
  Briefcase,
  Building2,
  FolderKanban,
  FileText,
  Download,
  Eye,
  Sparkles,
  Check,
  XCircle,
  Upload,
  GraduationCap,
  Plus,
  Search,
  Trash2,
  Users,
  X,
} from "lucide-react";
import React from "react";
import { useForm } from "react-hook-form";
import {
  Link,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { z } from "zod";

import {
  Button,
  Field,
  PageHeader,
  TextArea,
} from "../components/ui";
import { AI_ANALYSIS_TIMEOUT_MS, API_URL, api, apiBlob, apiDownload } from "../lib/api";
import { session } from "../lib/session";
import type {
  CurrentUser,
  EmploymentExperience,
  EmploymentType,
  PeoplePage as PeopleResult,
  Person,
  PersonCertification,
  PersonEducation,
  PersonSkill,
  PersonDocument,
  DocumentType,
  ProfileSuggestion,
  ProfileCompleteness,
  ProjectExperience,
} from "../types";

const wrapper =
  "mx-auto max-w-7xl px-6 py-10 lg:px-10";

const authSchema = z.object({
  email: z.string().email("Enter a valid email address."),
  password: z.string().min(12, "Password must be at least 12 characters."),
});

type AuthValues = z.infer<typeof authSchema>;

function AuthFrame({
  title,
  intro,
  children,
}: {
  title: string;
  intro: string;
  children: React.ReactNode;
}) {
  return (
    <main className="grid min-h-screen lg:grid-cols-[.9fr_1.1fr]">
      <section className="hidden bg-ink p-14 text-white lg:flex lg:flex-col">
        <div className="flex items-center gap-3 font-serif text-xl">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-coral">
            C
          </span>
          Capability Flow
        </div>

        <div className="my-auto max-w-xl">
          <p className="mb-5 text-xs font-bold uppercase tracking-[.25em] text-mint">
            Know what your organization can deliver
          </p>

          <h1 className="font-serif text-6xl leading-[1.05]">
            Turn experience into readiness.
          </h1>

          <p className="mt-7 text-lg leading-8 text-white/60">
            A secure workspace for the people, evidence,
            and capabilities behind every opportunity.
          </p>
        </div>

        <p className="text-xs text-white/30">
          Private by organization. Built for accountable
          decisions.
        </p>
      </section>

      <section className="grid place-items-center bg-[#f8f7f2] p-6">
        <div className="w-full max-w-md">
          <h2 className="font-serif text-4xl">
            {title}
          </h2>

          <p className="mb-8 mt-3 text-slate-500">
            {intro}
          </p>

          {children}
        </div>
      </section>
    </main>
  );
}

export function LoginPage() {
  const navigate = useNavigate();
  const [submitError, setSubmitError] = React.useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<AuthValues>({
    resolver: zodResolver(authSchema),
  });

  const login = useMutation({
    mutationFn: async (values: AuthValues) => {
      setSubmitError(null);

      const { access_token } = await api<{ access_token: string }>(
        "/auth/login",
        {
          method: "POST",
          body: JSON.stringify(values),
        },
      );

      localStorage.setItem("capability-flow-token", access_token);

      const me = await api<CurrentUser>("/auth/me");
      const membership = me.memberships[0];

      if (!membership) {
        throw new Error("Your account does not have an active organization membership.");
      }

      return { access_token, organization_id: membership.organization_id };
    },

    onSuccess: ({ access_token, organization_id }) => {
      session.set(access_token, organization_id);
      navigate("/");
    },

    onError: (error) => {
      localStorage.removeItem("capability-flow-token");
      setSubmitError(error instanceof Error ? error.message : "Sign in failed.");
    },
  });

  return (
    <AuthFrame
      title="Welcome back"
      intro="Sign in to your organization's private workspace."
    >
      <form
        className="space-y-5"
        noValidate
        onSubmit={handleSubmit(
          (values) => login.mutate(values),
          () => setSubmitError("Please correct the highlighted fields and try again."),
        )}
      >
        <Field
          label="Work email"
          type="email"
          autoComplete="email"
          error={errors.email?.message}
          {...register("email")}
        />

        <Field
          label="Password"
          type="password"
          autoComplete="current-password"
          error={errors.password?.message}
          {...register("password")}
        />

        {(submitError || login.error) && (
          <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700">
            {submitError ?? login.error?.message}
          </p>
        )}

        <Button type="submit" disabled={login.isPending}>
          {login.isPending ? "Signing in…" : "Sign in"}
        </Button>
      </form>

      <p className="mt-4 break-all text-xs text-slate-400">
        API: {API_URL}
      </p>

      <p className="mt-8 text-sm text-slate-500">
        New to Capability Flow?{" "}
        <Link className="font-semibold text-evergreen" to="/register">
          Create an organization
        </Link>
      </p>
    </AuthFrame>
  );
}

const registrationSchema =
  authSchema.extend({
    organization_name: z
      .string()
      .min(2, "Organization name must be at least 2 characters."),

    organization_slug:
      z
        .string()
        .regex(
          /^[a-z0-9]+(?:-[a-z0-9]+)*$/,
          "Use lowercase letters, numbers, and single hyphens only.",
        ),

    full_name: z
      .string()
      .min(2, "Full name must be at least 2 characters."),
  });

type RegistrationValues =
  z.infer<
    typeof registrationSchema
  >;

export function RegisterPage() {
  const navigate = useNavigate();
  const [submitError, setSubmitError] = React.useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegistrationValues>({
    resolver: zodResolver(registrationSchema),
  });

  const mutation = useMutation({
    mutationFn: (values: RegistrationValues) => {
      setSubmitError(null);
      return api<{
        access_token: string;
        organization_id: string;
      }>("/auth/register-organization", {
        method: "POST",
        body: JSON.stringify(values),
      });
    },

    onSuccess: (data) => {
      session.set(data.access_token, data.organization_id);
      navigate("/");
    },

    onError: (error) => {
      setSubmitError(
        error instanceof Error ? error.message : "Workspace creation failed.",
      );
    },
  });

  return (
    <AuthFrame
      title="Create your workspace"
      intro="Start with your organization and owner account."
    >
      <form
        className="grid gap-4"
        noValidate
        onSubmit={handleSubmit(
          (values) => mutation.mutate(values),
          () => setSubmitError("Please correct the highlighted fields and try again."),
        )}
      >
        <Field
          label="Organization name"
          error={errors.organization_name?.message}
          {...register("organization_name")}
        />

        <Field
          label="Workspace slug"
          placeholder="acme-group"
          error={errors.organization_slug?.message}
          {...register("organization_slug")}
        />

        <Field
          label="Your full name"
          error={errors.full_name?.message}
          {...register("full_name")}
        />

        <Field
          label="Work email"
          type="email"
          autoComplete="email"
          error={errors.email?.message}
          {...register("email")}
        />

        <Field
          label="Password"
          type="password"
          autoComplete="new-password"
          placeholder="At least 12 characters"
          error={errors.password?.message}
          {...register("password")}
        />

        {(submitError || mutation.error) && (
          <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700">
            {submitError ?? mutation.error?.message}
          </p>
        )}

        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Creating workspace…" : "Create workspace"}
        </Button>
      </form>

      <p className="mt-4 break-all text-xs text-slate-400">
        API: {API_URL}
      </p>

      <p className="mt-6 text-sm text-slate-500">
        Already registered?{" "}
        <Link className="font-semibold text-evergreen" to="/login">
          Sign in
        </Link>
      </p>
    </AuthFrame>
  );
}

export function DashboardPage() {
  const people = useQuery({
    queryKey: ["people"],

    queryFn: () =>
      api<PeopleResult>(
        "/people?limit=5",
      ),
  });

  const cards = [
    {
      label: "People records",
      value:
        people.data?.total ??
        "—",
      icon: Users,
      tone:
        "bg-mint text-evergreen",
    },
    {
      label:
        "Capability records",
      value: "Active",
      icon: Award,
      tone:
        "bg-[#fde7df] text-coral",
    },
    {
      label:
        "Workspace status",
      value: "Active",
      icon: Building2,
      tone:
        "bg-sand text-ink",
    },
  ];

  return (
    <div className={wrapper}>
      <PageHeader
        eyebrow="Workspace overview"
        title="Know what your organization can deliver."
      >
        Build a structured
        picture of your people,
        qualifications,
        certifications, and
        capabilities.
      </PageHeader>

      <div className="grid gap-5 md:grid-cols-3">
        {cards.map(
          ({
            label,
            value,
            icon: Icon,
            tone,
          }) => (
            <div
              className="rounded-2xl border border-black/5 bg-white p-6 shadow-soft"
              key={label}
            >
              <div
                className={`mb-8 grid h-11 w-11 place-items-center rounded-xl ${tone}`}
              >
                <Icon
                  size={20}
                />
              </div>

              <p className="text-sm text-slate-500">
                {label}
              </p>

              <p className="mt-1 font-serif text-3xl">
                {value}
              </p>
            </div>
          ),
        )}
      </div>

      <section className="mt-8 rounded-2xl bg-evergreen p-8 text-white">
        <p className="text-xs font-bold uppercase tracking-[.2em] text-mint">
          Capability foundation
        </p>

        <h2 className="mt-3 font-serif text-3xl">
          Build your
          organizational
          capability map
        </h2>

        <p className="mt-3 max-w-2xl text-sm leading-6 text-white/65">
          Maintain people,
          skills, education,
          professional
          certifications, and
          supporting records.
        </p>

        <Link
          to="/people"
          className="mt-6 inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-semibold text-evergreen"
        >
          Open people directory
          <ArrowRight
            size={16}
          />
        </Link>
      </section>
    </div>
  );
}

export function PeoplePage() {
  const [
    search,
    setSearch,
  ] = React.useState("");

  const query = useQuery({
    queryKey: ["people"],

    queryFn: () =>
      api<PeopleResult>(
        "/people",
      ),
  });

  const items =
    (
      query.data?.items ??
      []
    ).filter((person) =>
      person.display_name
        .toLowerCase()
        .includes(
          search.toLowerCase(),
        ),
    );

  return (
    <div className={wrapper}>
      <PageHeader
        eyebrow="Resource records"
        title="People directory"
        action={
          <Link
            to="/people/new"
            className="inline-flex items-center gap-2 rounded-xl bg-evergreen px-5 py-3 text-sm font-semibold text-white"
          >
            <Plus
              size={17}
            />
            Add person
          </Link>
        }
      >
        Maintain a current,
        private directory of
        the people your
        organization can draw
        on.
      </PageHeader>

      <div className="mb-5 flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4">
        <Search
          size={18}
          className="text-slate-400"
        />

        <input
          value={search}
          onChange={(event) =>
            setSearch(
              event.target.value,
            )
          }
          className="w-full bg-transparent py-3 outline-none"
          placeholder="Search by name…"
        />
      </div>

      {query.isLoading ? (
        <p>Loading people…</p>
      ) : items.length ===
        0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white py-20 text-center">
          <Users
            className="mx-auto text-slate-300"
            size={40}
          />

          <h2 className="mt-4 font-serif text-2xl">
            No people found
          </h2>

          <p className="mt-2 text-sm text-slate-500">
            Add your first
            person record to
            begin.
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <table className="w-full text-left">
            <thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-6 py-4">
                  Person
                </th>

                <th className="hidden px-6 py-4 sm:table-cell">
                  Availability
                </th>

                <th className="px-6 py-4">
                  Status
                </th>
              </tr>
            </thead>

            <tbody>
              {items.map(
                (person) => (
                  <tr
                    key={
                      person.id
                    }
                    className="border-t border-slate-100 hover:bg-slate-50"
                  >
                    <td className="px-6 py-5">
                      <Link
                        to={`/people/${person.id}`}
                        className="font-semibold text-ink hover:text-evergreen"
                      >
                        {
                          person.display_name
                        }
                      </Link>

                      <p className="text-sm text-slate-500">
                        {person.professional_title ||
                          "Title not recorded"}
                      </p>
                    </td>

                    <td className="hidden px-6 py-5 text-sm capitalize sm:table-cell">
                      {person.availability_status.replace(
                        "_",
                        " ",
                      )}
                    </td>

                    <td className="px-6 py-5">
                      <span className="rounded-full bg-mint px-3 py-1 text-xs font-semibold capitalize text-evergreen">
                        {
                          person.profile_status
                        }
                      </span>
                    </td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

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
            queryKey: [
              "people",
            ],
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
        eyebrow="New resource record"
        title="Add a person"
      >
        Enter only the essentials. After saving, upload the person's CV, certificates, degrees, and supporting evidence so AI can propose the rest of the profile for review.
      </PageHeader>

      <form
        onSubmit={handleSubmit(
          (values) =>
            mutation.mutate(
              values,
            ),
        )}
        className="max-w-4xl rounded-2xl bg-white p-7 shadow-soft"
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
              mutation.isPending
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

type CapabilityTab =
  | "overview"
  | "skills"
  | "education"
  | "certifications"
  | "work"
  | "projects"
  | "documents";

function EmptyCapability({
  icon: Icon,
  title,
  text,
}: {
  icon: React.ElementType;
  title: string;
  text: string;
}) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center">
      <Icon
        size={34}
        className="mx-auto text-slate-300"
      />

      <h3 className="mt-4 font-serif text-xl">
        {title}
      </h3>

      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">
        {text}
      </p>
    </div>
  );
}

function SkillPanel({
  personId,
}: {
  personId: string;
}) {
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
    queryKey: [
      "skills",
      personId,
    ],

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
        setName("");
        setYears("");
        setProficiency(
          "intermediate",
        );
        setAdding(false);

        queryClient.invalidateQueries(
          {
            queryKey: [
              "skills",
              personId,
            ],
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
        queryClient.invalidateQueries(
          {
            queryKey: [
              "skills",
              personId,
            ],
          },
        );
      },
    });

  return (
    <section className="rounded-2xl bg-white p-7 shadow-soft">
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
                className="flex items-center justify-between gap-5 rounded-xl border border-slate-200 p-4"
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

function EducationPanel({
  personId,
}: {
  personId: string;
}) {
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
    graduationYear,
    setGraduationYear,
  ] =
    React.useState("");

  const query = useQuery({
    queryKey: [
      "education",
      personId,
    ],

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

                graduation_year:
                  graduationYear ===
                    ""
                    ? null
                    : Number(
                      graduationYear,
                    ),
              }),
          },
        ),

      onSuccess: () => {
        setDegreeName("");
        setField("");
        setInstitution("");
        setCountry("");
        setGraduationYear(
          "",
        );
        setDegreeLevel(
          "bachelor",
        );
        setAdding(false);

        queryClient.invalidateQueries(
          {
            queryKey: [
              "education",
              personId,
            ],
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
        queryClient.invalidateQueries(
          {
            queryKey: [
              "education",
              personId,
            ],
          },
        );
      },
    });

  return (
    <section className="rounded-2xl bg-white p-7 shadow-soft">
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
              label="Graduation year"
              type="number"
              min="1900"
              max="2100"
              value={
                graduationYear
              }
              onChange={(
                event,
              ) =>
                setGraduationYear(
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
                className="flex justify-between gap-5 rounded-xl border border-slate-200 p-5"
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
                      education.graduation_year,
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

function CertificationPanel({
  personId,
}: {
  personId: string;
}) {
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
    queryKey: [
      "certifications",
      personId,
    ],

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
            queryKey: [
              "certifications",
              personId,
            ],
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
        queryClient.invalidateQueries(
          {
            queryKey: [
              "certifications",
              personId,
            ],
          },
        );
      },
    });

  return (
    <section className="rounded-2xl bg-white p-7 shadow-soft">
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
              type="date"
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
              type="date"
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
                className="flex justify-between gap-5 rounded-xl border border-slate-200 p-5"
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
                      ? `Expires ${certification.expiry_date}`
                      : "No expiry date"}
                  </p>

                  {certification.verification_url && (
                    <a
                      href={
                        certification.verification_url
                      }
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


function formatExperiencePeriod(
  startDate: string,
  endDate: string | null,
  isCurrent: boolean,
): string {
  const start = new Date(
    `${startDate}T00:00:00`,
  ).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
  });

  const end = isCurrent
    ? "Present"
    : endDate
      ? new Date(
        `${endDate}T00:00:00`,
      ).toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
      })
      : "Not recorded";

  return `${start} – ${end}`;
}

function WorkExperiencePanel({
  personId,
}: {
  personId: string;
}) {
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
    queryKey: ["employment", personId],
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
      resetForm();
      setAdding(false);
      queryClient.invalidateQueries({
        queryKey: ["employment", personId],
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
      queryClient.invalidateQueries({
        queryKey: ["employment", personId],
      });
    },
  });

  return (
    <section className="rounded-2xl bg-white p-7 shadow-soft">
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
              type="date"
              value={startDate}
              onChange={(event) =>
                setStartDate(event.target.value)
              }
            />

            <Field
              label="End date"
              type="date"
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
              className="rounded-xl border border-slate-200 p-5"
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

function ProjectsPanel({
  personId,
}: {
  personId: string;
}) {
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
    queryKey: ["projects", personId],
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
      resetForm();
      setAdding(false);
      queryClient.invalidateQueries({
        queryKey: ["projects", personId],
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
      queryClient.invalidateQueries({
        queryKey: ["projects", personId],
      });
    },
  });

  return (
    <section className="rounded-2xl bg-white p-7 shadow-soft">
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
              type="date"
              value={startDate}
              onChange={(event) =>
                setStartDate(event.target.value)
              }
            />

            <Field
              label="End date"
              type="date"
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
              className="rounded-xl border border-slate-200 p-5"
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


const documentTypeOptions: { value: DocumentType; label: string }[] = [
  { value: "cv", label: "CV / Resume" },
  { value: "certificate", label: "Professional certificate" },
  { value: "degree", label: "Degree / academic evidence" },
  { value: "good_completion_certificate", label: "Good completion certificate" },
  { value: "reference_letter", label: "Reference letter" },
  { value: "license", label: "License / accreditation" },
  { value: "project_evidence", label: "Project evidence" },
  { value: "employment_evidence", label: "Employment evidence" },
  { value: "other", label: "Other" },
];

type SuggestionFieldKind =
  | "text"
  | "number"
  | "date"
  | "textarea"
  | "select"
  | "checkbox";

type SuggestionField = {
  key: string;
  label: string;
  kind?: SuggestionFieldKind;
  options?: { value: string; label: string }[];
  placeholder?: string;
};

const suggestionFields: Record<ProfileSuggestion["category"], SuggestionField[]> = {
  profile: [
    { key: "professional_title", label: "Professional title" },
    { key: "summary", label: "Professional summary", kind: "textarea" },
    { key: "nationality", label: "Nationality" },
    { key: "country_of_residence", label: "Country of residence" },
  ],
  skill: [
    { key: "name", label: "Skill" },
    {
      key: "proficiency",
      label: "Proficiency",
      kind: "select",
      options: [
        { value: "", label: "Not specified" },
        { value: "beginner", label: "Beginner" },
        { value: "intermediate", label: "Intermediate" },
        { value: "advanced", label: "Advanced" },
        { value: "expert", label: "Expert" },
      ],
    },
    { key: "years_experience", label: "Years of experience", kind: "number" },
    { key: "last_used_year", label: "Last used year", kind: "number" },
    { key: "notes", label: "Notes", kind: "textarea" },
  ],
  education: [
    {
      key: "degree_level",
      label: "Degree level",
      kind: "select",
      options: [
        { value: "secondary", label: "Secondary" },
        { value: "certificate", label: "Certificate" },
        { value: "diploma", label: "Diploma" },
        { value: "associate", label: "Associate" },
        { value: "bachelor", label: "Bachelor" },
        { value: "master", label: "Master" },
        { value: "doctorate", label: "Doctorate" },
        { value: "professional", label: "Professional" },
        { value: "other", label: "Other" },
      ],
    },
    { key: "degree_name", label: "Degree name" },
    { key: "field_of_study", label: "Field of study" },
    { key: "institution", label: "Institution" },
    { key: "country", label: "Country" },
    { key: "start_year", label: "Start year", kind: "number" },
    { key: "graduation_year", label: "Graduation year", kind: "number" },
    { key: "notes", label: "Notes", kind: "textarea" },
  ],
  certification: [
    { key: "name", label: "Certification" },
    { key: "issuer", label: "Issuer" },
    { key: "credential_id", label: "Credential ID" },
    { key: "issue_date", label: "Issue date", kind: "date" },
    { key: "expiry_date", label: "Expiry date", kind: "date" },
    { key: "verification_url", label: "Verification URL" },
    { key: "notes", label: "Notes", kind: "textarea" },
  ],
  employment: [
    { key: "employer_name", label: "Employer" },
    { key: "job_title", label: "Job title" },
    {
      key: "employment_type",
      label: "Employment type",
      kind: "select",
      options: [
        { value: "", label: "Not specified" },
        { value: "full_time", label: "Full time" },
        { value: "part_time", label: "Part time" },
        { value: "contract", label: "Contract" },
        { value: "consulting", label: "Consulting" },
        { value: "temporary", label: "Temporary" },
        { value: "internship", label: "Internship" },
        { value: "volunteer", label: "Volunteer" },
        { value: "other", label: "Other" },
      ],
    },
    { key: "industry", label: "Industry / sector" },
    { key: "location", label: "Location" },
    { key: "country", label: "Country" },
    { key: "start_date", label: "Start date", kind: "date" },
    { key: "end_date", label: "End date", kind: "date" },
    { key: "is_current", label: "Current employment", kind: "checkbox" },
    { key: "description", label: "Role description", kind: "textarea" },
    { key: "responsibilities", label: "Responsibilities", kind: "textarea" },
    { key: "achievements", label: "Achievements", kind: "textarea" },
  ],
  project: [
    { key: "project_name", label: "Project name" },
    { key: "client_name", label: "Client" },
    { key: "role", label: "Role" },
    { key: "sector", label: "Sector" },
    { key: "location", label: "Location" },
    { key: "country", label: "Country" },
    { key: "start_date", label: "Start date", kind: "date" },
    { key: "end_date", label: "End date", kind: "date" },
    { key: "is_current", label: "Ongoing project", kind: "checkbox" },
    { key: "description", label: "Project description", kind: "textarea" },
    { key: "responsibilities", label: "Responsibilities", kind: "textarea" },
    { key: "outcomes", label: "Outcomes", kind: "textarea" },
    { key: "skills_summary", label: "Skills used", kind: "textarea" },
  ],
};

function readableSuggestionValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "Not recorded";
  }
  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }
  return String(value).replaceAll("_", " ");
}

function normalizeSuggestionPayload(
  category: ProfileSuggestion["category"],
  values: Record<string, unknown>,
): Record<string, unknown> {
  const numericFields = new Set([
    "years_experience",
    "last_used_year",
    "start_year",
    "graduation_year",
  ]);
  const result: Record<string, unknown> = {};

  for (const field of suggestionFields[category]) {
    const value = values[field.key];
    if (field.kind === "checkbox") {
      result[field.key] = Boolean(value);
    } else if (numericFields.has(field.key)) {
      result[field.key] =
        value === "" || value === null || value === undefined
          ? null
          : Number(value);
    } else {
      result[field.key] = value === "" || value === undefined ? null : value;
    }
  }

  return result;
}

function DocumentsPanel({ personId }: { personId: string }) {
  const queryClient = useQueryClient();
  const [files, setFiles] = React.useState<File[]>([]);
  const [batchProgress, setBatchProgress] = React.useState<string | null>(null);
  const [batchError, setBatchError] = React.useState<string | null>(null);
  const [documentType, setDocumentType] = React.useState<DocumentType>("cv");
  const [title, setTitle] = React.useState("");
  const [uploadError, setUploadError] = React.useState<string | null>(null);
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [editPayload, setEditPayload] = React.useState<Record<string, unknown>>({});
  const [reviewNotes, setReviewNotes] = React.useState<Record<string, string>>({});
  const [preview, setPreview] = React.useState<{
    document: PersonDocument;
    kind: "pdf" | "image" | "text";
    objectUrl?: string;
    text?: string;
  } | null>(null);
  const [previewBusy, setPreviewBusy] = React.useState(false);
  const [previewError, setPreviewError] = React.useState<string | null>(null);

  const documents = useQuery({
    queryKey: ["documents", personId],
    queryFn: () => api<PersonDocument[]>(`/people/${personId}/documents`),
  });
  const suggestions = useQuery({
    queryKey: ["profile-suggestions", personId],
    queryFn: () =>
      api<ProfileSuggestion[]>(`/people/${personId}/ai-suggestions?status=pending`),
  });
  const completeness = useQuery({
    queryKey: ["profile-completeness", personId],
    queryFn: () => api<ProfileCompleteness>(`/people/${personId}/completeness`),
  });

  const refreshProfile = () => {
    for (const key of [
      "documents",
      "profile-suggestions",
      "profile-completeness",
      "person",
      "skills",
      "education",
      "certifications",
      "employment",
      "projects",
    ]) {
      queryClient.invalidateQueries({ queryKey: [key, personId] });
    }
  };

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!files.length) throw new Error("Choose one or more documents first.");
      setUploadError(null);
      const uploaded: PersonDocument[] = [];
      for (let index = 0; index < files.length; index += 1) {
        const selectedFile = files[index];
        setBatchProgress(`Uploading ${index + 1} of ${files.length}: ${selectedFile.name}`);
        const form = new FormData();
        form.append("file", selectedFile);
        form.append("document_type", documentType);
        if (title.trim() && files.length === 1) form.append("title", title.trim());
        uploaded.push(await api<PersonDocument>(`/people/${personId}/documents`, {
          method: "POST",
          body: form,
        }));
      }
      return uploaded;
    },
    onSuccess: () => {
      setFiles([]);
      setTitle("");
      setBatchProgress(null);
      refreshProfile();
    },
    onError: (error) => {
      setBatchProgress(null);
      setUploadError(error instanceof Error ? error.message : "Upload failed.");
      refreshProfile();
    },
  });

  const analyze = useMutation({
    mutationFn: (documentId: string) =>
      api(`/people/${personId}/documents/${documentId}/analyze`, {
        method: "POST",
        timeoutMs: AI_ANALYSIS_TIMEOUT_MS,
      }),
    onSuccess: refreshProfile,
  });

  const analyzeAll = useMutation({
    mutationFn: async () => {
      const items = documents.data ?? [];
      if (!items.length) throw new Error("Upload documents before analyzing.");
      setBatchError(null);
      const failures: string[] = [];
      for (let index = 0; index < items.length; index += 1) {
        const document = items[index];
        setBatchProgress(`Analyzing ${index + 1} of ${items.length}: ${document.title}`);
        try {
          await api(`/people/${personId}/documents/${document.id}/analyze`, {
            method: "POST",
            timeoutMs: AI_ANALYSIS_TIMEOUT_MS,
          });
        } catch (error) {
          failures.push(`${document.title}: ${error instanceof Error ? error.message : "Analysis failed"}`);
        }
        refreshProfile();
      }
      if (failures.length) throw new Error(failures.join(" | "));
    },
    onSuccess: () => {
      setBatchProgress(null);
      refreshProfile();
    },
    onError: (error) => {
      setBatchProgress(null);
      setBatchError(error instanceof Error ? error.message : "Some documents could not be analyzed.");
      refreshProfile();
    },
  });

  const accept = useMutation({
    mutationFn: async (suggestion: ProfileSuggestion) => {
      const note = reviewNotes[suggestion.id]?.trim();
      if (note) {
        await api(`/people/${personId}/ai-suggestions/${suggestion.id}`, {
          method: "PATCH",
          body: JSON.stringify({ review_note: note }),
        });
      }
      return api(`/people/${personId}/ai-suggestions/${suggestion.id}/accept`, {
        method: "POST",
      });
    },
    onSuccess: () => {
      setEditingId(null);
      refreshProfile();
    },
  });

  const acceptAll = useMutation({
    mutationFn: async () => {
      const pending = suggestions.data ?? [];
      if (!pending.length) return;
      setBatchError(null);
      for (let index = 0; index < pending.length; index += 1) {
        const suggestion = pending[index];
        setBatchProgress(`Accepting ${index + 1} of ${pending.length}: ${suggestion.title}`);
        const note = reviewNotes[suggestion.id]?.trim();
        if (note) {
          await api(`/people/${personId}/ai-suggestions/${suggestion.id}`, {
            method: "PATCH",
            body: JSON.stringify({ review_note: note }),
          });
        }
        await api(`/people/${personId}/ai-suggestions/${suggestion.id}/accept`, { method: "POST" });
      }
    },
    onSuccess: () => {
      setBatchProgress(null);
      setEditingId(null);
      refreshProfile();
    },
    onError: (error) => {
      setBatchProgress(null);
      setBatchError(error instanceof Error ? error.message : "Accept all failed.");
      refreshProfile();
    },
  });

  const reject = useMutation({
    mutationFn: async (suggestion: ProfileSuggestion) => {
      const note = reviewNotes[suggestion.id]?.trim();
      if (note) {
        await api(`/people/${personId}/ai-suggestions/${suggestion.id}`, {
          method: "PATCH",
          body: JSON.stringify({ review_note: note }),
        });
      }
      return api(`/people/${personId}/ai-suggestions/${suggestion.id}/reject`, {
        method: "POST",
      });
    },
    onSuccess: refreshProfile,
  });

  const acceptEdited = useMutation({
    mutationFn: async (suggestion: ProfileSuggestion) => {
      const payload = normalizeSuggestionPayload(suggestion.category, editPayload);
      const reviewNote = reviewNotes[suggestion.id]?.trim() || null;

      await api(`/people/${personId}/ai-suggestions/${suggestion.id}`, {
        method: "PATCH",
        body: JSON.stringify({ payload, review_note: reviewNote }),
      });

      return api(`/people/${personId}/ai-suggestions/${suggestion.id}/accept`, {
        method: "POST",
      });
    },
    onSuccess: () => {
      setEditingId(null);
      setEditPayload({});
      refreshProfile();
    },
  });

  const remove = useMutation({
    mutationFn: (documentId: string) =>
      api<void>(`/people/${personId}/documents/${documentId}`, { method: "DELETE" }),
    onSuccess: refreshProfile,
  });

  const pendingCount = suggestions.data?.length ?? 0;
  const documentById = new Map((documents.data ?? []).map((item) => [item.id, item]));
  const reviewBusy = accept.isPending || reject.isPending || acceptEdited.isPending || acceptAll.isPending;

  const closePreview = () => {
    if (preview?.objectUrl) {
      window.URL.revokeObjectURL(preview.objectUrl);
    }
    setPreview(null);
    setPreviewError(null);
  };

  const openPreview = async (document: PersonDocument) => {
    closePreview();
    setPreviewBusy(true);
    setPreviewError(null);
    const extension = document.file_extension.toLowerCase();
    const nativePreview =
      extension === ".pdf" ||
      [".jpg", ".jpeg", ".png", ".webp", ".gif"].includes(extension);

    try {
      if (nativePreview) {
        const blob = await apiBlob(
          `/people/${personId}/documents/${document.id}/view`,
        );
        const objectUrl = window.URL.createObjectURL(blob);
        setPreview({
          document,
          kind: extension === ".pdf" ? "pdf" : "image",
          objectUrl,
        });
      } else {
        const result = await api<{ text: string }>(
          `/people/${personId}/documents/${document.id}/preview-text`,
        );
        setPreview({ document, kind: "text", text: result.text });
      }
    } catch (error) {
      setPreviewError(
        error instanceof Error ? error.message : "Document preview failed.",
      );
    } finally {
      setPreviewBusy(false);
    }
  };

  const startEditing = (suggestion: ProfileSuggestion) => {
    setEditingId(suggestion.id);
    setEditPayload({ ...suggestion.payload });
  };

  const updateEditValue = (key: string, value: unknown) => {
    setEditPayload((current) => ({ ...current, [key]: value }));
  };

  return (
    <div className="grid gap-6">
      <section className="grid gap-4 rounded-2xl bg-evergreen p-6 text-white md:grid-cols-2">
        <div>
          <p className="text-xs font-bold uppercase tracking-[.18em] text-mint">
            Profile readiness
          </p>
          <p className="mt-2 font-serif text-3xl">
            {completeness.data?.profile_percent ?? 0}% complete
          </p>
          <p className="mt-2 text-sm text-white/65">
            Gemini can propose profile facts, but nothing becomes verified profile data
            until a teammate reviews and accepts it.
          </p>
        </div>
        <div className="rounded-xl bg-white/10 p-4">
          <p className="text-sm text-white/60">Evidence-backed structured records</p>
          <p className="mt-1 text-2xl font-semibold">
            {completeness.data?.evidence_percent ?? 0}%
          </p>
          <p className="mt-3 text-xs text-white/50">
            {pendingCount} AI suggestion{pendingCount === 1 ? "" : "s"} awaiting review
          </p>
        </div>
      </section>

      <section className="rounded-2xl bg-white p-7 shadow-soft">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-serif text-2xl">Upload evidence</h2>
            <p className="mt-1 text-sm text-slate-500">
              Upload CVs, degrees, certificates, reference letters and project evidence.
              Gemini can analyze PDFs and common image formats directly.
            </p>
          </div>
          <Upload className="text-evergreen" size={24} />
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <label className="text-sm font-medium text-slate-700 md:col-span-2">
            Document
            <input
              type="file"
              multiple
              accept=".pdf,.doc,.docx,.xls,.xlsx,.xlsm,.csv,.tsv,.ppt,.pptx,.jpg,.jpeg,.png,.webp,.gif,.txt,.text,.md,.markdown,.rtf,.json,.jsonl,.xml,.html,.htm,.yaml,.yml,.odt,.ods,.odp"
              onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
              className="mt-2 block w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm"
            />
          </label>
          <label className="text-sm font-medium text-slate-700">
            Type
            <select
              value={documentType}
              onChange={(event) => setDocumentType(event.target.value as DocumentType)}
              className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3"
            >
              {documentTypeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <Field
            label="Title (optional)"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Defaults to the filename"
          />
        </div>
        {files.length > 0 && (
          <div className="mt-4 rounded-xl bg-slate-50 p-4 text-sm text-slate-600">
            <p className="font-semibold text-ink">{files.length} document{files.length === 1 ? "" : "s"} selected</p>
            <ul className="mt-2 space-y-1">
              {files.map((selectedFile) => (
                <li key={`${selectedFile.name}-${selectedFile.size}`}>{selectedFile.name} · {(selectedFile.size / 1024).toFixed(0)} KB</li>
              ))}
            </ul>
          </div>
        )}
        {(uploadError || uploadMutation.error) && (
          <p className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">
            {uploadError ?? uploadMutation.error?.message}
          </p>
        )}
        <div className="mt-5">
          <Button
            type="button"
            disabled={!files.length || uploadMutation.isPending || analyzeAll.isPending}
            onClick={() => uploadMutation.mutate()}
          >
            {uploadMutation.isPending ? batchProgress ?? "Uploading…" : `Upload ${files.length > 1 ? `${files.length} documents` : "document"}`}
          </Button>
        </div>
      </section>

      <section className="rounded-2xl bg-white p-7 shadow-soft">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <h2 className="font-serif text-2xl">Documents</h2>
          <Button type="button" disabled={!documents.data?.length || analyzeAll.isPending || analyze.isPending || uploadMutation.isPending} onClick={() => analyzeAll.mutate()}>
            <Sparkles size={15} className="mr-2 inline" />
            {analyzeAll.isPending ? batchProgress ?? "Analyzing…" : "Analyze all"}
          </Button>
        </div>
        <div className="mt-5 grid gap-3">
          {documents.isLoading ? (
            <p className="text-sm text-slate-500">Loading documents…</p>
          ) : documents.data?.length ? (
            documents.data.map((document) => (
              <article key={document.id} className="rounded-xl border border-slate-200 p-4">
                <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
                  <div className="flex min-w-0 items-start gap-3">
                    <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-sand">
                      <FileText size={18} />
                    </div>
                    <div className="min-w-0">
                      <p className="truncate font-semibold">{document.title}</p>
                      <p className="mt-1 text-xs text-slate-400">
                        {document.original_filename} · {(document.file_size / 1024).toFixed(0)} KB
                      </p>
                      <p className="mt-1 text-xs capitalize text-slate-500">
                        AI: {document.analysis_status.replaceAll("_", " ")}
                      </p>
                      {document.analysis_error && (
                        <p className="mt-2 text-xs text-red-600">{document.analysis_error}</p>
                      )}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      secondary
                      disabled={previewBusy}
                      onClick={() => void openPreview(document)}
                    >
                      <Eye size={15} className="mr-2 inline" />
                      {previewBusy ? "Opening…" : "View"}
                    </Button>
                    <Button
                      type="button"
                      secondary
                      onClick={() =>
                        apiDownload(
                          `/people/${personId}/documents/${document.id}/download`,
                          document.original_filename,
                        )
                      }
                    >
                      <Download size={15} className="mr-2 inline" />
                      Download
                    </Button>
                    <Button
                      type="button"
                      disabled={analyze.isPending || analyzeAll.isPending}
                      onClick={() => analyze.mutate(document.id)}
                    >
                      <Sparkles size={15} className="mr-2 inline" />
                      {document.analysis_status === "not_analyzed" ? "Analyze" : "Analyze again"}
                    </Button>
                    <button
                      type="button"
                      className="rounded-xl p-3 text-slate-400 hover:bg-red-50 hover:text-red-600"
                      onClick={() =>
                        window.confirm(`Delete ${document.title}?`) && remove.mutate(document.id)
                      }
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              </article>
            ))
          ) : (
            <EmptyCapability
              icon={FileText}
              title="No documents uploaded"
              text="Upload the person's CV and evidence. AI can then propose profile records for human review."
            />
          )}
        </div>
        {(analyze.error || batchError || previewError) && (
          <p className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">
            {previewError ?? batchError ?? analyze.error?.message}
          </p>
        )}
      </section>

      <section className="rounded-2xl bg-white p-7 shadow-soft">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
          <div>
            <p className="text-xs font-bold uppercase tracking-[.18em] text-evergreen">
              Human review queue
            </p>
            <h2 className="mt-2 font-serif text-2xl">AI suggestions</h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-500">
              Review the extracted facts as normal fields. Correct anything Gemini got wrong,
              then accept it into the structured profile or reject it.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="h-fit rounded-full bg-mint px-3 py-1 text-xs font-semibold text-evergreen">{pendingCount} pending</span>
            {pendingCount > 0 && (
              <Button type="button" disabled={reviewBusy || analyzeAll.isPending} onClick={() => {
                if (window.confirm(`Accept all ${pendingCount} pending Gemini suggestions exactly as shown?`)) acceptAll.mutate();
              }}>
                <Check size={15} className="mr-2 inline" />
                {acceptAll.isPending ? batchProgress ?? "Accepting…" : "Accept all"}
              </Button>
            )}
          </div>
        </div>

        <div className="mt-6 grid gap-5">
          {suggestions.isLoading ? (
            <p className="text-sm text-slate-500">Loading suggestions…</p>
          ) : suggestions.data?.length ? (
            suggestions.data.map((suggestion) => {
              const isEditing = editingId === suggestion.id;
              const source = documentById.get(suggestion.source_document_id);
              const fields = suggestionFields[suggestion.category];

              return (
                <article
                  key={suggestion.id}
                  className="overflow-hidden rounded-2xl border border-slate-200"
                >
                  <div className="flex flex-col justify-between gap-4 bg-slate-50 px-5 py-4 sm:flex-row sm:items-start">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-full bg-mint px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider text-evergreen">
                          {suggestion.category}
                        </span>
                        <span className="rounded-full bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-500 ring-1 ring-slate-200">
                          Awaiting review
                        </span>
                      </div>
                      <h3 className="mt-3 font-semibold text-ink">{suggestion.title}</h3>
                      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-400">
                        {suggestion.confidence !== null && (
                          <span>AI confidence {Math.round(suggestion.confidence * 100)}%</span>
                        )}
                        <span>
                          Evidence: {source?.title ?? source?.original_filename ?? "Uploaded document"}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="p-5">
                    {isEditing ? (
                      <div className="grid gap-4 md:grid-cols-2">
                        {fields.map((field) => {
                          const value = editPayload[field.key];

                          if (field.kind === "checkbox") {
                            return (
                              <label
                                key={field.key}
                                className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700 md:col-span-2"
                              >
                                <input
                                  type="checkbox"
                                  checked={Boolean(value)}
                                  onChange={(event) =>
                                    updateEditValue(field.key, event.target.checked)
                                  }
                                  className="h-4 w-4"
                                />
                                {field.label}
                              </label>
                            );
                          }

                          if (field.kind === "textarea") {
                            return (
                              <label
                                key={field.key}
                                className="text-sm font-medium text-slate-700 md:col-span-2"
                              >
                                {field.label}
                                <textarea
                                  rows={4}
                                  value={value == null ? "" : String(value)}
                                  onChange={(event) =>
                                    updateEditValue(field.key, event.target.value)
                                  }
                                  className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 outline-none focus:border-evergreen"
                                />
                              </label>
                            );
                          }

                          if (field.kind === "select") {
                            return (
                              <label key={field.key} className="text-sm font-medium text-slate-700">
                                {field.label}
                                <select
                                  value={value == null ? "" : String(value)}
                                  onChange={(event) =>
                                    updateEditValue(field.key, event.target.value)
                                  }
                                  className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 outline-none focus:border-evergreen"
                                >
                                  {field.options?.map((option) => (
                                    <option key={option.value} value={option.value}>
                                      {option.label}
                                    </option>
                                  ))}
                                </select>
                              </label>
                            );
                          }

                          return (
                            <label key={field.key} className="text-sm font-medium text-slate-700">
                              {field.label}
                              <input
                                type={field.kind === "date" ? "date" : field.kind === "number" ? "number" : "text"}
                                value={value == null ? "" : String(value)}
                                onChange={(event) =>
                                  updateEditValue(field.key, event.target.value)
                                }
                                className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 outline-none focus:border-evergreen"
                                placeholder={field.placeholder}
                              />
                            </label>
                          );
                        })}
                      </div>
                    ) : (
                      <dl className="grid gap-x-8 gap-y-4 md:grid-cols-2">
                        {fields.map((field) => (
                          <div
                            key={field.key}
                            className={field.kind === "textarea" ? "md:col-span-2" : ""}
                          >
                            <dt className="text-xs font-bold uppercase tracking-wider text-slate-400">
                              {field.label}
                            </dt>
                            <dd className="mt-1 whitespace-pre-line text-sm leading-6 text-slate-700">
                              {readableSuggestionValue(suggestion.payload[field.key])}
                            </dd>
                          </div>
                        ))}
                      </dl>
                    )}

                    <label className="mt-5 block text-sm font-medium text-slate-700">
                      Review note <span className="font-normal text-slate-400">(optional)</span>
                      <textarea
                        rows={2}
                        value={reviewNotes[suggestion.id] ?? suggestion.review_note ?? ""}
                        onChange={(event) =>
                          setReviewNotes((current) => ({
                            ...current,
                            [suggestion.id]: event.target.value,
                          }))
                        }
                        placeholder="Record why you changed or rejected this suggestion, if useful."
                        className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-evergreen"
                      />
                    </label>

                    <div className="mt-5 flex flex-wrap gap-2 border-t border-slate-100 pt-5">
                      {isEditing ? (
                        <>
                          <Button
                            type="button"
                            disabled={reviewBusy}
                            onClick={() => acceptEdited.mutate(suggestion)}
                          >
                            <Check size={15} className="mr-2 inline" />
                            {acceptEdited.isPending ? "Saving…" : "Save & accept"}
                          </Button>
                          <Button
                            type="button"
                            secondary
                            onClick={() => {
                              setEditingId(null);
                              setEditPayload({});
                            }}
                          >
                            Cancel
                          </Button>
                        </>
                      ) : (
                        <>
                          <Button
                            type="button"
                            disabled={reviewBusy}
                            onClick={() => accept.mutate(suggestion)}
                          >
                            <Check size={15} className="mr-2 inline" />
                            Accept as shown
                          </Button>
                          <Button
                            type="button"
                            secondary
                            disabled={reviewBusy}
                            onClick={() => startEditing(suggestion)}
                          >
                            Edit before accepting
                          </Button>
                          <button
                            type="button"
                            disabled={reviewBusy}
                            onClick={() => reject.mutate(suggestion)}
                            className="inline-flex items-center gap-2 rounded-xl bg-red-50 px-4 py-2.5 text-sm font-semibold text-red-700 hover:bg-red-100 disabled:opacity-50"
                          >
                            <XCircle size={16} />
                            Reject
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </article>
              );
            })
          ) : (
            <EmptyCapability
              icon={Sparkles}
              title="No suggestions waiting"
              text="Analyze an uploaded document. Extracted facts will appear here as reviewable fields before they enter the person's profile."
            />
          )}
        </div>

        {(accept.error || reject.error || acceptEdited.error || acceptAll.error || batchError) && (
          <p className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">
            {batchError ?? accept.error?.message ?? reject.error?.message ?? acceptEdited.error?.message ?? acceptAll.error?.message}
          </p>
        )}
      </section>

      {preview && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          role="dialog"
          aria-modal="true"
          aria-label={`Preview ${preview.document.title}`}
        >
          <div className="flex h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
            <div className="flex items-center justify-between gap-4 border-b border-slate-200 px-5 py-4">
              <div className="min-w-0">
                <p className="truncate font-semibold text-ink">{preview.document.title}</p>
                <p className="truncate text-xs text-slate-400">
                  {preview.document.original_filename}
                </p>
              </div>
              <div className="flex shrink-0 gap-2">
                <Button
                  type="button"
                  secondary
                  onClick={() =>
                    apiDownload(
                      `/people/${personId}/documents/${preview.document.id}/download`,
                      preview.document.original_filename,
                    )
                  }
                >
                  <Download size={15} className="mr-2 inline" />
                  Download
                </Button>
                <button
                  type="button"
                  aria-label="Close document preview"
                  className="rounded-xl p-3 text-slate-500 hover:bg-slate-100 hover:text-ink"
                  onClick={closePreview}
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            <div className="min-h-0 flex-1 bg-slate-100 p-3">
              {preview.kind === "pdf" && preview.objectUrl && (
                <iframe
                  title={preview.document.title}
                  src={preview.objectUrl}
                  className="h-full w-full rounded-xl bg-white"
                />
              )}
              {preview.kind === "image" && preview.objectUrl && (
                <div className="flex h-full items-center justify-center overflow-auto rounded-xl bg-white p-4">
                  <img
                    src={preview.objectUrl}
                    alt={preview.document.title}
                    className="max-h-full max-w-full object-contain"
                  />
                </div>
              )}
              {preview.kind === "text" && (
                <pre className="h-full overflow-auto whitespace-pre-wrap rounded-xl bg-white p-6 font-sans text-sm leading-6 text-slate-700">
                  {preview.text}
                </pre>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export function PersonPage() {
  const { personId } =
    useParams();

  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const archivePerson = useMutation({
    mutationFn: () =>
      api<void>(`/people/${personId}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["people"],
      });
      navigate("/people");
    },
  });

  const [searchParams, setSearchParams] = useSearchParams();
  const requestedTab = searchParams.get("tab") as CapabilityTab | null;
  const [tab, setTab] = React.useState<CapabilityTab>(
    requestedTab && ["overview", "documents", "skills", "education", "certifications", "work", "projects"].includes(requestedTab)
      ? requestedTab
      : "overview",
  );

  const query = useQuery({
    queryKey: [
      "person",
      personId,
    ],

    queryFn: () =>
      api<Person>(
        `/people/${personId}`,
      ),

    enabled:
      Boolean(personId),
  });

  if (query.isLoading) {
    return (
      <div className={wrapper}>
        Loading profile…
      </div>
    );
  }

  if (query.error) {
    return (
      <div className={wrapper}>
        <p className="text-red-700">
          {
            query.error
              .message
          }
        </p>
      </div>
    );
  }

  if (
    !query.data ||
    !personId
  ) {
    return (
      <div className={wrapper}>
        Person not found.
      </div>
    );
  }

  const person =
    query.data;

  const tabs: {
    id: CapabilityTab;
    label: string;
  }[] = [
      {
        id: "overview",
        label: "Overview",
      },
      {
        id: "documents",
        label: "Documents & AI",
      },
      {
        id: "skills",
        label: "Skills",
      },
      {
        id: "education",
        label: "Education",
      },
      {
        id: "certifications",
        label:
          "Certifications",
      },
      {
        id: "work",
        label: "Work Experience",
      },
      {
        id: "projects",
        label: "Projects",
      },
    ];

  return (
    <div className={wrapper}>
      <Link
        to="/people"
        className="mb-6 inline-flex items-center gap-2 text-sm text-slate-500"
      >
        <ArrowLeft
          size={16}
        />
        People directory
      </Link>

      <div className="overflow-hidden rounded-3xl bg-ink text-white shadow-soft">
        <div className="p-8">
          <div className="grid h-16 w-16 place-items-center rounded-2xl bg-coral font-serif text-2xl">
            {
              person
                .first_name[0]
            }
            {
              person
                .last_name[0]
            }
          </div>

          <h1 className="mt-6 font-serif text-4xl">
            {
              person.display_name
            }
          </h1>

          <p className="mt-2 text-white/60">
            {person.professional_title ||
              "Professional title not recorded"}
          </p>

          <div className="mt-6 flex flex-wrap gap-2">
            <span className="rounded-full bg-white/10 px-3 py-1.5 text-xs font-semibold capitalize">
              {
                person.profile_status
              }
            </span>

            <span className="rounded-full bg-white/10 px-3 py-1.5 text-xs font-semibold capitalize">
              {person.availability_status.replace(
                "_",
                " ",
              )}
            </span>
          </div>

          <div className="mt-6">
            <button
              type="button"
              disabled={archivePerson.isPending}
              onClick={() => {
                if (
                  window.confirm(
                    `Archive ${person.display_name}? The record will be removed from the active directory but retained for audit history.`,
                  )
                ) {
                  archivePerson.mutate();
                }
              }}
              className="inline-flex items-center gap-2 rounded-xl border border-white/15 px-4 py-2.5 text-sm font-semibold text-white/70 hover:bg-red-500/15 hover:text-white disabled:opacity-50"
            >
              <Trash2 size={16} />
              {archivePerson.isPending ? "Archiving…" : "Archive person"}
            </button>
            {archivePerson.error && (
              <p className="mt-3 text-sm text-red-200">
                {archivePerson.error.message}
              </p>
            )}
          </div>
        </div>

        <nav className="flex overflow-x-auto border-t border-white/10 px-5">
          {tabs.map(
            (item) => (
              <button
                key={
                  item.id
                }
                type="button"
                onClick={() => {
                  setTab(item.id);
                  setSearchParams(item.id === "overview" ? {} : { tab: item.id });
                }}
                className={`whitespace-nowrap border-b-2 px-4 py-4 text-sm font-semibold transition ${tab ===
                  item.id
                  ? "border-mint text-white"
                  : "border-transparent text-white/50 hover:text-white"
                  }`}
              >
                {
                  item.label
                }
              </button>
            ),
          )}
        </nav>
      </div>

      <div className="mt-6">
        {tab ===
          "overview" && (
            <div className="grid gap-6 md:grid-cols-[1.4fr_.6fr]">
              <section className="rounded-2xl bg-white p-7 shadow-soft">
                <h2 className="font-serif text-2xl">
                  Profile
                  summary
                </h2>

                <p className="mt-4 leading-7 text-slate-600">
                  {person.summary ||
                    "No professional summary has been added yet."}
                </p>
              </section>

              <aside className="rounded-2xl border border-slate-200 bg-white p-7">
                <h2 className="font-serif text-xl">
                  Details
                </h2>

                <dl className="mt-5 space-y-4 text-sm">
                  <div>
                    <dt className="text-slate-400">
                      Email
                    </dt>

                    <dd>
                      {person.primary_email ||
                        "Not recorded"}
                    </dd>
                  </div>

                  <div>
                    <dt className="text-slate-400">
                      Phone
                    </dt>

                    <dd>
                      {person.primary_phone ||
                        "Not recorded"}
                    </dd>
                  </div>

                  <div>
                    <dt className="text-slate-400">
                      Residence
                    </dt>

                    <dd>
                      {person.country_of_residence ||
                        "Not recorded"}
                    </dd>
                  </div>

                  <div>
                    <dt className="text-slate-400">
                      Availability
                    </dt>

                    <dd className="capitalize">
                      {person.availability_status.replace(
                        "_",
                        " ",
                      )}
                    </dd>
                  </div>
                </dl>
              </aside>
            </div>
          )}

        {tab === "documents" && (
          <DocumentsPanel personId={personId} />
        )}

        {tab ===
          "skills" && (
            <SkillPanel
              personId={
                personId
              }
            />
          )}

        {tab ===
          "education" && (
            <EducationPanel
              personId={
                personId
              }
            />
          )}

        {tab ===
          "certifications" && (
            <CertificationPanel
              personId={
                personId
              }
            />
          )}

        {tab ===
          "work" && (
            <WorkExperiencePanel
              personId={
                personId
              }
            />
          )}

        {tab ===
          "projects" && (
            <ProjectsPanel
              personId={
                personId
              }
            />
          )}

      </div>
    </div>
  );
}

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
    queryKey: [
      "organization",
    ],
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
    queryKey: [
      "organization-members",
    ],
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
            queryKey: [
              "organization-members",
            ],
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
            queryKey: [
              "organization-members",
            ],
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
        queryKey: ["organization-members"],
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
        <section className="rounded-2xl bg-white p-7 shadow-soft">
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

        <section className="rounded-2xl bg-white p-7 shadow-soft">
          <div>
            <p className="text-xs font-bold uppercase tracking-[.18em] text-evergreen">
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

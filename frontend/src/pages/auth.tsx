import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Layers2 } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { z } from "zod";
import { Button, Field } from "../components/ui";
import { api } from "../lib/api";
import { session } from "../lib/session";
import type { CurrentUser } from "../types";

const loginSchema = z.object({ email: z.string().email("Enter a valid email address."), password: z.string().min(12, "Password must be at least 12 characters.") });
const registerSchema = loginSchema.extend({ organization_name: z.string().min(2), organization_slug: z.string().regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, "Use lowercase letters, numbers, and hyphens."), full_name: z.string().min(2) });
function Brand() { return <div className="cf-auth-logo"><span className="cf-logo"><Layers2 size={16} /></span>Capability<span className="font-normal text-slate-400 -ml-2">Flow</span></div>; }
export function LoginPage() {
  const navigate = useNavigate(); const queryClient = useQueryClient();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof loginSchema>>({ resolver: zodResolver(loginSchema) });
  const login = useMutation({
    mutationFn: async (values: z.infer<typeof loginSchema>) => {
      setSubmitError(null);
      const data = await api<{ access_token: string; }>("/auth/login", { method: "POST", body: JSON.stringify(values) });
      session.setToken(data.access_token);
      const me = await api<CurrentUser>("/auth/me");
      const membership = me.memberships.find((item) => item.organization_id === session.organization()) ?? me.memberships[0];
      if (!membership) throw new Error("Your account does not have an active workspace membership.");
      return { token: data.access_token, organization: membership.organization_id };
    }, onSuccess: (data) => { queryClient.clear(); session.set(data.token, data.organization); navigate("/", { replace: true }); }, onError: (error) => { session.clear(); setSubmitError(error.message); }
  });
  return <main className="cf-auth"><div className="cf-auth-inner"><Brand /><h1>Welcome back</h1><p className="cf-auth-subtitle">Your people. Your expertise. In one place.</p>
    <form noValidate className="space-y-5" onSubmit={handleSubmit((values) => login.mutate(values), () => setSubmitError("Please correct the highlighted fields."))}>
      <Field label="Work email" type="email" autoComplete="email" error={errors.email?.message} {...register("email")} />
      <Field label="Password" type="password" autoComplete="current-password" error={errors.password?.message} {...register("password")} />
      {submitError && <p role="alert" className="cf-alert cf-alert-error">{submitError}</p>}
      <Button className="w-full" type="submit" disabled={login.isPending}>{login.isPending ? "Signing in..." : <>Sign in<ArrowRight size={15} /></>}</Button>
    </form><p className="mt-7 text-center text-xs text-slate-500">New here? <Link to="/register" className="font-semibold text-ink hover:underline">Create a workspace</Link></p><p className="mt-12 text-center text-[11px] text-slate-400">A private home for your team's capabilities.</p></div></main>;
}
export function RegisterPage() {
  const navigate = useNavigate(); const queryClient = useQueryClient();
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof registerSchema>>({ resolver: zodResolver(registerSchema) });
  const create = useMutation({ mutationFn: (values: z.infer<typeof registerSchema>) => api<{ access_token: string; organization_id: string; }>("/auth/register-organization", { method: "POST", body: JSON.stringify(values) }), onSuccess: (data) => { queryClient.clear(); session.set(data.access_token, data.organization_id); navigate("/", { replace: true }); } });
  return <main className="cf-auth"><div className="cf-auth-inner"><Brand /><h1>Create your workspace</h1><p className="cf-auth-subtitle">Bring your people, evidence, and opportunities together.</p><form noValidate className="space-y-4" onSubmit={handleSubmit((values) => create.mutate(values))}>
    <Field label="Organization" error={errors.organization_name?.message} {...register("organization_name")} />
    <Field label="Workspace slug" placeholder="acme-advisory" error={errors.organization_slug?.message} {...register("organization_slug")} />
    <Field label="Full name" autoComplete="name" error={errors.full_name?.message} {...register("full_name")} />
    <Field label="Work email" type="email" autoComplete="email" error={errors.email?.message} {...register("email")} />
    <Field label="Password" type="password" autoComplete="new-password" placeholder="At least 12 characters" error={errors.password?.message} {...register("password")} />
    {create.error && <p role="alert" className="cf-alert cf-alert-error">{create.error.message}</p>}
    <Button className="w-full" type="submit" disabled={create.isPending}>{create.isPending ? "Creating workspace..." : "Create workspace"}</Button>
  </form><p className="mt-6 text-center text-xs text-slate-500">Already have an account? <Link to="/login" className="font-semibold text-ink">Sign in</Link></p></div></main>;
}

/* Role permissions as enforced by the API (app/core/security.py and the route dependencies). */
const ROLES = [
  {
    role: "Admin",
    can: "Everything an operator can, plus deleting cache rules and seeing every user's traffic, usage and charges.",
  },
  {
    role: "Operator",
    can: "Creates and edits cache rules (only admins delete them), invalidates the cache, uploads and deletes documents. Sees their own usage and charges.",
  },
  {
    role: "Viewer",
    can: "Read-only access to every view. Sees their own usage and charges.",
  },
]

const STEPS = [
  {
    title: "The first admin",
    detail: "Created on the first start from ADMIN_EMAIL and ADMIN_PASSWORD in the server environment. Sign in with the username admin.",
  },
  {
    title: "Everyone else",
    detail: "Creates an account from the sign-in page. New accounts are read-only viewers.",
  },
  {
    title: "Higher roles",
    detail: "Operator and admin roles are granted by the system administrator on the server. They cannot be self-assigned.",
  },
]

export function Access() {
  return (
    <section id="access" className="border-b border-rule bg-paper">
      <div className="container grid gap-12 py-16 lg:grid-cols-2 lg:gap-16 lg:py-20">
        <div>
          <h2 className="text-[clamp(1.6rem,3vw,2.2rem)] font-semibold leading-tight tracking-[-0.02em] text-ink">
            Who can do what
          </h2>
          <p className="mt-3 text-[15px] leading-relaxed text-graphite">
            Every action is checked by the API, not only hidden in the console.
          </p>
          <dl className="mt-8 divide-y divide-rule border-y border-rule">
            {ROLES.map((item) => (
              <div key={item.role} className="grid grid-cols-[100px_1fr] gap-4 py-4">
                <dt className="text-[15px] font-medium text-ink">{item.role}</dt>
                <dd className="text-[14px] leading-relaxed text-graphite">{item.can}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div>
          <h2 className="text-[clamp(1.6rem,3vw,2.2rem)] font-semibold leading-tight tracking-[-0.02em] text-ink">
            Getting access
          </h2>
          <p className="mt-3 text-[15px] leading-relaxed text-graphite">
            The console has no public sign-up for privileged roles.
          </p>
          <ol className="mt-8 divide-y divide-rule border-y border-rule">
            {STEPS.map((step, index) => (
              <li key={step.title} className="grid grid-cols-[28px_1fr] gap-3 py-4">
                <span className="font-mono text-[13px] text-faint">{index + 1}</span>
                <div>
                  <p className="text-[15px] font-medium text-ink">{step.title}</p>
                  <p className="mt-1 text-[14px] leading-relaxed text-graphite">{step.detail}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  )
}

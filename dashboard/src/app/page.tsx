export default function Home() {
  return (
    <main className="dashboard-shell">
      <section className="hero">
        <div>
          <p className="eyebrow">ai-loop dashboard</p>
          <h1>Task control center</h1>
          <p className="lead">
            Track orchestration jobs, inspect logs, and review generated artifacts.
          </p>
        </div>
      </section>

      <section className="grid">
        <article className="panel">
          <h2>Active tasks</h2>
          <p>No tasks yet.</p>
        </article>
        <article className="panel">
          <h2>Latest logs</h2>
          <p>Runtime events will appear here.</p>
        </article>
        <article className="panel">
          <h2>Artifacts</h2>
          <p>Build outputs and generated files will be listed here.</p>
        </article>
      </section>
    </main>
  );
}

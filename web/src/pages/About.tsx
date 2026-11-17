export default function About() {
  return (
    <article className="max-w-2xl space-y-5 pt-12 text-muted [&_h2]:font-display [&_h2]:text-xl [&_h2]:text-ink [&_strong]:text-ink">
      <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">How Tenderlens works</h1>
      <p>Every public contract above the EU threshold is published on <strong>TED</strong>, the EU's tender journal, as a structured eForms notice. Tenderlens downloads every daily package since January 2024 — about 800,000 notices a year across Europe — and keeps the ones with a Swedish buyer.</p>
      <h2>The pipeline</h2>
      <p>A daily Databricks job downloads new packages, a Lakeflow pipeline parses each notice into lots, organisations and awards, and dbt builds the tables behind this site: who won what, in EUR, and when each contract is expected to end (reported end date, or start plus duration).</p>
      <h2>What to be careful with</h2>
      <p><strong>Framework agreements</strong> report a ceiling, and every supplier on the framework repeats it — so a supplier's "value won" can include ceilings it will never fully bill. <strong>End dates</strong> are estimates when the notice gives only a duration, and options to extend are not counted. Values that look like typos (over €5bn, or more than twice the notice's own total) are shown as "?".</p>
      <h2>Privacy</h2>
      <p>Only public procurement data is shown. Contact people, e-mail addresses and beneficial owners in the notices are never read, and winners who are private individuals (sole traders) are shown without a name or ID.</p>
    </article>
  )
}

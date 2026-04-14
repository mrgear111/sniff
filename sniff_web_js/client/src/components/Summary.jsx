export default function Summary({ data }) {
  if (!data) return null;

  return (
    <section className="card">
      <h2>Summary</h2>
      <p>
        <strong>Repository:</strong> {data.owner}/{data.repoName}
      </p>
      <p>
        <strong>Commits analyzed:</strong> {data.count}
      </p>
      <p>
        <strong>Likely Human:</strong> {data.bands['Likely Human']} |{' '}
        <strong>Mixed:</strong> {data.bands['Mixed / Uncertain']} |{' '}
        <strong>Likely AI-assisted:</strong> {data.bands['Likely AI-assisted']}
      </p>
    </section>
  );
}

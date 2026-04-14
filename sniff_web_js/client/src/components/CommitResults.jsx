export default function CommitResults({ data }) {
  if (!data || !data.results) return null;

  return (
    <section className="card">
      <h2>Commit Results</h2>
      <table>
        <thead>
          <tr>
            <th>Hash</th>
            <th>Author</th>
            <th>Message</th>
            <th>Score</th>
            <th>Band</th>
            <th>Reasons</th>
          </tr>
        </thead>
        <tbody>
          {data.results.map((row) => (
            <tr key={row.hash}>
              <td>
                <code>{row.shortHash}</code>
              </td>
              <td>{row.author}</td>
              <td>{row.message}</td>
              <td>{row.score}</td>
              <td>{row.band}</td>
              <td>{row.reasons.join(' | ')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

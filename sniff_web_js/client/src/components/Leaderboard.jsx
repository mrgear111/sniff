export default function Leaderboard({ data }) {
  if (!data || !data.leaderboard) return null;

  return (
    <section className="card">
      <h2>Contributor Leaderboard</h2>
      <table>
        <thead>
          <tr>
            <th>Author</th>
            <th>Commits</th>
            <th>High AI Commits</th>
            <th>Avg Score</th>
            <th>AI Density</th>
          </tr>
        </thead>
        <tbody>
          {data.leaderboard.map((row) => (
            <tr key={row.author}>
              <td>{row.author}</td>
              <td>{row.commitsAnalyzed}</td>
              <td>{row.highAiCommits}</td>
              <td>{row.avgScore}</td>
              <td>{row.aiDensity}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

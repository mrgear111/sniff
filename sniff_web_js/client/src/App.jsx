import { useState } from 'react';
import AnalysisForm from './components/AnalysisForm';
import Summary from './components/Summary';
import CommitResults from './components/CommitResults';
import Leaderboard from './components/Leaderboard';

export default function App() {
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState('');

  return (
    <main className="wrap">
      <h1>Sniff</h1>
      <AnalysisForm
        onResult={setResult}
        onStatusChange={setStatus}
      />
      {status && <p className="status">{status}</p>}
      <Summary data={result} />
      <CommitResults data={result} />
      <Leaderboard data={result} />
    </main>
  );
}

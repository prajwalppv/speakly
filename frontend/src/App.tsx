import AudioUploader from "./components/AudioUploader";
import "./App.css";

export default function App() {
  return (
    <main className="layout">
      <header className="layout__header">
        <h1>Speakly: Phase 1 Demo</h1>
        <p>
          This prototype wires the frontend to the FastAPI backend. Upload an audio file to
          confirm the hello pipeline works end-to-end.
        </p>
      </header>
      <AudioUploader />
    </main>
  );
}

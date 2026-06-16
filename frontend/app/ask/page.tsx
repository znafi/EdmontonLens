import AgentChat from "@/components/AgentChat";

export default function AskPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Ask</h1>
        <p className="text-sm text-slate-500">
          Type a question and CityBot will write the SQL, run it, and explain
          what it found. No sign-in needed.
        </p>
      </div>
      <AgentChat />
    </div>
  );
}

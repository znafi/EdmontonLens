import AgentChat from "@/components/AgentChat";

export default function AskPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Ask</h1>
      </div>
      <AgentChat />
    </div>
  );
}

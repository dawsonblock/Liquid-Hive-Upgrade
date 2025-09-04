export class LiquidHiveClient {
  constructor(baseUrl, apiKey) {
    this.baseUrl = (
      baseUrl ||
      process.env.BASE_URL ||
      "http://localhost:8000"
    ).replace(/\/$/, "");
    this.apiKey = apiKey || process.env.API_KEY;
  }
  _headers() {
    const h = { "Content-Type": "application/json" };
    if (this.apiKey) h["x-api-key"] = this.apiKey;
    return h;
  }
  async health() {
    const r = await fetch(`${this.baseUrl}/api/healthz`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  }
  async chat(q) {
    const r = await fetch(
      `${this.baseUrl}/api/chat?q=${encodeURIComponent(q)}`,
      { method: "POST" },
    );
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  }
  async arenaSubmit(input, reference, metadata) {
    const r = await fetch(`${this.baseUrl}/api/arena/submit`, {
      method: "POST",
      headers: this._headers(),
      body: JSON.stringify({ input, reference, metadata: metadata || {} }),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  }
  async arenaCompare(taskId, modelA, modelB, outputA, outputB, winner) {
    const body = {
      task_id: taskId,
      model_a: modelA,
      model_b: modelB,
      output_a: outputA,
      output_b: outputB,
    };
    if (winner) body.winner = winner;
    const r = await fetch(`${this.baseUrl}/api/arena/compare`, {
      method: "POST",
      headers: this._headers(),
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  }
  async arenaLeaderboard() {
    const r = await fetch(`${this.baseUrl}/api/arena/leaderboard`, {
      headers: this._headers(),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  }
}

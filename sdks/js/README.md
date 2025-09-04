# Liquid Hive JS SDK

Install:

```
npm install liquid-hive-client
```

Usage:

```js
import { LiquidHiveClient } from "liquid-hive-client";

const api = new LiquidHiveClient(process.env.BASE_URL, process.env.API_KEY);
const health = await api.health();
const chat = await api.chat("hello world");
const sub = await api.arenaSubmit("Translate hello to French");
const cmp = await api.arenaCompare(
  sub.task_id,
  "deepseek_v3",
  "qwen_7b",
  "A long answer",
  "short",
);
const lb = await api.arenaLeaderboard();
```

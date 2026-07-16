import fs from "fs";
import { SYMBOLS } from "../src/config.js";
import { fetchOHLCV } from "../src/vnstockApi.js";
import { scoreStock } from "../src/scoring.js";
import { sleep } from "../src/utils.js";

async function main() {
  console.log("Start scanning market...");

  console.log("Fetching VNINDEX...");
  const vnindexOhlcv = await fetchOHLCV("VNINDEX", 260);

  const results = [];

  for (const symbol of SYMBOLS) {
    try {
      console.log(`Scanning ${symbol}...`);

      const ohlcv = await fetchOHLCV(symbol, 260);
      const scored = scoreStock(symbol, ohlcv, vnindexOhlcv);

      if (scored) {
        results.push(scored);
      }

      // Delay nhẹ để tránh rate limit API
      await sleep(300);
    } catch (err) {
      console.error(`Error scanning ${symbol}:`, err.message);
    }
  }

  results.sort((a, b) => b.score - a.score);

  const output = {
    updatedAt: new Date().toISOString(),
    count: results.length,
    data: results
  };

  fs.writeFileSync("data.json", JSON.stringify(output, null, 2), "utf8");

  console.log(`Done. Wrote ${results.length} stocks to data.json`);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});

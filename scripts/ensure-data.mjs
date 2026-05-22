import { existsSync } from "fs";
import { spawnSync } from "child_process";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const webInventory = join(root, "public", "data", "inventory.json");

if (existsSync(webInventory)) {
  console.log("Web data found:", webInventory);
  process.exit(0);
}

const legacy = join(root, "data", "inventory.json");
if (existsSync(legacy)) {
  console.log("Exporting legacy data/inventory.json → public/ …");
  const r = spawnSync("python", ["-m", "metro_fb", "export-web"], {
    cwd: root,
    stdio: "inherit",
    shell: true,
  });
  process.exit(r.status ?? 1);
}

console.warn(
  "\n⚠ No inventory data. Run: npm run refresh\n   (or: python -m metro_fb scrape && npm run data)\n"
);

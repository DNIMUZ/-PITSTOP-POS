import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));

const skus = [
  "APX-101", "APX-102", "APX-103", "APX-104", "APX-105",
  "APX-201", "APX-202", "APX-203", "APX-204", "APX-205",
  "GRP-301", "GRP-302", "GRP-303", "GRP-304", "GRP-305",
  "ACS-401", "ACS-402", "ACS-403", "ACS-404", "ACS-405", "ACS-406", "ACS-407",
  "CLB-501", "CLB-502", "CLB-503", "CLB-504", "CLB-505",
  "KID-601", "KID-602", "KID-603", "KID-604", "KID-605",
  "KID-606", "KID-607", "KID-608", "KID-609",
];
const colors = [
  "#0f172a", "#b91c1c", "#1d4ed8", "#047857",
  "#7c3aed", "#b45309", "#0e7490", "#db2777",
];

const dir = join(root, "public", "products");
mkdirSync(dir, { recursive: true });

skus.forEach((sku, i) => {
  const c = colors[i % colors.length];
  const svg =
    '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">' +
    `<rect width="200" height="200" rx="18" fill="${c}"/>` +
    '<rect x="24" y="24" width="152" height="152" rx="12" fill="#ffffff" fill-opacity="0.08"/>' +
    '<text x="100" y="96" font-family="Arial, sans-serif" font-size="20" font-weight="700" fill="#ffffff" text-anchor="middle">PITSTOP</text>' +
    `<text x="100" y="124" font-family="Arial, sans-serif" font-size="15" fill="#ffffff" fill-opacity="0.85" text-anchor="middle">${sku}</text>` +
    "</svg>";
  writeFileSync(join(dir, `${sku.toLowerCase()}.svg`), svg);
});

console.log(`wrote ${skus.length} svg placeholders to ${dir}`);
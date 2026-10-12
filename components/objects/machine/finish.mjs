// finish.mjs — gives a 3D object the house finish and makes its web copy.
//   node finish.mjs <in.glb> <out-dir> [--name id] [--finish satin|keep] [--tex 1024]
// Writes <out-dir>/<id>.glb (finished, full quality) and <out-dir>/<id>.web.json (small copy the
// artifact page can load: quantized geometry, webp textures, packed as base64 in JSON because the
// page host does not serve .glb files).
// The house finish ("satin", Damon 2026-09-26): the light rolls off it like satin — the look of his
// 3D head. A clear lacquer coat over the object's own colours, roughness pulled down a little.
import { NodeIO } from "@gltf-transform/core";
import { ALL_EXTENSIONS, KHRMaterialsClearcoat } from "@gltf-transform/extensions";
import { weld, simplify, quantize, textureCompress, prune, dedup, center } from "@gltf-transform/functions";
import { MeshoptSimplifier } from "meshoptimizer";
import sharp from "sharp";
import fs from "node:fs";
import path from "node:path";

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf("--" + k); return i >= 0 ? args[i + 1] : d; };
const [inp, outDir] = args;
if (!inp || !outDir) { console.error("usage: node finish.mjs <in.glb> <out-dir> [--name id] [--finish satin|keep] [--tex 1024]"); process.exit(1); }
const id = opt("name", path.basename(inp, ".glb"));
const finish = opt("finish", "satin");
const tex = +opt("tex", "1024");
fs.mkdirSync(outDir, { recursive: true });

const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
const doc = await io.read(inp);
await doc.transform(center({ pivot: "center" }));

const F = JSON.parse(fs.readFileSync(new URL("../definitions/finish.json", import.meta.url)))[finish] || {};
if (F.clearcoat !== undefined) {
  const cc = doc.createExtension(KHRMaterialsClearcoat);
  for (const m of doc.getRoot().listMaterials()) {
    m.setRoughnessFactor(Math.min(m.getRoughnessFactor(), F.roughness_max));
    m.setMetallicFactor(Math.min(m.getMetallicFactor(), F.metallic_max));
    m.setExtension("KHR_materials_clearcoat", cc.createClearcoat().setClearcoatFactor(F.clearcoat).setClearcoatRoughnessFactor(F.clearcoat_roughness));
  }
}
await io.write(path.join(outDir, `${id}.glb`), doc);

// the web copy
await MeshoptSimplifier.ready;
await doc.transform(
  dedup(), prune(), weld(),
  simplify({ simplifier: MeshoptSimplifier, ratio: 0.3, error: 0.004 }),
  textureCompress({ encoder: sharp, targetFormat: "webp", resize: [tex, tex] }),
  quantize(),
);
const glb = await io.writeBinary(doc);
fs.writeFileSync(path.join(outDir, `${id}.web.json`), JSON.stringify({ glb: Buffer.from(glb).toString("base64") }));
console.log(`${id}: finished (${finish}) → ${(fs.statSync(path.join(outDir, `${id}.glb`)).size / 1e6).toFixed(1)} MB · web ${(glb.byteLength / 1e6).toFixed(1)} MB`);

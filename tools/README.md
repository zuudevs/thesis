# Workspace Tools

Perangkat bantu yang terkait langsung dengan workspace riset `v5`.

| Tool | Peran | Status source |
|---|---|---|
| [`dashboard/`](dashboard/README.md) | Monitoring record pengukuran tervalidasi melalui MongoDB, backend Express, dan frontend React | source terlacak; state lokal diabaikan Git |
| [`grapher/`](grapher/API.md) | CLI umum untuk merender Mermaid menjadi SVG | source terlacak; `node_modules` diabaikan Git |

## Boundaries

- `tools/` bukan bagian API library `ze_json` dan tidak mengubah kontrak ABI.
- File `.env`, database MongoDB, `node_modules`, build output, dan TypeScript
  incremental cache tidak boleh di-commit.
- Pipeline khusus naskah artikel tetap berada di repo `thesis-article`
  (`article/scripts/Grapher/`) agar reproducible bersama evidence artikel.
- Perubahan dashboard yang menyentuh aturan pengukuran harus menyertakan
  pengujian guardrail dan tidak boleh melonggarkan validasi schema.

## Verification

```sh
cd tools/dashboard
npm ci && npm ci --prefix backend && npm ci --prefix frontend
npm test
npm run build:frontend
```

```sh
cd tools/grapher
npm ci
npm run make -- path/to/smoke.mmd
```

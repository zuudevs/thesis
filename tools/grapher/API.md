# Workspace Mermaid Grapher

CLI kecil untuk merender diagram Mermaid menjadi SVG.

## Install

```sh
npm ci
```

## Use

```sh
npm run make -- path/to/diagram.mmd
```

Output SVG ditulis di current working directory dengan nama yang sama dan
ekstensi `.svg`. Renderer memakai [`pele`](https://pele.run/); dependensi
versioned dalam `package-lock.json`.

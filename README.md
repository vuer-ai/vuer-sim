# vuer-sim

Simulation materials for MuJoCo and USD scenes: physics materials with MJCF and USD
converters, visual-to-physics inference, LiDAR sensor materials, and a material editor
for vuer (`@vuer-ai/vuer-sim`).

The core needs only numpy; MuJoCo, USD and vuer are optional extras.

## Development

```bash
uv sync --group dev
make check   # lint, typecheck, fast tests: what PR CI runs
```

## License

MIT

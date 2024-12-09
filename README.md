# sysAdminToolboxBackend
# How to run
## Preparation
1. Install uv 
`pip install uv`
2. Open root directory sysAdminToolboxBackend. For example, `~/projs/python/sysAdminToolboxBackend`
3. Initialise init project
`uv init`
4. Create virtual environment
`uv venv`
5. Activate virtual environment with `source` command, script is based on your shell
`source .venv/bin/activate`
6. Install dependencies with
`uv pip sync pyproject.toml`

## Execution
1. Run project with( you need to be in root directory)
`python -m app.main`
2. Run test with 
`pytest`
3. To run backend in local mode with requests to test containers
`fastapi run  'app/test_local_main.py'`


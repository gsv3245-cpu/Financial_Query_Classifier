# Build verification checklist

The source files were syntax-checked in the build environment and the dataset was checked for 60 rows and all five required labels.

Because the build sandbox has no outbound package index/network access, the environment could not install Flask/Groq from PyPI here. Therefore the final browser/API runtime could not be executed inside this sandbox. The included `setup.bat`, `run.bat`, `README.md`, and pytest suite are intended for VS Code on the user's Windows machine.

Before submission, run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
python app.py
```

Then verify:

1. Open http://127.0.0.1:5000
2. Create a user.
3. Log in.
4. Submit a query in offline demo mode.
5. Confirm the result is stored in History.
6. Add the Groq key and set `MOCK_MODE=false`.
7. Restart Flask.
8. Submit a live LLM query.
9. Run `python evaluation/evaluate_model.py` for the final model test.
10. Run `python evaluation/confusion_matrix.py`.

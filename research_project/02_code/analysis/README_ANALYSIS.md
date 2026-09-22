# Analysis pipeline

The analysis modules are executable Python files restored from the archived concatenated source. The redesigned model families are in `08_MODEL_FAMILIES_REDESIGNED.py`.

Run the complete pipeline from an execution bundle containing the modules and locked inputs:

```powershell
$env:PYTHONIOENCODING = "utf-8"
python MASTER_REPLICATION_FINAL.py --workdir .
```

Outputs include:

- canonical H1–H5 results;
- symmetric native/common-sample results;
- joint horse-race results;
- serial-correlation, VIF, and endogeneity diagnostics;
- lead falsification and bank-trend robustness;
- redesigned model-family results;
- `FINAL_MANIFEST_SHA256.csv`.

The model remains associational. The lag/control-function module is diagnostic only and is not an IV estimator.

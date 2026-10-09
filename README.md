# Forensic Finders — Public Records Acquisition
Automated, reproducible collection of public Columbus GIS building and site-engineering permits for Case 001. The records are **research leads**, not evidence of a person's location or proof of construction activity.

## Run
```bash
python -m unittest discover -s tests -v
python -m hfmr.retriever --output evidence --start 2000 --end 2010
python -m hfmr.retriever --verify evidence
```
GitHub Actions: **Actions → Public records acquisition → Run workflow**. Weekly scheduled runs also execute. Each run publishes a downloadable evidence artifact (temporary GitHub storage). Preserve it separately.

Queries search several address variants; **validate every returned address and parcel**. Permit issuance is not a concrete-pour date. Historical plans and inspection attachments require other public record sources. No private portal access, CAPTCHA bypass, or restricted sources. A failed retrieval is never reported as zero matching records.

The first GitHub-hosted run is required to establish live source availability. Test success alone is not proof that any records were acquired.

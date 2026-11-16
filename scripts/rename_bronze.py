from datetime import datetime, timezone
from pathlib import Path
from paths import BRONZE

DRY_RUN = False

for old in sorted(BRONZE.glob("city=*/*.json")):
    if "__fetched_" in old.name:
        continue
    year = old.stem[:4] # "1979-01-01" -> "1979"
    fetched = datetime.fromtimestamp(old.stat().st_mtime, tz=timezone.utc)
    new = old.with_name(f"{year}-01-01_{year}-12-31__fetched_{fetched:%Y%m%dT%H%M%SZ}.json")
    print(old.relative_to(BRONZE), "->", new.name)
    if not DRY_RUN:
        if new.exists():
            raise FileExistsError(new) # stop immediately not overwrite
        old.rename(new)

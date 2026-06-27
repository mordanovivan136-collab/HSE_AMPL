from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from official_water_data import build_official_water_sheets

import build_project


def main() -> None:
    data_dir = Path("emml_project") / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    sheets = build_official_water_sheets()
    build_project.write_workbook(data_dir / "project_data.xlsx", sheets)
    build_project.write_workbook(data_dir / "data_sources.xlsx", {"data_sources": sheets["data_sources"]})
    print(f"Wrote {data_dir / 'project_data.xlsx'}")
    print(f"Wrote {data_dir / 'data_sources.xlsx'}")


if __name__ == "__main__":
    main()

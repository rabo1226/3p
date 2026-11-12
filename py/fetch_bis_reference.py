"""BIS GW 기준 데이터(노선, 정류장)를 한 번 받아 CSV로 저장한다.

routeInfo(노선 537건)와 busStopInfo(정류장 약 3,700건)는 자주 바뀌지 않으므로 한 번만 받아 두고 재사용한다.
저장 위치: data/bis_routes.csv, data/bis_stops.csv
"""
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import requests

BASE = "https://apis.data.go.kr/6310000/bis"
OUT = Path(__file__).with_name("data")


def load_key() -> str:
    env = Path(__file__).with_name(".env").read_text(encoding="utf-8")
    for line in env.splitlines():
        name, _, value = line.partition("=")
        if name.strip() == "BIS_SERVICE_KEY":
            return value.strip().strip("\"'")
    raise SystemExit(".env 에 BIS_SERVICE_KEY 가 없습니다.")


def fetch(op: str, key: str) -> pd.DataFrame:
    # Accept 헤더가 없으면 한글이 깨진다. numOfRows 를 크게 주면 한 번에 전체가 온다.
    r = requests.get(f"{BASE}/{op}", params={"serviceKey": key, "pageNo": 1, "numOfRows": 20000},
                     headers={"Accept": "application/xml"}, timeout=90)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    if root.findtext("resultCode") != "200":
        raise RuntimeError(f"{op}: {root.findtext('resultCode')} {root.findtext('resultMsg')}")
    rows = [{c.tag: (c.text or "").strip() for c in row} for row in root.findall("./list/row")]
    return pd.DataFrame(rows)


def main() -> None:
    key = load_key()
    OUT.mkdir(exist_ok=True)
    for op, name in [("routeInfo", "bis_routes.csv"), ("busStopInfo", "bis_stops.csv")]:
        df = fetch(op, key)
        df.to_csv(OUT / name, index=False, encoding="utf-8-sig")
        print(f"{op}: {len(df)}건 -> data/{name}")


if __name__ == "__main__":
    main()

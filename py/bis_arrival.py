"""울산광역시_BIS 정보_GW (공공데이터포털) - 버스 도착정보 수집 -> pandas DataFrame

이 API는 XML만 제공한다(JSON 옵션 없음). 그래서 XML을 파싱해 DataFrame으로 만들고,
필요하면 DataFrame.to_json() 으로 JSON 변환한다.

사용 예:
    python bis_arrival.py                    # 전체 도착정보 (페이지네이션으로 모두 수집)
    python bis_arrival.py --stopid 196040117 # 특정 정류소만
    python bis_arrival.py --stopid 196040117 --json out.json --csv out.csv
"""
import argparse
import os
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://apis.data.go.kr/6310000/bis"
OPERATION = "getBusArrivalInfo"

COLUMNS = {
    "ROUTENM": "노선번호",
    "ROUTEID": "노선ID",
    "STOPID": "정류소ID",
    "STOPNM": "정류소명",
    "VEHICLENO": "차량번호",
    "PRESENTSTOPNM": "현재위치(정류소)",
    "PREVSTOPCNT": "남은정류소수",
    "ARRIVALTIME": "도착예정(초)",
    "REMARK": "비고",
}


def load_service_key() -> str:
    """환경변수 BIS_SERVICE_KEY, 없으면 같은 폴더의 .env 에서 읽는다."""
    key = os.environ.get("BIS_SERVICE_KEY")
    if not key:
        env_path = Path(__file__).with_name(".env")
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                name, _, value = line.partition("=")
                if name.strip() == "BIS_SERVICE_KEY":
                    key = value.strip().strip("\"'")
    if not key:
        raise SystemExit("BIS_SERVICE_KEY 가 없습니다. .env 파일 또는 환경변수에 설정하세요.")
    return key


def fetch_page(key: str, page: int, rows: int, stopid: str | None) -> tuple[list[dict], int]:
    params = {"serviceKey": key, "pageNo": page, "numOfRows": rows}
    if stopid:
        params["stopid"] = stopid  # 소문자만 필터로 동작함
    # Accept 헤더가 없으면 서버가 charset 없이 응답하며 한글이 '?' 로 깨진다
    resp = requests.get(
        f"{BASE_URL}/{OPERATION}",
        params=params,
        headers={"Accept": "application/xml"},
        timeout=30,
    )
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    # 인증 오류 등: <Response><error><resultCode>..</resultCode><resultMsg>..</resultMsg>
    err = root.find(".//error")
    if err is not None:
        raise RuntimeError(f"API 오류 {err.findtext('resultCode')}: {err.findtext('resultMsg')}")
    code = root.findtext("resultCode")
    if code != "200":
        raise RuntimeError(f"API 오류 {code}: {root.findtext('resultMsg')}")

    total = int(root.findtext("totalCnt") or 0)
    rows_ = [{c.tag: (c.text or "").strip() for c in row} for row in root.findall("./list/row")]
    return rows_, total


def fetch_arrivals(key: str, stopid: str | None = None, rows_per_page: int = 1000) -> pd.DataFrame:
    records: list[dict] = []
    page = 1
    while True:
        rows, total = fetch_page(key, page, rows_per_page, stopid)
        records.extend(rows)
        if not rows or len(records) >= total:
            break
        page += 1

    df = pd.DataFrame(records)
    if df.empty:
        return df
    for col in ("PREVSTOPCNT", "ARRIVALTIME", "RNUM"):
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    # 도착 예정 버스가 없는 정류소는 정류소 정보만 담긴 빈 행으로 내려온다 -> 제외
    df = df.dropna(subset=["ARRIVALTIME"])
    df = df.sort_values(["STOPID", "ARRIVALTIME"]).reset_index(drop=True)
    df = df.rename(columns=COLUMNS)
    ordered = [c for c in COLUMNS.values() if c in df.columns]
    return df[ordered + [c for c in df.columns if c not in ordered]]


def main() -> None:
    ap = argparse.ArgumentParser(description="울산 BIS 버스 도착정보 -> DataFrame")
    ap.add_argument("--stopid", help="정류소 ID (생략하면 전체)")
    ap.add_argument("--json", help="JSON 파일로 저장할 경로")
    ap.add_argument("--csv", help="CSV 파일로 저장할 경로")
    args = ap.parse_args()

    df = fetch_arrivals(load_service_key(), args.stopid)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", None)
    print(f"{len(df)}건")
    print(df.head(20).to_string())

    if args.json:
        df.to_json(args.json, orient="records", force_ascii=False, indent=2)
    if args.csv:
        df.to_csv(args.csv, index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()

"""국토교통부 노선별 이용량(일별) 수집 - 울산(시도 31) 표본 일자별 노선 단위 집계

일별 원본은 노선 × 읍면동 × 이용자유형 × 시간대 행이라 하루에 약 4만 행(1,000행씩 43회 호출)이다.
개편 후보 노선을 찾는 데는 노선 단위 합계면 충분하므로 받으면서 바로 집계해 CSV로 저장한다.
이미 저장된 일자는 건너뛰므로 중간에 멈춰도 이어서 실행할 수 있다(호출 한도 일 1,000건 보호).

사용 예:
    python collect_route_volume.py                      # 기본 표본 일자 전체
    python collect_route_volume.py 20260408 20260415    # 지정한 일자만
"""
import csv
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests

URL = "https://apis.data.go.kr/1613000/TripVolumebyRoute/getDailyTripVolumebyRoute"
SGG = {"31110": "중구", "31140": "남구", "31170": "동구", "31200": "북구", "31710": "울주군"}
OUT_DIR = Path(__file__).with_name("data") / "route_volume"

# 개편(2024-12-21)과 이후 조정(2025-07-05 4차 미세조정, 2026-06 폐지노선 복원) 전후를 끼는 수요일들
DEFAULT_DATES = [
    "20241016", "20241218", "20250115", "20250319", "20250625", "20250716",
    "20251015", "20260114", "20260318", "20260617", "20260715", "20260916",
]


def load_key() -> str:
    env = Path(__file__).with_name(".env").read_text(encoding="utf-8")
    for line in env.splitlines():
        name, _, value = line.partition("=")
        if name.strip() == "BIS_SERVICE_KEY":
            return value.strip().strip("\"'")
    raise SystemExit(".env 에 BIS_SERVICE_KEY 가 없습니다.")


def get_page(key: str, ymd: str, sgg: str, page: int) -> dict:
    params = {"serviceKey": key, "opr_ymd": ymd, "ctpv_cd": "31", "sgg_cd": sgg,
              "pageNo": page, "numOfRows": 1000}
    for attempt in range(4):
        try:
            r = requests.get(URL, params=params, timeout=90)
            return r.json()
        except Exception as e:  # 시간 초과, 일시 오류
            print(f"    재시도 {attempt + 1}: {e}", flush=True)
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"{ymd} {sgg} p{page} 실패")


def collect_day(key: str, ymd: str) -> tuple[int, int]:
    """하루치를 받아 노선 단위로 합쳐 저장. (호출 수, 노선 수) 반환"""
    agg = defaultdict(lambda: {"ride": 0, "goff": 0, "sgg": set()})
    calls = 0
    for sgg, sgg_nm in SGG.items():
        page = 1
        while True:
            j = get_page(key, ymd, sgg, page)
            calls += 1
            if "Error" in j:
                code = j["Error"].get("code")
                if code == "50":      # NO_DATA_FOUND: 그 구에 해당 일자 데이터 없음
                    break
                raise RuntimeError(f"{ymd} {sgg}: {j['Error']}")
            body = j["Response"]["body"]
            items = (body.get("items") or {}).get("item", [])
            if isinstance(items, dict):
                items = [items]
            for it in items:
                k = (it["rte_id"], it["rte_nm"], it["dptre_sttn_nm"], it["arvl_sttn_nm"], it["trfc_mns_se_cd"])
                agg[k]["ride"] += int(it["ride_nope"])
                agg[k]["goff"] += int(it["goff_nope"])
                agg[k]["sgg"].add(sgg_nm)
            total = int(body.get("totalCount", 0))
            if page * 1000 >= total or not items:
                break
            page += 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{ymd}.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["rte_id", "rte_nm", "dptre_sttn_nm", "arvl_sttn_nm", "trfc_mns_se_cd", "ride", "goff", "sgg"])
        for (rid, nm, dp, ar, tr), v in sorted(agg.items()):
            w.writerow([rid, nm, dp, ar, tr, v["ride"], v["goff"], "/".join(sorted(v["sgg"]))])
    return calls, len(agg)


def main() -> None:
    key = load_key()
    dates = sys.argv[1:] or DEFAULT_DATES
    total_calls = 0
    for ymd in dates:
        if (OUT_DIR / f"{ymd}.csv").exists():
            print(f"{ymd} 이미 있음, 건너뜀", flush=True)
            continue
        t0 = time.time()
        calls, n = collect_day(key, ymd)
        total_calls += calls
        print(f"{ymd} 완료: 호출 {calls}회, 노선 {n}개, {time.time() - t0:.0f}초 (이번 실행 누적 호출 {total_calls})", flush=True)
    print("끝", flush=True)


if __name__ == "__main__":
    main()

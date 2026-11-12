"""노선 연결용 정류장 목록 수집

1) 국토부 노선별 차내 재차인원: 노선(rte_id)마다 정류장 순서, 정류장명 (5개 구를 합쳐야 노선 전체가 된다)
2) BIS GW allRouteDetailInfo: 노선(BRTID)마다 정류장 순서, 정류장명

두 목록의 정류장 이름 겹침으로 서로 다른 ID 체계의 노선을 연결한다.
저장: data/onboard_route_stops_<일자>.csv, data/bis_route_stops.csv

사용 예:
    python collect_route_stops.py onboard 20260916
    python collect_route_stops.py bis
"""
import csv
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

DATA = Path(__file__).with_name("data")
SGG = ["31110", "31140", "31170", "31200", "31710"]
ONBOARD = "https://apis.data.go.kr/1613000/NumberofOnBoardPassengersbyRoute/getNumberofOnBoardPassengersbyRoute"
BIS_DETAIL = "https://apis.data.go.kr/6310000/bis/allRouteDetailInfo"


def load_key() -> str:
    env = Path(__file__).with_name(".env").read_text(encoding="utf-8")
    for line in env.splitlines():
        name, _, value = line.partition("=")
        if name.strip() == "BIS_SERVICE_KEY":
            return value.strip().strip("\"'")
    raise SystemExit(".env 에 BIS_SERVICE_KEY 가 없습니다.")


def retry_get(url, params, headers=None):
    for attempt in range(4):
        try:
            return requests.get(url, params=params, headers=headers, timeout=90)
        except Exception as e:
            print(f"    재시도 {attempt + 1}: {e}", flush=True)
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"요청 실패: {url} {params}")


def collect_onboard(key: str, ymd: str) -> None:
    # (rte_id, sttn_seq) -> 정류장 정보와 하루 최대 평균 재차인원
    stops = {}
    meta = {}
    calls = 0
    for sgg in SGG:
        page = 1
        while True:
            r = retry_get(ONBOARD, {"serviceKey": key, "opr_ymd": ymd, "ctpv_cd": "31", "sgg_cd": sgg,
                                    "pageNo": page, "numOfRows": 1000})
            calls += 1
            j = r.json()
            if "Error" in j:
                if j["Error"].get("code") == "50":
                    break
                raise RuntimeError(f"{sgg}: {j['Error']}")
            body = j["Response"]["body"]
            items = (body.get("items") or {}).get("item", [])
            if isinstance(items, dict):
                items = [items]
            for it in items:
                if it["trfc_mns_se_cd"] != "B":
                    continue
                k = (it["rte_id"], int(it["sttn_seq"]))
                cur = stops.get(k)
                load = int(it["avg_scdtm_nope"])
                if cur is None:
                    stops[k] = {"sttn_id": it["sttn_id"], "sttn_nm": it["sttn_nm"], "max_load": load, "sgg": sgg}
                else:
                    cur["max_load"] = max(cur["max_load"], load)
                meta[it["rte_id"]] = (it["rte_nm"], it["dptre_sttn_nm"], it["arvl_sttn_nm"])
            total = int(body.get("totalCount", 0))
            print(f"  {ymd} {sgg} p{page} 누적 호출 {calls}, 노선 {len(meta)}, 정류장행 {len(stops)}", flush=True)
            if page * 1000 >= total or not items:
                break
            page += 1
    out = DATA / f"onboard_route_stops_{ymd}.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["rte_id", "rte_nm", "dptre_sttn_nm", "arvl_sttn_nm", "sttn_seq", "sttn_id", "sttn_nm", "max_load", "sgg"])
        for (rid, seq), v in sorted(stops.items()):
            nm, dp, ar = meta[rid]
            w.writerow([rid, nm, dp, ar, seq, v["sttn_id"], v["sttn_nm"], v["max_load"], v["sgg"]])
    print(f"저장: {out.name} (노선 {len(meta)}개, 정류장행 {len(stops)}, 호출 {calls}회)", flush=True)


def collect_bis(key: str) -> None:
    import pandas as pd
    routes = pd.read_csv(DATA / "bis_routes.csv", dtype=str, encoding="utf-8-sig")
    out = DATA / "bis_route_stops.csv"
    done = set()
    rows_all = []
    if out.exists():
        prev = pd.read_csv(out, dtype=str, encoding="utf-8-sig")
        done = set(prev.BRTID)
        rows_all = prev.to_dict("records")
    n = 0
    for brtid in routes.BRTID:
        if brtid in done:
            continue
        r = retry_get(BIS_DETAIL, {"serviceKey": key, "pageNo": 1, "numOfRows": 1000, "routeid": brtid},
                      headers={"Accept": "application/xml"})
        root = ET.fromstring(r.content)
        if root.findtext("resultCode") != "200":
            print(f"  {brtid}: {root.findtext('resultCode')} {root.findtext('resultMsg')}", flush=True)
            continue
        for row in root.findall("./list/row"):
            d = {c.tag: (c.text or "").strip() for c in row}
            rows_all.append({"BRTID": brtid, "STOPID": d.get("STOPID", ""), "STOPNM": d.get("STOPNM", ""),
                             "BRSSEQNO": d.get("BRSSEQNO", "")})
        n += 1
        if n % 50 == 0:
            pd.DataFrame(rows_all).to_csv(out, index=False, encoding="utf-8-sig")
            print(f"  BIS 노선 {n}개 처리 (저장됨)", flush=True)
    pd.DataFrame(rows_all).to_csv(out, index=False, encoding="utf-8-sig")
    print(f"저장: {out.name} ({len(set(r['BRTID'] for r in rows_all))}개 노선, {len(rows_all)}행)", flush=True)


if __name__ == "__main__":
    key = load_key()
    DATA.mkdir(exist_ok=True)
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "onboard":
        collect_onboard(key, sys.argv[2])
    elif mode == "bis":
        collect_bis(key)
    else:
        raise SystemExit("사용: python collect_route_stops.py onboard <YYYYMMDD> | bis")

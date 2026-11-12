"""임시 노선 세트 만들기 (화면 개발용, 혼잡도는 가짜)

1) 지정한 노선번호들의 GeoJSON 을 만들고 (make_route_geojson.build 재사용)
2) 순서대로 임시 혼잡도를 붙인 노선 목록(route-list.json)을 만든다.
   1~3번째: 혼잡(HIGH) / 4~7번째: 보통(MID) / 8~10번째: 여유(LOW)

실제 예측 결과가 연결되면 route-list.json 은 서버가 예측 결과로 채우는 응답으로 대체된다.
"""
import json
from pathlib import Path

import pandas as pd

from make_route_geojson import DEFAULT_OUT, build

HERE = Path(__file__).parent
STATIC_DATA = DEFAULT_OUT.parent  # .../static/data

# 이용량이 많고 노선 연결이 확인된 상위 노선 (이 순서대로 혼잡도를 붙임)
ROUTES = ["134", "114", "115", "432", "124", "215", "118", "753", "711", "142"]


def grade_for(rank: int) -> tuple[str, str]:
    if rank <= 3:
        return "HIGH", "혼잡"
    if rank <= 7:
        return "MID", "보통"
    return "LOW", "여유"


def main() -> None:
    read = lambda n: pd.read_csv(HERE / "data" / n, dtype=str, encoding="utf-8-sig")
    routes, route_stops, stops = read("bis_routes.csv"), read("bis_route_stops.csv"), read("bis_stops.csv")

    DEFAULT_OUT.mkdir(parents=True, exist_ok=True)
    items = []
    for rank, no in enumerate(ROUTES, start=1):
        fc = build(no, routes, route_stops, stops)
        (DEFAULT_OUT / f"{no}.geojson").write_text(
            json.dumps(fc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

        # 목록에 보여 줄 이름: 첫 방향의 시작 정류장 ↔ 끝 정류장
        stop_feats = [f for f in fc["features"] if f["properties"]["kind"] == "stop"]
        first_dir = fc["features"][0]["properties"]["brt_id"]
        seq = [f for f in stop_feats if f["properties"]["brt_id"] == first_dir]
        label = f"{seq[0]['properties']['name']} ↔ {seq[-1]['properties']['name']}"
        lines = [f for f in fc["features"] if f["properties"]["kind"] == "line"]

        grade, grade_label = grade_for(rank)
        items.append({"routeNo": no, "rank": rank, "grade": grade, "gradeLabel": grade_label,
                      "label": label, "directions": len(lines)})
        print(f"{rank:>2}. {no:>4}번 [{grade_label}] 방향 {len(lines)}개, 정류장 {len(stop_feats)}개, 건너뛴 정류장 {len(fc['skipped_stops'])}개 | {label}")

    out = STATIC_DATA / "route-list.json"
    payload = {"temp": True, "note": "임시 데이터: 혼잡도는 가짜(순서대로 혼잡/보통/여유)", "routes": items}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n저장: {out}")


if __name__ == "__main__":
    main()

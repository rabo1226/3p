"""BIS 데이터로 노선별 GeoJSON 만들기 (지도에 노선 선과 정류장을 그리기 위한 파일)

입력: data/bis_routes.csv(노선), data/bis_route_stops.csv(노선별 정류장 순서), data/bis_stops.csv(정류장 좌표)
출력: <출력 폴더>/<노선번호>.geojson

한 노선번호에 방향이 둘 이상이면 방향마다 선(LineString) 하나, 정류장마다 점(Point) 하나를 담는다.
GeoJSON 규칙에 따라 좌표는 [경도, 위도] 순서이다. (카카오맵 코드에서는 LatLng(위도, 경도) 순서로 바꿔 쓴다)

사용 예:
    python make_route_geojson.py 741
    python make_route_geojson.py 741 1144 --out "D:/.../static/data/routes"
"""
import argparse
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
DEFAULT_OUT = Path(r"D:\01-STUDY\dev\프로젝트\project3\project3\src\main\resources\static\data\routes")


def build(route_no: str, routes, route_stops, stops) -> dict:
    rows = routes[routes.BRTNO == route_no]
    if rows.empty:
        raise SystemExit(f"노선번호 {route_no} 를 찾을 수 없습니다.")

    features = []
    skipped = []
    for _, r in rows.iterrows():
        g = route_stops[route_stops.BRTID == r.BRTID].copy()
        g["seq"] = g.BRSSEQNO.astype(int)
        g = g.sort_values("seq")                       # 정류장 순서대로 정렬 (선이 뒤엉키지 않게)
        g = g.merge(stops[["STOPID", "STOPNAME", "STOPX", "STOPY"]], on="STOPID", how="left")

        # 좌표가 없거나 이상한 정류장은 건너뜀
        g["lng"] = pd.to_numeric(g.STOPX, errors="coerce")
        g["lat"] = pd.to_numeric(g.STOPY, errors="coerce")
        bad = g[g.lng.isna() | g.lat.isna() | (g.lng == 0) | (g.lat == 0)]
        skipped += bad.STOPID.tolist()
        g = g.drop(bad.index)
        g["order"] = range(1, len(g) + 1)              # 이 방향 안에서의 순번 1..N

        coords = [[round(x, 6), round(y, 6)] for x, y in zip(g.lng, g.lat)]
        props = {"route_no": route_no, "brt_id": r.BRTID, "name": r.BRTNAME, "stop_count": len(g)}
        features.append({"type": "Feature", "properties": {**props, "kind": "line"},
                         "geometry": {"type": "LineString", "coordinates": coords}})
        last = len(g)
        for _, s in g.iterrows():
            features.append({
                "type": "Feature",
                "properties": {"kind": "stop", "route_no": route_no, "brt_id": r.BRTID,
                               "stop_id": s.STOPID, "name": s.STOPNAME, "order": int(s.order),
                               "is_end": bool(s.order in (1, last))},
                "geometry": {"type": "Point", "coordinates": [round(s.lng, 6), round(s.lat, 6)]},
            })
    return {"type": "FeatureCollection", "route_no": route_no, "skipped_stops": skipped, "features": features}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("route_nos", nargs="+")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    read = lambda n: pd.read_csv(HERE / "data" / n, dtype=str, encoding="utf-8-sig")
    routes, route_stops, stops = read("bis_routes.csv"), read("bis_route_stops.csv"), read("bis_stops.csv")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for no in args.route_nos:
        fc = build(no, routes, route_stops, stops)
        path = out / f"{no}.geojson"
        path.write_text(json.dumps(fc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"저장: {path} ({path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()

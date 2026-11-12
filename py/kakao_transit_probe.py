"""카카오맵 대중교통 경로 조회 API 로 '실제 버스 노선 경로 좌표'를 얻을 수 있는지 시험한다.

노선의 방향마다 기점 정류장 -> 종점 정류장 으로 대중교통 경로를 조회하고,
결과 중 우리 노선번호와 같은 버스 구간(BUS step)이 있는지, 있다면 그 좌표가 우리 정류장들과 얼마나 맞는지 본다.

사용 예:
    python kakao_transit_probe.py                 # 134번
    python kakao_transit_probe.py --route 114
    python kakao_transit_probe.py --all           # route-list.json 의 모든 노선

필요: 같은 폴더 .env (또는 환경변수) 의 KAKAO_REST_KEY (REST API 키, 비밀 값 - 출력하지 않는다)
참고: 카카오 경로 좌표는 저장하지 않는다 (좌표 저장은 카카오 정책상 허용되지 않는다는 답변이 있음).
      파일로 남기는 것은 요약 텍스트(data/kakao_transit_probe_summary.txt)뿐이다.
"""
import argparse
import json
import math
import os
import statistics
import sys
import time
from pathlib import Path

import requests

API_URL = "https://dapi.kakao.com/v2/routing/publictraffic"
DEFAULT_GEOJSON_DIR = Path(r"D:\01-STUDY\dev\프로젝트\project3\project3\src\main\resources\static\data\routes")
OUT_DIR = Path(__file__).with_name("data")


def load_key() -> str:
    """환경변수 KAKAO_REST_KEY, 없으면 같은 폴더의 .env 에서 읽는다."""
    key = os.environ.get("KAKAO_REST_KEY")
    if not key:
        env_path = Path(__file__).with_name(".env")
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                name, _, value = line.partition("=")
                if name.strip() == "KAKAO_REST_KEY":
                    key = value.strip().strip("\"'")
    if not key:
        raise SystemExit("KAKAO_REST_KEY 가 없습니다. .env 파일 또는 환경변수에 설정하세요.")
    return key


def haversine_m(a, b) -> float:
    """a, b = (경도, 위도)"""
    r = 6371000
    p = math.pi / 180
    x = math.sin((b[1] - a[1]) * p / 2) ** 2 + math.cos(a[1] * p) * math.cos(b[1] * p) * math.sin((b[0] - a[0]) * p / 2) ** 2
    return 2 * r * math.asin(math.sqrt(x))


def load_directions(geojson_path: Path) -> list[dict]:
    """노선 geojson 에서 방향별 이름과 정류장(순서대로) 을 읽는다."""
    fc = json.loads(geojson_path.read_text(encoding="utf-8"))
    names = {f["properties"]["brt_id"]: f["properties"]["name"] for f in fc["features"] if f["properties"]["kind"] == "line"}
    stops = {}
    for f in fc["features"]:
        if f["properties"]["kind"] == "stop":
            stops.setdefault(f["properties"]["brt_id"], []).append(f)
    result = []
    for brt_id in sorted(names):
        ordered = sorted(stops.get(brt_id, []), key=lambda f: f["properties"]["order"])
        result.append({
            "brt_id": brt_id,
            "name": names[brt_id],
            "stops": [(f["properties"]["name"], tuple(f["geometry"]["coordinates"])) for f in ordered],
        })
    return result


def call_api(key: str, start, end, s_name: str, e_name: str) -> tuple[int, dict]:
    resp = requests.get(
        API_URL,
        params={
            "start_x": start[0], "start_y": start[1], "s_name": s_name,
            "end_x": end[0], "end_y": end[1], "e_name": e_name,
        },
        headers={"Authorization": f"KakaoAK {key}"},   # 키는 출력하지 않는다
        timeout=30,
    )
    try:
        body = resp.json()
    except ValueError:
        body = {"raw": resp.text[:300]}
    return resp.status_code, body


def summarize(route_no: str, direction: dict, status_code: int, body: dict, out: list[str]) -> None:
    out.append(f"\n=== {direction['name']} (brt_id {direction['brt_id']}) 정류장 {len(direction['stops'])}개 ===")
    out.append(f"HTTP {status_code}, status={body.get('status')}")
    if status_code != 200 or body.get("status") != "OK":
        out.append("응답 요약: " + json.dumps(body, ensure_ascii=False)[:400])
        return

    routes = body.get("routes", [])
    out.append(f"조회된 경로 {len(routes)}개")
    direct = []      # 환승 없이 우리 노선 하나로 가는 경로의 버스 구간 (기점~종점 전체) - 이것이 필요한 것
    partial = []     # 환승 경로 안의 일부 구간 (전체 경로가 아님)
    for i, r in enumerate(routes):
        p = r.get("properties", {})
        steps = r.get("steps", [])
        desc = []
        for s in steps:
            sp = s.get("properties", {})
            names = ",".join(v.get("name", "?") for v in sp.get("vehicles", []) or [])
            desc.append(f"{sp.get('type')}[{names}]({len((s.get('path') or {}).get('points', []))}pts)")
            is_ours = sp.get("type") == "BUS" and any(
                route_no == v.get("name", "").replace("번", "").strip() for v in sp.get("vehicles", []) or [])
            if is_ours:
                (direct if p.get("transfers") == 0 and len(steps) == 1 else partial).append((i + 1, s))
        out.append(f"  경로{i + 1}: type={p.get('type')} 환승={p.get('transfers')} 시간={p.get('totalTime')}s  " + " > ".join(desc))

    if not direct:
        out.append(f"=> {route_no}번 직행(환승 없음) 경로 없음 (환승 경로 안의 일부 구간 {len(partial)}개)")
        return

    idx, matched = direct[0]
    pts = matched["path"]["points"]
    out.append(f"=> {route_no}번 직행 경로 발견: 경로{idx}, 좌표 {len(pts)}개 (직행 경로 {len(direct)}개 중 첫째)")
    # 우리 정류장 좌표가 카카오 경로 좌표에서 얼마나 떨어져 있는지 (m)
    dists = [min(haversine_m(c, (x, y)) for x, y in pts) for _, c in direction["stops"]]
    length = sum(haversine_m(tuple(pts[i]), tuple(pts[i + 1])) for i in range(len(pts) - 1))
    out.append(f"   경로 길이 약 {length / 1000:.1f}km, 우리 정류장과의 최단거리: 중앙값 {statistics.median(dists):.0f}m, 최대 {max(dists):.0f}m")


def probe_route(key: str, route_no: str, geojson_dir: Path, out: list[str], verbose: bool) -> None:
    directions = load_directions(geojson_dir / f"{route_no}.geojson")
    out.append(f"\n##### 노선 {route_no}번 (방향 {len(directions)}개)")
    for d in directions:
        (s_name, start), (e_name, end) = d["stops"][0], d["stops"][-1]
        status_code, body = call_api(key, start, end, s_name, e_name)
        lines: list[str] = []
        summarize(route_no, d, status_code, body, lines)
        # 요약만 남긴다: 경로 목록(경로N 줄)은 --verbose 일 때만. 응답 원문(좌표)은 저장하지 않는다.
        out.extend(l for l in lines if verbose or not l.startswith("  경로"))
        time.sleep(0.3)   # 호출 간격 (일 한도 1,000건 보호)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--route", default="134")
    ap.add_argument("--all", action="store_true", help="route-list.json 의 모든 노선을 시험")
    ap.add_argument("--verbose", action="store_true", help="조회된 경로 목록까지 출력")
    ap.add_argument("--geojson-dir", type=Path, default=DEFAULT_GEOJSON_DIR)
    args = ap.parse_args()

    key = load_key()
    if args.all:
        listing = json.loads((args.geojson_dir.parent / "route-list.json").read_text(encoding="utf-8"))
        route_nos = [r["routeNo"] for r in listing["routes"]]
    else:
        route_nos = [args.route]

    out: list[str] = [f"카카오 대중교통 경로 시험: 노선 {len(route_nos)}개"]
    for route_no in route_nos:
        probe_route(key, route_no, args.geojson_dir, out, args.verbose)

    text = "\n".join(out)
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "kakao_transit_probe_summary.txt").write_text(text, encoding="utf-8")   # 요약 텍스트만 (좌표 없음)
    print(text)


if __name__ == "__main__":
    main()

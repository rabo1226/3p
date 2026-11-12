import re
import pandas as pd

P = r"D:\01-STUDY\dev\프로젝트\3p\py\data"
ob = pd.read_csv(rf"{P}\onboard_route_stops_20260916.csv", dtype=str, encoding="utf-8-sig")
bs = pd.read_csv(rf"{P}\bis_route_stops.csv", dtype=str, encoding="utf-8-sig")
routes = pd.read_csv(rf"{P}\bis_routes.csv", dtype=str, encoding="utf-8-sig")
vol = pd.read_csv(rf"{P}\route_volume\20260916.csv", dtype=str, encoding="utf-8-sig")
vol = vol[vol.trfc_mns_se_cd == "B"].copy()
vol["ride"] = vol.ride.astype(int)
tot = vol.ride.sum()
ride = vol.set_index("rte_id").ride


def norm(s):
    s = "" if pd.isna(s) else str(s)
    s = re.sub(r"\([^)]*\)?", "", s)
    return re.sub(r"[\s\.\-·,]", "", s)


ob["n"] = ob.sttn_nm.map(norm)
bs["n"] = bs.STOPNM.map(norm)
ob_set = {r: set(g.n) for r, g in ob.groupby("rte_id")}
bs_set = {r: set(g.n) for r, g in bs.groupby("BRTID")}
meta = ob.drop_duplicates("rte_id").set_index("rte_id")["rte_nm"]
brt = routes.set_index("BRTID")
by_no = routes.groupby("BRTNO").BRTID.apply(list).to_dict()
GU = {"1": "중구", "2": "남구", "3": "동구", "4": "북구", "5": "울주"}


def parse_no(rid):
    """노선 ID(8자리)에서 BIS 노선번호를 추정"""
    if rid.startswith("3106") and len(rid) == 8:
        a, b = rid[4], rid[5:7]
        for cand in (f"66{b}", f"{GU.get(a, '')}{b}"):   # 순환 노선은 BRTNO 66xx
            if cand in by_no:
                return cand
    for cand in (rid[4:7], rid[3:7], rid[2:7], str(int(rid[4:7]))):
        if cand in by_no:
            return cand
    return None


recs = []
for rid, a in ob_set.items():
    no = parse_no(rid)
    cands = by_no.get(no, []) if no else []
    best, cont = None, 0.0
    for bid in cands:
        b = bs_set.get(bid, set())
        c = len(a & b) / len(b) if b else 0
        if c > cont:
            best, cont = bid, c
    recs.append({"rte_id": rid, "rte_nm": meta[rid], "BRTNO": no, "n_variants": len(cands),
                 "BRTID": best, "cont": round(cont, 3), "ride": int(ride.get(rid, 0))})
cw = pd.DataFrame(recs)


def grade(r):
    if r.BRTNO is None:
        return "C_번호없음"
    if r.cont >= 0.6:
        return "A_번호+정류장확인"
    if r.cont >= 0.3:
        return "B_번호만(정류장약함)"
    return "C_정류장불일치"


cw["grade"] = cw.apply(grade, axis=1)
g = cw.groupby("grade").agg(노선=("ride", "size"), 승차=("ride", "sum"))
g["승차비율"] = (g.승차 / tot).round(3)
print(f"이용량 노선 {len(vol)}개 중 재차인원과 겹치는 {len(cw)}개, 하루 승차 {tot:,}")
print(g.to_string())

print("\n== 번호 후보가 여러 개(방향 변형)인 경우 ==")
print(cw[cw.BRTNO.notna()].n_variants.value_counts().sort_index().to_string())

print("\n== 승차 상위 20 ==")
for _, r in cw.sort_values("ride", ascending=False).head(20).iterrows():
    print(f"{r.rte_id} {r.rte_nm} 승차{r.ride} -> 노선번호 {r.BRTNO} {brt.BRTNAME.get(r.BRTID, '')} cont={r.cont} [{r.grade}]")

print("\n== 정류장 불일치(C) 상위 ==")
print(cw[cw.grade.str.startswith("C")].sort_values("ride", ascending=False).head(10)[["rte_id", "rte_nm", "BRTNO", "cont", "ride"]].to_string(index=False))

cw.to_csv(rf"{P}\route_crosswalk_v3.csv", index=False, encoding="utf-8-sig")
print("\n저장: data/route_crosswalk_v3.csv")

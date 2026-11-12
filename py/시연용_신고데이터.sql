-- 시연용 신고 데이터로 교체 (팀 공용 DB의 신고를 모두 지우고 새로 넣음)
-- 실행 전 읽을 것
--   * 이 스크립트는 REPORT(신고)와 REPORT_FILE(첨부)의 기존 데이터를 지웁니다. 먼저 [1]로 백업 표를 만들고, 필요하면 [5]로 되돌립니다.
--   * 팀원(박진호) 신고 데이터도 함께 지워지니, 실행 전에 팀에 알리세요.
--   * 신고자 이름·전화번호는 가짜 값(010-0000-0001 …)이고, 회원(MEMBER_NO)은 비워 둡니다. 시민 화면의 "내 신고"에는 보이지 않고 관리자 화면에서 보입니다.
--   * 접수 시각은 실행하는 날 기준으로 며칠 전인지로 계산합니다(장기 방치 신고는 15~17일 전이라 14일 기준을 넘음). 촬영 당일이나 전날 실행하세요.
--   * 순서: [1] 백업 → [2] 사전 점검(결과 확인) → [3] 교체 실행 → [4] 결과 확인 → 이상 없으면 COMMIT, 이상하면 ROLLBACK
--   * HeidiSQL에서는 [3]을 구간으로 선택해 한 번에 실행하세요. (START TRANSACTION 부터 [4]의 확인 쿼리까지)

-- [1] 백업 (실행한 날짜가 표 이름에 들어감: 한 번만 만들고, 같은 이름이 있으면 오류가 나니 그때는 이름을 바꾸세요)
CREATE TABLE report_backup_20261110 AS SELECT * FROM report;
CREATE TABLE report_file_backup_20261110 AS SELECT * FROM report_file;

-- [2] 사전 점검: 아래 둘 다 결과가 0행이어야 정상 (아니면 [3]을 실행하지 마세요)
-- (a) 이 데이터에서 쓰는 신고 유형 이름이 REPORT_TYPE에 모두 있는지
SELECT DISTINCT v.type_name AS 없는_유형
FROM (
  SELECT '개문발차 운행' AS type_name
UNION ALL
  SELECT '교통카드 단말기 오류' AS type_name
UNION ALL
  SELECT '기사 불친절(반말·욕설 등)' AS type_name
UNION ALL
  SELECT '기타 불편 사항' AS type_name
UNION ALL
  SELECT '난폭운전(급출발·급정거 등)' AS type_name
UNION ALL
  SELECT '냉·난방 고장' AS type_name
UNION ALL
  SELECT '무정차 통과' AS type_name
UNION ALL
  SELECT '배차간격·운행시간 미준수' AS type_name
UNION ALL
  SELECT '승차 거부' AS type_name
UNION ALL
  SELECT '신호위반' AS type_name
UNION ALL
  SELECT '안내방송 미실시' AS type_name
UNION ALL
  SELECT '요금 부당 징수' AS type_name
UNION ALL
  SELECT '운행 중 흡연' AS type_name
UNION ALL
  SELECT '정류장 외 승·하차' AS type_name
UNION ALL
  SELECT '차량 내부 청결 불량' AS type_name
UNION ALL
  SELECT '차량 정비 불량' AS type_name
UNION ALL
  SELECT '첫차·막차 미운행' AS type_name
UNION ALL
  SELECT '환승 할인 미적용' AS type_name
) v
LEFT JOIN report_type t ON t.TYPE_NAME = v.type_name
WHERE t.TYPE_NO IS NULL;

-- (b) 이 데이터에서 쓰는 노선이 BUS_ROUTE에 모두 있는지
SELECT DISTINCT v.route_no AS 없는_노선
FROM (
  SELECT '114' AS route_no
UNION ALL
  SELECT '115' AS route_no
UNION ALL
  SELECT '118' AS route_no
UNION ALL
  SELECT '124' AS route_no
UNION ALL
  SELECT '134' AS route_no
UNION ALL
  SELECT '142' AS route_no
UNION ALL
  SELECT '215' AS route_no
UNION ALL
  SELECT '422' AS route_no
UNION ALL
  SELECT '432' AS route_no
UNION ALL
  SELECT '452' AS route_no
UNION ALL
  SELECT '518' AS route_no
UNION ALL
  SELECT '711' AS route_no
UNION ALL
  SELECT '713' AS route_no
UNION ALL
  SELECT '753' AS route_no
UNION ALL
  SELECT '6104' AS route_no
UNION ALL
  SELECT '6205' AS route_no
UNION ALL
  SELECT '6303' AS route_no
UNION ALL
  SELECT '6612' AS route_no
) v
LEFT JOIN bus_route b ON b.ROUTE_NO = v.route_no
WHERE b.ROUTE_NO IS NULL;

-- [3] 교체 실행
START TRANSACTION;

DELETE FROM report_file;
DELETE FROM report;

CREATE TEMPORARY TABLE demo_report (
  route_no   VARCHAR(20),
  type_name  VARCHAR(50),
  status     VARCHAR(20),
  days_ago   INT,
  reg_time   TIME,
  name       VARCHAR(50),
  phone      VARCHAR(20),
  content    TEXT,
  answer     TEXT,
  answer_days_ago INT
);

INSERT INTO demo_report VALUES
  ('753', '배차간격·운행시간 미준수', 'RECEIVED', 17, '07:20:00', '김민수', '010-0000-0001', '명촌 방면 753번 배차 간격이 40분 넘게 벌어질 때가 많아 출근 시간에 계속 늦습니다. 시간표대로 운행되지 않는 것 같습니다.', NULL, NULL),
  ('142', '요금 부당 징수', 'RECEIVED', 16, '14:30:00', '이서연', '010-0000-0002', '교통카드 대신 현금을 냈는데 기사님이 거스름돈을 주지 않았습니다. 이전에도 비슷한 일이 있었습니다.', NULL, NULL),
  ('6205', '첫차·막차 미운행', 'PROCESSING', 15, '05:50:00', '박지훈', '010-0000-0003', '시간표의 첫차 시간에 맞춰 나갔는데 첫 버스가 오지 않았습니다. 다음 버스는 30분 뒤였습니다.', NULL, NULL),
  ('142', '요금 부당 징수', 'DONE', 13, '14:20:00', '최유진', '010-0000-0004', '현금으로 요금을 냈는데 기사님이 거스름돈을 주지 않고 그냥 출발했습니다. 천 원 차이지만 확인 부탁드립니다.', '운수회사에 확인한 결과 거스름돈을 돌려주지 않은 사실이 있어 해당 금액을 환급하고 기사님께 요금 수수 규정을 다시 안내했습니다.', 6),
  ('432', '배차간격·운행시간 미준수', 'DONE', 12, '07:35:00', '정다은', '010-0000-0005', '출근 시간대에 432번이 30분 넘게 오지 않다가 두 대가 연달아 왔습니다. 배차 간격이 너무 불규칙합니다.', '해당 시간대 운행 기록을 점검해 출근 시간 배차를 조정하고, 간격이 벌어지지 않도록 차고지에 안내했습니다.', 4),
  ('134', '승차 거부', 'RECEIVED', 12, '08:10:00', '강현우', '010-0000-0006', '꽃바위 방면 134번이 출근 시간에 정류장에 서 있는 저를 보고도 문을 열지 않고 그냥 출발했습니다. 다음 버스까지 20분 가까이 기다렸습니다.', NULL, NULL),
  ('115', '기사 불친절(반말·욕설 등)', 'DONE', 11, '17:50:00', '조은지', '010-0000-0007', '115번 기사님이 승객에게 짜증 섞인 말투로 반말을 하셨습니다. 어르신도 계셨는데 보기 좋지 않았습니다.', '해당 기사님께 서비스 교육을 실시했고, 같은 일이 반복되면 추가 조치하겠습니다. 불편을 드려 죄송합니다.', 5),
  ('215', '무정차 통과', 'RECEIVED', 11, '12:45:00', '윤성호', '010-0000-0008', '농소 방면 215번이 정류장에 승객이 있는데도 서지 않고 지나갔습니다.', NULL, NULL),
  ('134', '안내방송 미실시', 'DONE', 10, '09:05:00', '장미래', '010-0000-0009', '134번에서 다음 정류장 안내방송이 나오지 않아 내릴 곳을 지나칠 뻔했습니다.', '안내방송 장치를 점검해 고장 난 스피커를 교체했습니다.', 7),
  ('115', '무정차 통과', 'RECEIVED', 10, '19:10:00', '임도현', '010-0000-0010', '115번이 승객이 벨을 눌렀는데도 정류장을 그냥 지나쳐 다음 정류장에서 내렸습니다.', NULL, NULL),
  ('114', '정류장 외 승·하차', 'DONE', 9, '21:15:00', '한소율', '010-0000-0011', '114번이 정류장이 아닌 도로 한가운데에서 승객을 내려 주었습니다. 뒤따르는 차들이 있어 위험했습니다.', '해당 기사님께 정류장 정차 규정을 다시 안내하고 주의 조치했습니다.', 6),
  ('711', '무정차 통과', 'DONE', 9, '19:00:00', '오태양', '010-0000-0012', '711번이 벨을 눌렀는데도 정류장을 그냥 지나쳤습니다. 다음 정류장에서 한참을 걸어 돌아왔습니다.', '해당 기사님께 정차 규정을 교육하고 운행 기록을 점검했습니다.', 3),
  ('134', '승차 거부', 'RECEIVED', 9, '18:20:00', '서지안', '010-0000-0013', '퇴근 시간 시청 앞 정류장에서 134번 기사님이 만차라며 문을 열어 주지 않았는데, 앞쪽에는 자리가 남아 있었습니다.', NULL, NULL),
  ('124', '안내방송 미실시', 'RECEIVED', 9, '11:05:00', '권나영', '010-0000-0014', '124번에서 정류장 안내방송이 나오지 않아 처음 타는 사람은 어디서 내려야 하는지 알 수 없었습니다.', NULL, NULL),
  ('124', '냉·난방 고장', 'DONE', 8, '08:40:00', '신우진', '010-0000-0015', '124번 차 안 난방이 작동하지 않아 아침 내내 추웠습니다.', '차량 정비소에서 난방 장치를 점검하고 수리를 완료했습니다.', 5),
  ('118', '환승 할인 미적용', 'DONE', 8, '12:30:00', '김민수', '010-0000-0016', '30분 안에 환승했는데 118번에서 환승 할인이 적용되지 않고 요금이 전액 빠져나갔습니다.', '환승 처리 내역을 확인해 적용되지 않은 할인 금액을 환급했습니다. 단말기 설정도 함께 점검했습니다.', 4),
  ('711', '냉·난방 고장', 'RECEIVED', 8, '18:00:00', '이서연', '010-0000-0017', '711번 차량 안이 난방이 되지 않아 너무 추웠습니다. 날이 쌀쌀해 어르신들이 특히 힘들어했습니다.', NULL, NULL),
  ('518', '차량 내부 청결 불량', 'RECEIVED', 8, '10:05:00', '박지훈', '010-0000-0018', '518번 의자가 지저분하고 바닥에 쓰레기가 있었습니다.', NULL, NULL),
  ('215', '교통카드 단말기 오류', 'DONE', 7, '16:10:00', '최유진', '010-0000-0019', '215번 단말기에 카드를 여러 번 대도 인식이 되지 않아 뒤에 줄이 길어졌습니다.', '해당 차량의 교통카드 단말기를 새것으로 교체했습니다.', 3),
  ('6612', '정류장 외 승·하차', 'RECEIVED', 7, '21:05:00', '정다은', '010-0000-0020', '6612번 기사님이 정류장이 아닌 곳에서 승객을 내려 주었습니다. 도로 가운데라 위험해 보였습니다.', NULL, NULL),
  ('134', '난폭운전(급출발·급정거 등)', 'DONE', 6, '18:25:00', '강현우', '010-0000-0021', '134번이 정류장을 급하게 출발해 서 있던 승객이 크게 휘청였습니다. 아이를 안은 분도 있었습니다.', '블랙박스 영상을 확인해 급출발 사실을 확인했고, 해당 기사님께 안전 운전 교육을 실시했습니다.', 2),
  ('753', '차량 내부 청결 불량', 'DONE', 6, '10:20:00', '조은지', '010-0000-0022', '753번 의자에 음료가 흘러 끈적하고 바닥에 쓰레기가 그대로 있었습니다.', '해당 차량을 정밀 청소했고 운행 후 청소 점검을 강화했습니다.', 2),
  ('115', '무정차 통과', 'RECEIVED', 6, '08:40:00', '윤성호', '010-0000-0023', '정류장에서 손을 들었는데 115번이 서지 않고 지나갔습니다. 출근 시간이라 지각할 뻔했습니다.', NULL, NULL),
  ('114', '첫차·막차 미운행', 'RECEIVED', 6, '22:40:00', '장미래', '010-0000-0024', '시간표에는 22시 50분 막차가 있는데 40분 넘게 기다려도 오지 않았습니다. 결국 택시를 탔습니다.', NULL, NULL),
  ('6104', '교통카드 단말기 오류', 'RECEIVED', 6, '09:15:00', '임도현', '010-0000-0025', '6104번 단말기가 카드를 여러 번 대도 인식되지 않아 뒤에 줄이 길어졌습니다.', NULL, NULL),
  ('6205', '기타 불편 사항', 'DONE', 5, '15:45:00', '한소율', '010-0000-0026', '6205번 정류장 안내판의 노선 표시가 지워져 어느 버스가 오는지 알 수 없습니다.', '정류장 안내판을 새로 교체했습니다.', 1),
  ('134', '승차 거부', 'PROCESSING', 5, '07:45:00', '오태양', '010-0000-0027', '아침마다 같은 정류장에서 134번이 정차하지 않고 지나갑니다. 이번 주에만 두 번째입니다.', NULL, NULL),
  ('422', '안내방송 미실시', 'RECEIVED', 5, '11:20:00', '서지안', '010-0000-0028', '422번에서 정류장 안내방송이 나오지 않았습니다.', NULL, NULL),
  ('711', '냉·난방 고장', 'RECEIVED', 4, '08:50:00', '권나영', '010-0000-0029', '이번에도 711번 난방이 작동하지 않았습니다. 차량 번호를 확인해 주세요.', NULL, NULL),
  ('6303', '기타 불편 사항', 'RECEIVED', 4, '16:40:00', '신우진', '010-0000-0030', '6303번 정류장 시간표가 지워져 있어 배차 시간을 알아볼 수 없습니다.', NULL, NULL),
  ('215', '개문발차 운행', 'PROCESSING', 3, '16:05:00', '김민수', '010-0000-0031', '농소 방면 215번이 승객이 아직 내리는 중에 문이 열린 채로 출발했습니다. 어르신이 중심을 잃을 뻔했습니다.', NULL, NULL),
  ('134', '차량 정비 불량', 'PROCESSING', 3, '09:30:00', '이서연', '010-0000-0032', '134번에서 하차벨을 눌러도 울리지 않고, 뒷문이 한 번에 열리지 않아 승객들이 불편해했습니다.', NULL, NULL),
  ('118', '기사 불친절(반말·욕설 등)', 'RECEIVED', 3, '15:10:00', '박지훈', '010-0000-0033', '118번 기사님이 승객에게 큰 소리로 반말을 하며 빨리 내리라고 재촉했습니다.', NULL, NULL),
  ('124', '신호위반', 'RECEIVED', 2, '12:20:00', '최유진', '010-0000-0034', '율리 방면 124번이 교차로에서 적색 신호가 켜진 뒤에도 그대로 진입했습니다. 횡단보도를 건너던 보행자가 놀라 멈춰 섰습니다.', NULL, NULL),
  ('115', '무정차 통과', 'PROCESSING', 2, '13:15:00', '정다은', '010-0000-0035', '115번이 이번에도 승차하려는 사람이 있는데 정차하지 않았습니다. 같은 문제가 반복되고 있습니다.', NULL, NULL),
  ('713', '환승 할인 미적용', 'RECEIVED', 2, '07:55:00', '강현우', '010-0000-0036', '713번으로 환승했는데 환승 할인이 적용되지 않고 요금이 다시 빠져나갔습니다.', NULL, NULL),
  ('114', '난폭운전(급출발·급정거 등)', 'RECEIVED', 1, '17:55:00', '조은지', '010-0000-0037', '대왕암공원 방면 114번이 정류장에서 급출발해 서 있던 승객이 크게 휘청였습니다. 손잡이를 잡지 않았으면 넘어질 뻔했습니다.', NULL, NULL),
  ('432', '난폭운전(급출발·급정거 등)', 'RECEIVED', 1, '08:25:00', '윤성호', '010-0000-0038', '432번이 차선을 급하게 바꾸면서 급정거해 승객 여러 명이 앞으로 쏠렸습니다. 출근길이라 사람이 많았습니다.', NULL, NULL),
  ('452', '운행 중 흡연', 'RECEIVED', 1, '20:30:00', '장미래', '010-0000-0039', '452번 기사님이 정차 중에 문을 열고 담배를 피우셨습니다. 냄새가 차 안까지 들어왔습니다.', NULL, NULL);

-- 접수가 오래된 순서로 넣어 신고 번호가 작을수록 오래된 신고가 되게 함
INSERT INTO report (MEMBER_NO, REPORTER_NAME, REPORTER_PHONE, TYPE_NO, ROUTE_NO, CONTENT, STATUS, REG_DATE, ANSWER, ANSWER_DATE)
SELECT NULL, d.name, d.phone, t.TYPE_NO, d.route_no, d.content, d.status,
       TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL d.days_ago DAY), d.reg_time),
       d.answer,
       CASE WHEN d.answer_days_ago IS NULL THEN NULL
            ELSE TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL d.answer_days_ago DAY), '14:30:00') END
FROM demo_report d
INNER JOIN report_type t ON t.TYPE_NAME = d.type_name
ORDER BY d.days_ago DESC, d.reg_time;

DROP TEMPORARY TABLE demo_report;

-- [4] 결과 확인 (넣은 건수 39건 = 처리 완료 12 + 접수 22 + 처리중 5)
SELECT STATUS, COUNT(*) AS 건수 FROM report GROUP BY STATUS;
SELECT COUNT(*) AS 전체 FROM report;
SELECT R.REPORT_NO, R.ROUTE_NO, T.TYPE_NAME, R.STATUS, R.REG_DATE, R.ANSWER_DATE
FROM report R INNER JOIN report_type T ON R.TYPE_NO = T.TYPE_NO
ORDER BY R.REPORT_NO;

-- 확인 후:  COMMIT;   (이상하면:  ROLLBACK;)

-- [5] 되돌리기 (COMMIT 이후에 원래 데이터로 돌리고 싶을 때만)
--   DELETE FROM report_file;  DELETE FROM report;
--   INSERT INTO report SELECT * FROM report_backup_20261110;
--   INSERT INTO report_file SELECT * FROM report_file_backup_20261110;

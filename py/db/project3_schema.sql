-- project-3 데이터베이스 구조(스키마) 내보내기
-- 내보낸 날짜: 2026-10-23   (데이터는 포함하지 않음 / 구조만)
-- 원본 서버 문자셋: utf8mb4 / utf8mb4_general_ci
--
-- 집에서 쓰는 방법
--   1) MariaDB 설치 후 이 파일을 실행:   mariadb -u root -p < project3_schema.sql
--   2) 앱에서 쓸 계정을 만들기 (비밀번호는 직접 정하고 이 파일에 적지 않기):
--        CREATE USER 'user'@'localhost' IDENTIFIED BY '여기에_비밀번호';
--        GRANT ALL PRIVILEGES ON `project-3`.* TO 'user'@'localhost';
--        FLUSH PRIVILEGES;
--   3) application.yaml 의 datasource url 을 jdbc:log4jdbc:mariadb://localhost:3306/project-3 로,
--      username/password 를 위 계정으로 바꾸기

CREATE DATABASE IF NOT EXISTS `project-3` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `project-3`;

-- 테이블: member (행 0개)
CREATE TABLE IF NOT EXISTS `member` (
  `MEMBER_NO` int(11) NOT NULL AUTO_INCREMENT,
  `MEMBER_ID` varchar(50) NOT NULL,
  `MEMBER_PW` varchar(100) NOT NULL,
  `MEMBER_NAME` varchar(50) NOT NULL,
  `MEMBER_PHONE` varchar(20) NOT NULL,
  `REG_DATE` datetime NOT NULL DEFAULT current_timestamp(),
  `ROLE` varchar(10) NOT NULL DEFAULT 'USER',
  PRIMARY KEY (`MEMBER_NO`),
  UNIQUE KEY `UK_MEMBER_ID` (`MEMBER_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

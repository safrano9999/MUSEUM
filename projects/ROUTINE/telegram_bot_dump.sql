/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19-12.2.2-MariaDB, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: telegram_bot
-- ------------------------------------------------------
-- Server version	12.2.2-MariaDB-ubu2404

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*M!100616 SET @OLD_NOTE_VERBOSITY=@@NOTE_VERBOSITY, NOTE_VERBOSITY=0 */;

--
-- Table structure for table `routine_items`
--

DROP TABLE IF EXISTS `routine_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `routine_items` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `label` varchar(100) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `routine_items`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `routine_items` WRITE;
/*!40000 ALTER TABLE `routine_items` DISABLE KEYS */;
INSERT INTO `routine_items` VALUES
(1,'Task 1'),
(2,'Task 2'),
(3,'Task 3'),
(4,'Task 4'),
(5,'Task 5'),
(6,'Task 6'),
(7,'Task 7'),
(8,'Task 8'),
(9,'Task 9'),
(10,'Task 10'),
(11,'Task 11'),
(12,'Task 12'),
(13,'Task 13'),
(14,'Task 14'),
(15,'Task 15');
/*!40000 ALTER TABLE `routine_items` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Table structure for table `routine_log`
--

DROP TABLE IF EXISTS `routine_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `routine_log` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `session_date` date NOT NULL,
  `item_id` int(11) NOT NULL,
  `checked_at` timestamp NULL DEFAULT NULL,
  `note` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_session_item` (`session_date`,`item_id`),
  KEY `item_id` (`item_id`),
  CONSTRAINT `1` FOREIGN KEY (`item_id`) REFERENCES `routine_items` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=32 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `routine_log`
--

SET @OLD_AUTOCOMMIT=@@AUTOCOMMIT, @@AUTOCOMMIT=0;
LOCK TABLES `routine_log` WRITE;
/*!40000 ALTER TABLE `routine_log` DISABLE KEYS */;
INSERT INTO `routine_log` VALUES
(1,'2026-02-22',1,NULL,NULL),
(2,'2026-02-22',2,NULL,NULL),
(3,'2026-02-22',3,NULL,NULL),
(4,'2026-02-22',4,NULL,NULL),
(5,'2026-02-22',5,NULL,NULL),
(6,'2026-02-22',6,NULL,NULL),
(7,'2026-02-22',7,NULL,NULL),
(8,'2026-02-22',8,NULL,NULL),
(9,'2026-02-22',9,NULL,NULL),
(10,'2026-02-22',10,NULL,NULL),
(11,'2026-02-22',11,NULL,NULL),
(12,'2026-02-22',12,NULL,NULL),
(13,'2026-02-22',13,NULL,NULL),
(14,'2026-02-22',14,NULL,NULL),
(15,'2026-02-22',15,NULL,NULL);
/*!40000 ALTER TABLE `routine_log` ENABLE KEYS */;
UNLOCK TABLES;
COMMIT;
SET AUTOCOMMIT=@OLD_AUTOCOMMIT;

--
-- Dumping events for database 'telegram_bot'
--
/*!50106 SET @save_time_zone= @@TIME_ZONE */ ;
/*!50106 DROP EVENT IF EXISTS `routine_daily_reset` */;
DELIMITER ;;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;;
/*!50003 SET character_set_client  = utf8mb4 */ ;;
/*!50003 SET character_set_results = utf8mb4 */ ;;
/*!50003 SET collation_connection  = utf8mb4_uca1400_ai_ci */ ;;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;;
/*!50003 SET sql_mode              = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;;
/*!50003 SET @saved_time_zone      = @@time_zone */ ;;
/*!50003 SET time_zone             = 'SYSTEM' */ ;;
/*!50106 CREATE*/ /*!50117 DEFINER=`root`@`localhost`*/ /*!50106 EVENT `routine_daily_reset` ON SCHEDULE EVERY 1 DAY STARTS '2026-02-22 00:00:00' ON COMPLETION NOT PRESERVE ENABLE DO INSERT IGNORE INTO routine_log (session_date, item_id) SELECT CURDATE(), id FROM routine_items */ ;;
/*!50003 SET time_zone             = @saved_time_zone */ ;;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;;
/*!50003 SET character_set_client  = @saved_cs_client */ ;;
/*!50003 SET character_set_results = @saved_cs_results */ ;;
/*!50003 SET collation_connection  = @saved_col_connection */ ;;
DELIMITER ;
/*!50106 SET TIME_ZONE= @save_time_zone */ ;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*M!100616 SET NOTE_VERBOSITY=@OLD_NOTE_VERBOSITY */;

-- Dump completed on 2026-02-22  0:06:56

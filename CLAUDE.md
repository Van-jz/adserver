# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an RTB (Real-Time Bidding) advertising server system that implements both DSP (Demand-Side Platform) and SSP (Supply-Side Platform) functionality using OpenRTB 2.6 protocol. The main application is a Spring Boot service (`rtb/`) that handles bid requests from ad exchanges like Kwai.

**Technology Stack:**
- Spring Boot 2.3.3
- Java 1.8
- MyBatis-Plus 3.4.0 (ORM)
- MySQL
- Hutool (utility library)
- OkHttp (HTTP client)
- Aliyun OSS (object storage)

## Build and Run Commands

### Build
```bash
# Build with Maven (skipping tests)
cd rtb
mvn clean package -DskipTests

# Build with tests
mvn clean package
```

### Run
```bash
# Run Spring Boot application
cd rtb
mvn spring-boot:run

# Or run the JAR directly
java -jar target/springboot-scaffold-0.0.1-SNAPSHOT.jar
```

### Testing
```bash
# Run all tests
cd rtb
mvn test

# Run specific test class
mvn test -Dtest=SpringbootScaffoldApplicationTests
```

## Application Configuration

The application uses Spring profiles for different environments:
- **local**: Local development (`application-local.yml`)
- **dev0320**: Development environment (`application-dev0320.yml`)
- **dev7556**: Alternative dev environment (`application-dev7556.yml`)
- **prod0320**: Production environment (`application-prod0320.yml`)
- **prod7556**: Alternative prod environment (`application-prod7556.yml`)

Active profile is configured in `application.yml` (currently: `prod0320`)

**Important configuration properties:**
- `server.port`: Default 7721
- `bidUrl`: DSP bid endpoint URL
- `strategy`: Advertisement selection strategy (e.g., `bid_one_per_1000`)
- `logRootPath`: Log file storage path
- `server.taskEnable`: Enable/disable scheduled tasks
- `server.analysisLogFlag`: Enable/disable log analysis

## Architecture

### Package Structure

- **api/**: REST controllers (HTTP endpoints)
  - `SspController`: SSP bid request endpoint
  - `BidTestController`, `BidProdController`: Bid testing/production controllers
  - `DevController`: Development utilities

- **service/**: Business logic layer
  - `SspService`: SSP request handling
  - `IGoogleUserService`: Google user management
  - `IAdCostRecordService`: Ad cost tracking
  - `IAdPerformanceDayReportService`: Performance reporting
  - `IOssLogAnalysisService`: Log analysis from OSS

- **factory/**: Advertisement selection strategy pattern
  - `AdvertChoiceFactory`: Factory for selecting ad choice strategies
  - `IAdvertChoice`: Strategy interface
  - `AdvertChoiceBidOnePer1000`: Bid 1 per 1000 requests strategy
  - `AdvertChoiceFilterByCriteria`: Filter-based strategy

- **dto/**: Data Transfer Objects
  - `dto/req/`: OpenRTB bid request models (`BidRequest`, `Imp`, `Device`, `App`, etc.)
  - `dto/resp/`: OpenRTB bid response models (`BidResp`, `Seatbid`, `Bid`, etc.)

- **domain/**: Domain entities and value objects
  - `entity/`: Database entities (MyBatis-Plus)
  - `dto/`, `vo/`: Domain data transfer objects

- **repository/**: Data access layer (Repository pattern over MyBatis)

- **mapper/**: MyBatis mapper interfaces and XML files

- **task/**: Scheduled tasks
  - `ResetTask`: Daily bid interval reset, log synchronization to OSS

- **config/**: Spring configuration
  - `SysConfig`: System configuration (thread pool settings)
  - `OssBootConfiguration`: Aliyun OSS configuration
  - `MybatisPlusConfig`: MyBatis-Plus configuration
  - `WebMvcConfig`: Web MVC configuration

- **common/**: Shared components
  - `exception/`: Exception handling (`GlobalExceptionHandler`)
  - `enums/`: Status codes and enums
  - `dto/`: Common DTOs (`ApiResponse`)

- **utils/**: Utility classes

### Key Design Patterns

1. **Strategy Pattern**: Advertisement selection uses strategy pattern (`IAdvertChoice` implementations) configured via `strategy` property
2. **Factory Pattern**: `AdvertChoiceFactory` creates appropriate strategy instances
3. **Repository Pattern**: Abstraction layer over MyBatis mappers

### RTB Flow

1. SSP receives bid request from ad exchange (e.g., Kwai)
2. Request parsed into `BidRequest` DTO (OpenRTB 2.6 format)
3. Advertisement selection strategy determines which ads to bid on
4. HTTP request sent to downstream DSP via `SspService` using OkHttp
5. DSP response parsed into `BidResp` and returned to exchange
6. Performance/cost data logged to database and OSS

### Database Schema

Key entities:
- `GoogleUser`: User account information
- `GoogleUserDay`: Daily user statistics
- `GoogleUserDayReport`: Daily user performance reports
- `AdCostRecord`: Advertisement cost records
- `AdPerformanceDayReport`: Daily ad performance metrics
- `BidReqLog`: Bid request logs

Mapper XMLs located in: `rtb/src/main/resources/mapper/`

### Scheduled Tasks

Defined in `ResetTask.java`:
- **Daily 1:00 AM UTC**: Reset bid interval, log won price statistics
- **Daily 1:30 AM UTC**: Analyze logs from OSS (if `analysisLogFlag=true`)
- **Hourly**: Sync info logs to OSS, cleanup old logs (keeps max `logKeepMax` files)

### Thread Pool Configuration

HTTP client uses custom thread pool configured in `SysConfig`:
- Core threads: `sys.coreThreadNum` (default 20)
- Max threads: `sys.maxThreadNum` (default 200)
- Queue capacity: `sys.capacity` (default 108000)
- Thread name pattern: `sys.threadName` (default "httpclient")

## Important Notes

**Container Path Mapping:**
- Production container maps `/data/disk0/home` to `/home`
- CAUTION: Ensure log paths and file paths account for this mapping in production

**Log Management:**
- Logs automatically uploaded to Aliyun OSS
- Old logs deleted locally after successful upload
- Script available: `scripts/compress_and_verify_logs.sh`

**Security:**
- OSS credentials present in `application.yml` (should be externalized to environment variables)
- Database credentials in profile-specific configs

**OpenRTB Compliance:**
- Request/response DTOs implement OpenRTB 2.6 specification
- SKAdNetwork support included (`Skadn` objects)
- Supply chain transparency via `Schain` objects

## server info
- scp target/springboot-scaffold-0.0.1-SNAPSHOT.jar root@47.236.3.20:/data/disk0/springboot-scaffold_3.jar

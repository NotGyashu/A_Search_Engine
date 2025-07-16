# Documentation Organization Rules

## Documentation File Placement Rules

### Rule 1: All .md files for planning and analysis go to `docs/`
- **Location**: `mini_search_engine/docs/`
- **Purpose**: Centralized documentation for planning, analysis, and project documentation
- **Examples**:
  - `CLEANUP_SUMMARY.md`
  - `CRAWLER_PERFORMANCE_ANALYSIS_200s.md`
  - `HYBRID_CRAWLER_DOCUMENTATION.md`
  - `HYBRID_SUCCESS_SUMMARY.md`
  - `PERFORMANCE_OPTIMIZATION_PLAN.md`
  - `IMPLEMENTATION_PLAN.md`

### Rule 2: Component-specific README files stay in their directories
- **Location**: Component root directories
- **Purpose**: Immediate reference for component usage
- **Examples**:
  - `crawler/README.md`
  - `ai_search/README.md`

### Rule 3: Build and test scripts go to `crawler/scripts/`
- **Location**: `mini_search_engine/crawler/scripts/`
- **Purpose**: Standardized build and test processes
- **Files**:
  - `build.sh` - Builds crawler executables in `crawler/build/`
  - `test.sh` - Tests crawler functionality
  - `install_deps.sh` - Installs dependencies

### Rule 4: Data storage in `data/` directory
- **Location**: `mini_search_engine/data/`
- **Purpose**: Centralized data storage accessible by all components
- **Structure**:
  - `raw/` - Raw crawled data
  - `processed/` - Processed data
  - `disk_queue/` - Disk queue files

### Rule 5: Executables in `build/` directories
- **Location**: `mini_search_engine/crawler/build/`
- **Purpose**: Centralized executable storage
- **Examples**:
  - `crawler/build/crawler`
  - `crawler/build/hybrid_speed_crawler`

## Enforcement
- All new .md files for planning/analysis must be created in `docs/`
- Build scripts must use the standardized `crawler/scripts/build.sh`
- Test scripts must use the standardized `crawler/scripts/test.sh`
- Data must be stored in the main `data/` directory
- Executables must be built in component `build/` directories

## Benefits
1. **Centralized Documentation**: All planning docs in one place
2. **Standardized Scripts**: Consistent build and test processes
3. **Shared Data Access**: All components can access the same data
4. **Clean Organization**: Clear separation of concerns
5. **Easy Maintenance**: Predictable file locations

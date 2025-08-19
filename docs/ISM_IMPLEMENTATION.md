# Index State Management (ISM) Implementation Guide

## Overview

This implementation provides automated data lifecycle management for the search engine pipeline using OpenSearch Index State Management (ISM). It automatically deletes old daily indices after a specified retention period.

## Components

### 1. Index Templates (`indexer.py`)

**Purpose**: Automatically apply configurations to all new daily indices.

**Features**:
- Templates for both documents and chunks indices
- Automatic ISM policy assignment
- Consistent mappings and settings
- Priority-based template application

**Templates Created**:
- `documents_template`: Applies to `documents-*` indices
- `chunks_template`: Applies to `chunks-*` indices

### 2. ISM Policy (`ism_policy.json`)

**Policy Name**: `daily_crawl_data_management`

**Default Behavior**:
- Retention Period: 90 days
- States: `hot` → `delete`
- Automatic deletion after retention period

**Configuration**:
```json
{
  "policy_id": "daily_crawl_data_management",
  "states": [
    {
      "name": "hot",
      "transitions": [
        {
          "state_name": "delete",
          "conditions": {
            "min_index_age": "90d"
          }
        }
      ]
    },
    {
      "name": "delete",
      "actions": [{"delete": {}}]
    }
  ]
}
```

### 3. Management Script (`manage_ism.py`)

**Purpose**: Manual ISM policy management and monitoring.

**Commands**:
```bash
# Create ISM policy with default 90-day retention
python manage_ism.py create

# Create with custom retention period
python manage_ism.py create --retention-days 30

# Dry run (show what would be created)
python manage_ism.py create --dry-run

# Verify policy exists
python manage_ism.py verify

# List all indices with ISM status
python manage_ism.py list
```

## Implementation Details

### Automatic Policy Creation

The pipeline automatically:

1. **Creates ISM Policy**: On first run, creates the lifecycle policy
2. **Creates Templates**: Sets up index templates with ISM configuration
3. **Applies to New Indices**: All new daily indices automatically get the policy
4. **Manages Aliases**: Maintains stable alias names for searching

### Index Template Settings

Each template includes:

```python
"settings": {
  # ISM policy configuration
  "plugins.index_state_management.policy_id": "daily_crawl_data_management",
  "plugins.index_state_management.rollover_alias": "documents", # or "chunks"
  
  # Standard index settings
  "number_of_shards": 1,
  "number_of_replicas": 0,
  # ... other settings
}
```

### Manual Policy Application

For existing indices created before ISM was implemented:

```python
# Apply policy to all existing daily indices
indexer = OpenSearchIndexer()
results = indexer.apply_ism_policy_to_existing_indices()
print(f"Applied to {results['applied']} indices")
```

## Customization

### Changing Retention Period

**Method 1: During Policy Creation**
```python
indexer.create_ism_policy_if_needed(retention_days=60)  # 60 days instead of 90
```

**Method 2: Using Management Script**
```bash
python manage_ism.py create --retention-days 60
```

### Custom ISM States

For more advanced lifecycle management, modify `ism_policy.json`:

```json
{
  "states": [
    {
      "name": "hot",
      "actions": [],
      "transitions": [
        {
          "state_name": "warm",
          "conditions": {"min_index_age": "7d"}
        }
      ]
    },
    {
      "name": "warm",
      "actions": [
        {
          "replica_count": {
            "number_of_replicas": 0
          }
        }
      ],
      "transitions": [
        {
          "state_name": "delete",
          "conditions": {"min_index_age": "90d"}
        }
      ]
    },
    {
      "name": "delete",
      "actions": [{"delete": {}}]
    }
  ]
}
```

## Monitoring

### Check ISM Status

```python
indexer = OpenSearchIndexer()
status = indexer.get_ism_policy_status()

print(f"Policy exists: {status['policy_exists']}")
print(f"Managed indices: {len(status['managed_indices'])}")
print(f"Unmanaged indices: {len(status['unmanaged_indices'])}")
```

### OpenSearch Dashboards

Monitor ISM policies through the OpenSearch Dashboards UI:

1. Navigate to **Index Management** → **State management policies**
2. View policy details and index states
3. Monitor policy execution and errors

## Troubleshooting

### ISM Not Available

If ISM plugin is not available:
- The pipeline will continue to work without automated deletion
- Use manual cleanup: `indexer.cleanup_old_indices(days_to_keep=90)`
- Consider upgrading to a full OpenSearch distribution

### Policy Not Applied

Check if indices have the policy:
```bash
python manage_ism.py list
```

Apply policy to existing indices:
```python
indexer.apply_ism_policy_to_existing_indices()
```

### Custom OpenSearch Distributions

Some OpenSearch distributions may not include ISM:
- AWS OpenSearch Service: ISM available
- Self-hosted OpenSearch: Usually available
- Elasticsearch: Not available (different lifecycle management)

## Benefits

1. **Automated Cleanup**: No manual intervention needed
2. **Storage Cost Control**: Prevents unlimited data growth
3. **Performance Optimization**: Smaller index sets improve search performance
4. **Compliance**: Automated data retention for regulatory requirements
5. **Scalability**: Handles growing data volumes automatically

## Integration with Pipeline

The ISM implementation is fully integrated into the existing pipeline:

- **Zero Configuration**: Works out of the box with sensible defaults
- **Backward Compatible**: Existing indices continue to work
- **Non-Breaking**: Pipeline works even if ISM is not available
- **Configurable**: Easy to customize retention periods and policies

This implementation provides enterprise-grade data lifecycle management while maintaining the simplicity and reliability of the existing search pipeline.

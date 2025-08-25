#!/usr/bin/env python3
"""
ISM Policy Management Script

This script helps manage Index State Management (ISM) policies for the search engine pipeline.
Use this script to manually create, update, or verify ISM policies with the standalone indexer.
"""

import json
import os
from pathlib import Path
from comprehensive_indexer import ComprehensiveStandaloneIndexer

def load_ism_policy(policy_file: str = "ism_policy.json") -> dict:
    """Load ISM policy from JSON file."""
    policy_path = Path(__file__).parent / policy_file
    with open(policy_path, 'r') as f:
        return json.load(f)

def create_ism_policy(retention_days: int = 90, dry_run: bool = False):
    """Create or update the ISM policy."""
    print(f"🔄 Creating ISM policy with {retention_days} day retention...")
    
    if dry_run:
        print("📝 DRY RUN MODE - No changes will be made")
    
    try:
        # Initialize comprehensive indexer
        indexer = ComprehensiveStandaloneIndexer()
        
        if not indexer.client:
            print("❌ Failed to connect to OpenSearch")
            return False
        
        # Create the policy
        if not dry_run:
            success = indexer.create_ism_policy_if_needed(retention_days=retention_days)
            if success:
                print("✅ ISM policy created/verified successfully")
            else:
                print("❌ Failed to create ISM policy")
            return success
        else:
            policy = load_ism_policy()
            print("📄 Policy that would be created:")
            print(json.dumps(policy, indent=2))
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def verify_ism_policy():
    """Verify that the ISM policy exists and is working."""
    print("🔍 Verifying ISM policy...")
    
    try:
        indexer = OpenSearchIndexer()
        
        if not indexer.client:
            print("❌ Failed to connect to OpenSearch")
            return False
        
        # Check if policy exists
        policy_id = "daily_crawl_data_management"
        try:
            response = indexer.client.transport.perform_request(
                "GET", f"/_plugins/_ism/policies/{policy_id}"
            )
            print("✅ ISM policy exists and is active")
            print(f"📄 Policy details: {json.dumps(response, indent=2)}")
            return True
        except Exception as e:
            print(f"❌ ISM policy not found or not accessible: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def list_indices_with_ism():
    """List all indices and their ISM policy status."""
    print("📋 Listing indices with ISM policy status...")
    
    try:
        indexer = OpenSearchIndexer()
        
        if not indexer.client:
            print("❌ Failed to connect to OpenSearch")
            return False
        
        # Get all indices
        indices = indexer.client.indices.get_alias(index="*")
        
        print("\n📊 Index Status:")
        print("-" * 80)
        
        for index_name in sorted(indices.keys()):
            if (index_name.startswith(indexer.documents_index_base) or 
                index_name.startswith(indexer.chunks_index_base)):
                
                try:
                    # Get index settings to check ISM policy
                    settings = indexer.client.indices.get_settings(index=index_name)
                    policy_id = settings[index_name]["settings"]["index"].get(
                        "plugins.index_state_management.policy_id", "None"
                    )
                    print(f"  📂 {index_name:30} | ISM Policy: {policy_id}")
                except Exception as e:
                    print(f"  📂 {index_name:30} | Error: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage ISM policies for search engine pipeline")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create policy command
    create_parser = subparsers.add_parser("create", help="Create ISM policy")
    create_parser.add_argument("--retention-days", type=int, default=90, 
                              help="Number of days to retain data (default: 90)")
    create_parser.add_argument("--dry-run", action="store_true", 
                              help="Show what would be created without making changes")
    
    # Verify policy command
    verify_parser = subparsers.add_parser("verify", help="Verify ISM policy exists")
    
    # List indices command
    list_parser = subparsers.add_parser("list", help="List indices with ISM status")
    
    args = parser.parse_args()
    
    if args.command == "create":
        create_ism_policy(retention_days=args.retention_days, dry_run=args.dry_run)
    elif args.command == "verify":
        verify_ism_policy()
    elif args.command == "list":
        list_indices_with_ism()
    else:
        parser.print_help()

import pytest
from datetime import datetime
from pathlib import Path
from htmlgraph.session_manager import SessionManager
from htmlgraph.models import Node

def test_feature_claiming(tmp_path):
    # Setup
    manager = SessionManager(tmp_path)
    
    # Create a feature
    feature = manager.create_feature("Test Feature")
    feature_id = feature.id
    
    # Claim it for agent1
    manager.claim_feature(feature_id, agent="agent1")
    
    # Verify claim
    feature = manager.features_graph.get(feature_id)
    assert feature.agent_assigned == "agent1"
    assert feature.claimed_at is not None
    assert feature.claimed_by_session is not None
    
    # Try to claim it for agent2 (should fail because agent1 session is active)
    with pytest.raises(ValueError) as excinfo:
        manager.claim_feature(feature_id, agent="agent2")
    assert "already claimed by agent1" in str(excinfo.value)
    
    # Release claim
    manager.release_feature(feature_id, agent="agent1")
    
    # Verify release
    feature = manager.features_graph.get(feature_id)
    assert feature.agent_assigned is None
    assert feature.claimed_at is None
    assert feature.claimed_by_session is None
    
    # Now agent2 can claim it
    manager.claim_feature(feature_id, agent="agent2")
    feature = manager.features_graph.get(feature_id)
    assert feature.agent_assigned == "agent2"

def test_auto_release_on_session_end(tmp_path):
    manager = SessionManager(tmp_path)
    
    # Start session
    session = manager.start_session("sess-1", agent="agent1")
    
    # Create and claim feature
    feature = manager.create_feature("Test Feature")
    manager.claim_feature(feature.id, agent="agent1")
    
    # Verify claimed
    feature = manager.features_graph.get(feature.id)
    assert feature.agent_assigned == "agent1"
    assert feature.claimed_by_session == "sess-1"
    
    # End session
    manager.end_session("sess-1")
    
    # Verify auto-released
    feature = manager.features_graph.get(feature.id)
    assert feature.agent_assigned is None
    assert feature.claimed_by_session is None

def test_start_feature_enforcement(tmp_path):
    manager = SessionManager(tmp_path)
    
    # Agent1 claims feature
    feature = manager.create_feature("Test Feature")
    manager.claim_feature(feature.id, agent="agent1")
    
    # Agent2 tries to start it
    with pytest.raises(ValueError) as excinfo:
        manager.start_feature(feature.id, agent="agent2")
    assert "claimed by agent1" in str(excinfo.value)
    
    # Agent1 can start it
    manager.start_feature(feature.id, agent="agent1")
    feature = manager.features_graph.get(feature.id)
    assert feature.status == "in-progress"

def test_auto_claim_on_start(tmp_path):
    manager = SessionManager(tmp_path)
    
    feature = manager.create_feature("Test Feature")
    
    # Start feature without prior claim
    manager.start_feature(feature.id, agent="agent1")
    
    # Verify it was auto-claimed
    feature = manager.features_graph.get(feature.id)
    assert feature.agent_assigned == "agent1"
    assert feature.status == "in-progress"

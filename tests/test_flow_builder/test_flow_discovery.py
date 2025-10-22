"""
Tests for flow discovery module (Phase 4.1).

Following TEST-FIRST discipline.
Phase 4: Scan existing flows to avoid duplication
"""

from pathlib import Path

import pytest

from amplifier.flow_builder.flow_discovery import FlowInfo, scan_flows


class TestFlowScanning:
    """Tests for scanning existing workflow files."""

    def test_scan_flows_returns_list(self, tmp_path):
        """scan_flows() returns list of FlowInfo objects."""
        # Create test flow file
        flow_file = tmp_path / "test-flow.yaml"
        flow_file.write_text("""workflow:
  name: test-flow
  description: Test workflow
  version: 1.0.0

nodes:
  - id: step1
    name: Step 1
    prompt: Do something
""")

        flows = scan_flows(tmp_path)

        assert isinstance(flows, list)
        assert len(flows) == 1
        assert isinstance(flows[0], FlowInfo)

    def test_scan_flows_extracts_metadata(self, tmp_path):
        """scan_flows() extracts name, description from YAML."""
        flow_file = tmp_path / "auth-flow.yaml"
        flow_file.write_text("""workflow:
  name: auth-flow
  description: Authentication workflow
  version: 1.0.0

nodes:
  - id: validate
    name: Validate
    prompt: Validate user
""")

        flows = scan_flows(tmp_path)

        assert len(flows) == 1
        assert flows[0].name == "auth-flow"
        assert flows[0].description == "Authentication workflow"
        assert flows[0].file_path == flow_file

    def test_scan_flows_handles_multiple_files(self, tmp_path):
        """scan_flows() finds all YAML files in directory."""
        # Create multiple flow files
        for i in range(3):
            flow_file = tmp_path / f"flow-{i}.yaml"
            flow_file.write_text(f"""workflow:
  name: flow-{i}
  description: Flow {i}
  version: 1.0.0

nodes:
  - id: step
    name: Step
    prompt: Do something
""")

        flows = scan_flows(tmp_path)

        assert len(flows) == 3
        names = {f.name for f in flows}
        assert names == {"flow-0", "flow-1", "flow-2"}

    def test_scan_flows_empty_directory(self, tmp_path):
        """scan_flows() returns empty list for empty directory."""
        flows = scan_flows(tmp_path)
        assert flows == []

    def test_scan_flows_skips_malformed_yaml(self, tmp_path):
        """scan_flows() skips files with invalid YAML."""
        # Good file
        good_file = tmp_path / "good.yaml"
        good_file.write_text("""workflow:
  name: good
  description: Good workflow
  version: 1.0.0

nodes:
  - id: step
    name: Step
    prompt: Do something
""")

        # Bad file
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("{ invalid yaml [[[")

        flows = scan_flows(tmp_path)

        assert len(flows) == 1
        assert flows[0].name == "good"

    def test_scan_flows_extracts_node_count(self, tmp_path):
        """scan_flows() counts nodes in workflow."""
        flow_file = tmp_path / "multi-node.yaml"
        flow_file.write_text("""workflow:
  name: multi-node
  description: Multi-node workflow
  version: 1.0.0

nodes:
  - id: step1
    name: Step 1
    prompt: Do first thing
  - id: step2
    name: Step 2
    prompt: Do second thing
  - id: step3
    name: Step 3
    prompt: Do third thing
""")

        flows = scan_flows(tmp_path)

        assert len(flows) == 1
        assert flows[0].node_count == 3

    def test_scan_flows_handles_missing_description(self, tmp_path):
        """scan_flows() handles workflows without description."""
        flow_file = tmp_path / "no-desc.yaml"
        flow_file.write_text("""workflow:
  name: no-desc
  version: 1.0.0

nodes:
  - id: step
    name: Step
    prompt: Do something
""")

        flows = scan_flows(tmp_path)

        assert len(flows) == 1
        assert flows[0].name == "no-desc"
        assert flows[0].description == ""


class TestFlowInfoDataclass:
    """Tests for FlowInfo dataclass."""

    def test_flow_info_has_required_fields(self):
        """FlowInfo has name, description, file_path fields."""
        info = FlowInfo(
            name="test",
            description="Test flow",
            file_path=Path("test.yaml"),
            node_count=1,
        )

        assert info.name == "test"
        assert info.description == "Test flow"
        assert info.file_path == Path("test.yaml")
        assert info.node_count == 1


class TestSimilarityCheck:
    """Tests for AI-based similarity checking (Phase 4.2)."""

    @pytest.mark.asyncio
    async def test_check_similarity_returns_none_for_no_match(self, tmp_path):
        """check_similarity() returns None when no similar flows exist."""
        from amplifier.flow_builder.flow_discovery import check_similarity

        # Create dissimilar flow
        flow_file = tmp_path / "auth.yaml"
        flow_file.write_text("""workflow:
  name: auth
  description: Authenticate users
  version: 1.0.0

nodes:
  - id: validate
    name: Validate
    prompt: Validate credentials
""")

        flows = scan_flows(tmp_path)
        user_goal = "Generate documentation for API endpoints"

        similar = await check_similarity(user_goal, flows)

        assert similar is None

    @pytest.mark.asyncio
    async def test_check_similarity_detects_obvious_duplicate(self, tmp_path):
        """check_similarity() detects when user goal matches existing flow."""
        from amplifier.flow_builder.flow_discovery import check_similarity

        # Create flow about authentication
        flow_file = tmp_path / "auth.yaml"
        flow_file.write_text("""workflow:
  name: auth
  description: Implement user authentication with JWT tokens
  version: 1.0.0

nodes:
  - id: implement
    name: Implement
    prompt: Implement auth
""")

        flows = scan_flows(tmp_path)
        user_goal = "I need to add JWT authentication to my app"

        similar = await check_similarity(user_goal, flows)

        assert similar is not None
        assert similar.name == "auth"

    @pytest.mark.asyncio
    async def test_check_similarity_handles_empty_flow_list(self):
        """check_similarity() handles empty flow list gracefully."""
        from amplifier.flow_builder.flow_discovery import check_similarity

        similar = await check_similarity("Do something", [])

        assert similar is None

    @pytest.mark.asyncio
    async def test_check_similarity_uses_ai_for_semantic_match(self, tmp_path):
        """check_similarity() uses AI to detect semantic similarities."""
        from amplifier.flow_builder.flow_discovery import check_similarity

        # Flow about code review
        flow_file = tmp_path / "review.yaml"
        flow_file.write_text("""workflow:
  name: review
  description: Analyze code quality and suggest improvements
  version: 1.0.0

nodes:
  - id: analyze
    name: Analyze
    prompt: Review code
""")

        flows = scan_flows(tmp_path)
        # Semantically similar but different wording
        user_goal = "Check my code for bugs and best practices"

        similar = await check_similarity(user_goal, flows)

        # Should detect semantic similarity
        assert similar is not None
        assert similar.name == "review"

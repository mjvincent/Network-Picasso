from __future__ import annotations

from network_picasso.drawio import render_multipage_drawio
from network_picasso.style_memory import extract_style_memory, style_memory_markdown, style_memory_prompt


def test_extract_style_memory_creates_prompt_ready_preferences():
    architecture = {
        "project": {"name": "Style Memory Test", "environment": "Production"},
        "render_plan": {"pattern": "vsi-vpc"},
        "ibm_cloud": {
            "regions": [{"name": "us-south"}],
            "vpcs": [{"name": "Production VPC"}],
            "compute": [{"name": "Application VSI"}],
            "connectivity": [{"name": "Direct Link"}],
        },
    }
    xml = render_multipage_drawio(architecture)

    memory = extract_style_memory(xml, name="Seller preferred style")

    assert memory["schemaVersion"] == 1
    assert memory["name"] == "Seller preferred style"
    assert memory["metrics"]["pageCount"] == 5
    assert "Deployment" in memory["pageOrder"]
    assert memory["preferences"]["connectorRouting"].startswith("orthogonal")
    assert any("service labels" in item for item in memory["promptGuidance"])
    assert "Saved Draw.io style memory" in style_memory_prompt(memory)
    assert "Preferred Guidance" in style_memory_markdown(memory)

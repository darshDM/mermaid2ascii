"""Basic smoke tests. Run with: python -m unittest discover -s tests"""
import unittest

from mermaid_ascii import DiagramType, MermaidParseError, UnsupportedDiagramError, convert
from mermaid_ascii.detector import detect_diagram_type
from mermaid_ascii.models import Direction, EdgeStyle, NodeShape
from mermaid_ascii.parsers.factory import ParserFactory


class DetectorTests(unittest.TestCase):
    def test_flowchart_keyword(self):
        self.assertEqual(detect_diagram_type("flowchart TD\nA-->B"), DiagramType.FLOWCHART)

    def test_graph_keyword(self):
        self.assertEqual(detect_diagram_type("graph LR\nA-->B"), DiagramType.FLOWCHART)

    def test_bare_edges_fall_back_to_flowchart(self):
        self.assertEqual(detect_diagram_type("A --> B"), DiagramType.FLOWCHART)

    def test_unknown_type(self):
        self.assertEqual(detect_diagram_type("sequenceDiagram\nA->>B: hi"), DiagramType.SEQUENCE)

    def test_empty_input_raises(self):
        with self.assertRaises(MermaidParseError):
            detect_diagram_type("   ")


class FlowchartParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = ParserFactory.get_parser(DiagramType.FLOWCHART)

    def test_direction_parsed(self):
        graph = self.parser.parse("flowchart LR\nA-->B")
        self.assertEqual(graph.direction, Direction.LEFT_RIGHT)

    def test_default_direction(self):
        graph = self.parser.parse("A-->B")
        self.assertEqual(graph.direction, Direction.TOP_DOWN)

    def test_node_shapes(self):
        graph = self.parser.parse(
            "flowchart TD\n"
            "A[Rect] --> B(Round)\n"
            "B --> C{Diamond}\n"
            "C --> D((Circle))\n"
            "D --> E([Stadium])\n"
            "E --> F[[Sub]]\n"
            "F --> G[(Cyl)]\n"
        )
        self.assertEqual(graph.get_node("A").shape, NodeShape.RECTANGLE)
        self.assertEqual(graph.get_node("B").shape, NodeShape.ROUNDED)
        self.assertEqual(graph.get_node("C").shape, NodeShape.RHOMBUS)
        self.assertEqual(graph.get_node("D").shape, NodeShape.CIRCLE)
        self.assertEqual(graph.get_node("E").shape, NodeShape.STADIUM)
        self.assertEqual(graph.get_node("F").shape, NodeShape.SUBROUTINE)
        self.assertEqual(graph.get_node("G").shape, NodeShape.CYLINDER)

    def test_edge_label_pipe_syntax(self):
        graph = self.parser.parse("flowchart TD\nA -->|Yes| B")
        self.assertEqual(graph.edges[0].label, "Yes")

    def test_edge_label_inline_syntax(self):
        graph = self.parser.parse("flowchart TD\nA -- Yes --> B")
        self.assertEqual(graph.edges[0].label, "Yes")

    def test_edge_styles(self):
        graph = self.parser.parse(
            "flowchart TD\nA-->B\nB---C\nC-.->D\nD==>E\n"
        )
        styles = [e.style for e in graph.edges]
        self.assertEqual(styles, [
            EdgeStyle.SOLID, EdgeStyle.OPEN, EdgeStyle.DOTTED, EdgeStyle.THICK,
        ])

    def test_chained_edges(self):
        graph = self.parser.parse("flowchart TD\nA --> B --> C")
        self.assertEqual(len(graph.edges), 2)
        self.assertEqual(len(graph.nodes), 3)

    def test_subgraph_lines_ignored_but_nodes_kept(self):
        graph = self.parser.parse(
            "flowchart TD\nsubgraph S1\nA-->B\nend\nB-->C\n"
        )
        self.assertIn("A", graph.nodes)
        self.assertIn("C", graph.nodes)

    def test_empty_input_raises(self):
        with self.assertRaises(MermaidParseError):
            self.parser.parse("")

    def test_no_nodes_raises(self):
        with self.assertRaises(MermaidParseError):
            self.parser.parse("flowchart TD\n%% just a comment\n")


class ConvertEndToEndTests(unittest.TestCase):
    def test_simple_flowchart_renders_nonempty(self):
        out = convert("flowchart TD\nA[Start]-->B{Ok?}\nB-->|Yes|C[Done]\nB-->|No|A")
        self.assertIn("Start", out)
        self.assertIn("Done", out)
        self.assertIn("Ok?", out)

    def test_unsupported_diagram_raises(self):
        with self.assertRaises(UnsupportedDiagramError):
            convert("classDiagram\nAnimal <|-- Duck")

    def test_left_right_direction_is_wider_than_tall(self):
        out = convert("flowchart LR\nA[One]-->B[Two]-->C[Three]")
        lines = out.splitlines()
        self.assertGreater(max(len(l) for l in lines), len(lines))

    def test_cycle_does_not_crash(self):
        out = convert("flowchart TD\nA-->B\nB-->A")
        self.assertIn("A", out)
        self.assertIn("B", out)

    def test_all_node_labels_present_in_output(self):
        out = convert(
            "flowchart TD\n"
            "A[Client] --> B[Load Balancer]\n"
            "B --> C[Server One]\n"
            "B --> D[Server Two]\n"
            "C --> E[(Database)]\n"
            "D --> E\n"
        )
        for label in ("Client", "Load Balancer", "Server One", "Server Two", "Database"):
            self.assertIn(label, out)

    def test_max_width_tightens_spacing(self):
        source = (
            "flowchart TD\n"
            "A{Route} --> B[Authentication Service]\n"
            "A --> C[Billing Service]\n"
            "A --> D[Inventory Service]\n"
            "A --> E[Shipping Service]\n"
            "A --> F[Notification Service]\n"
        )
        loose = convert(source)
        tight = convert(source, max_width=60)
        loose_width = max(len(l) for l in loose.splitlines())
        tight_width = max(len(l) for l in tight.splitlines())
        self.assertLess(tight_width, loose_width)

    def test_direction_override(self):
        out_td = convert("flowchart TD\nA-->B-->C")
        out_lr = convert("flowchart TD\nA-->B-->C", direction="LR")
        # forcing LR should make it wider-than-tall relative to the TD version
        td_lines = out_td.splitlines()
        lr_lines = out_lr.splitlines()
        self.assertGreater(len(td_lines), len(lr_lines))

    def test_dense_pipeline_with_rollback_loops_does_not_corrupt_boxes(self):
        # Regression test: a layer with several stacked/side-by-side
        # siblings plus multiple back-edges (rollback loops) used to have
        # detour routing cut straight through sibling boxes, replacing
        # part of their text with line-drawing characters.
        source = (
            "flowchart LR\n"
            "A[Commit] --> B[Lint]\n"
            "A --> C[Unit Tests]\n"
            "A --> D[Static Analysis]\n"
            "B --> E{Checks pass?}\n"
            "C --> E\n"
            "D --> E\n"
            "E -->|No| F[Notify Dev]\n"
            "F --> A\n"
            "E -->|Yes| G[Build Image]\n"
            "G --> H[Container Scan]\n"
            "H -->|Vuln found| F\n"
            "H -->|Clean| I[Push Registry]\n"
            "I --> J[Deploy Staging]\n"
            "J --> K[Smoke Tests]\n"
            "K -->|Fail| L[Rollback Staging]\n"
            "L --> J\n"
            "K -->|Pass| M[Deploy Production]\n"
            "M --> N[Monitor]\n"
            "N -->|Errors spike| O[Rollback Production]\n"
            "O --> M\n"
        )
        out = convert(source)
        for label in (
            "Commit", "Lint", "Unit Tests", "Static Analysis", "Notify Dev",
            "Build Image", "Container Scan", "Push Registry", "Deploy Staging",
            "Smoke Tests", "Rollback Staging", "Deploy Production", "Monitor",
            "Rollback", "Production",
        ):
            self.assertIn(label, out, f"{label!r} was corrupted or missing from output")


if __name__ == "__main__":
    unittest.main()

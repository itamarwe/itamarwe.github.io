"""
EON — Making organizational data AI-queryable
A 3b1b/Manim-style loopable explainer of the four layers:
    1. Joinability detection
    2. Semantic analysis by LLM
    3. RAG over tables
    4. NL -> SQL

Render:
    pip install manim

  # 16:9 — Twitter / X / YouTube — 1920x1080
    manim -qh eon_layers_manim.py EONLayers

  # 4:5 — LinkedIn feed — 1080x1350
    manim --resolution 1080,1350 -qm eon_layers_manim.py EONLayersTall

The scene fades to black at the start and end, so it loops cleanly.
"""

from manim import *
import numpy as np

# 3b1b-ish palette
BG     = "#0E1116"
LIGHT  = "#E8E8E8"
GREY   = "#7A8090"
DIM    = "#3C4250"
BLUE   = "#58C4DD"
TEAL   = "#5CD0B3"
YELLOW = "#FFD866"
GREEN  = "#83C167"
RED    = "#FC6255"
PURPLE = "#9A72AC"
ORANGE = "#FF8E3C"


class EONLayers(Scene):
    def construct(self):
        self.camera.background_color = BG
        self.intro_title()
        self.layer1_joinability()
        self.layer2_semantic()
        self.layer3_rag()
        self.layer4_nl2sql()
        self.outro_loop()

    # ============================================================
    #  INTRO
    # ============================================================
    def intro_title(self):
        line1 = Text("Making organizational data", font_size=36, color=LIGHT)
        line2 = Text("AI-queryable", font_size=58, color=BLUE, weight=BOLD)
        line2.next_to(line1, DOWN, buff=0.35)
        sub = Text("four layers", font_size=20, color=GREY, slant=ITALIC)
        sub.next_to(line2, DOWN, buff=0.55)

        self.play(Write(line1), run_time=1.2)
        self.play(FadeIn(line2, shift=UP * 0.2), run_time=0.8)
        self.play(FadeIn(sub), run_time=0.4)
        self.wait(0.9)
        self.play(FadeOut(VGroup(line1, line2, sub)), run_time=0.7)

    # ============================================================
    #  LAYER 1 — JOINABILITY DETECTION
    # ============================================================
    def layer1_joinability(self):
        header = self._header(1, "Joinability detection", BLUE)
        self.play(FadeIn(header, shift=DOWN * 0.2), run_time=0.5)

        tbl_a = self._mini_table(
            "RDS · users",
            [("id", "u_8f2a91…"), ("email", "ada@x.com"), ("name", "Ada")],
            BLUE,
        ).shift(LEFT * 3.7 + UP * 0.2)

        tbl_b = self._mini_table(
            "Mongo · events",
            [("userId", "u_8f2a91…"), ("ts", "1717…"), ("kind", "click")],
            PURPLE,
        ).shift(RIGHT * 3.7 + UP * 0.2)

        self.play(FadeIn(tbl_a, shift=RIGHT * 0.3), FadeIn(tbl_b, shift=LEFT * 0.3))
        self.wait(0.4)

        # The naive LLM-only mistake
        guess = Text(
            '"both look like UUIDs → join?"',
            font_size=18, color=GREY, slant=ITALIC,
        ).next_to(VGroup(tbl_a, tbl_b), DOWN, buff=0.55)
        cross = Cross(scale_factor=0.18).set_color(RED).set_stroke(width=5)
        cross.next_to(guess, RIGHT, buff=0.25)
        self.play(FadeIn(guess))
        self.play(Create(cross))
        self.wait(0.7)
        self.play(FadeOut(guess), FadeOut(cross))

        # Min-hash sketches
        sketch_a = self._sketch_row([1, 0, 1, 1, 0, 1, 0, 1, 1, 0], BLUE)
        sketch_b = self._sketch_row([1, 0, 1, 1, 0, 1, 1, 1, 1, 0], PURPLE)
        sketch_a.next_to(tbl_a, DOWN, buff=0.55)
        sketch_b.next_to(tbl_b, DOWN, buff=0.55)
        lbl_a = Text("min-hash(id)", font_size=14, color=GREY).next_to(sketch_a, DOWN, buff=0.15)
        lbl_b = Text("min-hash(userId)", font_size=14, color=GREY).next_to(sketch_b, DOWN, buff=0.15)

        self.play(
            LaggedStart(
                FadeIn(sketch_a), FadeIn(sketch_b),
                FadeIn(lbl_a),    FadeIn(lbl_b),
                lag_ratio=0.15,
            )
        )
        self.wait(0.4)

        # Compare → overlap
        arrow = DoubleArrow(
            sketch_a.get_right(), sketch_b.get_left(),
            color=YELLOW, buff=0.3, stroke_width=4, tip_length=0.18,
        )
        self.play(GrowArrow(arrow))

        overlap = Text("≈ 0.94 Jaccard", font_size=28, color=GREEN, weight=BOLD)
        overlap.next_to(arrow, DOWN, buff=0.45)
        evidence = Text(
            "physical overlap, not a guess",
            font_size=14, color=GREY, slant=ITALIC,
        ).next_to(overlap, DOWN, buff=0.1)

        self.play(Write(overlap), FadeIn(evidence))
        self.wait(1.5)

        self.play(
            *[
                FadeOut(m)
                for m in [
                    header, tbl_a, tbl_b, sketch_a, sketch_b,
                    lbl_a, lbl_b, arrow, overlap, evidence,
                ]
            ],
            run_time=0.7,
        )

    # ============================================================
    #  LAYER 2 — SEMANTIC ANALYSIS BY LLM
    # ============================================================
    def layer2_semantic(self):
        header = self._header(2, "Semantic analysis", TEAL)
        self.play(FadeIn(header, shift=DOWN * 0.2), run_time=0.5)

        tbl = self._mini_table(
            "orders_2024",
            [("oid", "9f2b…"), ("uid", "u_8f2a…"), ("amt", "42.10"), ("flag", "P")],
            TEAL,
        ).shift(LEFT * 4.0 + DOWN * 0.2)
        self.play(FadeIn(tbl, shift=RIGHT * 0.3))

        # Inputs feeding the LLM
        inputs = VGroup(
            Text("• column names",       font_size=16, color=LIGHT),
            Text("• sampled rows",       font_size=16, color=LIGHT),
            Text("• source: postgres",   font_size=16, color=LIGHT),
            Text("• joinability hints",  font_size=16, color=YELLOW),
        ).arrange(DOWN, buff=0.18, aligned_edge=LEFT)
        inputs.next_to(tbl, RIGHT, buff=1.0)

        self.play(
            LaggedStart(*[FadeIn(t, shift=RIGHT * 0.2) for t in inputs], lag_ratio=0.18)
        )
        self.wait(0.3)

        brain = self._llm_node(TEAL).shift(RIGHT * 2.6 + DOWN * 0.2)
        self.play(FadeIn(brain, scale=0.7))

        arrow_in = Arrow(
            inputs.get_right(), brain.get_left(),
            color=GREY, buff=0.25, stroke_width=3, tip_length=0.18,
        )
        self.play(GrowArrow(arrow_in))

        # Pulse
        self.play(brain[0].animate.set_stroke(color=YELLOW, width=5), run_time=0.35)
        self.play(brain[0].animate.set_stroke(color=TEAL, width=3),   run_time=0.35)

        # Output description
        out = VGroup(
            Text("oid  → order primary key",   font_size=14, color=LIGHT),
            Text("uid  → users.id (FK, 94%)",  font_size=14, color=YELLOW),
            Text("amt  → USD amount",          font_size=14, color=LIGHT),
            Text("flag → status enum P|S|C",   font_size=14, color=LIGHT),
        ).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
        out_box = SurroundingRectangle(out, color=TEAL, buff=0.25, stroke_width=2)
        out_group = VGroup(out_box, out).next_to(brain, DOWN, buff=0.55)

        arrow_out = Arrow(
            brain.get_bottom(), out_box.get_top(),
            color=GREY, buff=0.1, stroke_width=3, tip_length=0.18,
        )
        self.play(GrowArrow(arrow_out))
        self.play(FadeIn(out_group, shift=DOWN * 0.2))
        self.wait(1.6)

        self.play(
            *[FadeOut(m) for m in [header, tbl, inputs, brain, arrow_in, arrow_out, out_group]],
            run_time=0.7,
        )

    # ============================================================
    #  LAYER 3 — RAG OVER TABLES
    # ============================================================
    def layer3_rag(self):
        header = self._header(3, "RAG over tables", YELLOW)
        self.play(FadeIn(header, shift=DOWN * 0.2), run_time=0.5)

        sub = VGroup(
            Text("an index of ",   font_size=18, color=GREY),
            Text("tables",         font_size=18, color=LIGHT, weight=BOLD),
            Text(" — by ",         font_size=18, color=GREY),
            Text("meaning",        font_size=18, color=TEAL, weight=BOLD),
            Text(" + ",            font_size=18, color=GREY),
            Text("joinability",    font_size=18, color=BLUE, weight=BOLD),
        ).arrange(RIGHT, buff=0.05).next_to(header, DOWN, buff=0.3)
        self.play(FadeIn(sub))
        self.wait(0.3)

        # Many little table icons on the left
        np.random.seed(7)
        icons = VGroup()
        for _ in range(24):
            ic = Rectangle(width=0.36, height=0.26, color=GREY, stroke_width=1.5)
            line = Line(
                ic.get_left() + RIGHT * 0.05, ic.get_right() + LEFT * 0.05,
                color=GREY, stroke_width=1,
            ).shift(UP * 0.05)
            icons.add(VGroup(ic, line))
        icons.arrange_in_grid(rows=4, cols=6, buff=0.18)
        icons.shift(LEFT * 3.8 + DOWN * 0.4)
        self.play(LaggedStartMap(FadeIn, icons, lag_ratio=0.04), run_time=1.0)
        self.wait(0.2)

        # Embedding space on the right
        space_center = RIGHT * 3.3 + DOWN * 0.4
        guide = DashedVMobject(
            Circle(radius=2.0, color=DIM, stroke_width=1)
        ).move_to(space_center)
        guide_lbl = Text("table index", font_size=14, color=GREY).next_to(guide, UP, buff=0.15)
        self.play(Create(guide), FadeIn(guide_lbl))

        clusters = {
            BLUE:   space_center + np.array([-0.9,  0.7, 0]),
            PURPLE: space_center + np.array([ 0.9,  0.4, 0]),
            TEAL:   space_center + np.array([-0.3, -0.9, 0]),
            ORANGE: space_center + np.array([ 1.0, -0.7, 0]),
        }
        cluster_list = list(clusters.items())

        # Transform each icon into a coloured dot at its cluster
        anims = []
        dots = VGroup()
        for i, ic in enumerate(icons):
            color, center = cluster_list[i % len(cluster_list)]
            jitter = np.array(
                [np.random.uniform(-0.32, 0.32), np.random.uniform(-0.32, 0.32), 0]
            )
            target = Dot(center + jitter, color=color, radius=0.08)
            dots.add(target)
            anims.append(Transform(ic, target))
        self.play(LaggedStart(*anims, lag_ratio=0.03), run_time=1.6)
        self.wait(0.3)

        cluster_labels = VGroup(
            Text("users",   font_size=14, color=BLUE  ).move_to(clusters[BLUE]   + UP   * 0.55),
            Text("events",  font_size=14, color=PURPLE).move_to(clusters[PURPLE] + UP   * 0.45),
            Text("orders",  font_size=14, color=TEAL  ).move_to(clusters[TEAL]   + DOWN * 0.55),
            Text("billing", font_size=14, color=ORANGE).move_to(clusters[ORANGE] + DOWN * 0.55),
        )
        self.play(LaggedStartMap(FadeIn, cluster_labels, lag_ratio=0.15))
        self.wait(0.3)

        # Joinability edges *within* clusters — layer 1 carried through
        edges = VGroup()
        for color, center in clusters.items():
            members = [d for d in dots if np.linalg.norm(d.get_center() - center) < 0.55]
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    if np.random.random() < 0.45:
                        edges.add(
                            Line(
                                members[i].get_center(), members[j].get_center(),
                                color=YELLOW, stroke_width=1, stroke_opacity=0.55,
                            )
                        )
        self.play(LaggedStartMap(Create, edges, lag_ratio=0.04), run_time=0.8)
        self.wait(0.4)

        # Query arriving
        q_origin = LEFT * 3.8 + DOWN * 0.4
        q_label = Text(
            '"orders by user last month"',
            font_size=18, color=YELLOW, weight=BOLD,
        ).move_to(q_origin)
        self.play(Write(q_label))
        q_dot = Dot(q_origin, color=YELLOW, radius=0.12)
        self.play(FadeOut(q_label), FadeIn(q_dot))

        target_pt = clusters[TEAL] + np.array([0.1, 0.15, 0])
        path = CurvedArrow(q_origin, target_pt, color=YELLOW, angle=-PI / 4, stroke_width=2)
        self.play(Create(path), q_dot.animate.move_to(target_pt), run_time=1.2)

        # Highlight neighbours
        ring = Circle(radius=0.65, color=YELLOW, stroke_width=2).move_to(clusters[TEAL])
        self.play(Create(ring))
        nearby = [d for d in dots if np.linalg.norm(d.get_center() - clusters[TEAL]) < 0.55]
        if nearby:
            self.play(*[d.animate.scale(1.6) for d in nearby], run_time=0.4)
            self.play(*[d.animate.scale(1 / 1.6) for d in nearby], run_time=0.4)

        retrieved = Text(
            "tables to query →",
            font_size=16, color=YELLOW, weight=BOLD,
        ).next_to(ring, RIGHT, buff=0.3)
        self.play(FadeIn(retrieved, shift=LEFT * 0.2))
        self.wait(1.0)

        self.play(
            *[
                FadeOut(m)
                for m in [
                    header, sub, guide, guide_lbl, icons, dots,
                    cluster_labels, edges, q_dot, path, ring, retrieved,
                ]
            ],
            run_time=0.7,
        )

    # ============================================================
    #  LAYER 4 — NL → SQL
    # ============================================================
    def layer4_nl2sql(self):
        header = self._header(4, "NL → SQL", ORANGE)
        self.play(FadeIn(header, shift=DOWN * 0.2), run_time=0.5)

        q = Text(
            '"how many orders per user last month?"',
            font_size=22, color=YELLOW, weight=BOLD,
        )
        q.next_to(header, DOWN, buff=0.35)
        self.play(Write(q))
        self.wait(0.3)

        x_pos = [-4.2, 0.0, 4.2]

        step_labels = VGroup(
            Text("retrieve cluster", font_size=14, color=GREY).move_to([x_pos[0], 1.5, 0]),
            Text("join graph",       font_size=14, color=GREY).move_to([x_pos[1], 1.5, 0]),
            Text("generate SQL",     font_size=14, color=GREY).move_to([x_pos[2], 1.5, 0]),
        )

        # --- 1. Retrieved cluster (three small tables) ---
        cluster = VGroup(
            self._small_table("users",  BLUE),
            self._small_table("orders", TEAL),
            self._small_table("events", PURPLE),
        ).arrange(DOWN, buff=0.28).move_to([x_pos[0], -1.0, 0])
        self.play(FadeIn(step_labels[0]), LaggedStartMap(FadeIn, cluster, lag_ratio=0.2))
        self.wait(0.3)

        # --- 2. Join graph ---
        node_u = Circle(radius=0.32, color=BLUE,   stroke_width=3).move_to([x_pos[1] - 0.9, -0.6, 0])
        node_o = Circle(radius=0.32, color=TEAL,   stroke_width=3).move_to([x_pos[1] + 0.9, -0.6, 0])
        node_e = Circle(radius=0.32, color=PURPLE, stroke_width=3).move_to([x_pos[1],      -1.8, 0])
        lbl_u = Text("u", font_size=14, color=BLUE  ).move_to(node_u)
        lbl_o = Text("o", font_size=14, color=TEAL  ).move_to(node_o)
        lbl_e = Text("e", font_size=14, color=PURPLE).move_to(node_e)

        edge_uo = Line(node_u.get_right(),  node_o.get_left(), color=YELLOW, stroke_width=4)
        edge_ue = Line(node_u.get_bottom(), node_e.get_top(),  color=YELLOW, stroke_width=2)
        edge_oe = Line(node_o.get_bottom(), node_e.get_top(),  color=GREY,   stroke_width=2)

        edge_lbl_uo = Text("0.94", font_size=12, color=YELLOW).next_to(edge_uo, UP,    buff=0.05)
        edge_lbl_ue = Text("0.71", font_size=11, color=YELLOW).next_to(edge_ue, LEFT,  buff=0.05)
        edge_lbl_oe = Text("0.12", font_size=11, color=GREY  ).next_to(edge_oe, RIGHT, buff=0.05)

        self.play(
            FadeIn(step_labels[1]),
            FadeIn(VGroup(node_u, node_o, node_e, lbl_u, lbl_o, lbl_e)),
        )
        self.play(Create(edge_uo), Create(edge_ue), Create(edge_oe))
        self.play(FadeIn(VGroup(edge_lbl_uo, edge_lbl_ue, edge_lbl_oe)))
        self.wait(0.4)

        # --- 3. Generated SQL ---
        sql = VGroup(
            Text("SELECT u.id,",               font_size=16, color=LIGHT),
            Text("       count(*) AS orders",  font_size=16, color=LIGHT),
            Text("FROM users u",               font_size=16, color=LIGHT),
            Text("JOIN orders o",              font_size=16, color=LIGHT),
            Text("  ON o.uid = u.id",          font_size=16, color=YELLOW),
            Text("WHERE o.ts > now()-30d",     font_size=16, color=LIGHT),
            Text("GROUP BY u.id;",             font_size=16, color=LIGHT),
        ).arrange(DOWN, buff=0.08, aligned_edge=LEFT)
        sql_box = SurroundingRectangle(sql, color=ORANGE, buff=0.25, stroke_width=2)
        sql_group = VGroup(sql_box, sql).move_to([x_pos[2], -1.1, 0])

        self.play(FadeIn(step_labels[2]), FadeIn(sql_group, shift=UP * 0.2))
        self.wait(0.3)

        # Connecting arrows
        arrow1 = Arrow([x_pos[0] + 1.0, -1.0, 0], [x_pos[1] - 1.5, -1.0, 0],
                       color=GREY, stroke_width=2, tip_length=0.15)
        arrow2 = Arrow([x_pos[1] + 1.5, -1.0, 0], [x_pos[2] - 1.7, -1.0, 0],
                       color=GREY, stroke_width=2, tip_length=0.15)
        self.play(GrowArrow(arrow1), GrowArrow(arrow2))
        self.wait(0.7)

        conf = Text("user confirms cluster ✓", font_size=16, color=GREEN, weight=BOLD)
        conf.next_to(sql_group, DOWN, buff=0.45)
        self.play(FadeIn(conf, shift=UP * 0.2))
        self.wait(1.5)

        self.play(
            *[
                FadeOut(m)
                for m in [
                    header, q, step_labels, cluster,
                    node_u, node_o, node_e, lbl_u, lbl_o, lbl_e,
                    edge_uo, edge_ue, edge_oe,
                    edge_lbl_uo, edge_lbl_ue, edge_lbl_oe,
                    arrow1, arrow2, sql_group, conf,
                ]
            ],
            run_time=0.8,
        )

    # ============================================================
    #  OUTRO — recap + loop point
    # ============================================================
    def outro_loop(self):
        layers = VGroup(
            Text("1  joinability", font_size=24, color=BLUE),
            Text("2  semantic",    font_size=24, color=TEAL),
            Text("3  RAG",         font_size=24, color=YELLOW),
            Text("4  NL → SQL",    font_size=24, color=ORANGE),
        ).arrange(DOWN, buff=0.3, aligned_edge=LEFT)
        layers.move_to(ORIGIN)

        self.play(LaggedStartMap(FadeIn, layers, lag_ratio=0.2))
        self.wait(1.3)
        self.play(FadeOut(layers), run_time=1.0)
        # Hold black for a beat — the next iteration of intro_title fades in from the same black
        self.wait(0.3)

    # ============================================================
    #  small helpers
    # ============================================================
    def _header(self, n, label, color):
        num = Text(f"0{n}", font_size=22, color=color, weight=BOLD)
        bar = Line(ORIGIN, RIGHT * 0.35, color=color, stroke_width=3)\
              .next_to(num, RIGHT, buff=0.25)
        txt = Text(label, font_size=30, color=LIGHT).next_to(bar, RIGHT, buff=0.25)
        return VGroup(num, bar, txt).to_edge(UP, buff=0.5)

    def _mini_table(self, title, rows, accent):
        t = Text(title, font_size=18, color=accent, weight=BOLD)
        items = VGroup()
        for col, val in rows:
            row = VGroup(
                Text(col, font_size=15, color=LIGHT),
                Text(val, font_size=13, color=GREY),
            ).arrange(RIGHT, buff=0.5)
            items.add(row)
        items.arrange(DOWN, buff=0.14, aligned_edge=LEFT)
        items.next_to(t, DOWN, buff=0.22, aligned_edge=LEFT)
        box = SurroundingRectangle(
            VGroup(t, items), color=accent, buff=0.28, stroke_width=2
        )
        return VGroup(box, t, items)

    def _sketch_row(self, bits, color):
        cells = VGroup()
        for b in bits:
            cells.add(
                Square(
                    side_length=0.22,
                    color=color,
                    fill_opacity=(1.0 if b else 0.0),
                    stroke_width=1,
                )
            )
        cells.arrange(RIGHT, buff=0.04)
        return cells

    def _llm_node(self, color):
        outer = RegularPolygon(n=6, color=color, stroke_width=3).scale(0.85)
        inner = Text("LLM", font_size=20, color=color, weight=BOLD).move_to(outer)
        return VGroup(outer, inner)

    def _small_table(self, name, color):
        rect = Rectangle(width=1.4, height=0.55, color=color, stroke_width=2)
        line = Line(
            rect.get_left() + RIGHT * 0.1, rect.get_right() + LEFT * 0.1,
            color=color, stroke_width=1,
        ).shift(UP * 0.1)
        lbl = Text(name, font_size=14, color=color).move_to(
            rect.get_center() + DOWN * 0.1
        )
        return VGroup(rect, line, lbl)


# ================================================================
#  4:5 vertical variant for LinkedIn (1080x1350)
# ================================================================
class EONLayersTall(EONLayers):
    """
    Re-flows every layer to fit a tall 4:5 frame (≈ 6.4 wide × 8 tall in
    scene units when rendered at 1080×1350). All helpers and the intro /
    outro are inherited from EONLayers because they're already centered.
    """

    # ---------- LAYER 1 (vertical) ----------
    def layer1_joinability(self):
        header = self._header(1, "Joinability", BLUE)
        self.play(FadeIn(header, shift=DOWN * 0.2), run_time=0.5)

        tbl_a = self._mini_table(
            "RDS · users",
            [("id", "u_8f2a91…"), ("email", "ada@x.com"), ("name", "Ada")],
            BLUE,
        ).move_to([0, 2.5, 0])

        tbl_b = self._mini_table(
            "Mongo · events",
            [("userId", "u_8f2a91…"), ("ts", "1717…"), ("kind", "click")],
            PURPLE,
        ).move_to([0, -2.5, 0])

        self.play(FadeIn(tbl_a, shift=DOWN * 0.3), FadeIn(tbl_b, shift=UP * 0.3))
        self.wait(0.4)

        # Naive guess between the two tables
        guess = Text('"both look like UUIDs → join?"',
                     font_size=16, color=GREY, slant=ITALIC).move_to([0, 1.1, 0])
        cross = Cross(scale_factor=0.16).set_color(RED).set_stroke(width=5)
        cross.next_to(guess, RIGHT, buff=0.2)
        self.play(FadeIn(guess))
        self.play(Create(cross))
        self.wait(0.7)
        self.play(FadeOut(guess), FadeOut(cross))

        # Min-hash sketches stacked vertically
        sketch_a = self._sketch_row([1, 0, 1, 1, 0, 1, 0, 1, 1, 0], BLUE).move_to([0.6, 1.1, 0])
        sketch_b = self._sketch_row([1, 0, 1, 1, 0, 1, 1, 1, 1, 0], PURPLE).move_to([0.6, -1.1, 0])
        lbl_a = Text("min-hash(id)",     font_size=13, color=GREY).next_to(sketch_a, LEFT, buff=0.18)
        lbl_b = Text("min-hash(userId)", font_size=13, color=GREY).next_to(sketch_b, LEFT, buff=0.18)

        self.play(
            LaggedStart(
                FadeIn(sketch_a), FadeIn(sketch_b),
                FadeIn(lbl_a), FadeIn(lbl_b),
                lag_ratio=0.15,
            )
        )
        self.wait(0.4)

        arrow = DoubleArrow(
            sketch_a.get_bottom(), sketch_b.get_top(),
            color=YELLOW, buff=0.2, stroke_width=4, tip_length=0.18,
        )
        self.play(GrowArrow(arrow))

        overlap = Text("≈ 0.94 Jaccard", font_size=22, color=GREEN, weight=BOLD)
        overlap.next_to(arrow, RIGHT, buff=0.35)
        evidence = Text(
            "physical overlap,\nnot a guess",
            font_size=12, color=GREY, slant=ITALIC,
        ).next_to(overlap, DOWN, buff=0.15, aligned_edge=LEFT)

        self.play(Write(overlap), FadeIn(evidence))
        self.wait(1.4)

        self.play(
            *[FadeOut(m) for m in [
                header, tbl_a, tbl_b, sketch_a, sketch_b,
                lbl_a, lbl_b, arrow, overlap, evidence,
            ]],
            run_time=0.7,
        )

    # ---------- LAYER 2 (vertical) ----------
    def layer2_semantic(self):
        header = self._header(2, "Semantic analysis", TEAL)
        self.play(FadeIn(header, shift=DOWN * 0.2), run_time=0.5)

        tbl = self._mini_table(
            "orders_2024",
            [("oid", "9f2b…"), ("uid", "u_8f2a…"), ("amt", "42.10"), ("flag", "P")],
            TEAL,
        ).move_to([-1.6, 2.4, 0])

        inputs = VGroup(
            Text("• column names",      font_size=14, color=LIGHT),
            Text("• sampled rows",      font_size=14, color=LIGHT),
            Text("• source: postgres",  font_size=14, color=LIGHT),
            Text("• joinability hints", font_size=14, color=YELLOW),
        ).arrange(DOWN, buff=0.14, aligned_edge=LEFT).move_to([1.6, 2.4, 0])

        self.play(FadeIn(tbl, shift=DOWN * 0.2))
        self.play(LaggedStart(*[FadeIn(t, shift=LEFT * 0.2) for t in inputs], lag_ratio=0.18))
        self.wait(0.3)

        brain = self._llm_node(TEAL).scale(0.85).move_to([0, 0.4, 0])
        arrow_l = Arrow(tbl.get_bottom(),    brain.get_top() + LEFT * 0.4,
                        color=GREY, buff=0.15, stroke_width=3, tip_length=0.15)
        arrow_r = Arrow(inputs.get_bottom(), brain.get_top() + RIGHT * 0.4,
                        color=GREY, buff=0.15, stroke_width=3, tip_length=0.15)

        self.play(FadeIn(brain, scale=0.7))
        self.play(GrowArrow(arrow_l), GrowArrow(arrow_r))

        self.play(brain[0].animate.set_stroke(color=YELLOW, width=5), run_time=0.35)
        self.play(brain[0].animate.set_stroke(color=TEAL,   width=3), run_time=0.35)

        out = VGroup(
            Text("oid  → order primary key",   font_size=13, color=LIGHT),
            Text("uid  → users.id (FK, 94%)",  font_size=13, color=YELLOW),
            Text("amt  → USD amount",          font_size=13, color=LIGHT),
            Text("flag → status enum P|S|C",   font_size=13, color=LIGHT),
        ).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
        out_box = SurroundingRectangle(out, color=TEAL, buff=0.22, stroke_width=2)
        out_group = VGroup(out_box, out).move_to([0, -2.3, 0])

        arrow_out = Arrow(brain.get_bottom(), out_box.get_top(),
                          color=GREY, buff=0.1, stroke_width=3, tip_length=0.18)
        self.play(GrowArrow(arrow_out))
        self.play(FadeIn(out_group, shift=DOWN * 0.2))
        self.wait(1.6)

        self.play(
            *[FadeOut(m) for m in [
                header, tbl, inputs, brain, arrow_l, arrow_r, arrow_out, out_group,
            ]],
            run_time=0.7,
        )

    # ---------- LAYER 3 (vertical) ----------
    def layer3_rag(self):
        header = self._header(3, "RAG over tables", YELLOW)
        self.play(FadeIn(header, shift=DOWN * 0.2), run_time=0.5)

        sub = VGroup(
            Text("an index of ",   font_size=15, color=GREY),
            Text("tables",         font_size=15, color=LIGHT, weight=BOLD),
            Text(" — by ",         font_size=15, color=GREY),
            Text("meaning",        font_size=15, color=TEAL, weight=BOLD),
            Text(" + ",            font_size=15, color=GREY),
            Text("joinability",    font_size=15, color=BLUE, weight=BOLD),
        ).arrange(RIGHT, buff=0.05).next_to(header, DOWN, buff=0.25)
        self.play(FadeIn(sub))
        self.wait(0.3)

        np.random.seed(7)
        icons = VGroup()
        for _ in range(24):
            ic = Rectangle(width=0.30, height=0.22, color=GREY, stroke_width=1.5)
            line = Line(
                ic.get_left() + RIGHT * 0.04, ic.get_right() + LEFT * 0.04,
                color=GREY, stroke_width=1,
            ).shift(UP * 0.04)
            icons.add(VGroup(ic, line))
        icons.arrange_in_grid(rows=3, cols=8, buff=0.16)
        icons.move_to([0, 1.9, 0])
        self.play(LaggedStartMap(FadeIn, icons, lag_ratio=0.04), run_time=1.0)
        self.wait(0.2)

        # Embedding / index space at the bottom
        space_center = np.array([0, -1.6, 0])
        guide = DashedVMobject(
            Circle(radius=1.8, color=DIM, stroke_width=1)
        ).move_to(space_center)
        guide_lbl = Text("table index", font_size=13, color=GREY).next_to(guide, UP, buff=0.12)
        self.play(Create(guide), FadeIn(guide_lbl))

        clusters = {
            BLUE:   space_center + np.array([-0.8,  0.65, 0]),
            PURPLE: space_center + np.array([ 0.8,  0.35, 0]),
            TEAL:   space_center + np.array([-0.3, -0.85, 0]),
            ORANGE: space_center + np.array([ 0.9, -0.65, 0]),
        }
        cluster_list = list(clusters.items())

        anims, dots = [], VGroup()
        for i, ic in enumerate(icons):
            color, center = cluster_list[i % len(cluster_list)]
            jitter = np.array([np.random.uniform(-0.28, 0.28),
                               np.random.uniform(-0.28, 0.28), 0])
            target = Dot(center + jitter, color=color, radius=0.07)
            dots.add(target)
            anims.append(Transform(ic, target))
        self.play(LaggedStart(*anims, lag_ratio=0.03), run_time=1.6)
        self.wait(0.3)

        cluster_labels = VGroup(
            Text("users",   font_size=12, color=BLUE  ).move_to(clusters[BLUE]   + UP   * 0.45),
            Text("events",  font_size=12, color=PURPLE).move_to(clusters[PURPLE] + UP   * 0.4),
            Text("orders",  font_size=12, color=TEAL  ).move_to(clusters[TEAL]   + DOWN * 0.45),
            Text("billing", font_size=12, color=ORANGE).move_to(clusters[ORANGE] + DOWN * 0.45),
        )
        self.play(LaggedStartMap(FadeIn, cluster_labels, lag_ratio=0.15))
        self.wait(0.25)

        # Joinability edges within clusters — layer 1 carried through
        edges = VGroup()
        for color, center in clusters.items():
            members = [d for d in dots if np.linalg.norm(d.get_center() - center) < 0.5]
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    if np.random.random() < 0.45:
                        edges.add(
                            Line(
                                members[i].get_center(), members[j].get_center(),
                                color=YELLOW, stroke_width=1, stroke_opacity=0.55,
                            )
                        )
        self.play(LaggedStartMap(Create, edges, lag_ratio=0.04), run_time=0.8)
        self.wait(0.3)

        # Query arrives from above
        q_origin = np.array([0, 0.3, 0])
        q_label = Text('"orders by user last month"',
                       font_size=15, color=YELLOW, weight=BOLD).move_to(q_origin)
        self.play(Write(q_label))
        q_dot = Dot(q_origin, color=YELLOW, radius=0.11)
        self.play(FadeOut(q_label), FadeIn(q_dot))

        target_pt = clusters[TEAL] + np.array([0.05, 0.1, 0])
        path = CurvedArrow(q_origin, target_pt, color=YELLOW, angle=-PI / 4, stroke_width=2)
        self.play(Create(path), q_dot.animate.move_to(target_pt), run_time=1.2)

        ring = Circle(radius=0.6, color=YELLOW, stroke_width=2).move_to(clusters[TEAL])
        self.play(Create(ring))
        nearby = [d for d in dots if np.linalg.norm(d.get_center() - clusters[TEAL]) < 0.55]
        if nearby:
            self.play(*[d.animate.scale(1.6) for d in nearby], run_time=0.4)
            self.play(*[d.animate.scale(1 / 1.6) for d in nearby], run_time=0.4)

        retrieved = Text("tables to query →", font_size=14,
                         color=YELLOW, weight=BOLD).next_to(ring, RIGHT, buff=0.2)
        self.play(FadeIn(retrieved, shift=LEFT * 0.2))
        self.wait(1.0)

        self.play(
            *[FadeOut(m) for m in [
                header, sub, guide, guide_lbl, icons, dots,
                cluster_labels, edges, q_dot, path, ring, retrieved,
            ]],
            run_time=0.7,
        )

    # ---------- LAYER 4 (vertical) ----------
    def layer4_nl2sql(self):
        header = self._header(4, "NL → SQL", ORANGE)
        self.play(FadeIn(header, shift=DOWN * 0.2), run_time=0.5)

        q = Text('"orders per user last month?"',
                 font_size=18, color=YELLOW, weight=BOLD)
        q.next_to(header, DOWN, buff=0.25)
        self.play(Write(q))
        self.wait(0.3)

        # --- Step 1: cluster of retrieved tables (horizontal row) ---
        step1_lbl = Text("retrieve cluster", font_size=12, color=GREY)
        cluster = VGroup(
            self._small_table("users",  BLUE),
            self._small_table("orders", TEAL),
            self._small_table("events", PURPLE),
        ).arrange(RIGHT, buff=0.3)
        for icon in cluster:
            icon.scale(0.85)
        cluster.move_to([0, 1.7, 0])
        step1_lbl.next_to(cluster, UP, buff=0.15)
        self.play(FadeIn(step1_lbl), LaggedStartMap(FadeIn, cluster, lag_ratio=0.2))
        self.wait(0.3)

        # --- Step 2: join graph (compact) ---
        step2_lbl = Text("join graph", font_size=12, color=GREY).move_to([0, 0.7, 0])
        node_u = Circle(radius=0.26, color=BLUE,   stroke_width=3).move_to([-0.8, -0.1, 0])
        node_o = Circle(radius=0.26, color=TEAL,   stroke_width=3).move_to([ 0.8, -0.1, 0])
        node_e = Circle(radius=0.26, color=PURPLE, stroke_width=3).move_to([ 0.0, -1.0, 0])
        lbl_u = Text("u", font_size=13, color=BLUE  ).move_to(node_u)
        lbl_o = Text("o", font_size=13, color=TEAL  ).move_to(node_o)
        lbl_e = Text("e", font_size=13, color=PURPLE).move_to(node_e)

        edge_uo = Line(node_u.get_right(),  node_o.get_left(),  color=YELLOW, stroke_width=4)
        edge_ue = Line(node_u.get_bottom(), node_e.get_top(),   color=YELLOW, stroke_width=2)
        edge_oe = Line(node_o.get_bottom(), node_e.get_top(),   color=GREY,   stroke_width=2)

        edge_lbl_uo = Text("0.94", font_size=10, color=YELLOW).next_to(edge_uo, UP,    buff=0.04)
        edge_lbl_ue = Text("0.71", font_size= 9, color=YELLOW).next_to(edge_ue, LEFT,  buff=0.04)
        edge_lbl_oe = Text("0.12", font_size= 9, color=GREY  ).next_to(edge_oe, RIGHT, buff=0.04)

        self.play(FadeIn(step2_lbl),
                  FadeIn(VGroup(node_u, node_o, node_e, lbl_u, lbl_o, lbl_e)))
        self.play(Create(edge_uo), Create(edge_ue), Create(edge_oe))
        self.play(FadeIn(VGroup(edge_lbl_uo, edge_lbl_ue, edge_lbl_oe)))
        self.wait(0.4)

        # --- Step 3: generated SQL ---
        step3_lbl = Text("generate SQL", font_size=12, color=GREY).move_to([0, -1.55, 0])
        sql = VGroup(
            Text("SELECT u.id, count(*)",     font_size=14, color=LIGHT),
            Text("FROM users u",              font_size=14, color=LIGHT),
            Text("JOIN orders o",             font_size=14, color=LIGHT),
            Text("  ON o.uid = u.id",         font_size=14, color=YELLOW),
            Text("WHERE o.ts > now()-30d",    font_size=14, color=LIGHT),
            Text("GROUP BY u.id;",            font_size=14, color=LIGHT),
        ).arrange(DOWN, buff=0.06, aligned_edge=LEFT)
        sql_box = SurroundingRectangle(sql, color=ORANGE, buff=0.2, stroke_width=2)
        sql_group = VGroup(sql_box, sql).move_to([0, -2.7, 0])
        self.play(FadeIn(step3_lbl), FadeIn(sql_group, shift=UP * 0.2))
        self.wait(0.3)

        conf = Text("user confirms cluster ✓", font_size=13, color=GREEN, weight=BOLD)
        conf.next_to(sql_group, DOWN, buff=0.2)
        self.play(FadeIn(conf, shift=UP * 0.15))
        self.wait(1.5)

        self.play(
            *[FadeOut(m) for m in [
                header, q,
                step1_lbl, cluster,
                step2_lbl, node_u, node_o, node_e, lbl_u, lbl_o, lbl_e,
                edge_uo, edge_ue, edge_oe,
                edge_lbl_uo, edge_lbl_ue, edge_lbl_oe,
                step3_lbl, sql_group, conf,
            ]],
            run_time=0.8,
        )
